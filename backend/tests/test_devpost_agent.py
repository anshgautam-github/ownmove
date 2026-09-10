"""Exercises `DevpostHackathonAgent` end-to-end with a fake HTTP client --
no real network call is ever made (see `FakeHttpClient` below); nothing here
depends on devpost.com being reachable or returning any particular data.

Sample hackathon payloads mirror the REAL shape of
`https://devpost.com/api/hackathons` (verified by inspecting that endpoint's
actual response, not guessed -- see `app/ingestion/agents/sources/
devpost.py`'s module docstring for the full sample).
"""

from datetime import date

import pytest

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.ingestion.agents.base import AgentContext
from app.ingestion.agents.sources.devpost import (
    DevpostHackathonAgent,
    _absolute_url,
    _build_description,
    _clean_prize_text,
    _looks_remote,
    _parse_deadline,
    select_top_candidates,
)
from app.ingestion.models.config import AgentConfig, RetryConfig
from app.ingestion.models.discovery import RawExtraction
from app.ingestion.services.opportunity_service import OpportunityService
from app.ingestion.utils.logging import get_agent_logger
from app.ingestion.utils.rate_limit import NullRateLimiter

# ---------------------------------------------------------------------------
# Fakes -- no real network, no real Supabase, matching every other test in
# this suite (see tests/test_opportunity_service.py, tests/test_ingestion_pipeline.py).
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"simulated HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json_data


class FakeHttpClient:
    """`pages` is a list of `FakeResponse`, one per page (1-indexed by
    position: `pages[0]` answers `page=1`, etc). Requesting past the end of
    the list returns an empty-hackathons page, matching how Devpost's real
    API would behave past the last page. `fail_on_page` optionally raises
    for one specific page number, to exercise discover()'s partial-failure
    handling."""

    def __init__(self, pages: list[FakeResponse], *, fail_on_page: int | None = None):
        self.pages = pages
        self.fail_on_page = fail_on_page
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url: str, params: dict | None = None) -> FakeResponse:
        params = dict(params or {})
        self.calls.append((url, params))
        page = params.get("page", 1)
        if self.fail_on_page is not None and page == self.fail_on_page:
            raise RuntimeError(f"simulated network failure on page {page}")
        idx = page - 1
        if idx < 0 or idx >= len(self.pages):
            return FakeResponse({"hackathons": [], "meta": {"total_count": 0}})
        return self.pages[idx]


