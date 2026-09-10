"""Devfolio -- the second `app.ingestion` source agent.

**Discovery mechanism (confirmed by direct inspection of the live public
site, not assumed):**

Devfolio's `/hackathons` listing pages (`/hackathons`, `/hackathons/open`,
`/hackathons/past`, the dynamic route `/hackathons/[hackathonStatus]`) are
a Next.js app built with SSG (`getStaticProps` -- confirmed via `"gsp":true`
in the embedded `__NEXT_DATA__` script tag). `robots.txt` is fully open
(`User-agent: *`, empty `Disallow`), and a plain, unauthenticated GET to any
of those pages returns HTTP 200 with real HTML -- no CAPTCHA/bot-challenge
interstitial was ever served (the site sits behind Cloudflare, but only its
passive CDN/fingerprinting beacons are present, not an active challenge).

The static HTML shell itself does NOT contain the hackathon list -- Next.js
fetches that client-side, after hydration, from its own internal SSG
rehydration route: `GET https://devfolio.co/_next/data/<buildId>/hackathons.json`.
This was found by watching the *real* network traffic a real browser
generates loading `/hackathons/open` (not guessed, not reverse-engineered
from a minified JS bundle) -- it is the literal mechanism Devfolio's own
frontend uses to render its own listing page. `<buildId>` is not a stable
public API version; it changes on every Devfolio deploy. But it doesn't need
to be hardcoded: every server-rendered `/hackathons*` page embeds the
CURRENT buildId in a `<script id="__NEXT_DATA__" type="application/json">`
tag as a plain top-level `"buildId"` key, so `discover()` below is a
self-healing two-step fetch: (1) GET the plain `/hackathons` HTML shell and
parse today's buildId out of it; (2) GET
`https://devfolio.co/_next/data/<that buildId>/hackathons.json` with it.
Confirmed directly: this exact two-request sequence, using a buildId
extracted moments earlier from step 1's own response, returns HTTP 200 with
real, current hackathon data both times.

That JSON response (`pageProps.dehydratedState.queries[0].state.data`) is a
single snapshot containing FOUR already-classified buckets --
`open_hackathons`, `upcoming_hackathons`, `past_hackathons`, and
`featured_hackathons` -- regardless of which `/hackathons/<status>` shell
page's buildId was used to fetch it (confirmed: the bare `/hackathons` shell
and the `/hackathons/open` shell both resolve to the identical
`_next/data/<buildId>/hackathons.json` path). This means Devfolio's OWN
backend already does the open-vs-ended classification -- `discover()` does
not need to guess "is this hackathon still open" from date math; it trusts
`open_hackathons`/`upcoming_hackathons` (still actionable) and discards
`past_hackathons` (Devfolio's own "ended" bucket), the same way
`DevpostHackathonAgent.discover()` trusts Devpost's own `open_state` field
rather than re-deriving it.

One entry in any of those buckets looks like (real, observed shape):

    {
      "uuid": "2061a11b47c74daa90f2760db6c951f6",
      "slug": "webcraft24",
      "name": "WebCraft24",
      "type": "HACKATHON",
      "starts_at": "2026-09-25T01:30:00+00:00",
      "ends_at": "2026-09-26T01:30:00+00:00",
      "is_online": false,
      "devfolio_official": null,
      "rating": 0,
      "timezone": "Asia/Calcutta",
      "participants_count": 900,
      "participants_details": [...],
      "themes": [{"theme": {"name": "No Restrictions"}}],
      "settings": {
        "reg_ends_at": "2026-09-10T18:29:00+00:00",
        "reg_starts_at": "2026-07-30T04:30:00+00:00",
        "review": false,
        "site": null,
        "twitter": null, "facebook": null, "telegram": null,
        "discord": null, "medium": null, "instagram": null, "slack": null,
        "featured_cover_img": null, "featured_cover_img_v2": null,
        "external_apply_url": null
      }
    }

Every field this agent uses comes directly from that literal shape -- see
`extract()`/`normalize()`'s docstrings for exactly which field maps to
which `NormalizedOpportunity` attribute, and `normalize()`'s apply_url
comment (mirrored from this module's own read of the task spec's apply-URL
safety requirement) for why `apply_url` is never invented.

**A second, richer data source (confirmed separately, used only for
enrichment -- see `extract()`):** the listing shape above never carries a
usable image, free-text location, or long-form description --
`settings.featured_cover_img`/`featured_cover_img_v2` are confirmed always
null on every real record sampled, and there is no location/desc field at
all. Each hackathon's OWN page, however, does have all three. Confirmed
directly: `GET https://devfolio.co/_next/data/<buildId>/hackathon3/<slug>/
overview.json?slug=<slug>` -- reachable from the plain `devfolio.co` domain
itself, no per-hackathon subdomain request required, and using the exact
same buildId `discover()`'s own step 1 already extracted (confirmed
identical across the main site and every hackathon subdomain checked, since
they're all served by the one Next.js deployment) -- returns HTTP 200 with

    {"pageProps": {"hackathon": {
        "uuid": "...", "slug": "...", "name": "...",
        "cover_img": "https://assets.devfolio.co/hackathons/<uuid>/assets/cover/<id>.png",
        "location": "NIT Raipur, Great Eastern Road, Amanaka, Raipur, Chhattisgarh, India",
        "city": "Raipur", "country": "India",
        "tagline": "Central India's Largest Hackathon",
        "desc": "**CODEUTSAVA** isn't just an event...(markdown)",
        ...
    }, "moreHackathons": [...], ...}}

`cover_img` matches that page's own `og:image`/`twitter:image` meta tags
exactly, i.e. it is the literal picture Devfolio's own site shows for that
hackathon. There is no separate small square "logo" field on this object
(only on the unrelated `moreHackathons[i].settings.logo` entries, which
describe OTHER, merely-recommended hackathons, not the one being fetched)
-- `cover_img` is what `normalize()` uses for `logo_url`.
"""

