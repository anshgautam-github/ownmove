"""`BaseOpportunityAgent` — the interface every opportunity source
implements — and `AgentContext`, the framework's dependency-injection seam.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4

import httpx

from app.ingestion.models.config import AgentConfig
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.run import AgentRunResult
from app.ingestion.models.validation import ValidationResult
from app.ingestion.utils.logging import IngestionLogAdapter, get_agent_logger
from app.ingestion.utils.rate_limit import RateLimiter, build_rate_limiter


@dataclass
class AgentContext:
    """Everything an agent's `discover`/`extract` calls need injected
    rather than constructed inline — the framework's dependency-injection
    seam. A test can hand an agent a context with a fake `http_client`/
    `rate_limiter` and never touch the network; production code gets one
    built by `IngestionPipeline`/`IngestionService` from the agent's own
    `AgentConfig`, shared across every listing in a run so rate limiting is
    enforced across the whole run rather than reset per-listing.
    """

    config: AgentConfig
    http_client: httpx.AsyncClient
    rate_limiter: RateLimiter
    logger: IngestionLogAdapter
    run_id: str = field(default_factory=lambda: uuid4().hex)


class BaseOpportunityAgent(ABC):
    """The interface every opportunity source implements.

    Adding a new source means writing exactly one new subclass that
    implements `discover`, `extract`, `normalize` and `validate` — see
    `app/ingestion/README.md` for a full worked example. `run()` is
    intentionally NOT abstract: it is a concrete template method every
    agent inherits for free, wiring those four steps together through the
    shared `IngestionPipeline` (retry, rate limiting, structured logging,
    and per-listing error isolation already applied there). "Every agent
    implements `run()`" is satisfied by inheritance — the base class exists
    specifically so no subclass has to hand-write orchestration logic that
    would otherwise be identical across every source.

    Override `run()` itself only if a source genuinely can't be expressed
    as "discover URLs, then per-URL extract -> normalize -> validate" —
    that should be rare enough to warrant a second look before doing it.
    """

    #: Unique, stable key this agent registers under — also becomes
    #: `NormalizedOpportunity.source`. Set as a class attribute on every
    #: subclass (or override `default_config()` to supply it another way).
    source: str = ""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or self.default_config()
        if not self.config.source:
            raise ValueError(f"{type(self).__name__}.config.source must be set.")
        self.source = self.config.source
        # Optional, opt-in: a `discover()` implementation that ranks/caps
        # its own candidates (see `DevpostHackathonAgent.discover()`) MAY
        # set this to a dict of small stats before returning, e.g.
        # `{"raw_discovered": 47, "selected": 25}`. `IngestionPipeline`
        # copies `"raw_discovered"` onto `AgentRunResult.raw_candidate_count`
        # if present. Agents that don't set it (the common case -- most
        # sources' `discovered_count` already IS the raw count) leave this
        # `None`, and nothing downstream requires it to be set.
        self.last_discovery_stats: dict[str, int] | None = None

    # ---- subclass hook: configuration -------------------------------------

    @classmethod
    def default_config(cls) -> AgentConfig:
        """The config used when a subclass is instantiated with no explicit
        `AgentConfig` — sane framework defaults (see
        `app.core.config.settings`) keyed to `cls.source`. Override to set
        source-specific timeouts/retry/rate-limit values without forcing
        every call site to pass a config."""
        if not cls.source:
            raise ValueError(f"{cls.__name__} must set a `source` class attribute or override `default_config()`.")
        return AgentConfig.with_defaults(source=cls.source)

    # ---- the four steps every source-specific subclass implements --------

    @abstractmethod
    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        """Find candidate opportunity URLs (e.g. paginate a listing page,
        call a source's search API). Return every `DiscoveredListing`
        found — the pipeline handles concurrency and rate limiting for the
        `extract()` calls that follow, so `discover()` itself doesn't need
        to throttle its own pagination beyond using `ctx.rate_limiter` for
        each page request it makes."""

    @abstractmethod
    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        """Fetch the raw content for one discovered listing. Should do the
        minimum I/O necessary (one page fetch, one API call) — parsing
        belongs in `normalize()`, not here. The pipeline wraps this call
        with `ctx.rate_limiter.acquire()` and the agent's `RetryConfig`
        automatically; implementations don't need to retry internally."""

    @abstractmethod
    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        """Parse `raw.raw_content` into a `NormalizedOpportunity`. Pure/CPU
        work — no I/O, no network calls — so the pipeline never retries or
        rate-limits it. Raise on unparseable content; the pipeline records
        it as an `IngestionError` for that URL and continues with the rest
        of the run rather than aborting."""

    @abstractmethod
    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        """Decide whether a normalized opportunity is good enough to keep.
        Most implementations should start with
        `app.ingestion.utils.validation.basic_field_checks()` for the
        generic checks (non-empty title, well-formed URLs, a de-dupe key)
        and layer source-specific rules on top."""

    # ---- the shared orchestration every agent gets for free ---------------

    async def run(self, ctx: AgentContext | None = None) -> AgentRunResult:
        """Run this agent end-to-end through the shared
        `IngestionPipeline`. Building a default `AgentContext` when none is
        given keeps `agent.run()` usable standalone (a script, a test, a
        REPL); `IngestionService.run_all()` instead builds and passes one
        context per agent itself, which is the normal production path.
        """
        # Local import: `pipeline.runner` imports agent *types* for type
        # hints, so importing it at module load time here would cycle.
        from app.ingestion.pipeline.runner import IngestionPipeline

        owns_context = ctx is None
        if ctx is None:
            ctx = await self.build_default_context()

        try:
            return await IngestionPipeline().run(self, ctx)
        finally:
            if owns_context:
                await ctx.http_client.aclose()

    async def build_default_context(self) -> AgentContext:
        """Construct a context from this agent's own `AgentConfig`. Used
        only when nothing is injected (see `run()` above) — production
        orchestration (`IngestionService`) builds and shares contexts
        itself instead of relying on this."""
        return AgentContext(
            config=self.config,
            http_client=httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                headers={"User-Agent": self.config.user_agent},
                follow_redirects=True,
            ),
            rate_limiter=build_rate_limiter(self.config.rate_limit),
            logger=get_agent_logger(self.source),
        )
