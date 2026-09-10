"""`IngestionPipeline` — orchestrates discover -> extract -> normalize ->
validate for any `BaseOpportunityAgent`, identical regardless of source.

Flow, per the framework spec:

    Agent
      -> discover()      one retried, rate-limited call -> list[DiscoveredListing]
      -> extract()       per-listing, retried + rate-limited + bounded-concurrency
      -> normalize()     per-listing, pure
      -> validate()      per-listing, pure
      -> AgentRunResult  in-memory only — nothing here writes to a database

A failure at any per-listing stage is recorded as an `IngestionError` and
that listing is skipped; it never aborts the rest of the run. A failure at
`discover()` — there being nothing to discover from — does abort the run,
since there is nothing left to process.

Ordering: `result.opportunities`/`result.errors` are assembled in the SAME
order as `listings` (the order `discover()` returned them in), even though
each listing's extract/normalize/validate runs concurrently (bounded by
`max_concurrency`). This matters for an agent whose `discover()` already
ranked its candidates best-first (see `DevpostHackathonAgent.discover()`):
a caller that wants "the top N *valid* opportunities" can just take the
first N of `result.opportunities` in order, without needing to know how the
pipeline scheduled its internal work. This relies on `asyncio.gather`'s
documented guarantee that returned results are ordered to match the input
awaitables, regardless of completion order — not on any locking.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.run import AgentRunResult, IngestionError
from app.ingestion.utils.logging import IngestionLogAdapter
from app.ingestion.utils.retry import RetryExhaustedError, retry_async


@dataclass
class _ListingOutcome:
    """What one listing's extract -> normalize -> validate produced —
    returned by `_process_listing` rather than mutating `AgentRunResult`
    directly, so `IngestionPipeline.run()` can apply every outcome back
    onto `result` in `listings` order after `asyncio.gather` completes (see
    module docstring's "Ordering" note)."""

    extracted: bool = False
    normalized: bool = False
    valid: bool | None = None  # None until validate() actually runs
    opportunity: NormalizedOpportunity | None = None
    error: IngestionError | None = None

    def apply(self, result: AgentRunResult) -> None:
        if self.extracted:
            result.extracted_count += 1
        if self.normalized:
            result.normalized_count += 1
        if self.valid is True:
            result.valid_count += 1
            if self.opportunity is not None:
                result.opportunities.append(self.opportunity)
        elif self.valid is False:
            result.invalid_count += 1
        if self.error is not None:
            result.errors.append(self.error)


class IngestionPipeline:
    """Stateless orchestrator — holds no run-specific state itself
    (`AgentRunResult` does), so one instance can be reused across agents and
    runs, or constructed fresh per call; both are equivalent."""

    async def run(self, agent: BaseOpportunityAgent, ctx: AgentContext) -> AgentRunResult:
        result = AgentRunResult(run_id=ctx.run_id, source=agent.source)
        logger = ctx.logger.bind(run_id=ctx.run_id, stage="discover")

        # ---- 1. discover -----------------------------------------------------
        logger.info("Starting discovery")
        try:
            listings = await self._call_with_retry(
                agent.discover, ctx, config=ctx.config.retry, logger=logger
            )
        except RetryExhaustedError as exc:
            logger.warning("Discovery failed after %d attempt(s): %s", exc.attempts, exc.last_error)
            result.errors.append(
                IngestionError(stage="discover", message=str(exc.last_error), attempts=exc.attempts)
            )
            return result.mark_finished()

        result.discovered_count = len(listings)
        # Opt-in: an agent whose discover() ranks/caps its own raw candidate
        # pool may report the pre-cap count here — see
        # `BaseOpportunityAgent.last_discovery_stats`'s docstring.
        if agent.last_discovery_stats is not None:
            result.raw_candidate_count = agent.last_discovery_stats.get("raw_discovered")
        logger.info("Discovered %d listing(s)", len(listings))

        # ---- 2-4. extract -> normalize -> validate, per listing --------------
        semaphore = asyncio.Semaphore(max(1, ctx.config.max_concurrency))

        async def process(listing: DiscoveredListing) -> _ListingOutcome:
            async with semaphore:
                return await self._process_listing(agent, ctx, listing)

        # `asyncio.gather` returns results in the order of the awaitables
        # passed to it, regardless of completion order — so `outcomes[i]`
        # corresponds to `listings[i]` even though the tasks themselves ran
        # concurrently. Applying them in this order is what preserves
        # discover()'s own ranking all the way through to `result.opportunities`.
        outcomes = await asyncio.gather(*(process(listing) for listing in listings))
        for outcome in outcomes:
            outcome.apply(result)

        ctx.logger.bind(run_id=ctx.run_id).info(
            "Run finished: %d extracted, %d normalized, %d valid, %d invalid, %d error(s)",
            result.extracted_count,
            result.normalized_count,
            result.valid_count,
            result.invalid_count,
            len(result.errors),
        )
        return result.mark_finished()

    async def _process_listing(
        self,
        agent: BaseOpportunityAgent,
        ctx: AgentContext,
        listing: DiscoveredListing,
    ) -> _ListingOutcome:
        listing_logger = ctx.logger.bind(run_id=ctx.run_id, stage="extract", url=listing.url)
        outcome = _ListingOutcome()

        # ---- extract: I/O, so it's the stage that's rate-limited + retried ---
        try:
            raw: RawExtraction = await self._call_with_retry(
                agent.extract,
                ctx,
                listing,
                config=ctx.config.retry,
                logger=listing_logger,
                rate_limited=True,
            )
        except RetryExhaustedError as exc:
            listing_logger.warning(
                "Extraction failed after %d attempt(s): %s", exc.attempts, exc.last_error
            )
            outcome.error = IngestionError(
                stage="extract", url=listing.url, message=str(exc.last_error), attempts=exc.attempts
            )
            return outcome
        outcome.extracted = True

        # ---- normalize: pure transform, no retry / no rate limit --------------
        try:
            normalized: NormalizedOpportunity = agent.normalize(ctx, raw)
        except Exception as exc:  # noqa: BLE001 - a source's own parser can raise anything
            listing_logger.warning("Normalization failed: %s", exc)
            outcome.error = IngestionError(stage="normalize", url=listing.url, message=str(exc))
            return outcome
        outcome.normalized = True

        # ---- validate: pure check, no retry / no rate limit --------------------
        try:
            validation = agent.validate(ctx, normalized)
        except Exception as exc:  # noqa: BLE001
            listing_logger.warning("Validation raised unexpectedly: %s", exc)
            outcome.error = IngestionError(stage="validate", url=listing.url, message=str(exc))
            return outcome

        if validation.is_valid:
            outcome.valid = True
            outcome.opportunity = normalized
            if validation.warnings:
                listing_logger.info(
                    "Accepted with %d warning(s): %s", len(validation.warnings), validation.warnings
                )
        else:
            outcome.valid = False
            listing_logger.info("Rejected by validate(): %s", validation.errors)

        return outcome

    @staticmethod
    async def _call_with_retry(
        fn: Callable[..., Awaitable],
        ctx: AgentContext,
        *args,
        config,
        logger: IngestionLogAdapter,
        rate_limited: bool = False,
    ):
        async def attempt():
            if rate_limited:
                await ctx.rate_limiter.acquire()
            return await fn(ctx, *args)

        def on_retry(attempt_number: int, exc: BaseException) -> None:
            logger.info("Attempt %d failed (%s); retrying", attempt_number, exc)

        return await retry_async(attempt, config=config, on_retry=on_retry)
