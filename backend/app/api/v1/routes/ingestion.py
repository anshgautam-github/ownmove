"""Opportunity ingestion trigger -- the smallest production-appropriate
mechanism to actually execute `app.ingestion` on a schedule (see
`app/ingestion/jobs/registry.py`'s `JobRegistry.due_sources()` docstring:
"nothing calls this on a timer yet").

This module IS that missing timer's trigger point, not the timer itself:
a daily cron job, a Supabase scheduled Edge Function, or any other external
scheduler hits `POST /ingestion/run-due` once a day (or once a minute, if
it wants cron-granularity scheduling -- `due_sources()` only returns sources
that are actually due, so an over-frequent caller is a no-op most of the
time, not a problem). Deliberately NOT a background-worker/queue-based
design (`app.workers.queue.get_queue()` is still an in-memory no-op --
see that module) -- running Devpost's ingestion inline, synchronously,
within one HTTP request is well within a normal request timeout (a handful
of rate-limited `/api/hackathons` page fetches, no per-listing network
calls -- see `DevpostHackathonAgent.extract()`), so there is no real
infrastructure to add here yet. If a future source is slow enough that this
stops being true, that's the point to introduce a real queue -- not before.

Auth: a single shared-secret header (`X-Ingestion-Admin-Key`), checked
against `settings.INGESTION_ADMIN_API_KEY`. Deliberately NOT built on
`CurrentUser`/`app.core.security.verify_token` (see `app/api/deps.py`) --
those authenticate a *person* via their own Supabase session, and nothing
in this codebase has an admin/role concept to layer on top of one yet (no
`is_admin` column, no role claim, nothing). Building a full RBAC system
just for this one trigger route would be exactly the kind of heavyweight
infrastructure the framework spec asks agents/routes to avoid adding without
real justification. A shared secret between this API and whatever external
scheduler calls it is the right amount of protection for a single
server-to-server trigger; if more admin-only endpoints get added later,
that's the point to build a real admin-role system and migrate this route
onto it, not before. `INGESTION_ADMIN_API_KEY` defaults to `""`, which
means this router FAILS CLOSED (503) rather than open until an operator
deliberately configures it. The key itself is never logged or echoed back
in any response -- see `require_ingestion_admin_key()` and
`_run_and_persist()` below, neither of which ever touches the header value
except to compare it.

Dry run: every route below accepts `?dry_run=true`. A dry run runs the
EXACT same discover -> extract -> normalize -> validate pipeline (already
100% read-only -- see `app/ingestion/pipeline/runner.py`'s module
docstring) and the exact same duplicate-detection reads
(`OpportunityService.preview_batch()`, which shares its resolution logic
with the real `save_batch()` -- see that module), but calls zero
`insert()`/`update()`/enrichment-enqueue operations. Use it to sanity-check
a source (new config, a code change, an unfamiliar day's data) before
letting it write.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.core.logging import get_logger

# Import side effect: registers every real source agent (currently just
# DevpostHackathonAgent) with `agent_registry`, and its schedule with
# `job_registry` -- see `app/ingestion/agents/sources/__init__.py`'s
# docstring for why this is the one place that import needs to happen.
from app.ingestion.agents.sources import DevpostHackathonAgent  # noqa: F401
from app.ingestion.models.summary import IngestionRunSummary, build_run_summary
from app.ingestion.services.ingestion_service import IngestionService
from app.ingestion.services.opportunity_service import OpportunityService

logger = get_logger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


async def require_ingestion_admin_key(
    x_ingestion_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.INGESTION_ADMIN_API_KEY:
        raise ServiceUnavailableError(
            "Ingestion endpoints are disabled: INGESTION_ADMIN_API_KEY is not configured."
        )
    if not x_ingestion_admin_key or x_ingestion_admin_key != settings.INGESTION_ADMIN_API_KEY:
        raise UnauthorizedError("Missing or invalid X-Ingestion-Admin-Key header.")


async def _run_and_persist(
    service: IngestionService, source: str, *, dry_run: bool
) -> IngestionRunSummary:
    """Shared by both routes below: run one source through the pipeline,
    then either persist what it produced (`save_batch`) or, for a dry run,
    only preview what WOULD happen (`preview_batch`) -- see module
    docstring. Either way, `run_result.daily_save_limit` (the agent's own
    declared cap -- see `AgentConfig.daily_save_limit`) is what stops the
    batch early once enough candidates have been created/updated (or, in a
    dry run, would have been).
    """
    run_result = await service.run_source(source)
    opportunity_service = OpportunityService()

    if dry_run:
        batch_result = opportunity_service.preview_batch(
            run_result.opportunities, max_success_count=run_result.daily_save_limit
        )
    else:
        batch_result = await opportunity_service.save_batch(
            run_result.opportunities, max_success_count=run_result.daily_save_limit
        )

    return build_run_summary(run_result, batch_result, dry_run=dry_run)


@router.post(
    "/run/{source}",
    summary="Run one registered ingestion source on demand, optionally as a dry run",
    dependencies=[Depends(require_ingestion_admin_key)],
    response_model=IngestionRunSummary,
)
async def run_source(
    source: str,
    dry_run: Annotated[
        bool, Query(description="If true, run discovery/validation/dedup but write nothing.")
    ] = False,
) -> IngestionRunSummary:
    service = IngestionService()
    summary = await _run_and_persist(service, source, dry_run=dry_run)
    logger.info(
        "Ingestion run via API: source=%s dry_run=%s status=%s inserted=%d updated=%d failed=%d",
        source,
        dry_run,
        summary.status,
        summary.inserted,
        summary.updated,
        summary.failed,
    )
    return summary


@router.get(
    "/due",
    summary="List registered sources whose schedule says they should run right now",
    dependencies=[Depends(require_ingestion_admin_key)],
)
async def due_sources() -> dict:
    service = IngestionService()
    return {"due": service.due_sources()}


@router.post(
    "/run-due",
    summary="Run every currently-due registered source, optionally as a dry run",
    dependencies=[Depends(require_ingestion_admin_key)],
)
async def run_due_sources(
    dry_run: Annotated[
        bool, Query(description="If true, run discovery/validation/dedup but write nothing.")
    ] = False,
) -> dict:
    """The actual daily-cron integration point (see module docstring): an
    external scheduler hits this on a cadence at least as fine as the
    tightest `ScheduleConfig` any registered source uses (daily, for
    Devpost -- see `app/ingestion/agents/sources/devpost.py`). Sources that
    aren't due yet are silently skipped, not errored, so calling this more
    often than necessary (e.g. hourly, to approximate cron-minute
    granularity for a future source with a tighter schedule) is safe.
    """
    service = IngestionService()
    due = service.due_sources()
    results = [await _run_and_persist(service, source, dry_run=dry_run) for source in due]
    logger.info("Ingestion run-due via API: due=%s dry_run=%s", due, dry_run)
    return {"due": due, "dry_run": dry_run, "results": results}
