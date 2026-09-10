"""Exercises `DevfolioAgent` end-to-end with a fake HTTP client -- no real
network call is ever made (see `FakeHttpClient` below); nothing here
depends on devfolio.co being reachable or returning any particular data.

Sample payloads mirror the REAL shape of Devfolio's own two-step discovery
mechanism (a `__NEXT_DATA__`-embedded buildId, then
`_next/data/<buildId>/hackathons.json`) -- verified by inspecting that
mechanism directly (a real browser's own network traffic loading Devfolio's
public `/hackathons` pages), not guessed. See
`app/ingestion/agents/sources/devfolio.py`'s module docstring for the full
real sample this file's fixtures are drawn from.

Also covers `extract()`'s optional per-candidate enrichment fetch (the
per-hackathon `overview.json` page -- see that module docstring's "second,
richer data source" section) that populates `logo_url`/`location`/
`description` with real Devfolio data instead of leaving them empty/
templated. `FakeHttpClient` routes that request separately from the
`hackathons.json` discovery request (both URLs contain `/_next/data/`, so
they're told apart by the more specific `overview.json` substring) -- see
its own docstring.
"""

import json
from datetime import date

import pytest

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.ingestion.agents.base import AgentContext
from app.ingestion.agents.sources.devfolio import (
    DevfolioAgent,
    _apply_url,
    _build_description,
    _build_enriched_description,
    _canonical_url,
    _clean_markdown_to_text,
    _extract_build_id,
    _extract_location,
    _extract_logo_url,
    _format_duration,
    _parse_devfolio_datetime,
    _themes_to_tags,
    select_top_candidates,
)
from app.ingestion.models.config import AgentConfig, RetryConfig
from app.ingestion.models.discovery import RawExtraction
from app.ingestion.services.opportunity_service import OpportunityService
from app.ingestion.utils.logging import get_agent_logger
from app.ingestion.utils.rate_limit import NullRateLimiter

# ---------------------------------------------------------------------------
# Fakes -- no real network, no real Supabase, matching every other test in
# this suite (see tests/test_devpost_agent.py, tests/test_opportunity_service.py).
# ---------------------------------------------------------------------------

_BUILD_ID = "test-build-id-abc123"


class FakeResponse:
    def __init__(
        self, *, text: str | None = None, json_data: dict | None = None, status_code: int = 200
    ):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"simulated HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json_data


class FakeHttpClient:
    """Dispatches by URL, not by call order: any URL containing
    `overview.json` (the per-candidate enrichment page -- see
    `extract()`) gets `overview_response`; any OTHER URL containing
    `/_next/data/` (the `hackathons.json` discovery fetch) gets
    `data_response`; everything else (the plain `/hackathons` shell page)
    gets `shell_response`. This mirrors `discover()`'s own fixed
    two-request shape plus `extract()`'s optional third, per-candidate
    request -- there is no pagination to route on here, unlike Devpost's
    fake client.

    `overview_response` defaults to a bare HTTP 404 when not given, so
    every test that doesn't care about enrichment (most of this file) can
    keep using `_client_for()`/`FakeHttpClient(shell_response=...,
    data_response=...)` unchanged: `extract()` sees a non-200, logs it, and
    normalize() falls back to its pre-enrichment behavior exactly as
    before this feature existed.
    """

    def __init__(
        self,
        *,
        shell_response: FakeResponse | None = None,
        data_response: FakeResponse | None = None,
        overview_response: FakeResponse | None = None,
        fail_shell: bool = False,
        fail_data: bool = False,
        fail_overview: bool = False,
    ):
        self.shell_response = shell_response
        self.data_response = data_response
        self.overview_response = overview_response or FakeResponse(status_code=404)
        self.fail_shell = fail_shell
        self.fail_data = fail_data
        self.fail_overview = fail_overview
        self.calls: list[str] = []

    async def get(self, url: str, params: dict | None = None) -> FakeResponse:
        self.calls.append(url)
        if "overview.json" in url:
            if self.fail_overview:
                raise RuntimeError("simulated network failure fetching overview.json")
            return self.overview_response
        if "/_next/data/" in url:
            if self.fail_data:
                raise RuntimeError("simulated network failure fetching hackathons.json")
            return self.data_response
        if self.fail_shell:
            raise RuntimeError("simulated network failure fetching the hackathons page")
        return self.shell_response


class FakeOpportunityRepository:
    """Same duck-typed fake shape as tests/test_devpost_agent.py's, kept
    self-contained here rather than imported so this file has no
    cross-file test coupling."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._next_id = 1

    def get_by_source_and_source_id(self, source: str, source_id: str) -> dict | None:
        for row in self.rows.values():
            if row.get("source") == source and row.get("source_id") == source_id:
                return row
        return None

    def get_by_fingerprint(self, fingerprint: str) -> dict | None:
        for row in self.rows.values():
            if row.get("fingerprint") == fingerprint:
                return row
        return None

    def insert(self, row: dict) -> dict:
        row_id = f"row-{self._next_id}"
        self._next_id += 1
        stored = {"id": row_id, "enrichment_status": "pending", **row}
        self.rows[row_id] = stored
        return stored

    def update(self, opportunity_id: str, row: dict) -> dict:
        existing = self.rows.get(opportunity_id)
        if existing is None:
            raise ExternalServiceError(f"no such row {opportunity_id}")
        existing.update(row)
        return existing

    def set_enrichment_status(self, opportunity_id, *, status, queued_at=None):
        existing = self.rows[opportunity_id]
        existing["enrichment_status"] = status
        return existing

    def count_pending_enrichment(self) -> int:
        return sum(1 for row in self.rows.values() if row.get("enrichment_status") != "completed")


class FakeQueue:
    def __init__(self):
        self.enqueued: list[tuple[str, dict]] = []

    async def enqueue(self, task: str, /, **payload) -> str:
        self.enqueued.append((task, payload))
        return f"fake-{len(self.enqueued)}"


def _shell_html(build_id: str | None = _BUILD_ID) -> str:
    """A minimal but realistic `/hackathons` page shell -- just enough
    `__NEXT_DATA__` structure for `_extract_build_id` to find the buildId,
    matching the real page's confirmed shape (see this module's docstring
    and `devfolio.py`'s own)."""
    next_data = {
        "props": {"pageProps": {}},
        "page": "/hackathons",
        "query": {},
        "buildId": build_id,
        "gsp": True,
    }
    if build_id is None:
        del next_data["buildId"]
    return (
        "<html><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>'
        "</body></html>"
    )


