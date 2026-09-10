"""Opportunity recommendation engine — "For You".

Thin on purpose, same shape as every other router in this codebase: each
handler is a one-line call into RecommendationService, which owns the
actual hybrid semantic + keyword retrieval, merging and ranking (see
app/services/recommendation_service.py, ranking.py).
"""

from fastapi import APIRouter

from app.api.deps import AccessToken, CurrentUser, rate_limit
from app.core.rate_limit_policy import RateLimitCategory
from app.schemas.recommendation import MatchRequest, RecommendationResponse, RecommendedOpportunity
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

_service = RecommendationService()

# All three routes below are AI_EXPENSIVE: /for-you and /match do CPU-bound
# embedding + hybrid retrieval work inline (including a bounded lazy
# backfill — RECOMMENDATION_INLINE_BACKFILL_LIMIT), and /refresh does the
# same at a larger scale (RECOMMENDATION_REFRESH_BACKFILL_LIMIT=200) — see
# app/core/config.py. None of these are cheap DB reads.


@router.get(
    "/for-you",
    response_model=RecommendationResponse,
    summary="Ranked recommendations for the signed-in user",
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def for_you(user: CurrentUser, access_token: AccessToken) -> RecommendationResponse:
    """Hybrid (semantic + keyword) recommendations ranked for the caller's
    own profile. Not an eligibility filter — see recommendation_service.py.
    """
    return await _service.recommend_for_user(user_id=user.id, access_token=access_token)


@router.post(
    "/match",
    response_model=RecommendedOpportunity,
    summary="Score a specific opportunity against the user profile",
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def match(
    request: MatchRequest, user: CurrentUser, access_token: AccessToken
) -> RecommendedOpportunity:
    """Same scoring as /for-you, narrowed to one opportunity — useful for
    showing a match score on a listing that isn't necessarily in the
    caller's current top-N."""
    return await _service.score_match(
        user_id=user.id, opportunity_id=request.opportunity_id, access_token=access_token
    )


@router.post(
    "/refresh",
    response_model=RecommendationResponse,
    summary="Recompute recommendations",
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def refresh(user: CurrentUser, access_token: AccessToken) -> RecommendationResponse:
    """Recompute and re-cache the caller's recommendations, with a larger
    opportunity-embedding backfill batch than /for-you's inline one — see
    RecommendationService.refresh_recommendations for why this runs
    synchronously rather than truly enqueuing a background job today.
    """
    return await _service.refresh_recommendations(user_id=user.id, access_token=access_token)
