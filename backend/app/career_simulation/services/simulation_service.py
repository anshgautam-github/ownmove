"""Orchestration only — no FastAPI imports, mirrors
`app.career_roadmap.services.roadmap_service` and
`app.profile_analysis.services.analysis_service` in shape. Read this file
first to understand the whole feature: create pending row -> generate ->
complete/fail -> return.

Security note (binding, from the feature spec): `profile_id` is ALWAYS
`user_id` taken from the authenticated caller (`CurrentUser`/`AccessToken`
in the router), never a value read from the request body — a client cannot
ask this service to create, read, or list simulations for anyone but
themselves, regardless of what a request payload might contain. LLM calls
happen only in this backend process; the API key is never sent to or
usable by the frontend.

Data-integrity note (also binding): nothing here ever writes to
`profiles`, `experiences`, or any other real-data table based on a
simulation's hypothetical result — `career_simulations` rows are the only
place simulation output is ever persisted.
"""

from datetime import datetime, timezone

from app.career_simulation.schemas.simulation import (
    CareerSimulationResponse,
    SimulationCompareRequest,
    SimulationCreateRequest,
    SimulationHistoryItem,
)
from app.career_simulation.services.generators.factory import get_simulation_generator
from app.career_simulation.services.repository import CareerSimulationRepository
from app.career_simulation.utils.context import SimulationContext
from app.core.exceptions import NotFoundError
from app.db.supabase import get_supabase

# The LLM-facing `verdict.level` inside `result` is UPPERCASE; the DB's flat
# `verdict` column has a CHECK constraint requiring lowercase snake_case.
# This is the one place that translation happens (see schemas/simulation.py's
# module docstring for the full reasoning).
_VERDICT_DB_MAP = {
    "HIGH_VALUE": "high_value",
    "USEFUL": "useful",
    "LIMITED_VALUE": "limited_value",
    "LOW_VALUE": "low_value",
}


def _to_response(row: dict) -> CareerSimulationResponse:
    return CareerSimulationResponse(
        id=row["id"],
        profile_id=row["profile_id"],
        simulation_type=row["simulation_type"],
        target_role=row["target_role"],
        scenario_title=row["scenario_title"],
        scenario_input=row.get("scenario_input") or {},
        result=row.get("result"),
        verdict=row.get("verdict"),
        status=row["status"],
        model_used=row.get("model_used"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_simulation(
    *, user_id: str, access_token: str, request: SimulationCreateRequest
) -> CareerSimulationResponse:
    """Run one hypothetical action against the authenticated user's own
    profile and persist the result. Two-phase write: an initial `pending`
    row is inserted before the generator runs, then updated to `completed`
    (with the result) or `failed` — so a crash mid-generation still leaves
    an honest, visible record rather than silently losing the attempt.
    """
    client = get_supabase(access_token=access_token)
    repository = CareerSimulationRepository(client)

    profile = repository.get_profile(user_id)
    experiences = repository.get_experiences(user_id)
    latest_analysis = repository.get_latest_profile_analysis(user_id)

    row = repository.create_pending(
        {
            "profile_id": user_id,
            "simulation_type": request.simulation_type,
            "target_role": request.target_role,
            "scenario_title": request.scenario_title,
            "scenario_input": request.scenario_input,
        }
    )

    context = SimulationContext(
        profile=profile,
        experiences=experiences,
        latest_analysis=latest_analysis,
        simulation_type=request.simulation_type,
        target_role=request.target_role,
        scenario_title=request.scenario_title,
        scenario_input=request.scenario_input,
    )

    generator = get_simulation_generator()
    try:
        result = await generator.generate(context)
    except Exception:
        repository.mark_failed(row["id"], user_id)
        raise

    updated = repository.complete(
        row["id"],
        user_id,
        {
            "result": result.model_dump(mode="json"),
            "verdict": _VERDICT_DB_MAP.get(result.verdict.level),
            "model_used": generator.name,
            "status": "completed",
            "completed_at": _now_iso(),
        },
    )
    return _to_response(updated)


async def compare_simulations(
    *, user_id: str, access_token: str, request: SimulationCompareRequest
) -> CareerSimulationResponse:
    """Evaluate two hypothetical actions against the SAME current profile
    and SAME target role, independently first, then produce a head-to-head
    verdict. Persisted as a single `simulation_type='compare_moves'` row
    whose `scenario_input` holds both options and whose `result` holds the
    full `ComparisonResult` (both independent evaluations plus the
    comparison). `verdict` is left `NULL` for a comparison row — the
    CHECK constraint explicitly permits null, and a single high_value/
    useful/limited_value/low_value headline doesn't meaningfully describe
    "which of two options is the better fit"; that lives inside
    `result.comparison` instead.
    """
    client = get_supabase(access_token=access_token)
    repository = CareerSimulationRepository(client)

    profile = repository.get_profile(user_id)
    experiences = repository.get_experiences(user_id)
    latest_analysis = repository.get_latest_profile_analysis(user_id)

    row = repository.create_pending(
        {
            "profile_id": user_id,
            "simulation_type": "compare_moves",
            "target_role": request.target_role,
            "scenario_title": f"{request.option_a.scenario_title} vs. {request.option_b.scenario_title}",
            "scenario_input": {
                "option_a": request.option_a.model_dump(),
                "option_b": request.option_b.model_dump(),
            },
        }
    )

    context_a = SimulationContext(
        profile=profile,
        experiences=experiences,
        latest_analysis=latest_analysis,
        simulation_type=request.option_a.simulation_type,
        target_role=request.target_role,
        scenario_title=request.option_a.scenario_title,
        scenario_input=request.option_a.scenario_input,
    )
    context_b = SimulationContext(
        profile=profile,
        experiences=experiences,
        latest_analysis=latest_analysis,
        simulation_type=request.option_b.simulation_type,
        target_role=request.target_role,
        scenario_title=request.option_b.scenario_title,
        scenario_input=request.option_b.scenario_input,
    )

    generator = get_simulation_generator()
    try:
        comparison = await generator.compare(context_a, context_b)
    except Exception:
        repository.mark_failed(row["id"], user_id)
        raise

    updated = repository.complete(
        row["id"],
        user_id,
        {
            "result": comparison.model_dump(mode="json"),
            "verdict": None,
            "model_used": generator.name,
            "status": "completed",
            "completed_at": _now_iso(),
        },
    )
    return _to_response(updated)


async def get_simulation(*, user_id: str, access_token: str, simulation_id: str) -> CareerSimulationResponse:
    client = get_supabase(access_token=access_token)
    repository = CareerSimulationRepository(client)

    row = repository.get_by_id(simulation_id, user_id)
    if row is None:
        raise NotFoundError("That career simulation could not be found.")
    return _to_response(row)


async def list_recent_simulations(*, user_id: str, access_token: str) -> list[SimulationHistoryItem]:
    """Every past simulation's headline (scenario, target role, verdict,
    date), newest first — powers the "Recent Simulations" list. Returns an
    empty list (not a 404) when there's no history yet."""
    client = get_supabase(access_token=access_token)
    repository = CareerSimulationRepository(client)

    rows = repository.list_recent(user_id)
    return [SimulationHistoryItem(**row) for row in rows]


async def delete_simulation(*, user_id: str, access_token: str, simulation_id: str) -> None:
    client = get_supabase(access_token=access_token)
    repository = CareerSimulationRepository(client)
    repository.delete_simulation(simulation_id, user_id)