def _client_for(
    hackathons: list[dict],
    *,
    build_id: str = _BUILD_ID,
    overview_response: FakeResponse | None = None,
) -> "FakeHttpClient":
    """Convenience for the common case in this file: a fake client whose
    shell page reports `build_id` and whose data response's
    `open_hackathons` bucket is exactly `hackathons`. Most tests only need
    one bucket populated -- this cuts the two-`FakeResponse` boilerplate
    that would otherwise repeat on nearly every test. `overview_response`
    is passed straight through to `FakeHttpClient` for the (few) tests that
    care what `extract()`'s enrichment fetch returns -- every other test
    gets that endpoint's default 404 (see `FakeHttpClient`'s docstring)."""
    return FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html(build_id)),
        data_response=_data_response(open_=hackathons),
        overview_response=overview_response,
    )


def _overview_json(
    *, cover_img: str | None = None, location: str | None = None, tagline: str | None = None,
    desc: str | None = None,
) -> FakeResponse:
    """A minimal but realistic per-candidate enrichment page response --
    `_next/data/<buildId>/hackathon3/<slug>/overview.json`'s real shape
    (see `devfolio.py`'s module docstring), trimmed to just the fields
    `extract()` reads out of `pageProps.hackathon`."""
    return FakeResponse(
        json_data={
            "pageProps": {
                "hackathon": {
                    "cover_img": cover_img,
                    "location": location,
                    "tagline": tagline,
                    "desc": desc,
                },
                "moreHackathons": [],
            }
        }
    )


def _data_response(*, open_=None, upcoming=None, past=None, featured=None) -> FakeResponse:
    payload = {
        "pageProps": {
            "dehydratedState": {
                "queries": [
                    {
                        "queryKey": "fetchAllHackathonTypes",
                        "state": {
                            "data": {
                                "open_hackathons": open_ or [],
                                "upcoming_hackathons": upcoming or [],
                                "past_hackathons": past or [],
                                "featured_hackathons": featured or [],
                            }
                        },
                    }
                ]
            }
        }
    }
    return FakeResponse(json_data=payload)


def _hackathon(**overrides) -> dict:
    settings_overrides = overrides.pop("settings", None)
    base = {
        "uuid": "2061a11b47c74daa90f2760db6c951f6",
        "slug": "webcraft24",
        "name": "WebCraft24",
        "type": "HACKATHON",
        "starts_at": "2026-09-25T01:30:00+00:00",
        "ends_at": "2026-09-26T01:30:00+00:00",
        "is_online": False,
        "devfolio_official": None,
        "rating": 0,
        "timezone": "Asia/Calcutta",
        "participants_count": 900,
        "participants_details": [],
        "themes": [{"theme": {"name": "AI"}}],
        "settings": {
            "reg_ends_at": "2026-09-20T18:29:00+00:00",
            "reg_starts_at": "2026-07-30T04:30:00+00:00",
            "review": False,
            "site": None,
            "twitter": None,
            "facebook": None,
            "telegram": None,
            "discord": None,
            "medium": None,
            "instagram": None,
            "slack": None,
            "featured_cover_img": None,
            "featured_cover_img_v2": None,
            "external_apply_url": None,
        },
    }
    base.update(overrides)
    if settings_overrides:
        base["settings"] = {**base["settings"], **settings_overrides}
    return base


def _distinct_hackathons(n: int, *, start: int = 0, **overrides) -> list[dict]:
    """`n` hackathons that are genuinely distinct by fingerprint (title,
    organization, apply_url) -- same purpose as `test_devpost_agent.py`'s
    helper of the same name: `_hackathon(uuid=...)` alone with a shared
    slug/name would make every one after the first look like a
    cross-source duplicate of the first under `OpportunityService`'s real
    fingerprint dedup."""
    return [
        _hackathon(
            uuid=f"uuid-{start + i:08d}",
            slug=f"hackathon-{start + i}",
            name=f"Hackathon {start + i}",
            **overrides,
        )
        for i in range(n)
    ]


def _ctx(http_client, *, retry_attempts: int = 1) -> AgentContext:
    config = AgentConfig.with_defaults(
        source="devfolio",
        retry=RetryConfig(
            max_attempts=retry_attempts, base_delay_seconds=0.001, max_delay_seconds=0.002
        ),
    )
    return AgentContext(
        config=config,
        http_client=http_client,
        rate_limiter=NullRateLimiter(),
        logger=get_agent_logger("devfolio"),
    )


