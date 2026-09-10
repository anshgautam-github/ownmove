"""`IngestionService` — the dependency-injection-friendly entrypoint the
rest of the backend calls (a future thin router, a worker task, a
management script, or a scheduler tick) instead of reaching into
`AgentRegistry` / `IngestionPipeline` / `JobRegistry` directly.

Like every other service in this codebase (see `backend/README.md`'s
"Services never import FastAPI"), this raises `AppError` subclasses and
returns plain data — it is callable from a route, a background worker, or a
script identically. Nothing here persists anything: `run_source()`/
`run_all()` return in-memory `AgentRunResult`s, matching the framework-wide
"no database writes yet" constraint (see the package README).
"""

import asyncio

import httpx

from app.core.exceptions import NotFoundError
from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import AgentRegistry, agent_registry
from app.ingestion.jobs.registry import JobRegistry, job_registry
from app.ingestion.models.run import AgentRunResult
from app.ingestion.pipeline.runner import IngestionPipeline
from app.ingestion.utils.logging import get_agent_logger
from app.ingestion.utils.rate_limit import build_rate_limiter
from app.utils.time import utc_now


class IngestionService:
    """Takes its collaborators as constructor arguments rather than reaching
    for module-level singletons directly. The process-wide `agent_registry`/
    `job_registry` are just the defaults — a test can construct an
    `IngestionService` around fake registries and a fake `IngestionPipeline`
    with zero monkeypatching."""

    def __init__(
        self,
        *,
        agents: AgentRegistry | None = None,
        pipeline: IngestionPipeline | None = None,
        jobs: JobRegistry | None = None,
    ) -> None:
        self.agents = agents or agent_registry
        self.pipeline = pipeline or IngestionPipeline()
        self.jobs = jobs or job_registry

    async def run_source(self, source: str) -> AgentRunResult:
        """Run exactly one registered agent end-to-end. Raises
        `NotFoundError` — the same `AppError` subclass a route would use —
        if `source` isn't registered, so this is directly callable from a
        future route with no translation layer needed."""
        try:
            agent_cls = self.agents.get(source)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc

        return await self._run_and_record(agent_cls())

    async def run_all(self, *, only_enabled: bool = True) -> list[AgentRunResult]:
        """Run every registered agent concurrently. Each agent gets its own
        `AgentContext` (own HTTP client, own rate limiter), so one slow or
        failing source can never block or throttle another."""
        agents = [agent_cls() for agent_cls in self.agents.all()]
        if only_enabled:
            agents = [agent for agent in agents if agent.config.enabled]

        results = await asyncio.gather(*(self._run_and_record(agent) for agent in agents))
        return list(results)

    def due_sources(self) -> list[str]:
        """Registered, schedulable sources whose `ScheduleConfig` says they
        should run right now. Exposed so a future scheduler loop only ever
        needs to call `due_sources()` then `run_source()` per result — it
        never has to know `JobRegistry`/`AgentRegistry` exist. No scheduler
        loop calls this yet (see `app/ingestion/jobs/__init__.py`)."""
        return [source for source in self.jobs.due_sources() if source in self.agents]

    async def _run_and_record(self, agent: BaseOpportunityAgent) -> AgentRunResult:
        ctx = await self._build_context(agent)
        try:
            result = await self.pipeline.run(agent, ctx)
        finally:
            await ctx.http_client.aclose()

        # Relay the agent's own declared save cap (if any) onto the result,
        # so a caller that persists `result.opportunities` (the ingestion
        # route today) knows how many it's allowed to actually save without
        # needing to know `agent.config` exists -- see
        # `AgentConfig.daily_save_limit`'s docstring.
        result.daily_save_limit = agent.config.daily_save_limit

        self.jobs.record_run(agent.source, at=utc_now())
        return result

    @staticmethod
    async def _build_context(agent: BaseOpportunityAgent) -> AgentContext:
        """The service's own dependency-injection point for the normal
        production path: one fresh `AgentContext` per run, built from the
        agent's `AgentConfig`. Tests that want a fake HTTP client/rate
        limiter should construct an `AgentContext` themselves and call
        `agent.run(ctx)` directly rather than going through this."""
        return AgentContext(
            config=agent.config,
            http_client=httpx.AsyncClient(
                timeout=agent.config.timeout_seconds,
                headers={"User-Agent": agent.config.user_agent},
                follow_redirects=True,
            ),
            rate_limiter=build_rate_limiter(agent.config.rate_limit),
            logger=get_agent_logger(agent.source),
        )
