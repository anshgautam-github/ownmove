"""Exercises the Opportunity Ingestion Framework end-to-end with an
in-memory fake agent — no real network calls, no database. Confirms the
framework's own machinery (pipeline orchestration, retry, rate limiting,
registries, service layer, scheduling) works before any source-specific
crawler is written against it.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import NotFoundError
from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import AgentRegistry
from app.ingestion.jobs.registry import JobRegistry
from app.ingestion.jobs.schedule import ScheduleConfig, should_run
from app.ingestion.models.config import AgentConfig, RateLimitConfig, RetryConfig
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.validation import ValidationResult
from app.ingestion.services.ingestion_service import IngestionService
from app.ingestion.utils.rate_limit import TokenBucketRateLimiter
from app.ingestion.utils.retry import RetryExhaustedError, retry_async
from app.ingestion.utils.validation import basic_field_checks, to_validation_result


class FakeAgent(BaseOpportunityAgent):
    """Discovers 3 fixed listings; `fail_urls` lets a test force `extract()`
    to raise for specific ones, to exercise the error/retry path."""

    source = "fake-source"

    def __init__(self, config: AgentConfig | None = None, *, fail_urls: set[str] | None = None):
        super().__init__(config)
        self.fail_urls = fail_urls or set()

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        return [DiscoveredListing(url=f"https://example.com/{i}", source=self.source) for i in range(3)]

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        if listing.url in self.fail_urls:
            raise RuntimeError(f"simulated failure for {listing.url}")
        return RawExtraction(url=listing.url, source=self.source, raw_content=f"title:{listing.url}")

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        return NormalizedOpportunity(
            category="programs",
            title=raw.raw_content.split(":", 1)[1],
            apply_url=raw.url,
            source=self.source,
            source_id=raw.url,
        )

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        return to_validation_result(basic_field_checks(opportunity))


# Fast retry settings so failure-path tests don't actually sleep for seconds.
_FAST_RETRY = RetryConfig(max_attempts=2, base_delay_seconds=0.001, max_delay_seconds=0.002)


async def test_agent_run_succeeds_end_to_end():
    agent = FakeAgent()
    result = await agent.run()

    assert result.discovered_count == 3
    assert result.extracted_count == 3
    assert result.normalized_count == 3
    assert result.valid_count == 3
    assert result.invalid_count == 0
    assert result.errors == []
    assert result.status == "success"
    assert {o.apply_url for o in result.opportunities} == {
        "https://example.com/0",
        "https://example.com/1",
        "https://example.com/2",
    }


async def test_agent_run_isolates_per_listing_failures():
    config = AgentConfig.with_defaults(source="fake-source", retry=_FAST_RETRY)
    agent = FakeAgent(config, fail_urls={"https://example.com/1"})

    result = await agent.run()

    assert result.discovered_count == 3
    assert result.valid_count == 2
    assert len(result.errors) == 1
    assert result.errors[0].stage == "extract"
    assert result.errors[0].url == "https://example.com/1"
    assert result.status == "partial"


async def test_agent_registry_register_and_lookup():
    registry = AgentRegistry()
    registry.register(FakeAgent)

    assert "fake-source" in registry
    assert registry.get("fake-source") is FakeAgent
    assert registry.all_sources() == ["fake-source"]

    with pytest.raises(KeyError):
        registry.get("does-not-exist")

    with pytest.raises(ValueError):
        class DuplicateAgent(FakeAgent):
            pass

        registry.register(DuplicateAgent)


async def test_ingestion_service_run_source_and_run_all():
    registry = AgentRegistry()
    registry.register(FakeAgent)
    jobs = JobRegistry()
    service = IngestionService(agents=registry, jobs=jobs)

    result = await service.run_source("fake-source")
    assert result.valid_count == 3
    assert jobs.last_run_at("fake-source") is not None

    with pytest.raises(NotFoundError):
        await service.run_source("unknown-source")

    all_results = await service.run_all()
    assert len(all_results) == 1
    assert all_results[0].source == "fake-source"


async def test_retry_async_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    value = await retry_async(flaky, config=RetryConfig(max_attempts=5, base_delay_seconds=0.001, max_delay_seconds=0.002))

    assert value == "ok"
    assert calls["n"] == 3


async def test_retry_async_raises_after_exhausting_attempts():
    async def always_fails():
        raise ValueError("permanent")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await retry_async(always_fails, config=_FAST_RETRY)

    assert exc_info.value.attempts == 2
    assert isinstance(exc_info.value.last_error, ValueError)


async def test_token_bucket_rate_limiter_allows_burst_then_throttles():
    limiter = TokenBucketRateLimiter(RateLimitConfig(requests_per_second=1000, burst=2))

    # Burst of 2 should be immediate; this just confirms it doesn't raise
    # or hang for a generous rate/burst combination.
    await limiter.acquire()
    await limiter.acquire()


def test_interval_schedule_due_logic():
    now = datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc)
    schedule = ScheduleConfig.every(60)

    assert should_run(schedule, last_run_at=None, now=now) is True
    assert should_run(schedule, last_run_at=now, now=now) is False
    assert should_run(schedule, last_run_at=now - timedelta(seconds=61), now=now) is True

    disabled = ScheduleConfig(kind="interval", interval_seconds=60, enabled=False)
    assert should_run(disabled, last_run_at=None, now=now) is False


def test_cron_schedule_due_logic():
    now = datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc)  # a Thursday
    schedule = ScheduleConfig.cron("0 10 * * *")  # every day at 10:00

    assert should_run(schedule, last_run_at=None, now=now) is True
    assert should_run(schedule, last_run_at=now - timedelta(days=1), now=now) is True
    assert should_run(schedule, last_run_at=now, now=now) is False

    off_hour = now.replace(hour=11)
    assert should_run(schedule, last_run_at=None, now=off_hour) is False


# ---------------------------------------------------------------------------
# Ordering: result.opportunities must come back in the SAME order as
# discover() returned its listings, even though extract/normalize/validate
# run concurrently -- see pipeline/runner.py's module docstring.
# ---------------------------------------------------------------------------


class _VariableDelayAgent(BaseOpportunityAgent):
    """Discovers N listings in a fixed order, but extract() for EARLIER
    listings deliberately finishes LATER (a descending artificial delay) --
    if the pipeline naively appended to a shared list as each task
    completed, this would come back in REVERSE order. Proves ordering is
    preserved by construction (asyncio.gather's return-order guarantee),
    not by accident of scheduling."""

    source = "variable-delay-source"

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        return [
            DiscoveredListing(url=f"https://example.com/{i}", source=self.source) for i in range(5)
        ]

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        index = int(listing.url.rsplit("/", 1)[1])
        # Descending delay: listing 0 finishes LAST, listing 4 finishes FIRST.
        await asyncio.sleep(0.01 * (5 - index))
        return RawExtraction(
            url=listing.url, source=self.source, raw_content=f"title:{listing.url}"
        )

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        return NormalizedOpportunity(
            category="programs",
            title=raw.raw_content.split(":", 1)[1],
            apply_url=raw.url,
            source=self.source,
            source_id=raw.url,
        )

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        return to_validation_result(basic_field_checks(opportunity))


async def test_pipeline_preserves_discover_order_despite_concurrent_completion():
    config = AgentConfig.with_defaults(source="variable-delay-source", max_concurrency=5)
    agent = _VariableDelayAgent(config)

    result = await agent.run()

    expected = [f"https://example.com/{i}" for i in range(5)]
    assert [o.source_id for o in result.opportunities] == expected


async def test_pipeline_reports_raw_discovery_stats_when_agent_provides_them():
    class RankingAgent(FakeAgent):
        source = "ranking-source"

        async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
            listings = await super().discover(ctx)
            self.last_discovery_stats = {"raw_discovered": 99, "selected": len(listings)}
            return listings

    agent = RankingAgent(AgentConfig.with_defaults(source="ranking-source"))
    result = await agent.run()

    assert result.raw_candidate_count == 99
    assert result.discovered_count == 3


async def test_pipeline_leaves_raw_candidate_count_none_when_agent_does_not_report_it():
    result = await FakeAgent().run()
    assert result.raw_candidate_count is None


# ---------------------------------------------------------------------------
# AgentConfig.daily_save_limit propagation: IngestionService relays an
# agent's own declared save cap onto AgentRunResult, for a persister to use.
# ---------------------------------------------------------------------------


async def test_ingestion_service_relays_daily_save_limit_onto_run_result():
    registry = AgentRegistry()
    registry.register(FakeAgent)
    jobs = JobRegistry()
    service = IngestionService(agents=registry, jobs=jobs)

    # FakeAgent's default_config() doesn't set daily_save_limit -- confirms
    # the "no cap" default (None) survives the relay untouched.
    result = await service.run_source("fake-source")
    assert result.daily_save_limit is None


async def test_ingestion_service_relays_a_configured_daily_save_limit():
    class CappedAgent(FakeAgent):
        source = "capped-source"

        @classmethod
        def default_config(cls) -> AgentConfig:
            return AgentConfig.with_defaults(source=cls.source, daily_save_limit=7)

    registry = AgentRegistry()
    registry.register(CappedAgent)
    jobs = JobRegistry()
    service = IngestionService(agents=registry, jobs=jobs)

    result = await service.run_source("capped-source")

    assert result.daily_save_limit == 7