@pytest.fixture(autouse=True)
def _reset_hackathon_settings(monkeypatch):
    """Every test gets known-good HACKATHON_DAILY_LIMIT/
    HACKATHON_CANDIDATE_POOL_SIZE/DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION
    regardless of the real `.env` -- individual tests override further via
    monkeypatch as needed. Mirrors `test_devpost_agent.py`'s fixture of the
    same name."""
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 20)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 60)
    monkeypatch.setattr(settings, "DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION", True)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_parse_devfolio_datetime_valid():
    parsed = _parse_devfolio_datetime("2026-09-10T18:29:00+00:00")
    assert parsed is not None
    assert parsed.year == 2026 and parsed.month == 9 and parsed.day == 10


@pytest.mark.parametrize("text", [None, "", "not-a-date", "2026/09/10"])
def test_parse_devfolio_datetime_unparseable_returns_none(text):
    assert _parse_devfolio_datetime(text) is None


def test_extract_build_id_from_valid_next_data():
    assert _extract_build_id(_shell_html("abc-123")) == "abc-123"


@pytest.mark.parametrize(
    "html_text",
    [
        "<html><body>no next data here</body></html>",
        '<script id="__NEXT_DATA__" type="application/json">not json</script>',
        _shell_html(None),  # __NEXT_DATA__ present but missing buildId
    ],
)
def test_extract_build_id_returns_none_when_unparseable(html_text):
    assert _extract_build_id(html_text) is None


def test_canonical_url_from_slug():
    assert _canonical_url(_hackathon(slug="webcraft24")) == "https://webcraft24.devfolio.co/"


def test_canonical_url_none_when_slug_missing():
    assert _canonical_url(_hackathon(slug="")) is None
    hackathon = _hackathon()
    del hackathon["slug"]
    assert _canonical_url(hackathon) is None


def test_apply_url_falls_back_to_canonical_when_no_external_url():
    hackathon = _hackathon()  # external_apply_url is None in the default fixture
    canonical = _canonical_url(hackathon)
    assert _apply_url(hackathon, canonical_url=canonical) == canonical


def test_apply_url_uses_external_apply_url_verbatim_when_set():
    hackathon = _hackathon(settings={"external_apply_url": "https://forms.example.com/apply/webcraft"})
    canonical = _canonical_url(hackathon)
    assert _apply_url(hackathon, canonical_url=canonical) == "https://forms.example.com/apply/webcraft"


def test_apply_url_never_invents_when_no_slug_and_no_external_url():
    hackathon = _hackathon(slug="")
    assert _apply_url(hackathon, canonical_url=None) is None


def test_themes_to_tags_extracts_names():
    hackathon = _hackathon(themes=[{"theme": {"name": "AI"}}, {"theme": {"name": "FinTech"}}])
    assert _themes_to_tags(hackathon) == ["AI", "FinTech"]


def test_themes_to_tags_empty_when_no_themes():
    assert _themes_to_tags(_hackathon(themes=[])) == []
    assert _themes_to_tags(_hackathon(themes=None)) == []


def test_format_duration_same_day():
    from datetime import datetime

    starts = datetime.fromisoformat("2026-09-25T01:30:00+00:00")
    ends = datetime.fromisoformat("2026-09-25T20:00:00+00:00")
    assert _format_duration(starts, ends) == "Sep 25, 2026"


def test_format_duration_cross_day():
    from datetime import datetime

    starts = datetime.fromisoformat("2026-09-25T01:30:00+00:00")
    ends = datetime.fromisoformat("2026-09-26T01:30:00+00:00")
    assert _format_duration(starts, ends) == "Sep 25 - Sep 26, 2026"


def test_format_duration_none_when_either_end_missing():
    assert _format_duration(None, None) is None


def test_build_description_assembles_from_literal_fields():
    description = _build_description(is_online=True, tags=["AI", "FinTech"], participants_count=42)
    assert description == "Online hackathon. Themes: AI, FinTech. 42 participant(s) so far."


def test_build_description_offline_no_tags_no_participants():
    description = _build_description(is_online=False, tags=[], participants_count=0)
    assert description == "In-person hackathon."


# ---------------------------------------------------------------------------
# _clean_markdown_to_text -- enrichment page's `desc` -> plain text excerpt
# ---------------------------------------------------------------------------


def test_clean_markdown_to_text_strips_bold_and_collapses_whitespace():
    markdown = "**CODEUTSAVA** isn't just an event—it's a  **celebration**  of code!"
    cleaned = _clean_markdown_to_text(markdown)
    assert cleaned == "CODEUTSAVA isn't just an event—it's a celebration of code!"
    assert "*" not in cleaned


def test_clean_markdown_to_text_strips_links_and_images_to_their_visible_text():
    markdown = "See our ![logo](https://example.com/logo.png) and [website](https://example.com)."
    cleaned = _clean_markdown_to_text(markdown)
    assert cleaned == "See our logo and website."


def test_clean_markdown_to_text_strips_headings_and_quote_markers():
    markdown = "# Big Heading\n\n> A quoted line\n\nBody `code` text."
    cleaned = _clean_markdown_to_text(markdown)
    assert "#" not in cleaned
    assert ">" not in cleaned
    assert "`" not in cleaned
    assert "Big Heading" in cleaned
    assert "Body" in cleaned


def test_clean_markdown_to_text_truncates_long_text_on_a_word_boundary():
    markdown = " ".join(["word"] * 200)  # far longer than _DESCRIPTION_MAX_LENGTH
    cleaned = _clean_markdown_to_text(markdown, max_length=50)
    assert len(cleaned) <= 51  # 50 chars + the ellipsis character
    assert cleaned.endswith("…")
    assert not cleaned[:-1].endswith(" ")  # trimmed on a word boundary, no trailing space


