"""HTTP layer for Career Roadmap. Thin on purpose, mirrors
`app.profile_analysis.routers.analysis_router` — every handler is a one-line
call into roadmap_service, with no business logic here.
"""

from fastapi import APIRouter

from app.api.deps import AccessToken, CurrentUser, rate_limit
from app.career_roadmap.schemas.roadmap import CareerRoadmapResponse, RoadmapGenerateRequest
from app.career_roadmap.services import roadmap_service
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/career-ai", tags=["career-ai"])


@router.post(
    "/career-roadmap",
    response_model=CareerRoadmapResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def create_or_regenerate_roadmap(
    request: RoadmapGenerateRequest,
    user: CurrentUser,
    access_token: AccessToken,
) -> CareerRoadmapResponse:
    """Generate a fresh roadmap for the authenticated user and persist it.
    Since `career_roadmaps` holds at most one row per user, this same
    endpoint backs both the setup screen's "Generate Roadmap" button and the
    roadmap view's "Regenerate Roadmap" button — the latter simply resends
    the currently stored setup answers. Uses OpenAI (via LangChain) if
    OPENAI_API_KEY is configured, otherwise a deterministic mock generator —
    see services/generators/factory.py.
    """
    return await roadmap_service.generate_roadmap(user_id=user.id, access_token=access_token, request=request)


@router.get(
    "/career-roadmap",
    response_model=CareerRoadmapResponse,
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_current_roadmap(
    user: CurrentUser,
    access_token: AccessToken,
) -> CareerRoadmapResponse:
    """Fetch the user's current roadmap without generating anything. 404s
    (NotFoundError -> `not_found`) if none exists yet — the frontend renders
    that as the setup screen, not an error state.
    """
    return await roadmap_service.get_current_roadmap(user_id=user.id, access_token=access_token)
