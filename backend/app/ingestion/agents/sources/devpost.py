"""Devpost -- the first real `app.ingestion` source agent.

Discovery hits `https://devpost.com/api/hackathons`, the same JSON endpoint
devpost.com/hackathons' own listing page calls client-side to render and
filter its hackathon cards (confirmed by inspecting that page's own network
traffic, not assumed) -- publicly reachable, no API key, no auth, no
private/undocumented parameter. It returns a `hackathons` array and a
`meta` object (`{"total_count": ..., "per_page": ..., "fuzzy": ...}`); one
hackathon entry looks like:

    {
      "id": 31050,
      "title": "Expo 26 Hackathon",
      "displayed_location": {"icon": "map-marker-alt", "location": "The Venue Hotel Jeddah"},
      "open_state": "open",
      "thumbnail_url": "//d112y698adiu2z.cloudfront.net/photos/...",
      "url": "https://expo-26-hackathon.devpost.com/",
      "time_left_to_submission": "9 days left",
      "submission_period_dates": "Sep 09 - 18, 2026",
      "themes": [{"id": 16, "name": "Health"}],
      "prize_amount": "$<span data-currency-value>0</span>",
      "registrations_count": 2,
      "featured": false,
      "organization_name": "abbvie",
      "winners_announced": false,
      "invite_only": true,
      ...
    }

That single response already carries everything this agent needs -- title,
organizer, dates, prize, themes, thumbnail, open/closed state, and the
hackathon's own URL. See `extract()`'s docstring for why that means this
agent deliberately does NOT fetch a second, per-hackathon page.
"""

import html
import json
import re
from datetime import date
from urllib.parse import urlparse

from app.core.config import settings
from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import agent_registry
from app.ingestion.jobs.registry import job_registry
from app.ingestion.jobs.schedule import ScheduleConfig
from app.ingestion.models.config import AgentConfig, RateLimitConfig
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.validation import ValidationIssue, ValidationResult
from app.ingestion.utils.validation import basic_field_checks, to_validation_result
from app.utils.time import utc_now

_API_URL = "https://devpost.com/api/hackathons"

# open_state values worth ranking (see `_rank_key`) -- anything else
# (unrecognized/missing) sorts last within its own tier rather than
# crashing on an unexpected value.
_OPEN_STATE_PRIORITY = {"open": 0, "upcoming": 1}