def test_clean_markdown_to_text_none_for_none_or_blank_or_markdown_only():
    assert _clean_markdown_to_text(None) is None
    assert _clean_markdown_to_text("") is None
    assert _clean_markdown_to_text("   ") is None
    assert _clean_markdown_to_text("***") is None  # cleans down to nothing


def test_clean_markdown_to_text_non_string_input_returns_none():
    assert _clean_markdown_to_text(123) is None  # type: ignore[arg-type]
    assert _clean_markdown_to_text(["not", "a", "string"]) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _extract_logo_url / _extract_location / _build_enriched_description --
# enrichment-preferred, listing-endpoint-fallback field mapping (pure)
# ---------------------------------------------------------------------------


def test_extract_logo_url_prefers_enrichment_cover_img():
    enrichment = {"cover_img": "https://assets.devfolio.co/hackathons/x/assets/cover/1.png"}
    settings_block = {
        "featured_cover_img": "https://old.example.com/1.png",
        "featured_cover_img_v2": "https://old.example.com/2.png",
    }
    assert _extract_logo_url(enrichment, settings_block) == enrichment["cover_img"]


def test_extract_logo_url_falls_back_to_featured_cover_img_when_enrichment_empty():
    settings_block = {
        "featured_cover_img": "https://old.example.com/1.png",
        "featured_cover_img_v2": "https://old.example.com/2.png",
    }
    assert _extract_logo_url({}, settings_block) == "https://old.example.com/2.png"
    only_v1 = {"featured_cover_img": "https://old.example.com/1.png", "featured_cover_img_v2": None}
    assert _extract_logo_url({}, only_v1) == "https://old.example.com/1.png"


def test_extract_logo_url_none_when_nothing_available():
    assert _extract_logo_url({}, {}) is None
    empty_settings = {"featured_cover_img": None, "featured_cover_img_v2": ""}
    assert _extract_logo_url({"cover_img": None}, empty_settings) is None


def test_extract_location_from_enrichment():
    address = "NIT Raipur, Raipur, India"
    assert _extract_location({"location": address}) == address


def test_extract_location_none_when_missing_or_blank():
    assert _extract_location({}) is None
    assert _extract_location({"location": None}) is None
    assert _extract_location({"location": "   "}) is None


def test_build_enriched_description_prefers_tagline_and_desc_excerpt():
    enrichment = {
        "tagline": "Central India's Largest Hackathon",
        "desc": "**CODEUTSAVA** is a celebration of code.",
    }
    description = _build_enriched_description(
        enrichment, is_online=False, tags=["AI"], participants_count=10
    )
    assert description == "Central India's Largest Hackathon. CODEUTSAVA is a celebration of code."


def test_build_enriched_description_tagline_only_gets_a_period_appended():
    description = _build_enriched_description(
        {"tagline": "Great hackathon"}, is_online=False, tags=[], participants_count=None
    )
    assert description == "Great hackathon."


def test_build_enriched_description_tagline_with_existing_punctuation_unchanged():
    description = _build_enriched_description(
        {"tagline": "Is this great?"}, is_online=False, tags=[], participants_count=None
    )
    assert description == "Is this great?"


def test_build_enriched_description_falls_back_to_templated_summary_when_enrichment_empty():
    description = _build_enriched_description(
        {}, is_online=True, tags=["AI", "FinTech"], participants_count=42
    )
    assert description == "Online hackathon. Themes: AI, FinTech. 42 participant(s) so far."


def test_build_enriched_description_falls_back_when_tagline_and_desc_both_blank():
    description = _build_enriched_description(
        {"tagline": "   ", "desc": "***"}, is_online=False, tags=[], participants_count=0
    )
    assert description == "In-person hackathon."


# ---------------------------------------------------------------------------
# select_top_candidates -- ranking + pool cap (pure, no I/O)
# ---------------------------------------------------------------------------


def test_select_top_candidates_caps_to_limit():
    candidates = [(_hackathon(uuid=f"u{i}", slug=f"s{i}"), "open_hackathons") for i in range(35)]
    selected = select_top_candidates(candidates, 20, today=date(2026, 9, 10))
    assert len(selected) == 20


def test_select_top_candidates_limit_zero_returns_empty():
    candidates = [(_hackathon(uuid=f"u{i}"), "open_hackathons") for i in range(5)]
    assert select_top_candidates(candidates, 0) == []


def test_select_top_candidates_ranks_open_before_upcoming():
    upcoming = (_hackathon(uuid="u1", slug="a"), "upcoming_hackathons")
    open_one = (_hackathon(uuid="u2", slug="b"), "open_hackathons")
    selected = select_top_candidates([upcoming, open_one], 2, today=date(2026, 9, 10))
    assert [h["uuid"] for h, _ in selected] == ["u2", "u1"]


def test_select_top_candidates_ranks_by_soonest_registration_deadline_first():
    far = (
        _hackathon(uuid="u1", slug="far", settings={"reg_ends_at": "2026-12-31T00:00:00+00:00"}),
        "open_hackathons",
    )
    soon = (
        _hackathon(uuid="u2", slug="soon", settings={"reg_ends_at": "2026-09-12T00:00:00+00:00"}),
        "open_hackathons",
    )
    selected = select_top_candidates([far, soon], 2, today=date(2026, 9, 10))
    assert [h["uuid"] for h, _ in selected] == ["u2", "u1"]


# ---------------------------------------------------------------------------
# discover()
# ---------------------------------------------------------------------------


