"""Product analytics.

Scaffolded only — no business logic yet. Every handler raises
NotImplementedYetError (HTTP 501) so the API surface is visible in
/docs and the frontend service layer can be written against it.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, rate_limit
from app.core.exceptions import NotImplementedYetError
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    summary="Record a product analytics event",
    dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)],
)
async def track_event(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/overview",
    summary="Aggregated activity for the signed-in user",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def overview(user: CurrentUser):
    raise NotImplementedYetError()
