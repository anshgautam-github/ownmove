"""Per-agent configuration — everything about *how* an agent is allowed to
behave (identity, HTTP timeout, retry policy, rate limit), as opposed to
*what* it scrapes (which lives entirely in the agent subclass).

Deliberately separate from scheduling (`app.ingestion.jobs.schedule`): a
`ScheduleConfig` says *when* an agent should run, this says how it should
behave *while* running. Keeping them apart means a source's HTTP manners
don't need to change just because its cadence changes, and vice versa.
"""

from pydantic import BaseModel, Field

from app.core.config import settings


class RetryConfig(BaseModel):
    """See `app.ingestion.utils.retry.retry_async` for how these are used."""

    max_attempts: int = Field(default=3, ge=1)
    base_delay_seconds: float = Field(default=1.0, gt=0)
    max_delay_seconds: float = Field(default=30.0, gt=0)
    # Full jitter (Marc Brooker/AWS style): sleep for `random(0, backoff)`
    # rather than exactly `backoff`, so a bunch of listings failing at once
    # don't all retry in lockstep and hammer the source at the same instant.
    jitter: bool = True


class RateLimitConfig(BaseModel):
    """See `app.ingestion.utils.rate_limit.TokenBucketRateLimiter`."""

    requests_per_second: float = Field(default=1.0, gt=0)
    burst: int = Field(default=1, ge=1)


class AgentConfig(BaseModel):
    """Constructor input for `BaseOpportunityAgent`. A concrete agent
    provides one of these (usually via a small classmethod default plus
    `.env`-driven overrides for tuning) — nothing about the framework itself
    needs to change per source."""

    # Unique key the agent registers under and every result is tagged with.
    # Convention: lowercase, hyphenated, stable forever (it becomes
    # `NormalizedOpportunity.source` / `OpportunityRow.source`).
    source: str
    default_category: str | None = None

    timeout_seconds: float = Field(default=15.0, gt=0)
    user_agent: str = Field(
        default_factory=lambda: settings.INGESTION_USER_AGENT
    )

    retry: RetryConfig = Field(default_factory=RetryConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Concurrent `extract()` calls the pipeline will run for this agent's
    # discovered listings. Independent of `rate_limit`, which throttles
    # request *frequency*; this caps request *concurrency*.
    max_concurrency: int = Field(default=5, ge=1)

    # A disabled agent stays registered (so it still shows up in listings,
    # docs, admin tooling) but `IngestionService.run_all()` skips it.
    enabled: bool = True

    # Optional per-source cap on how many opportunities a single run is
    # allowed to actually INSERT/UPDATE (as opposed to `discover()`'s own
    # candidate-selection limit, which bounds how much extract/normalize/
    # validate work happens). `None` (the default) means "no save cap" --
    # every valid opportunity produced gets saved, the framework's original
    # behavior. A source that wants "at most N *saved* per run" (see
    # `DevpostHackathonAgent.default_config()`) sets this; the actual
    # stopping logic lives in `OpportunityService.save_batch()`/
    # `preview_batch()`'s `max_success_count` parameter, not here -- this
    # field is just how an agent communicates its own target to whatever
    # persists its output.
    daily_save_limit: int | None = Field(default=None, ge=1)

    @classmethod
    def with_defaults(cls, source: str, **overrides) -> "AgentConfig":
        """Convenience for the common case of using the ingestion-wide
        defaults from `app.core.config.settings` with a couple of per-agent
        overrides — see `app/ingestion/README.md` for an example agent."""
        base = {
            "source": source,
            "timeout_seconds": settings.INGESTION_DEFAULT_TIMEOUT_SECONDS,
            "retry": RetryConfig(
                max_attempts=settings.INGESTION_DEFAULT_MAX_RETRIES,
                base_delay_seconds=settings.INGESTION_DEFAULT_RETRY_BASE_DELAY_SECONDS,
            ),
            "rate_limit": RateLimitConfig(
                requests_per_second=settings.INGESTION_DEFAULT_RATE_LIMIT_PER_SECOND,
                burst=settings.INGESTION_DEFAULT_BURST,
            ),
            "max_concurrency": settings.INGESTION_DEFAULT_MAX_CONCURRENCY,
        }
        base.update(overrides)
        return cls(**base)