async def test_discover_two_requests_shell_then_data():
    client = FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html()),
        data_response=_data_response(open_=[_hackathon()]),
    )
    agent = DevfolioAgent()

    listings = await agent.discover(_ctx(client))

    assert len(client.calls) == 2
    assert client.calls[0] == "https://devfolio.co/hackathons"
    assert client.calls[1] == f"https://devfolio.co/_next/data/{_BUILD_ID}/hackathons.json"
    assert len(listings) == 1
    assert listings[0].url == "https://webcraft24.devfolio.co/"


async def test_discover_excludes_past_hackathons():
    client = FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html()),
        data_response=_data_response(
            open_=[_hackathon(uuid="open-1", slug="open-1")],
            past=[_hackathon(uuid="past-1", slug="past-1")],
        ),
    )
    agent = DevfolioAgent()

    listings = await agent.discover(_ctx(client))

    assert [listing.metadata["uuid"] for listing in listings] == ["open-1"]


async def test_discover_includes_upcoming_and_featured_deduped_against_open():
    shared = _hackathon(uuid="shared-1", slug="shared-1")
    client = FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html()),
        data_response=_data_response(
            open_=[shared],
            upcoming=[_hackathon(uuid="upcoming-1", slug="upcoming-1")],
            featured=[shared, _hackathon(uuid="featured-only-1", slug="featured-only-1")],
        ),
    )
    agent = DevfolioAgent()

    listings = await agent.discover(_ctx(client))

    ids = {listing.metadata["uuid"] for listing in listings}
    assert ids == {"shared-1", "upcoming-1", "featured-only-1"}
    # "shared-1" appeared in both open_hackathons and featured_hackathons --
    # must be kept exactly once, not duplicated.
    assert len(listings) == 3


async def test_discover_filters_malformed_listings():
    client = FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html()),
        data_response=_data_response(
            open_=[
                _hackathon(uuid="good-1", slug="good-1"),
                {**_hackathon(uuid="missing-slug"), "slug": ""},
                {**_hackathon(uuid="missing-name"), "name": ""},
                {**_hackathon(slug="missing-uuid"), "uuid": None},
            ]
        ),
    )
    agent = DevfolioAgent()

    listings = await agent.discover(_ctx(client))

    assert [listing.metadata["uuid"] for listing in listings] == ["good-1"]


async def test_discover_applies_candidate_pool_size_not_daily_limit(monkeypatch):
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 3)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 7)
    open_hackathons = _distinct_hackathons(10)
    client = _client_for(open_hackathons)
    agent = DevfolioAgent()

    listings = await agent.discover(_ctx(client))

    assert len(listings) == 7  # capped by the pool size, not the daily limit
    assert agent.last_discovery_stats == {"raw_discovered": 10, "selected": 7}


async def test_discover_raises_when_shell_page_request_fails():
    client = FakeHttpClient(fail_shell=True)
    agent = DevfolioAgent()

    with pytest.raises(RuntimeError):
        await agent.discover(_ctx(client))


async def test_discover_raises_when_build_id_cannot_be_found():
    client = FakeHttpClient(
        shell_response=FakeResponse(text="<html><body>no next data</body></html>")
    )
    agent = DevfolioAgent()

    with pytest.raises(ValueError):
        await agent.discover(_ctx(client))


async def test_discover_raises_when_data_json_request_fails():
    client = FakeHttpClient(shell_response=FakeResponse(text=_shell_html()), fail_data=True)
    agent = DevfolioAgent()

    with pytest.raises(RuntimeError):
        await agent.discover(_ctx(client))


# ---------------------------------------------------------------------------
# extract()
# ---------------------------------------------------------------------------


async def test_extract_fetches_one_enrichment_request_per_candidate_by_default():
    """`DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION` defaults True (see
    `_reset_hackathon_settings`) -- extract() should make exactly one
    additional request, to the per-hackathon enrichment page, reusing
    discover()'s own buildId rather than re-fetching the shell page."""
    client = _client_for(
        [_hackathon(slug="webcraft24")],
        overview_response=_overview_json(cover_img="https://assets.devfolio.co/cover.png"),
    )
    agent = DevfolioAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    calls_after_discover = len(client.calls)

    raw = await agent.extract(ctx, listings[0])

    assert len(client.calls) == calls_after_discover + 1
    enrichment_url = client.calls[-1]
    assert "overview.json" in enrichment_url
    assert f"/_next/data/{_BUILD_ID}/hackathon3/webcraft24/" in enrichment_url
    assert "slug=webcraft24" in enrichment_url
    assert raw.content_type == "json"
    assert raw.raw_content
    assert json.loads(raw.raw_content)["_enrichment"]["cover_img"] == "https://assets.devfolio.co/cover.png"
    # The buildId used only to build the enrichment URL is not itself part
    # of the normalized-facing payload.
    assert "_build_id" not in json.loads(raw.raw_content)


async def test_extract_makes_no_additional_http_call_when_enrichment_disabled(monkeypatch):
    monkeypatch.setattr(settings, "DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION", False)
    client = _client_for([_hackathon()])
    agent = DevfolioAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    calls_after_discover = len(client.calls)

    raw = await agent.extract(ctx, listings[0])

    assert len(client.calls) == calls_after_discover  # extract() added zero calls
    assert json.loads(raw.raw_content)["_enrichment"] == {}


async def test_extract_degrades_gracefully_on_enrichment_http_error():
    """A non-200 from the enrichment page must not fail the listing --
    extract() logs it and moves on with empty enrichment."""
    client = _client_for([_hackathon()], overview_response=FakeResponse(status_code=500))
    agent = DevfolioAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    raw = await agent.extract(ctx, listings[0])

    assert json.loads(raw.raw_content)["_enrichment"] == {}


