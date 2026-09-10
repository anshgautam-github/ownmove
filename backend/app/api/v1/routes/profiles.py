"""User profile management.

Scaffolded only — no business logic yet. Every handler raises
NotImplementedYetError (HTTP 501) so the API surface is visible in
/docs and the frontend service layer can be written against it.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, rate_limit
from app.core.exceptions import NotImplementedYetError
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", summary="Fetch the signed-in user's profile", dependencies=[rate_limit(RateLimitCategory.AUTH_READ)])
async def get_my_profile(user: CurrentUser):
    raise NotImplementedYetError()


@router.patch("/me", summary="Update the signed-in user's profile", dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)])
async def update_my_profile(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/me/analysis",
    summary="AI analysis of profile strengths and gaps",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def get_profile_analysis(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/me/strength",
    summary="Computed profile strength score",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def get_profile_strength(user: CurrentUser):
    raise NotImplementedYetError()