import json
import re
from datetime import date, datetime
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

# The plain, server-rendered listing page -- its own HTML embeds the
# current buildId (see module docstring). Any `/hackathons*` shell page
# would work equally well; the bare listing page is used because it's the
# most obviously "canonical" one and imposes no extra assumption about
# which status sub-route stays stable over time.
_HACKATHONS_PAGE_URL = "https://devfolio.co/hackathons"
_NEXT_DATA_URL_TEMPLATE = "https://devfolio.co/_next/data/{build_id}/hackathons.json"

# Per-hackathon enrichment page (see module docstring's "second, richer
# data source" section) -- reused buildId from discover()'s own step 1, no
# extra shell-page fetch needed. Reachable from the plain devfolio.co
# domain (not the hackathon's own subdomain), confirmed directly.
_OVERVIEW_URL_TEMPLATE = (
    "https://devfolio.co/_next/data/{build_id}/hackathon3/{slug}/overview.json?slug={slug}"
)

_NEXT_DATA_SCRIPT_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)

# Longest plain-text excerpt of a hackathon's own (markdown) `desc` field
# kept in `description` -- mirrors the rest of this codebase's existing
# description style (Devpost's `_build_description`, this module's own
# pre-enrichment fallback below): a short blurb, not a full copy of the
# source page's prose.
_DESCRIPTION_MAX_LENGTH = 400

_MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_EMPHASIS_RE = re.compile(r"[*_`#>~]+")
_WHITESPACE_RE = re.compile(r"\s+")

# Devfolio's own classification (the bucket key a hackathon was returned
# under in `hackathons.json`) -- the direct analog of Devpost's
# `open_state`. `past_hackathons` is deliberately NOT in this map: it is
# never fetched into the candidate pool at all (see `discover()`), so it
# never needs a priority tier.
_BUCKET_PRIORITY = {"open_hackathons": 0, "upcoming_hackathons": 1}

# Buckets actually fetched into the candidate pool, in priority order.
# `featured_hackathons` is included (deduped by uuid against the other two
# -- see `discover()`) since a hackathon appearing there is, by definition,
# one Devfolio itself is actively promoting; nothing observed so far
# confirms whether it ever contains a hackathon NOT already present in
# `open_hackathons`/`upcoming_hackathons`, so it is treated as "possibly
# overlapping, never assumed disjoint."
_CANDIDATE_BUCKETS = ("open_hackathons", "upcoming_hackathons", "featured_hackathons")

# Sentinel urgency (days until registration closes) for a candidate whose
# `settings.reg_ends_at` didn't parse -- sorts after every candidate with a
# real number rather than being treated as maximally urgent or crashing.
# Mirrors `devpost.py`'s `_UNKNOWN_URGENCY_DAYS`.
_UNKNOWN_URGENCY_DAYS = 10_000