async def test_extract_degrades_gracefully_on_enrichment_network_failure():
    client = FakeHttpClient(
        shell_response=FakeResponse(text=_shell_html()),
        data_response=_data_response(open_=[_hackathon()]),
        fail_overview=True,
    )
    agent = DevfolioAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    raw = await agent.extract(ctx, listings[0])  # must not raise

    assert json.loads(raw.raw_content)["_enrichment"] == {}


async def test_extract_skips_enrichment_fetch_when_build_id_missing():
    """Defensive: if a listing somehow reached extract() without a
    `_build_id` in its metadata, extract() must not attempt (or crash
    trying to build a URL for) the enrichment fetch."""
    client = _client_for([_hackathon()])
    agent = DevfolioAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    listing = listings[0]
    listing.metadata.pop("_build_id", None)
    calls_before = len(client.calls)

    raw = await agent.extract(ctx, listing)

    assert len(client.calls) == calls_before  # no enrichment call attempted
    assert json.loads(raw.raw_content)["_enrichment"] == {}


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


def _raw_for(hackathon: dict, *, enrichment: dict | None = None) -> RawExtraction:
    """`enrichment` mirrors what `extract()` stashes at `data["_enrichment"]`
    -- omitted (the default) reproduces every listing this file already
    exercises with no enrichment page fetched, matching real behavior when
    `DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION` is off or the fetch failed/404'd."""
    payload = {**hackathon, "_enrichment": enrichment or {}}
    return RawExtraction(
        url=_canonical_url(hackathon) or "",
        source="devfolio",
        content_type="json",
        raw_content=json.dumps(payload),
    )


def test_normalize_maps_all_fields_from_realistic_sample():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))

    assert opportunity.category == "hackathons"
    assert opportunity.title == "WebCraft24"
    assert opportunity.organization is None
    assert opportunity.logo_url is None
    assert opportunity.location is None
    assert opportunity.is_remote is False
    assert opportunity.apply_url == "https://webcraft24.devfolio.co/"
    assert opportunity.source_url == "https://webcraft24.devfolio.co/"
    assert opportunity.source == "devfolio"
    assert opportunity.source_id == "2061a11b47c74daa90f2760db6c951f6"
    assert opportunity.tags == ["ai"]  # normalise_tags lowercases
    assert opportunity.duration == "Sep 25 - Sep 26, 2026"
    assert opportunity.application_deadline == date(2026, 9, 20)
    assert opportunity.posted_at is None
    assert "In-person hackathon." in opportunity.description
    assert "AI" in opportunity.description


def test_normalize_is_remote_true_for_online_event():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon(is_online=True)))
    assert opportunity.is_remote is True
    assert "Online hackathon." in opportunity.description


def test_normalize_uses_external_apply_url_when_present():
    agent = DevfolioAgent()
    hackathon = _hackathon(settings={"external_apply_url": "https://forms.example.com/apply"})
    opportunity = agent.normalize(None, _raw_for(hackathon))

    assert opportunity.apply_url == "https://forms.example.com/apply"
    # source_url is UNCHANGED -- always the slug-derived canonical page,
    # regardless of where apply_url points.
    assert opportunity.source_url == "https://webcraft24.devfolio.co/"


def test_normalize_uses_logo_from_featured_cover_img_v2_preferred():
    agent = DevfolioAgent()
    hackathon = _hackathon(
        settings={
            "featured_cover_img": "https://assets.devfolio.co/cover-v1.png",
            "featured_cover_img_v2": "https://assets.devfolio.co/cover-v2.png",
        }
    )
    opportunity = agent.normalize(None, _raw_for(hackathon))
    assert opportunity.logo_url == "https://assets.devfolio.co/cover-v2.png"


def test_normalize_prefers_enriched_cover_img_over_featured_cover_img():
    agent = DevfolioAgent()
    hackathon = _hackathon(
        settings={
            "featured_cover_img": "https://old.example.com/1.png",
            "featured_cover_img_v2": "https://old.example.com/2.png",
        }
    )
    enrichment = {"cover_img": "https://assets.devfolio.co/hackathons/x/assets/cover/254.png"}
    opportunity = agent.normalize(None, _raw_for(hackathon, enrichment=enrichment))
    assert opportunity.logo_url == "https://assets.devfolio.co/hackathons/x/assets/cover/254.png"


def test_normalize_uses_enriched_location():
    agent = DevfolioAgent()
    address = "NIT Raipur, Great Eastern Road, Amanaka, Raipur, Chhattisgarh, India"
    opportunity = agent.normalize(None, _raw_for(_hackathon(), enrichment={"location": address}))
    assert opportunity.location == address


def test_normalize_uses_enriched_tagline_and_desc_for_description():
    agent = DevfolioAgent()
    enrichment = {
        "tagline": "Central India's Largest Hackathon",
        "desc": "**CODEUTSAVA** is a celebration of code, hosted by the Turing Club.",
    }
    opportunity = agent.normalize(None, _raw_for(_hackathon(), enrichment=enrichment))
    assert opportunity.description == (
        "Central India's Largest Hackathon. "
        "CODEUTSAVA is a celebration of code, hosted by the Turing Club."
    )
    assert "*" not in opportunity.description


def test_normalize_description_falls_back_to_templated_summary_without_enrichment():
    """Same real-world case `test_normalize_maps_all_fields_from_realistic_sample`
    already covers -- kept here explicitly next to the enrichment tests so
    the fallback behavior is visible alongside what it falls back FROM."""
    agent = DevfolioAgent()
    hackathon = _hackathon(is_online=False, themes=[{"theme": {"name": "AI"}}])
    opportunity = agent.normalize(None, _raw_for(hackathon))
    assert opportunity.description == "In-person hackathon. Themes: AI. 900 participant(s) so far."