class FakeOpportunityRepository:
    """Same duck-typed fake shape as tests/test_opportunity_service.py's,
    kept self-contained here rather than imported so this file has no
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


def _hackathon(**overrides) -> dict:
    base = {
        "id": 31050,
        "title": "Expo 26 Hackathon",
        "displayed_location": {"icon": "map-marker-alt", "location": "The Venue Hotel Jeddah"},
        "open_state": "open",
        "thumbnail_url": "//d112y698adiu2z.cloudfront.net/photos/example.png",
        "url": "https://expo-26-hackathon.devpost.com/",
        "time_left_to_submission": "9 days left",
        "submission_period_dates": "Sep 09 - 18, 2026",
        "themes": [{"id": 16, "name": "Health"}],
        "prize_amount": "$<span data-currency-value>5,000</span>",
        "registrations_count": 2,
        "featured": False,
        "organization_name": "abbvie",
        "winners_announced": False,
        "invite_only": False,
    }
    base.update(overrides)
    return base


def _distinct_hackathons(n: int, *, start: int = 0, **overrides) -> list[dict]:
    """`n` hackathons that are genuinely distinct by fingerprint (title,
    organization, apply_url), not just by id -- `_hackathon(id=i)` alone
    reuses the same title/url for every `i`, which makes every one after
    the first look like a cross-source duplicate of the first under
    `OpportunityService`'s real fingerprint dedup. Tests that save more than
    one hackathon and expect more than one row need this, not raw
    `_hackathon(id=i)` calls."""
    return [
        _hackathon(
            id=start + i,
            title=f"Hackathon {start + i}",
            url=f"https://hackathon-{start + i}.devpost.com/",
            **overrides,
        )
        for i in range(n)
    ]


def _ctx(http_client, *, retry_attempts: int = 1) -> AgentContext:
    config = AgentConfig.with_defaults(
        source="devpost",
        retry=RetryConfig(
            max_attempts=retry_attempts, base_delay_seconds=0.001, max_delay_seconds=0.002
        ),
    )
    return AgentContext(
        config=config,
        http_client=http_client,
        rate_limiter=NullRateLimiter(),
        logger=get_agent_logger("devpost"),
    )


@pytest.fixture(autouse=True)
def _reset_hackathon_settings(monkeypatch):
    """Every test gets known-good HACKATHON_DAILY_LIMIT/
    HACKATHON_CANDIDATE_POOL_SIZE/DEVPOST_MAX_DISCOVERY_PAGES regardless of
    the real `.env` -- individual tests override further via monkeypatch as
    needed."""
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 20)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 60)
    monkeypatch.setattr(settings, "DEVPOST_MAX_DISCOVERY_PAGES", 6)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_parse_deadline_same_month():
    assert _parse_deadline("Sep 09 - 18, 2026") == date(2026, 9, 18)


def test_parse_deadline_cross_month():
    assert _parse_deadline("Sep 28 - Oct 05, 2026") == date(2026, 10, 5)


@pytest.mark.parametrize(
    "text",
    [None, "", "TBD", "Sometime this fall", "Sep 09 - 18", "rolling"],
)
def test_parse_deadline_unparseable_returns_none(text):
    assert _parse_deadline(text) is None


def test_absolute_url_fixes_protocol_relative():
    assert _absolute_url("//cdn.example.com/x.png") == "https://cdn.example.com/x.png"


def test_absolute_url_passthrough_and_none():
    assert _absolute_url("https://example.com/x.png") == "https://example.com/x.png"
    assert _absolute_url(None) is None
    assert _absolute_url("") is None


def test_looks_remote_via_globe_icon():
    assert _looks_remote({"icon": "globe", "location": "Somewhere"}) is True


def test_looks_remote_via_text_keyword():
    assert _looks_remote({"icon": "map-marker-alt", "location": "Online"}) is True


def test_looks_remote_false_for_physical_venue():
    assert _looks_remote({"icon": "map-marker-alt", "location": "The Venue Hotel Jeddah"}) is False


def test_clean_prize_text_strips_html_and_entities():
    assert _clean_prize_text("$<span data-currency-value>5,000</span>") == "$5,000"
    assert _clean_prize_text(None) is None


def test_build_description_assembles_from_literal_fields():
    description = _build_description(
        organization="abbvie", tags=["Health", "AI"], prize_text="$5,000", invite_only=False
    )
    assert description == "Hosted by abbvie. Themes: Health, AI. Prize pool: $5,000."


def test_build_description_skips_zero_prize_and_none_when_nothing_available():
    description = _build_description(organization=None, tags=[], prize_text="$0", invite_only=False)
    assert description is None


# ---------------------------------------------------------------------------
# select_top_candidates -- ranking + daily cap (pure, no I/O)
# ---------------------------------------------------------------------------


def test_select_top_candidates_caps_to_limit():
    candidates = [_hackathon(id=i, url=f"https://x{i}.devpost.com/") for i in range(35)]
    selected = select_top_candidates(candidates, 20, today=date(2026, 9, 10))
    assert len(selected) == 20


def test_select_top_candidates_limit_zero_returns_empty():
    candidates = [_hackathon(id=i) for i in range(5)]
    assert select_top_candidates(candidates, 0) == []


def test_select_top_candidates_ranks_open_before_upcoming():
    upcoming = _hackathon(id=1, open_state="upcoming", featured=True)
    open_one = _hackathon(id=2, open_state="open", featured=False)
    selected = select_top_candidates([upcoming, open_one], 2, today=date(2026, 9, 10))
    assert [h["id"] for h in selected] == [2, 1]


def test_select_top_candidates_ranks_by_soonest_deadline_first():
    far = _hackathon(id=1, submission_period_dates="Dec 01 - 31, 2026")
    soon = _hackathon(id=2, submission_period_dates="Sep 09 - 12, 2026")
    selected = select_top_candidates([far, soon], 2, today=date(2026, 9, 10))
    assert [h["id"] for h in selected] == [2, 1]


# ---------------------------------------------------------------------------
# discover()
# ---------------------------------------------------------------------------


async def test_discover_filters_invite_only_and_ended_and_missing_url():
    page = FakeResponse(
        {
            "hackathons": [
                _hackathon(id=1),
                _hackathon(id=2, invite_only=True),
                _hackathon(id=3, winners_announced=True),
                _hackathon(id=4, open_state="ended"),
                _hackathon(id=5, url=None),
            ],
            "meta": {"total_count": 5},
        }
    )
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()
    listings = await agent.discover(_ctx(client))

    assert [listing.metadata["id"] for listing in listings] == [1]


async def test_discover_paginates_until_total_count_reached():
    page1 = FakeResponse(
        {"hackathons": [_hackathon(id=i) for i in range(1, 10)], "meta": {"total_count": 12}}
    )
    page2 = FakeResponse(
        {"hackathons": [_hackathon(id=i) for i in range(10, 13)], "meta": {"total_count": 12}}
    )
    client = FakeHttpClient([page1, page2])
    agent = DevpostHackathonAgent()

    listings = await agent.discover(_ctx(client))

    assert len(client.calls) == 2
    assert len(listings) == 12


async def test_discover_stops_at_max_discovery_pages(monkeypatch):
    monkeypatch.setattr(settings, "DEVPOST_MAX_DISCOVERY_PAGES", 2)
    # Every page reports far more remaining than 2 pages could ever cover,
    # so pagination only stops because of the page cap, not total_count.
    pages = [
        FakeResponse(
            {
                "hackathons": [_hackathon(id=i) for i in range(n * 9, n * 9 + 9)],
                "meta": {"total_count": 999},
            }
        )
        for n in range(5)
    ]
    client = FakeHttpClient(pages)
    agent = DevpostHackathonAgent()

    await agent.discover(_ctx(client))

    assert len(client.calls) == 2


async def test_discover_applies_candidate_pool_size_not_daily_limit(monkeypatch):
    # discover() selects up to HACKATHON_CANDIDATE_POOL_SIZE candidates for
    # processing -- NOT HACKATHON_DAILY_LIMIT. The daily *save* limit is
    # enforced later, by OpportunityService.save_batch()'s max_success_count
    # (see test_save_batch_stops_at_daily_save_limit_with_headroom below) --
    # this is the "B" behavior a production-readiness review chose over the
    # previous "cap candidates processed" ("A") behavior.
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 3)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 7)
    page = FakeResponse(
        {"hackathons": [_hackathon(id=i) for i in range(10)], "meta": {"total_count": 10}}
    )
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()

    listings = await agent.discover(_ctx(client))

    assert len(listings) == 7  # capped by the pool size, not the daily limit
    assert agent.last_discovery_stats == {"raw_discovered": 10, "selected": 7}


async def test_discover_raises_when_first_page_fails():
    client = FakeHttpClient([], fail_on_page=1)
    agent = DevpostHackathonAgent()

    with pytest.raises(RuntimeError):
        await agent.discover(_ctx(client))


async def test_discover_degrades_gracefully_when_a_later_page_fails():
    page1 = FakeResponse(
        {"hackathons": [_hackathon(id=i) for i in range(5)], "meta": {"total_count": 50}}
    )
    client = FakeHttpClient([page1], fail_on_page=2)
    agent = DevpostHackathonAgent()

    listings = await agent.discover(_ctx(client))

    # Page 1's 5 candidates are kept even though page 2 failed -- discover()
    # does NOT raise once at least one page has already succeeded.
    assert len(listings) == 5


# ---------------------------------------------------------------------------
# extract()
# ---------------------------------------------------------------------------


async def test_extract_makes_no_additional_http_call():
    page = FakeResponse({"hackathons": [_hackathon()], "meta": {"total_count": 1}})
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()
    ctx = _ctx(client)

    listings = await agent.discover(ctx)
    calls_after_discover = len(client.calls)

    raw = await agent.extract(ctx, listings[0])

    assert len(client.calls) == calls_after_discover  # extract() added zero calls
    assert raw.content_type == "json"
    assert raw.raw_content  # metadata was serialized, not fetched again


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


def _raw_for(hackathon: dict) -> RawExtraction:
    import json as _json

    return RawExtraction(
        url=hackathon["url"],
        source="devpost",
        content_type="json",
        raw_content=_json.dumps(hackathon),
    )


def test_normalize_maps_all_fields_from_realistic_sample():
    agent = DevpostHackathonAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))

    assert opportunity.category == "hackathons"
    assert opportunity.title == "Expo 26 Hackathon"
    assert opportunity.organization == "abbvie"
    assert opportunity.logo_url == "https://d112y698adiu2z.cloudfront.net/photos/example.png"
    assert opportunity.apply_url == "https://expo-26-hackathon.devpost.com/"
    assert opportunity.source_url == "https://expo-26-hackathon.devpost.com/"
    assert opportunity.source == "devpost"
    assert opportunity.source_id == "31050"
    assert opportunity.tags == ["health"]  # normalise_tags lowercases
    assert opportunity.duration == "Sep 09 - 18, 2026"
    assert opportunity.application_deadline == date(2026, 9, 18)
    assert opportunity.is_remote is False
    assert opportunity.location == "The Venue Hotel Jeddah"
    assert "abbvie" in opportunity.description
    assert "$5,000" in opportunity.description


def test_normalize_handles_missing_optional_fields_gracefully():
    agent = DevpostHackathonAgent()
    sparse = _hackathon(
        displayed_location={},
        themes=[],
        prize_amount=None,
        organization_name=None,
        submission_period_dates=None,
        thumbnail_url=None,
    )
    opportunity = agent.normalize(None, _raw_for(sparse))

    assert opportunity.tags == []
    assert opportunity.duration is None
    assert opportunity.application_deadline is None
    assert opportunity.logo_url is None
    assert opportunity.location is None
    assert opportunity.organization is None
    # Still has a usable, non-hallucinated apply_url -- nothing here was invented.
    assert opportunity.apply_url == sparse["url"]


def test_normalize_raises_on_missing_required_fields():
    agent = DevpostHackathonAgent()
    broken = _hackathon()
    del broken["title"]

    with pytest.raises(ValueError):
        agent.normalize(None, _raw_for(broken))


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


def test_validate_accepts_a_good_opportunity():
    agent = DevpostHackathonAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))

    result = agent.validate(None, opportunity)

    assert result.is_valid is True


def test_validate_rejects_non_devpost_apply_url():
    agent = DevpostHackathonAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"apply_url": "https://evil.example.com/apply"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "apply_url" for issue in result.errors)


def test_validate_rejects_wrong_category():
    agent = DevpostHackathonAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"category": "programs"})

    result = agent.validate(None, tampered)

    assert result.is_valid is False
    assert any(issue.field == "category" for issue in result.errors)


def test_validate_warns_on_non_numeric_source_id():
    agent = DevpostHackathonAgent()
    opportunity = agent.normalize(None, _raw_for(_hackathon()))
    tampered = opportunity.model_copy(update={"source_id": "not-a-number"})

    result = agent.validate(None, tampered)

    assert result.is_valid is True  # warning severity, not error
    assert any(
        issue.field == "source_id" and issue.severity == "warning" for issue in result.warnings
    )


# ---------------------------------------------------------------------------
# Full agent.run() -- discover -> extract -> normalize -> validate, through
# the real IngestionPipeline, with per-listing failure isolation.
# ---------------------------------------------------------------------------


async def test_agent_run_end_to_end_produces_valid_hackathon_opportunities():
    page = FakeResponse(
        {
            "hackathons": [
                _hackathon(id=1),
                _hackathon(id=2, invite_only=True),
                _hackathon(id=3, title="Second Hackathon", url="https://second.devpost.com/"),
            ],
            "meta": {"total_count": 3},
        }
    )
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()

    result = await agent.run(_ctx(client))

    # id=2 was invite-only -- discover() filtered it out before extract()
    # ever ran, so it never even shows up as a normalize/validate failure.
    assert result.discovered_count == 2
    assert result.valid_count == 2
    assert result.errors == []
    assert {o.category for o in result.opportunities} == {"hackathons"}
    assert {o.source for o in result.opportunities} == {"devpost"}


async def test_agent_run_isolates_one_malformed_candidate():
    broken = _hackathon(id=99, url="https://broken.devpost.com/")
    del broken["title"]
    page = FakeResponse(
        {"hackathons": [_hackathon(id=1), broken], "meta": {"total_count": 2}}
    )
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()

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
    page = FakeResponse({"hackathons": [_hackathon()], "meta": {"total_count": 1}})
    client = FakeHttpClient([page])
    agent = DevpostHackathonAgent()

    run_result = await agent.run(_ctx(client))

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    batch = await service.save_batch(run_result.opportunities)

    assert batch.created == 1
    assert batch.errors == 0
    (row,) = repository.rows.values()
    assert row["category"] == "hackathons"
    assert row["source"] == "devpost"
    assert row["source_id"] == "31050"
    assert row["is_active"] is True


async def test_dedup_running_ingestion_three_times_creates_no_duplicates():
    # Literal "Devpost ingestion / Devpost ingestion / Devpost ingestion"
    # scenario from the production-readiness review: three independent runs
    # of the exact same source data must converge on exactly one row, not
    # accumulate one per run.
    page = FakeResponse({"hackathons": [_hackathon()], "meta": {"total_count": 1}})

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    run1 = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    batch1 = await service.save_batch(run1.opportunities)
    assert batch1.created == 1
    assert batch1.updated == 0
    assert len(repository.rows) == 1

    # Run 2: (source, source_id) de-dup -- the strong identity match.
    run2 = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    batch2 = await service.save_batch(run2.opportunities)
    assert batch2.created == 0
    assert batch2.updated == 1
    assert len(repository.rows) == 1

    # Run 3: same again -- confirms run 2's update didn't somehow change the
    # identity key (e.g. by re-writing source_id) in a way that would let a
    # fourth run insert a second row.
    run3 = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    batch3 = await service.save_batch(run3.opportunities)
    assert batch3.created == 0
    assert batch3.updated == 1
    assert len(repository.rows) == 1

    (row,) = repository.rows.values()
    assert row["source"] == "devpost"
    assert row["source_id"] == "31050"


async def test_dedup_cross_source_fingerprint_still_works_for_devpost_rows():
    # A second, independent lookup path: if (source, source_id) somehow
    # didn't match (e.g. a different source scraping the same real-world
    # hackathon under a different id), the content fingerprint still catches
    # it. Simulated here by seeding the repository with a row that has a
    # DIFFERENT source/source_id but the SAME (title, organization,
    # apply_url) content Devpost's own listing would normalize to.
    page = FakeResponse({"hackathons": [_hackathon()], "meta": {"total_count": 1}})
    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    run = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
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
    assert len(repository.rows) == 1  # updated the existing row, not a new one


# ---------------------------------------------------------------------------
# 20/day = "B": stop once HACKATHON_DAILY_LIMIT are actually saved, not once
# HACKATHON_DAILY_LIMIT candidates have been attempted.
# ---------------------------------------------------------------------------


async def test_save_batch_stops_at_daily_save_limit_with_headroom(monkeypatch):
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 20)
    monkeypatch.setattr(settings, "HACKATHON_CANDIDATE_POOL_SIZE", 60)

    # 22 fully valid candidates + 3 with an empty title (normalize() raises
    # on those -- an "earlier invalid candidate" that must NOT reduce the
    # final saved count below 20, since there's enough headroom in the pool).
    hackathons = _distinct_hackathons(22)
    hackathons += [
        _hackathon(id=100 + i, url=f"https://hackathon-{100 + i}.devpost.com/", title="")
        for i in range(3)
    ]
    page = FakeResponse({"hackathons": hackathons, "meta": {"total_count": len(hackathons)}})

    run_result = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    assert run_result.valid_count == 22  # the 3 empty-title ones were dropped at normalize()
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
    # Fewer good candidates than the cap exist -- must save all of them
    # without error, not wait for a full batch of 20 that will never come.
    hackathons = _distinct_hackathons(5)
    page = FakeResponse({"hackathons": hackathons, "meta": {"total_count": 5}})

    run_result = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    assert run_result.valid_count == 5

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    batch = await service.save_batch(run_result.opportunities, max_success_count=20)

    assert batch.created == 5
    assert batch.skipped == 0
    assert len(repository.rows) == 5


async def test_devpost_default_config_declares_the_daily_save_limit(monkeypatch):
    monkeypatch.setattr(settings, "HACKATHON_DAILY_LIMIT", 42)
    agent = DevpostHackathonAgent()
    assert agent.config.daily_save_limit == 42


# ---------------------------------------------------------------------------
# Dry run: preview_batch() must resolve identically to save_batch() but
# write nothing.
# ---------------------------------------------------------------------------


async def test_dry_run_preview_batch_makes_zero_writes():
    hackathons = _distinct_hackathons(5)
    page = FakeResponse({"hackathons": hackathons, "meta": {"total_count": 5}})

    run_result = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())
    preview = service.preview_batch(run_result.opportunities, max_success_count=20)

    assert preview.created == 5  # counted as "would create"
    assert repository.rows == {}  # but nothing was actually written
    assert {r.outcome for r in preview.results} == {"would_create"}


async def test_dry_run_preview_batch_detects_existing_duplicates_without_writing():
    hackathons = _distinct_hackathons(3)
    page = FakeResponse({"hackathons": hackathons, "meta": {"total_count": 3}})

    repository = FakeOpportunityRepository()
    service = OpportunityService(repository=repository, queue=FakeQueue())

    # A real run first, so there's something for the dry run to find as a
    # duplicate.
    real_run = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    await service.save_batch(real_run.opportunities)
    assert len(repository.rows) == 3

    dry_run_result = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    preview = service.preview_batch(dry_run_result.opportunities)

    assert preview.created == 0
    assert preview.updated == 3
    assert {r.outcome for r in preview.results} == {"would_update"}
    assert len(repository.rows) == 3  # still just the 3 from the real run above


async def test_dry_run_preview_batch_respects_daily_save_limit_cap():
    hackathons = _distinct_hackathons(10)
    page = FakeResponse({"hackathons": hackathons, "meta": {"total_count": 10}})

    run_result = await DevpostHackathonAgent().run(_ctx(FakeHttpClient([page])))
    service = OpportunityService(repository=FakeOpportunityRepository(), queue=FakeQueue())

    preview = service.preview_batch(run_result.opportunities, max_success_count=4)

    assert preview.created == 4
    assert preview.skipped == 6