def _parse_devfolio_datetime(value: str | None) -> datetime | None:
    """Devfolio's own datetimes are plain ISO-8601 with an explicit UTC
    offset (e.g. `"2026-09-10T18:29:00+00:00"`) -- `datetime.fromisoformat`
    handles that shape directly in the Python versions this codebase
    targets. Returns `None` on anything else rather than guessing."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_build_id(html_text: str) -> str | None:
    """Pulls today's Next.js buildId out of a server-rendered `/hackathons*`
    page's own `__NEXT_DATA__` script tag (see module docstring) -- the
    self-healing half of this agent's discovery mechanism. Returns `None`
    (never a guessed/hardcoded id) if the tag is missing or unparseable,
    e.g. because Devfolio's frontend markup changed shape."""
    match = _NEXT_DATA_SCRIPT_RE.search(html_text)
    if not match:
        return None
    try:
        next_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    build_id = next_data.get("buildId")
    return build_id if isinstance(build_id, str) and build_id else None


def _canonical_url(hackathon: dict) -> str | None:
    """Devfolio's own, universally-observed slug -> subdomain template
    (`https://<slug>.devfolio.co/`) -- confirmed across every real record
    inspected, not assumed. This is what `source_url` always is, and what
    `apply_url` falls back to when `settings.external_apply_url` isn't set
    (see `normalize()`)."""
    slug = (hackathon.get("slug") or "").strip()
    if not slug:
        return None
    return f"https://{slug}.devfolio.co/"


def _apply_url(hackathon: dict, *, canonical_url: str | None) -> str | None:
    """Task spec, apply-URL safety, verbatim requirement: never invent or
    construct an apply URL unless the URL structure is explicitly verified
    from source data. Devfolio's `settings.external_apply_url` is an
    EXPLICIT field Devfolio itself uses to say "send applicants somewhere
    other than this event's own page" -- when it's set (truthy), it IS the
    apply destination, literally, with no transformation. When it's
    null/absent (every record observed so far), the fallback is
    `canonical_url`, Devfolio's own slug-subdomain template -- also a
    literal, verified pattern, not an invented one. Nothing here is ever
    templated from an LLM guess or a partial field."""
    settings_block = hackathon.get("settings") or {}
    external = settings_block.get("external_apply_url")
    if isinstance(external, str) and external.strip():
        return external.strip()
    return canonical_url


def _themes_to_tags(hackathon: dict) -> list[str]:
    tags: list[str] = []
    for entry in hackathon.get("themes") or []:
        theme = (entry or {}).get("theme") or {}
        name = theme.get("name")
        if name:
            tags.append(name)
    return tags


def _format_duration(starts_at: datetime | None, ends_at: datetime | None) -> str | None:
    """A short, human-readable event-date range built entirely from the
    literal `starts_at`/`ends_at` timestamps -- deterministic formatting of
    real data, not invented text. `None` when either end is missing/
    unparseable rather than a half-populated string."""
    if starts_at is None or ends_at is None:
        return None
    if starts_at.date() == ends_at.date():
        return starts_at.strftime("%b %d, %Y")
    return f"{starts_at.strftime('%b %d')} - {ends_at.strftime('%b %d, %Y')}"


def _build_description(
    *, is_online: bool, tags: list[str], participants_count: int | None
) -> str | None:
    """Mirrors `devpost.py`'s `_build_description` -- assembled entirely
    out of literal fields Devfolio provided (online/offline status, themes,
    participant count), never invented content."""
    parts: list[str] = ["Online hackathon." if is_online else "In-person hackathon."]
    if tags:
        parts.append(f"Themes: {', '.join(tags)}.")
    if isinstance(participants_count, int) and participants_count > 0:
        parts.append(f"{participants_count} participant(s) so far.")
    return " ".join(parts) or None