def test_normalize_logo_location_description_all_none_or_fallback_without_enrichment():
    """The 20 Devfolio rows already ingested before this feature existed
    have no `_enrichment` (extract() didn't write one yet) -- normalize()
    must still behave exactly as it did before, so a re-run backfills
    rather than erroring on an old-shaped payload."""
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    assert opportunity.logo_url is None
    assert opportunity.location is None
    assert opportunity.description == "In-person hackathon. Themes: AI. 900 participant(s) so far."


def test_normalize_handles_missing_optional_fields_gracefully():
    agent = DevfolioAgent()
    sparse = _hackathon(
        themes=[],
        starts_at=None,
        ends_at=None,
        participants_count=None,
        settings={"reg_ends_at": None, "featured_cover_img": None, "featured_cover_img_v2": None},
    )
    opportunity = agent.normalize(None, _raw_for(sparse))

    assert opportunity.tags == []
    assert opportunity.duration is None
    assert opportunity.application_deadline is None
    assert opportunity.logo_url is None
    assert opportunity.organization is None
    assert opportunity.location is None
    # Still has a usable, non-hallucinated apply_url -- nothing here was invented.
    assert opportunity.apply_url == "https://webcraft24.devfolio.co/"


def test_normalize_raises_on_missing_required_fields():
    agent = DevfolioAgent()
    broken = _hackathon()
    broken["name"] = ""

    with pytest.raises(ValueError):
        agent.normalize(None, _raw_for(broken))


def test_normalize_raises_when_slug_missing():
    agent = DevfolioAgent()
    broken = _hackathon()
    broken["slug"] = ""

    with pytest.raises(ValueError):
        agent.normalize(None, _raw_for(broken))


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


def test_validate_accepts_a_good_opportunity():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))

    result = agent.validate(None, opportunity)

    assert result.is_valid is True


def test_validate_accepts_external_apply_url_off_devfolio_domain():
    # apply_url is intentionally NOT restricted to devfolio.co -- Devfolio's
    # own external_apply_url field can legitimately point elsewhere. Only
    # source_url (always this agent's own construction) is checked.
    agent = DevfolioAgent()
    hackathon = _hackathon(settings={"external_apply_url": "https://forms.example.com/apply"})
    opportunity = agent.normalize(None, _raw_for(hackathon))

    result = agent.validate(None, opportunity)

    assert result.is_valid is True


def test_validate_rejects_tampered_source_url_off_devfolio_domain():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"source_url": "https://evil.example.com/webcraft24"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "source_url" for issue in result.errors)


def test_validate_rejects_wrong_category():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"category": "programs"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "category" for issue in result.errors)


def test_validate_rejects_wrong_source():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"source": "devpost"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "source" for issue in result.errors)


def test_validate_rejects_missing_source_id():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"source_id": ""})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "source_id" for issue in result.errors)


def test_validate_rejects_malformed_apply_url():
    agent = DevfolioAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"apply_url": "not-a-url"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "apply_url" for issue in result.errors)


# ---------------------------------------------------------------------------
# Full agent.run() -- discover -> extract -> normalize -> validate, through
# the real IngestionPipeline, with per-listing failure isolation.
# ---------------------------------------------------------------------------


async def test_agent_run_end_to_end_produces_valid_hackathon_opportunities():
    client = _client_for(
        [
            _hackathon(uuid="u1", slug="s1", name="First"),
            _hackathon(uuid="u2", slug="s2", name="Second"),
        ]
    )
    agent = DevfolioAgent()

    result = await agent.run(_ctx(client))

    assert result.discovered_count == 2
    assert result.valid_count == 2
    assert result.errors == []
    assert {o.category for o in result.opportunities} == {"hackathons"}
    assert {o.source for o in result.opportunities} == {"devfolio"}


async def test_agent_run_isolates_one_malformed_candidate():
    # Whitespace-only name passes discover()'s truthiness check (a
    # non-empty string) but normalize()'s `.strip()` reduces it to an
    # empty title -- exercising the SAME "one bad candidate mid-run must
    # not abort the rest" guarantee `test_devpost_agent.py` checks, just
    # triggered at the point where Devfolio's own data can actually go bad
    # after discover()'s cheaper presence checks.
    broken = _hackathon(uuid="broken-1", slug="broken-1", name="   ")
    good = _hackathon(uuid="good-1", slug="good-1", name="Good Hackathon")
    client = _client_for([good, broken])
    agent = DevfolioAgent()

    result = await agent.run(_ctx(client))

    assert result.discovered_count == 2
    assert result.valid_count == 1
    assert len(result.errors) == 1
    assert result.errors[0].stage == "normalize"
    assert result.status == "partial"


# ---------------------------------------------------------------------------
# Integration: agent output -> OpportunityService -> persistence layer
# (fake repository, matching tests/test_opportunity_service.py's approach --
# no real Supabase call).
# ---------------------------------------------------------------------------


async def test_full_pipeline_reaches_opportunity_service_with_hackathons_category():
    client = _client_for([_hackathon()])
    agent = DevfolioAgent()

    run_result = await agent.run(_ctx(client))

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    batch = await service.save_batch(run_result.opportunities)

    assert batch.created == 1
    assert batch.errors == 0
    (row,) = repository.rows.values()
    assert row["category"] == "hackathons"
    assert row["source"] == "devfolio"
    assert row["source_id"] == "2061a11b47c74daa90f2760db6c951f6"
    assert row["is_active"] is True


