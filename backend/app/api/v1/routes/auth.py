"""Authentication verification endpoints.

Scaffolded only — no business logic yet. Every handler raises
NotImplementedYetError (HTTP 501) so the API surface is visible in
/docs and the frontend service layer can be written against it.

NOTE: this is NOT where login/signup/password-reset happen — the frontend
talks to Supabase Auth directly for all of that (see AUTH_SECURITY_AUDIT.md
and backend/RATE_LIMITING.md). These two routes exist only for a caller who
already has a Supabase JWT to double-check it / fetch their own identity
server-side, which is why they're CurrentUser-gated like everything else
here rather than being public "login" endpoints in need of their own,
different rate-limit treatment.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, rate_limit
from app.core.exceptions import NotImplementedYetError
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    summary="Return the caller identity from the verified Supabase JWT",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_me(user: CurrentUser):
    raise NotImplementedYetError()


@router.post(
    "/verify",
    summary="Validate a Supabase access token",
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def verify(user: CurrentUser):
    raise NotImplementedYetError()
