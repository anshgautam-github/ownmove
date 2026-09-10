"""Opportunity catalogue (internships, programs, hackathons, ...).

Scaffolded only — no business logic yet. Every handler raises
NotImplementedYetError (HTTP 501) so the API surface is visible in
/docs and the frontend service layer can be written against it.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, rate_limit
from app.core.exceptions import NotImplementedYetError
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("/", summary="List opportunities by category", dependencies=[rate_limit(RateLimitCategory.AUTH_READ)])
async def list_opportunities(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/search",
    summary="Keyword + semantic search over opportunities",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def search_opportunities(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/saved",
    summary="List the caller's saved opportunities",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def list_saved(user: CurrentUser):
    raise NotImplementedYetError()


@router.get(
    "/{opportunity_id}",
    summary="Fetch a single opportunity",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def get_opportunity(user: CurrentUser):
    raise NotImplementedYetError()


@router.post(
    "/{opportunity_id}/save",
    summary="Bookmark an opportunity",
    dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)],
)
async def save_opportunity(user: CurrentUser):
    raise NotImplementedYetError()


@router.delete(
    "/{opportunity_id}/save",
    summary="Remove a bookmark",
    dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)],
)
async def unsave_opportunity(user: CurrentUser):
    raise NotImplementedYetError()