async def test_dedup_running_ingestion_three_times_creates_no_duplicates():
    client_factory = lambda: _client_for([_hackathon()])  # noqa: E731

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    run1 = await DevfolioAgent().run(_ctx(client_factory()))
    batch1 = await service.save_batch(run1.opportunities)
    assert batch1.created == 1
    assert batch1.updated == 0
    assert len(repository.rows) == 1

    run2 = await DevfolioAgent().run(_ctx(client_factory()))
    batch2 = await service.save_batch(run2.opportunities)
    assert batch2.created == 0
    assert batch2.updated == 1
    assert len(repository.rows) == 1

    run3 = await DevfolioAgent().run(_ctx(client_factory()))
    batch3 = await service.save_batch(run3.opportunities)
    assert batch3.created == 0
    assert batch3.updated == 1
    assert len(repository.rows) == 1

    (row,) = repository.rows.values()
    assert row["source"] == "devfolio"
    assert row["source_id"] == "2061a11b47c74daa90f2760db6c951f6"


async def test_dedup_cross_source_fingerprint_still_works_for_devfolio_rows():
    client = _client_for([_hackathon()])
    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    run = await DevfolioAgent().run(_ctx(client))
    (opportunity,) = run.opportunities
    fingerprint = service.generate_fingerprint(opportunity)
    repository.rows["existing-row"] = {
        "id": "existing-row",
        "source": "some-other-source",
        "source_id": "different-id",
        "fingerprint": fingerprint,
    }

    batch = await service.save_batch(run.opportunities)

    assert batch.created == 0
    assert batch.updated == 1
    assert len(repository.rows) == 1


# ---------------------------------------------------------------------------
# 20/day: stop once HACKATHON_DAILY_LIMIT are actually saved, not once
# HACKATHON_DAILY_LIMIT candidates have been attempted.
# ---------------------------------------------------------------------------


async def test_save_batch_stops_at_daily_save_limit_with_headroom(monkeypatch):
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 20)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 60)

    # 22 fully valid candidates + 3 with a whitespace-only name (normalize()
    # raises on those -- an "earlier invalid candidate" that must NOT
    # reduce the final saved count below 20, since there's enough headroom
    # in the pool).
    hackathons = _distinct_hackathons(22)
    hackathons += [
        _hackathon(uuid=f"broken-{i}", slug=f"broken-{i}", name="   ") for i in range(3)
    ]
    client = _client_for(hackathons)

    run_result = await DevfolioAgent().run(_ctx(client))
    assert run_result.valid_count == 22
    assert len(run_result.errors) == 3
    assert all(e.stage == "normalize" for e in run_result.errors)

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    batch = await service.save_batch(
        run_result.opportunities, max_success_count=settings.HACKATHON_DAILY_LIMIT
    )

    assert batch.created == 20
    assert batch.updated == 0
    assert batch.skipped == 2  # 22 valid - 20 saved = 2 never attempted
    assert batch.rejected == 0
    assert batch.errors == 0
    assert len(repository.rows) == 20


async def test_save_batch_saves_all_when_fewer_than_daily_limit_are_valid():
    hackathons = _distinct_hackathons(5)
    client = _client_for(hackathons)

    run_result = await DevfolioAgent().run(_ctx(client))
    assert run_result.valid_count == 5

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    batch = await service.save_batch(run_result.opportunities, max_success_count=20)

    assert batch.created == 5
    assert batch.skipped == 0
    assert len(repository.rows) == 5


async def test_devfolio_default_config_declares_the_daily_save_limit(monkeypatch):
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 42)
    agent = DevfolioAgent()
    assert agent.config.daily_save_limit == 42


async def test_devfolio_default_config_enabled_tracks_settings(monkeypatch):
    monkeypatch.setattr(settings, "DEVFOLIO_ENABLED", False)
    agent = DevfolioAgent()
    assert agent.config.enabled is False


# ---------------------------------------------------------------------------
# Dry run: preview_batch() must resolve identically to save_batch() but
# write nothing.
# ---------------------------------------------------------------------------


async def test_dry_run_preview_batch_makes_zero_writes():
    hackathons = _distinct_hackathons(5)
    client = _client_for(hackathons)

    run_result = await DevfolioAgent().run(_ctx(client))

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    preview = service.preview_batch(run_result.opportunities, max_success_count=20)

    assert preview.created == 5  # counted as "would create"
    assert repository.rows == {}  # but nothing was actually written
    assert {r.outcome for r in preview.results} == {"would_create"}


async def test_dry_run_preview_batch_detects_existing_duplicates_without_writing():
    hackathons = _distinct_hackathons(3)

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    real_client = _client_for(hackathons)
    real_run = await DevfolioAgent().run(_ctx(real_client))
    await service.save_batch(real_run.opportunities)
    assert len(repository.rows) == 3

    dry_client = _client_for(hackathons)
    dry_run_result = await DevfolioAgent().run(_ctx(dry_client))
    preview = service.preview_batch(dry_run_result.opportunities)

    assert preview.created == 0
    assert preview.updated == 3
    assert {r.outcome for r in preview.results} == {"would_update"}
    assert len(repository.rows) == 3  # still just the 3 from the real run above


async def test_dry_run_preview_batch_respects_daily_save_limit_cap():
    hackathons = _distinct_hackathons(10)
    client = _client_for(hackathons)

    run_result = await DevfolioAgent().run(_ctx(client))
    service = OpportunityService(repository=FakeOpportunityRepository(), queue=FakeQueue())

    preview = service.preview_batch(run_result.opportunities, max_success_count=4)

    assert preview.created == 4
    assert preview.skipped == 6