def _clean_markdown_to_text(
    markdown_text: str | None, *, max_length: int = _DESCRIPTION_MAX_LENGTH
) -> str | None:
    """Devfolio's own `desc` field is free-text markdown written by each
    hackathon's organizers -- shown here only as a short plain-text
    excerpt, matching this codebase's existing description style (no
    markdown renderer exists anywhere in the frontend, confirmed before
    writing this). Strips image/link syntax down to their visible text,
    strips remaining emphasis/heading/quote markers, collapses whitespace,
    and truncates on a word boundary. Returns `None` for anything that
    isn't a non-empty string, or that cleans down to nothing."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return None
    text = _MARKDOWN_IMAGE_RE.sub(r"\1", markdown_text)
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_EMPHASIS_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return None
    if len(text) > max_length:
        truncated = text[:max_length].rsplit(" ", 1)[0].rstrip(",.;:")
        text = f"{truncated}…" if truncated else f"{text[:max_length].rstrip()}…"
    return text


def _extract_logo_url(enrichment: dict, settings_block: dict) -> str | None:
    """Prefers the enrichment page's real `cover_img` (see module
    docstring) -- the literal picture Devfolio's own site shows for this
    hackathon. Falls back to the listing endpoint's `featured_cover_img*`
    fields (confirmed always null in every record sampled, but kept as a
    defensive fallback rather than deleted, in case Devfolio ever starts
    populating them) when enrichment wasn't fetched or came back empty."""
    for candidate in (
        enrichment.get("cover_img"),
        settings_block.get("featured_cover_img_v2"),
        settings_block.get("featured_cover_img"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_location(enrichment: dict) -> str | None:
    """The listing endpoint has no free-text location field at all; the
    enrichment page's `location` does (e.g. "NIT Raipur, Great Eastern
    Road, Amanaka, Raipur, Chhattisgarh, India"). `None` when enrichment
    wasn't fetched, came back empty, or this is an online-only event with
    nothing Devfolio itself put in that field."""
    location = enrichment.get("location")
    return location.strip() if isinstance(location, str) and location.strip() else None


def _build_enriched_description(
    enrichment: dict, *, is_online: bool, tags: list[str], participants_count: int | None
) -> str | None:
    """Prefers the enrichment page's own `tagline` + a cleaned excerpt of
    its `desc` (real, organizer-written copy) when available. Falls back to
    `_build_description`'s templated summary -- the original behavior --
    when enrichment wasn't fetched or both fields came back empty, so a
    failed/skipped enrichment fetch degrades to the previous, still-useful
    output rather than an empty description."""
    tagline = enrichment.get("tagline")
    tagline = tagline.strip() if isinstance(tagline, str) and tagline.strip() else None
    desc_excerpt = _clean_markdown_to_text(enrichment.get("desc"))

    parts: list[str] = []
    if tagline:
        parts.append(tagline if tagline.endswith((".", "!", "?")) else f"{tagline}.")
    if desc_excerpt:
        parts.append(desc_excerpt)
    if parts:
        return " ".join(parts)

    return _build_description(is_online=is_online, tags=tags, participants_count=participants_count)


def _urgency_days(hackathon: dict, *, today: date) -> int:
    """Days until this hackathon's REGISTRATION deadline
    (`settings.reg_ends_at` -- not `starts_at`/`ends_at`, which are event
    dates, a distinct concept), for ranking only. Mirrors `devpost.py`'s
    `_urgency_days`, minus that agent's free-text fallback parsing (Devfolio
    gives a real ISO timestamp directly, so there's no second, fuzzier
    signal to fall back to)."""
    reg_ends_at = _parse_devfolio_datetime((hackathon.get("settings") or {}).get("reg_ends_at"))
    if reg_ends_at is None:
        return _UNKNOWN_URGENCY_DAYS
    return (reg_ends_at.date() - today).days


def _rank_key(hackathon: dict, *, bucket: str, today: date) -> tuple:
    """Sort key for `select_top_candidates` -- ascending, so the smallest
    tuple wins. Tiers, mirroring the task spec's requested signal order and
    `devpost.py`'s `_rank_key` shape:

    1. Devfolio's own open-before-upcoming classification (`_BUCKET_PRIORITY`).
    2. soonest registration deadline first (`_urgency_days`).
    3. `devfolio_official` as a tie-break bonus, the closest Devfolio-native
       analog to Devpost's own `featured` flag (always `null` in every
       record observed so far, but handled in case it's ever populated).
    4. `slug`, alphabetically, purely for a deterministic final order.
       Devfolio's data does NOT expose a "recently added" signal the way
       Devpost's incrementing numeric `id` doubles as one (a `uuid` carries
       no ordering information) -- this tier is a stable tiebreaker only,
       not a recency proxy, and that gap is called out explicitly in this
       agent's test suite and the implementation's final Limitations note
       rather than silently faked.
    """
    return (
        _BUCKET_PRIORITY.get(bucket, 2),
        _urgency_days(hackathon, today=today),
        0 if hackathon.get("devfolio_official") else 1,
        hackathon.get("slug") or "",
    )


def select_top_candidates(
    candidates: list[tuple[dict, str]], limit: int, *, today: date | None = None
) -> list[tuple[dict, str]]:
    """Pure, I/O-free ranking + cap, mirroring `devpost.py`'s function of
    the same name -- called from `discover()` AFTER both Devfolio requests
    complete but BEFORE any candidate proceeds to `extract()`/`normalize()`.
    Each candidate is a `(hackathon_dict, source_bucket)` pair so
    `_rank_key` can use the bucket a hackathon was actually classified
    under by Devfolio itself."""
    if limit <= 0:
        return []
    today = today or utc_now().date()
    return sorted(
        candidates, key=lambda pair: _rank_key(pair[0], bucket=pair[1], today=today)
    )[:limit]


class DevfolioAgent(BaseOpportunityAgent):
    """`app.ingestion` source agent for Devfolio hackathons.

    Deliberately conservative on request volume against a third-party site
    we don't control, same posture as `DevpostHackathonAgent`:
    `default_config()` tightens the framework-wide rate limit/concurrency
    defaults. Unlike Devpost (whose single discovery call already returns
    everything `normalize()` needs), Devfolio's listing endpoint never
    exposes a usable image/location/description -- so when
    `settings.DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION` is on (the default),
    `extract()` makes ONE additional request per candidate to fetch that
    hackathon's own enrichment page (see module docstring and `extract()`'s
    own docstring). A full run costs 2 + up to `HACKATHON_CANDIDATE_POOL_SIZE`
    HTTP requests, not a fixed 2 -- a deliberate, documented departure from
    this agent's original zero-extra-request design, made because that
    design left `logo_url`/`location`/`description` permanently empty for
    every Devfolio row. Turning the flag off restores the original
    2-requests-total behavior with no code change.
    """

    source = "devfolio"
    default_category = "hackathons"

    @classmethod
    def default_config(cls) -> AgentConfig:
        return AgentConfig.with_defaults(
            source=cls.source,
            default_category=cls.default_category,
            timeout_seconds=settings.DEVFOLIO_REQUEST_TIMEOUT_SECONDS,
            rate_limit=RateLimitConfig(
                requests_per_second=settings.DEVFOLIO_RATE_LIMIT_PER_SECOND, burst=1
            ),
            max_concurrency=1,
            enabled=settings.DEVFOLIO_ENABLED,
            # Same shared knob Devpost uses -- see `settings.HACKATHON_DAILY_LIMIT`'s
            # comment in `app/core/config.py`: "max successful saves per run
            # for this source", not a cross-source shared budget.
            daily_save_limit=settings.HACKATHON_DAILY_LIMIT,
        )

    # ---- discover -----------------------------------------------------------

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        """Two requests, always: (1) the plain `/hackathons` HTML shell, to
        read today's Next.js buildId out of its own `__NEXT_DATA__` tag;
        (2) `_next/data/<that buildId>/hackathons.json`, Devfolio's own
        client-side data route, using it. See the module docstring for why
        this -- and not a guessed/hardcoded "API" -- is the actual, current
        mechanism Devfolio's own frontend relies on.

        Unlike `DevpostHackathonAgent.discover()`, there is no classic
        pagination to loop over (Devfolio's real listing page uses
        `useInfiniteQuery`-style infinite scroll client-side, but the single
        `hackathons.json` snapshot this agent fetches already contains every
        currently-listed hackathon across all of Devfolio's own buckets in
        one response -- confirmed directly, not assumed). So there is
        nothing analogous to `DEVPOST_MAX_DISCOVERY_PAGES` to bound here;
        see this agent's module-level settings comment in
        `app/core/config.py` for why no such setting was added.

        Failure handling: unlike Devpost's "a later page can fail and we
        still keep earlier pages' candidates" case, both requests here are
        REQUIRED to get any candidates at all (step 1 produces zero
        candidates by itself, only a buildId) -- so any failure at either
        step (including a buildId that can't be parsed out of a
        successfully-fetched shell page) raises, letting the pipeline's own
        `retry_async` wrapper (see `IngestionPipeline.run()`) retry the
        whole two-step sequence from scratch.
        """
        discover_logger = ctx.logger.bind(stage="discover")

        await ctx.rate_limiter.acquire()
        try:
            shell_response = await ctx.http_client.get(_HACKATHONS_PAGE_URL)
            shell_response.raise_for_status()
            shell_html = shell_response.text
        except Exception as exc:  # noqa: BLE001 - see docstring: nothing to salvage, must propagate
            discover_logger.warning("Devfolio hackathons page request failed: %s", exc)
            raise

        build_id = _extract_build_id(shell_html)
        if not build_id:
            discover_logger.warning(
                "Could not find a buildId in Devfolio's __NEXT_DATA__ tag -- "
                "the page's markup may have changed."
            )
            raise ValueError("Devfolio discovery: no buildId found in __NEXT_DATA__.")

        await ctx.rate_limiter.acquire()
        try:
            data_url = _NEXT_DATA_URL_TEMPLATE.format(build_id=build_id)
            data_response = await ctx.http_client.get(data_url)
            data_response.raise_for_status()
            payload = data_response.json()
        except Exception as exc:  # noqa: BLE001 - see docstring: nothing to salvage, must propagate
            discover_logger.warning("Devfolio hackathons.json request failed: %s", exc)
            raise

        queries = (payload.get("pageProps") or {}).get("dehydratedState", {}).get("queries") or []
        bucket_data: dict = {}
        for query in queries:
            state_data = (query.get("state") or {}).get("data")
            if isinstance(state_data, dict):
                bucket_data = state_data
                break

        seen_uuids: set[str] = set()
        candidates: list[tuple[dict, str]] = []
        for bucket in _CANDIDATE_BUCKETS:
            for hackathon in bucket_data.get(bucket) or []:
                hackathon_uuid = hackathon.get("uuid")
                if not hackathon_uuid or hackathon_uuid in seen_uuids:
                    continue
                if not hackathon.get("slug") or not hackathon.get("name"):
                    # No usable URL / clearly-invalid record -- skip rather
                    # than let a malformed entry reach extract()/normalize().
                    continue
                seen_uuids.add(hackathon_uuid)
                candidates.append((hackathon, bucket))

        discover_logger.info(
            "Devfolio discovery: %d eligible candidate(s) found before ranking/cap", len(candidates)
        )

        # Same shared "candidate pool" ceiling Devpost uses -- see
        # `settings.HACKATHON_CANDIDATE_POOL_SIZE`'s comment in
        # `app/core/config.py`: it's already documented as a hackathon-
        # CATEGORY-wide safety margin, not a Devpost-specific constant, and
        # Devfolio's own discovery cost profile (2 fixed requests, not
        # N pages) doesn't call for a different ceiling of its own.
        selected = select_top_candidates(candidates, settings.HACKATHON_CANDIDATE_POOL_SIZE)

        self.last_discovery_stats = {"raw_discovered": len(candidates), "selected": len(selected)}

        discover_logger.info(
            "Devfolio discovery: selected %d of %d candidate(s) "
            "(pool_size=%d, daily_save_limit=%d)",
            len(selected), len(candidates),
            settings.HACKATHON_CANDIDATE_POOL_SIZE, settings.HACKATHON_DAILY_LIMIT,
        )

        listings: list[DiscoveredListing] = []
        for hackathon, bucket in selected:
            url = _canonical_url(hackathon)
            if not url:
                continue
            listings.append(
                DiscoveredListing(
                    url=url,
                    source=self.source,
                    # `_build_id` lets extract() fetch this hackathon's own
                    # enrichment page (see module docstring) using the
                    # SAME buildId already extracted above, instead of
                    # spending a second shell-page request per candidate.
                    metadata={**hackathon, "_bucket": bucket, "_build_id": build_id},
                )
            )
        return listings

    # ---- extract --------------------------------------------------------------

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        """`discover()`'s single `hackathons.json` fetch already returned
        this hackathon's full listing record into `listing.metadata` -- that
        part is unchanged. What's new: when `settings.DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION`
        is on, this also fetches that hackathon's own enrichment page (see
        module docstring) to pick up `cover_img`/`location`/`desc`/`tagline`,
        none of which `hackathons.json` exposes.

        This is enrichment, not a required step, so it fails soft: any
        problem (network error, non-200, unexpected JSON shape, missing
        buildId because `discover()` somehow didn't record one) is logged
        and swallowed rather than raised -- `normalize()` below falls back
        to its pre-enrichment behavior (logo_url/location left `None`, the
        old templated description) exactly as if this fetch never
        happened. A flaky enrichment page must never take down an otherwise
        good listing.
        """
        metadata = dict(listing.metadata)
        build_id = metadata.pop("_build_id", None)
        slug = metadata.get("slug")
        enrichment: dict = {}

        if settings.DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION and build_id and slug:
            extract_logger = ctx.logger.bind(stage="extract")
            await ctx.rate_limiter.acquire()
            try:
                overview_url = _OVERVIEW_URL_TEMPLATE.format(build_id=build_id, slug=slug)
                overview_response = await ctx.http_client.get(overview_url)
                if overview_response.status_code == 200:
                    overview_payload = overview_response.json()
                    hackathon_detail = (overview_payload.get("pageProps") or {}).get("hackathon")
                    if isinstance(hackathon_detail, dict):
                        enrichment = {
                            "cover_img": hackathon_detail.get("cover_img"),
                            "location": hackathon_detail.get("location"),
                            "desc": hackathon_detail.get("desc"),
                            "tagline": hackathon_detail.get("tagline"),
                        }
                else:
                    extract_logger.info(
                        "Devfolio enrichment page for %r returned HTTP %d -- "
                        "continuing without logo/location/description.",
                        slug, overview_response.status_code,
                    )
            except Exception as exc:  # noqa: BLE001 - enrichment is best-effort, never fatal
                extract_logger.warning(
                    "Devfolio enrichment page fetch failed for %r -- "
                    "continuing without logo/location/description: %s",
                    slug, exc,
                )

        metadata["_enrichment"] = enrichment
        return RawExtraction(
            url=listing.url,
            source=self.source,
            content_type="json",
            http_status=200,
            raw_content=json.dumps(metadata),
            metadata=metadata,
        )

    # ---- normalize --------------------------------------------------------------

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        data = json.loads(raw.raw_content)

        hackathon_uuid = data.get("uuid")
        title = (data.get("name") or "").strip()
        canonical_url = _canonical_url(data)
        if not hackathon_uuid or not title or not canonical_url:
            # Recorded as a `normalize` IngestionError for this one listing;
            # the pipeline continues with the rest of the run -- see
            # `IngestionPipeline._process_listing`.
            raise ValueError(f"Devfolio listing is missing uuid/name/slug; got: {data!r}")

        settings_block = data.get("settings") or {}
        enrichment = data.get("_enrichment") or {}
        tags = _themes_to_tags(data)
        starts_at = _parse_devfolio_datetime(data.get("starts_at"))
        ends_at = _parse_devfolio_datetime(data.get("ends_at"))
        reg_ends_at = _parse_devfolio_datetime(settings_block.get("reg_ends_at"))
        is_online = bool(data.get("is_online"))

        return NormalizedOpportunity(
            category="hackathons",
            title=title,
            # Devfolio's listing JSON exposes no organizer/host field (the
            # union of every real key observed across dozens of sampled
            # records -- see this module's own inspection notes -- has
            # nothing named organizer/host/organization); left `None`
            # rather than guessed, per the framework-wide "never invent
            # missing values" rule. The enrichment page (see module
            # docstring) doesn't have one either.
            organization=None,
            # Real cover image from the enrichment page when available (see
            # `_extract_logo_url`'s docstring) -- else the listing
            # endpoint's always-null `featured_cover_img*` fields, else
            # `None`. Never invented.
            logo_url=_extract_logo_url(enrichment, settings_block),
            description=_build_enriched_description(
                enrichment,
                is_online=is_online,
                tags=tags,
                participants_count=data.get("participants_count"),
            ),
            # Real free-text location from the enrichment page when
            # available (see `_extract_location`'s docstring) -- `None`
            # when enrichment wasn't fetched/came back empty, same as
            # before this field existed.
            location=_extract_location(enrichment),
            is_remote=is_online,
            # `settings.external_apply_url` when Devfolio itself set it,
            # else the confirmed slug->subdomain template -- see
            # `_apply_url()`'s docstring. Never anything else.
            apply_url=_apply_url(data, canonical_url=canonical_url),
            source_url=canonical_url,
            tags=tags,
            duration=_format_duration(starts_at, ends_at),
            # The REGISTRATION deadline (`settings.reg_ends_at`), not the
            # event's own start/end dates -- see module docstring.
            application_deadline=reg_ends_at.date() if reg_ends_at else None,
            # No `created_at`-equivalent field was found anywhere in
            # Devfolio's listing JSON (see the union-of-keys inspection
            # referenced in the module docstring) -- left `None` rather
            # than substituting `starts_at`/`reg_starts_at`, which are
            # different concepts (event/registration start, not "when this
            # record was posted").
            posted_at=None,
            source=self.source,
            source_id=str(hackathon_uuid),
        )

    # ---- validate --------------------------------------------------------------

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        issues = list(basic_field_checks(opportunity))

        if opportunity.category != "hackathons":
            issues.append(
                ValidationIssue(
                    field="category",
                    message="DevfolioAgent must only ever produce category='hackathons'.",
                    severity="error",
                )
            )

        if opportunity.source != "devfolio":
            issues.append(
                ValidationIssue(
                    field="source",
                    message=(
                        f"DevfolioAgent must only ever produce source='devfolio', "
                        f"got {opportunity.source!r}."
                    ),
                    severity="error",
                )
            )

        # `source_url` is ALWAYS this agent's own slug->subdomain
        # construction (see `_canonical_url()`) -- never influenced by an
        # externally-supplied field -- so, unlike `apply_url` (which
        # Devfolio's own `external_apply_url` can legitimately point off
        # Devfolio entirely), it is safe and meaningful to defensively
        # assert it is still a devfolio.co URL. This is the Devfolio
        # equivalent of `devpost.py`'s "apply_url must be a devpost.com
        # domain" check, applied to the field that actually carries that
        # invariant here.
        if opportunity.source_url:
            host = urlparse(opportunity.source_url).netloc.lower()
            if host != "devfolio.co" and not host.endswith(".devfolio.co"):
                issues.append(
                    ValidationIssue(
                        field="source_url",
                        message=f"source_url host {host!r} is not a devfolio.co domain.",
                        severity="error",
                    )
                )

        # apply_url itself is intentionally NOT restricted to devfolio.co --
        # Devfolio's own `external_apply_url` field can legitimately point
        # anywhere off-site (see `_apply_url()`'s docstring); the anti-
        # fabrication guarantee here is that `normalize()` only ever copies
        # it verbatim from that literal field or falls back to
        # `source_url`, never constructs a third value. `basic_field_checks`
        # above already rejects anything that isn't a well-formed http(s)
        # URL.

        if not opportunity.source_id:
            issues.append(
                ValidationIssue(
                    field="source_id",
                    message="Missing Devfolio uuid (source_id) -- required for de-duplication.",
                    severity="error",
                )
            )

        return to_validation_result(issues)


agent_registry.register(DevfolioAgent)

# Every 3 days (not daily, unlike Devpost -- an explicit, deliberate choice
# for this source only, made when the extra per-candidate enrichment fetch
# was added to extract() -- see this module's own module docstring and
# `settings.DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION`'s comment in
# app/core/config.py). `interval` (not `cron`) so "due" means "at least 3
# days since this source's own last run", not "matches a specific
# clock-time" -- exactly what "every 3 days" should mean.
#
# IMPORTANT operational note: `JobRegistry._last_run_at` (see
# app/ingestion/jobs/registry.py) is an in-memory dict on a process-wide
# singleton -- it is NOT persisted anywhere, so it resets to "never run"
# every time the backend process restarts (a redeploy, a crash, or --
# notably -- an ephemeral/free hosting tier's web service spinning down
# after inactivity and cold-starting on the next request). That makes
# `GET /ingestion/due` / `POST /ingestion/run-due` (see
# app/api/v1/routes/ingestion.py) reliable ONLY on a host that keeps this
# process running continuously between polls. Until/unless this app is on
# a host like that, the actual every-3-days cadence in production is
# enforced by an EXTERNAL scheduler (e.g. Supabase's pg_cron + pg_net, or
# any other cron) calling `POST /ingestion/run/devfolio` directly on its
# own 3-day cron schedule -- that route always runs on demand regardless
# of this registration (see `run_source()` in that same file). This
# `ScheduleConfig` is registered anyway so `GET /ingestion/due` keeps
# reporting accurate operator-facing "is Devfolio due" info even though it
# isn't (yet) what's actually driving execution in production, and so a
# future move to a persistently-running host + `/ingestion/run-due` works
# correctly with zero further code changes.
job_registry.set("devfolio", ScheduleConfig.every(3 * 24 * 60 * 60))