# Matches Devpost's `submission_period_dates` free text in both shapes it's
# known to use: same month ("Sep 09 - 18, 2026") and cross-month
# ("Sep 28 - Oct 05, 2026"). Both anchor on the RANGE END, which is what
# `application_deadline` (the column's only date field -- see
# `supabase/schema/002_opportunities.sql`) is used for elsewhere in this
# codebase: the last day something is actionable, not when it started.
_SAME_MONTH_RANGE_RE = re.compile(
    r"^(?P<month>[A-Za-z]{3})\s+\d{1,2}\s*-\s*(?P<day>\d{1,2}),\s*(?P<year>\d{4})$"
)
_CROSS_MONTH_RANGE_RE = re.compile(
    r"^[A-Za-z]{3}\s+\d{1,2}\s*-\s*(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})$"
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_DAYS_LEFT_RE = re.compile(r"(\d+)\s*day", re.IGNORECASE)
_HOURS_LEFT_RE = re.compile(r"(\d+)\s*hour", re.IGNORECASE)

# Sentinel urgency (in "days until deadline") for a candidate whose deadline
# couldn't be parsed from either `submission_period_dates` or
# `time_left_to_submission` -- sorts after every candidate with a real
# number, rather than being treated as maximally urgent (0) or crashing.
_UNKNOWN_URGENCY_DAYS = 10_000


def _parse_deadline(date_range_text: str | None) -> date | None:
    """Parses Devpost's `submission_period_dates` free text into the END
    date of the range. Returns `None` on anything that doesn't match one of
    the two known shapes exactly -- never guesses a year or a day, per the
    framework-wide rule (see `app/ingestion/README.md` and this agent's
    module docstring) that an unparseable field is left null, not
    hallucinated.
    """
    if not date_range_text:
        return None

    text = date_range_text.strip()
    match = _CROSS_MONTH_RANGE_RE.match(text) or _SAME_MONTH_RANGE_RE.match(text)
    if not match:
        return None

    try:
        from datetime import datetime as _dt

        parsed = _dt.strptime(
            f"{match.group('month')} {match.group('day')} {match.group('year')}", "%b %d %Y"
        )
    except ValueError:
        return None
    return parsed.date()


def _absolute_url(url: str | None) -> str | None:
    """Devpost's `thumbnail_url` is protocol-relative (`//cdn.../photo.png`)
    -- valid in an `<img src>` but not a well-formed absolute URL on its
    own, which is what `basic_field_checks`' `_looks_like_url` (and any
    normal URL-handling code) expects. Prefixing `https:` is a mechanical
    normalization of Devpost's own literal value, not an invented one."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    return url or None


def _looks_remote(displayed_location: dict) -> bool:
    """`displayed_location` is Devpost's own {icon, location} pair. A
    "globe" icon is Devpost's own signal for an online hackathon (as
    opposed to `map-marker-alt` for a physical venue, e.g. the Jeddah
    example in the module docstring); the location text itself saying
    "online"/"virtual"/"anywhere" is a second, independent signal from the
    same source data. Either being true is enough -- this is a
    normalization heuristic over literal source fields, not a guess."""
    icon = (displayed_location.get("icon") or "").strip().lower()
    if icon in {"globe", "globe-americas", "wifi"}:
        return True
    location_text = (displayed_location.get("location") or "").strip().lower()
    return any(keyword in location_text for keyword in ("online", "virtual", "anywhere"))


def _clean_prize_text(raw_prize_amount: str | None) -> str | None:
    """`prize_amount` arrives as an HTML fragment (Devpost wraps the number
    in a `<span data-currency-value>` for their own client-side currency
    formatting, e.g. `"$<span data-currency-value>0</span>"`). Strips the
    markup and unescapes entities to get plain text (`"$0"`) -- the literal
    source value, just de-HTMLed, not reworded."""
    if not raw_prize_amount:
        return None
    cleaned = html.unescape(_HTML_TAG_RE.sub("", raw_prize_amount)).strip()
    return cleaned or None


def _build_description(
    *, organization: str | None, tags: list[str], prize_text: str | None, invite_only: bool
) -> str | None:
    """Assembles a short, factual description entirely out of literal
    source fields (organizer, themes, prize, invite-only status) --
    templating existing data into readable prose, not inventing content
    Devpost didn't provide. Returns `None` (not an empty string) when none
    of those fields were present, so `basic_field_checks` can correctly flag
    "no apply_url and no description" if that ever happens (it won't in
    practice here, since `apply_url` is always set from the same listing --
    see `normalize()`)."""
    parts: list[str] = []
    if organization:
        parts.append(f"Hosted by {organization}.")
    if tags:
        parts.append(f"Themes: {', '.join(tags)}.")
    if prize_text and prize_text not in ("$0", "$", "0"):
        parts.append(f"Prize pool: {prize_text}.")
    if invite_only:
        parts.append("Invite-only.")
    return " ".join(parts) or None


def _urgency_days(hackathon: dict, *, today: date) -> int:
    """How many days until this hackathon's submission deadline, for
    ranking (see `_rank_key`) -- NOT written back onto the
    `NormalizedOpportunity` (that's `_parse_deadline`'s job, used directly
    in `normalize()`). Prefers the precise parsed deadline; falls back to a
    rough day/hour count scraped from Devpost's own `time_left_to_submission`
    ("9 days left") when the date range itself didn't parse; falls back
    further to a large sentinel so a candidate with no usable urgency signal
    at all sorts after every candidate that has one, rather than being
    mistaken for either "extremely urgent" or "furthest away"."""
    deadline = _parse_deadline(hackathon.get("submission_period_dates"))
    if deadline is not None:
        return (deadline - today).days

    time_left = hackathon.get("time_left_to_submission") or ""
    days_match = _DAYS_LEFT_RE.search(time_left)
    if days_match:
        return int(days_match.group(1))
    hours_match = _HOURS_LEFT_RE.search(time_left)
    if hours_match:
        return 0  # less than a day left -- more urgent than any whole-day count

    return _UNKNOWN_URGENCY_DAYS


def _rank_key(hackathon: dict, *, today: date) -> tuple:
    """Sort key for `select_top_candidates` -- ascending, so the smallest
    tuple wins. Tiers, in the order the task spec asked for:

    1. open registration before upcoming (open_state) -- an "open" listing
       is actionable today, an "upcoming" one isn't yet.
    2. soonest deadline / start first (urgency, in days -- see
       `_urgency_days`; also covers "upcoming start date" since an unparsed
       deadline falls back to Devpost's own "days left" framing).
    3. Devpost's own `featured` flag as a tie-break bonus.
    4. recency (higher Devpost id = created more recently), as the final
       tiebreaker.
    """
    return (
        _OPEN_STATE_PRIORITY.get(hackathon.get("open_state"), 2),
        _urgency_days(hackathon, today=today),
        0 if hackathon.get("featured") else 1,
        -(hackathon.get("id") or 0),
    )


def select_top_candidates(
    hackathons: list[dict], limit: int, *, today: date | None = None
) -> list[dict]:
    """Pure, I/O-free ranking + cap -- called from `discover()` AFTER
    Devpost's listing pages are fetched but BEFORE any candidate proceeds to
    `extract()`/`normalize()`, per the task's "cap after discovery, before
    expensive work" requirement. Kept as a standalone function (not a
    method) so it's directly unit-testable with plain dicts and no
    `AgentContext`/HTTP mocking required.
    """
    if limit <= 0:
        return []
    today = today or utc_now().date()
    return sorted(hackathons, key=lambda h: _rank_key(h, today=today))[:limit]


class DevpostHackathonAgent(BaseOpportunityAgent):
    """`app.ingestion` source agent for Devpost hackathons.

    Deliberately conservative on request volume against a third-party site
    we don't control: `default_config()` below overrides the framework-wide
    rate limit/concurrency defaults to be tighter than
    `INGESTION_DEFAULT_*`, and `extract()` makes NO additional per-listing
    request at all (see its docstring) -- a full run costs at most
    `DEVPOST_MAX_DISCOVERY_PAGES` requests total, not
    `DEVPOST_MAX_DISCOVERY_PAGES + HACKATHON_CANDIDATE_POOL_SIZE`.
    """

    source = "devpost"
    default_category = "hackathons"

    @classmethod
    def default_config(cls) -> AgentConfig:
        return AgentConfig.with_defaults(
            source=cls.source,
            default_category=cls.default_category,
            timeout_seconds=settings.DEVPOST_REQUEST_TIMEOUT_SECONDS,
            rate_limit=RateLimitConfig(
                requests_per_second=settings.DEVPOST_RATE_LIMIT_PER_SECOND, burst=1
            ),
            max_concurrency=1,
            enabled=settings.DEVPOST_ENABLED,
            # See `AgentConfig.daily_save_limit`'s docstring: this is what
            # tells a persister (the ingestion route) to stop once this many
            # hackathons have actually been created/updated, rather than
            # attempting to save every candidate `discover()` selected.
            daily_save_limit=settings.HACKATHON_DAILY_LIMIT,
        )

    # ---- discover -----------------------------------------------------------

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        """Paginates `GET /api/hackathons?status[]=open&order_by=recently-added`,
        filters out listings that aren't real general-audience opportunities
        (`invite_only`, already-decided/`ended` ones), ranks what's left
        (`select_top_candidates`), and caps to
        `settings.HACKATHON_CANDIDATE_POOL_SIZE` (a safety margin ABOVE the
        `HACKATHON_DAILY_LIMIT` opportunities a run actually aims to save --
        see `app/core/config.py`'s comment on both settings and
        `OpportunityService.save_batch()`'s `max_success_count` parameter for
        where the real 20/day stop condition is enforced) -- all before
        returning, so `extract()`/`normalize()`/`validate()` only ever run on
        the (at most) `HACKATHON_CANDIDATE_POOL_SIZE` candidates this run
        actually keeps.

        Failure handling: if the very FIRST page request fails, this raises
        (propagates) so the pipeline's own retry (`IngestionPipeline.run()`
        wraps the whole `discover()` call in `retry_async`) can retry the
        entire call from scratch -- there is nothing to salvage from zero
        successful pages. If a LATER page fails after at least one page
        already succeeded, this logs and stops paginating rather than
        raising: the candidates already gathered are real and worth keeping,
        and re-running discover() from page 1 again (which the outer retry
        would do on a raise) is wasted work that would likely hit the same
        failing page again anyway.
        """
        collected: list[dict] = []
        seen_ids: set[int] = set()
        total_count: int | None = None
        max_pages = max(1, settings.DEVPOST_MAX_DISCOVERY_PAGES)
        discover_logger = ctx.logger.bind(stage="discover")

        page = 1
        while page <= max_pages:
            await ctx.rate_limiter.acquire()
            try:
                response = await ctx.http_client.get(
                    _API_URL,
                    params={"status[]": "open", "order_by": "recently-added", "page": page},
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 - see docstring: page 1 re-raises, later pages degrade
                if page == 1:
                    discover_logger.warning("Devpost page 1 request failed: %s", exc)
                    raise
                discover_logger.info(
                    "Devpost pagination stopped early at page %d after %d page(s) succeeded: %s",
                    page, page - 1, exc,
                )
                break

            hackathons = payload.get("hackathons") or []
            if not hackathons:
                break

            for hackathon in hackathons:
                hackathon_id = hackathon.get("id")
                if hackathon_id is None or hackathon_id in seen_ids:
                    continue
                seen_ids.add(hackathon_id)

                if hackathon.get("invite_only"):
                    continue
                if hackathon.get("winners_announced") or hackathon.get("open_state") == "ended":
                    continue
                if not hackathon.get("url"):
                    continue

                collected.append(hackathon)

            meta = payload.get("meta") or {}
            if isinstance(meta.get("total_count"), int):
                total_count = meta["total_count"]
            if total_count is not None and len(seen_ids) >= total_count:
                break

            page += 1

        discover_logger.info(
            "Devpost discovery: %d eligible candidate(s) found before ranking/cap", len(collected)
        )

        # Select up to the CANDIDATE POOL size here (a safety margin above
        # HACKATHON_DAILY_LIMIT), not the daily save limit itself -- the
        # actual "stop at HACKATHON_DAILY_LIMIT saved" decision happens
        # later, in `OpportunityService.save_batch()`/`preview_batch()`,
        # once we know which of these ranked candidates are actually valid.
        # Selecting only `HACKATHON_DAILY_LIMIT` here would mean a handful
        # of invalid/duplicate candidates earlier in the ranking silently
        # reduces how many real hackathons end up saved below 20 -- see
        # `settings.HACKATHON_DAILY_LIMIT`'s comment in `app/core/config.py`.
        selected = select_top_candidates(collected, settings.HACKATHON_CANDIDATE_POOL_SIZE)

        # Reported via `self.last_discovery_stats` so `AgentRunResult.raw_candidate_count`
        # can distinguish "candidates Devpost actually had" from "candidates
        # selected for processing" -- see `BaseOpportunityAgent.last_discovery_stats`.
        self.last_discovery_stats = {"raw_discovered": len(collected), "selected": len(selected)}

        discover_logger.info(
            "Devpost discovery: selected %d of %d candidate(s) (pool_size=%d, daily_save_limit=%d)",
            len(selected), len(collected),
            settings.HACKATHON_CANDIDATE_POOL_SIZE, settings.HACKATHON_DAILY_LIMIT,
        )

        return [
            DiscoveredListing(url=hackathon["url"], source=self.source, metadata=hackathon)
            for hackathon in selected
        ]

    # ---- extract --------------------------------------------------------------

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        """No second network request. `discover()`'s single `/api/hackathons`
        call already returned this hackathon's full structured data (see the
        module docstring) into `listing.metadata` -- fetching each
        hackathon's own `*.devpost.com` microsite here would add up to
        `HACKATHON_CANDIDATE_POOL_SIZE` more requests against dozens of
        different, independently-operated pages for no field `normalize()` below
        actually needs, which is exactly the "unnecessary/aggressive
        scraping" the framework asks every agent to avoid. `extract()` here
        is a pure repackaging step: `listing.metadata` becomes
        `RawExtraction.raw_content`, JSON-encoded so `normalize()` parses it
        the same way regardless of how it got there.
        """
        return RawExtraction(
            url=listing.url,
            source=self.source,
            content_type="json",
            http_status=200,
            raw_content=json.dumps(listing.metadata),
            metadata=listing.metadata,
        )

    # ---- normalize --------------------------------------------------------------

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        data = json.loads(raw.raw_content)

        hackathon_id = data.get("id")
        title = (data.get("title") or "").strip()
        url = data.get("url") or raw.url
        if hackathon_id is None or not title or not url:
            # Pipeline records this as a `normalize` IngestionError for this
            # one listing and continues with the rest of the run -- see
            # `IngestionPipeline._process_listing`.
            raise ValueError(f"Devpost listing is missing id/title/url; got: {data!r}")

        displayed_location = data.get("displayed_location") or {}
        tags = [theme.get("name", "") for theme in (data.get("themes") or []) if theme.get("name")]
        duration_text = data.get("submission_period_dates") or None
        prize_text = _clean_prize_text(data.get("prize_amount"))

        return NormalizedOpportunity(
            category="hackathons",
            title=title,
            organization=data.get("organization_name") or None,
            logo_url=_absolute_url(data.get("thumbnail_url")),
            description=_build_description(
                organization=data.get("organization_name") or None,
                tags=tags,
                prize_text=prize_text,
                invite_only=bool(data.get("invite_only")),
            ),
            location=displayed_location.get("location") or None,
            is_remote=_looks_remote(displayed_location),
            # `url` is Devpost's own field for this hackathon's page -- the
            # one place a real person goes to register/apply/submit. Never
            # synthesized: if Devpost didn't give us a URL, `discover()`
            # already skipped this listing (see its `if not hackathon.get("url")`
            # filter) rather than let one reach here.
            apply_url=url,
            source_url=url,
            tags=tags,
            duration=duration_text,
            application_deadline=_parse_deadline(duration_text),
            source=self.source,
            source_id=str(hackathon_id),
        )

    # ---- validate --------------------------------------------------------------

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        issues = list(basic_field_checks(opportunity))

        if opportunity.category != "hackathons":
            issues.append(
                ValidationIssue(
                    field="category",
                    message="DevpostHackathonAgent must only ever produce category='hackathons'.",
                    severity="error",
                )
            )

        if not opportunity.source_id.isdigit():
            issues.append(
                ValidationIssue(
                    field="source_id",
                    message=(
                        f"Devpost source_id {opportunity.source_id!r} is not the numeric "
                        "hackathon id Devpost's API returns."
                    ),
                    severity="warning",
                )
            )

        # Defense-in-depth against a parsing bug ever substituting a wrong
        # URL: this agent must never accept an apply_url that isn't
        # literally a devpost.com page, mirroring the framework-wide rule
        # ("never allow an LLM or parser to invent an apply_url") applied
        # specifically to what THIS source is allowed to point at.
        if opportunity.apply_url:
            host = urlparse(opportunity.apply_url).netloc.lower()
            if host != "devpost.com" and not host.endswith(".devpost.com"):
                issues.append(
                    ValidationIssue(
                        field="apply_url",
                        message=f"apply_url host {host!r} is not a devpost.com domain.",
                        severity="error",
                    )
                )

        return to_validation_result(issues)


agent_registry.register(DevpostHackathonAgent)

# Daily at 06:00 UTC -- once a day, off-peak, well ahead of any reasonable
# timezone's morning. Purely a default: re-registering with a different
# `ScheduleConfig` (job_registry.set("devpost", ...)) at any point changes
# it, and nothing about DevpostHackathonAgent itself depends on this exact
# time. Registering it here (not in api/v1/routes/ingestion.py) matches the
# framework's own stated pattern (see app/ingestion/README.md's "Adding a
# new source" -- schedule registration lives beside the agent that owns it.
job_registry.set("devpost", ScheduleConfig.cron("0 6 * * *"))
