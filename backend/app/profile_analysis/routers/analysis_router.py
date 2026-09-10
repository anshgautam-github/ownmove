"""HTTP layer for Profile Analysis. Thin on purpose — every handler is a
one-line call into analysis_service, with no business logic here. If a
handler body ever grows past "call the service, return the result," that
logic belongs in the service, not the router.
"""

from fastapi import APIRouter

from app.api.deps import AccessToken, CurrentUser, rate_limit
from app.core.rate_limit_policy import RateLimitCategory
from app.profile_analysis.schemas.analysis import ProfileAnalysisResponse, ScoreHistoryPoint
from app.profile_analysis.services import analysis_service

router = APIRouter(prefix="/career-ai", tags=["career-ai"])


@router.post(
    "/profile-analysis",
    response_model=ProfileAnalysisResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def create_profile_analysis(
    user: CurrentUser,
    access_token: AccessToken,
) -> ProfileAnalysisResponse:
    """Generate a fresh analysis for the authenticated user, persist it, and
    return it. Uses OpenAI (via LangChain/LangGraph) if OPENAI_API_KEY is
    configured, otherwise a deterministic mock generator — see
    services/generators/factory.py. Either way the response shape is
    identical.
    """
    return await analysis_service.run_profile_analysis(user_id=user.id, access_token=access_token)


@router.get(
    "/profile-analysis",
    response_model=ProfileAnalysisResponse,
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_latest_profile_analysis(
    user: CurrentUser,
    access_token: AccessToken,
) -> ProfileAnalysisResponse:
    """Fetch the most recently generated analysis without spending a new AI
    call. 404s (NotFoundError -> `not_found`) if the user has never run one —
    the frontend renders that as its empty state, not an error state.
    """
    return await analysis_service.get_latest_profile_analysis(user_id=user.id, access_token=access_token)


@router.get(
    "/profile-analysis/history",
    response_model=list[ScoreHistoryPoint],
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_profile_analysis_history(
    user: CurrentUser,
    access_token: AccessToken,
) -> list[ScoreHistoryPoint]:
    """Every past analysis's headline score, oldest first — powers the
    Profile Timeline section. Returns `[]` (never a 404) when there's no
    history yet; the frontend renders that as "not enough data" inline.
    """
    return await analysis_service.get_profile_analysis_history(user_id=user.id, access_token=access_token)
