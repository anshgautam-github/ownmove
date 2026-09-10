"""HTTP layer for Career Simulation. Thin on purpose, mirrors
`app.career_roadmap.routers.roadmap_router` — every handler is a one-line
call into simulation_service, with no business logic here.

Route order matters: `/career-simulation/history` is registered before
`/career-simulation/{simulation_id}` so FastAPI never tries to parse
"history" as a simulation id.
"""

from fastapi import APIRouter

from app.api.deps import AccessToken, CurrentUser, rate_limit
from app.career_simulation.schemas.simulation import (
    CareerSimulationResponse,
    SimulationCompareRequest,
    SimulationCreateRequest,
    SimulationHistoryItem,
)
from app.career_simulation.services import simulation_service
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/career-ai", tags=["career-ai"])


@router.post(
    "/career-simulation",
    response_model=CareerSimulationResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def create_simulation(
    request: SimulationCreateRequest,
    user: CurrentUser,
    access_token: AccessToken,
) -> CareerSimulationResponse:
    """Run one hypothetical career action against the authenticated user's
    own profile. Uses OpenAI (via LangChain) if OPENAI_API_KEY is
    configured, otherwise a deterministic mock generator — see
    services/generators/factory.py. `profile_id` is always the
    authenticated user's own id, never taken from the request body.
    """
    return await simulation_service.create_simulation(user_id=user.id, access_token=access_token, request=request)


@router.post(
    "/career-simulation/compare",
    response_model=CareerSimulationResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def compare_simulations(
    request: SimulationCompareRequest,
    user: CurrentUser,
    access_token: AccessToken,
) -> CareerSimulationResponse:
    """Evaluate two hypothetical actions against the same current profile
    and target role, independently first, then a head-to-head verdict."""
    return await simulation_service.compare_simulations(user_id=user.id, access_token=access_token, request=request)


@router.get(
    "/career-simulation/history",
    response_model=list[SimulationHistoryItem],
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_simulation_history(
    user: CurrentUser,
    access_token: AccessToken,
) -> list[SimulationHistoryItem]:
    """Every past simulation's headline, newest first. Returns `[]` (never
    a 404) when there's no history yet."""
    return await simulation_service.list_recent_simulations(user_id=user.id, access_token=access_token)


@router.get(
    "/career-simulation/{simulation_id}",
    response_model=CareerSimulationResponse,
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_simulation(
    simulation_id: str,
    user: CurrentUser,
    access_token: AccessToken,
) -> CareerSimulationResponse:
    """Fetch one previously-run simulation or comparison by id. 404s
    (NotFoundError -> `not_found`) if it doesn't exist or doesn't belong to
    the authenticated user — RLS enforces the ownership check at the
    database layer regardless of what this code does.
    """
    return await simulation_service.get_simulation(
        user_id=user.id, access_token=access_token, simulation_id=simulation_id
    )


@router.delete(
    "/career-simulation/{simulation_id}",
    status_code=204,
    dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)],
)
async def delete_simulation(
    simulation_id: str,
    user: CurrentUser,
    access_token: AccessToken,
) -> None:
    """Delete a past simulation or comparison. RLS ensures you can only
    delete your own.
    """
    await simulation_service.delete_simulation(
        user_id=user.id, access_token=access_token, simulation_id=simulation_id
    )
