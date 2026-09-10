"""Shared FastAPI dependencies.

Route handlers declare what they need (a user, a db client, pagination) and
these functions supply it. Centralising them keeps auth enforcement
consistent across every router.
"""

from typing import Annotated

from fastapi import Depends, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.exceptions import RateLimitError, ServiceUnavailableError, UnauthorizedError
from app.core.logging import get_logger
from app.core.rate_limit_policy import RateLimitCategory, build_rules, fail_open_for
from app.core.rate_limiter import RateLimiter
from app.core.redis_client import get_redis
from app.core.security import AuthenticatedUser, verify_token

logger = get_logger(__name__)

# auto_error=False so a missing header raises our UnauthorizedError (uniform
# error shape) rather than FastAPI's default 403 response.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Require a valid Supabase JWT. Use on every protected route."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing Authorization header.")

    return verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser | None:
    """Identify the caller when a token is present, but never reject."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return verify_token(credentials.credentials)
    except UnauthorizedError:
        return None


async def get_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """The raw bearer JWT, not just the identity decoded from it.

    Needed whenever a service must call Supabase AS the user (via
    db.supabase.get_supabase(access_token=...)) so Row Level Security is
    enforced with that user's own auth.uid() — e.g. profile_analysis, which
    reads and writes rows the user owns rather than acting as a trusted
    background job.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing Authorization header.")
    return credentials.credentials


class Pagination:
    """Standard limit/offset paging shared by list endpoints."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        self.limit = limit
        self.offset = offset


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthenticatedUser | None, Depends(get_optional_user)]
AccessToken = Annotated[str, Depends(get_access_token)]
PaginationParams = Annotated[Pagination, Depends()]


def rate_limit(category: RateLimitCategory) -> Depends:
    """Route-level rate-limit dependency factory.

    Usage — attach to the specific route(s) it applies to, not globally:

        @router.post(
            "/career-simulation",
            dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
        )

    Deliberately a dependency, not app-wide middleware: different routes in
    this API have genuinely different cost profiles (a 501 stub vs. an LLM
    call), so the category — and therefore the limit — is a property of the
    route, decided at the route, not a single blanket policy applied to
    everything. See backend/RATE_LIMITING.md for the full per-route
    breakdown and the middleware-vs-dependency reasoning.

    Keyed by the authenticated user when a valid token is present
    (`OptionalUser`, not `CurrentUser` — so this dependency itself never
    rejects an unauthenticated caller; the route's own `CurrentUser`
    parameter still does that separately, keeping rate limiting and
    authorization as two distinct checks per REQUIREMENT #13). The client
    IP is always resolved too, since AI_EXPENSIVE layers a per-IP rule on
    top of the per-user one regardless of auth state.

    This function is only ever called with a fixed set of AppError
    subclasses it raises itself; nothing here changes authentication,
    session, or token handling.
    """

    async def _dependency(request: Request, response: Response, user: OptionalUser) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = get_client_ip(request)
        rules = build_rules(category, user_id=user.id if user else None, client_ip=client_ip)
        decision = await RateLimiter(get_redis()).check_many(rules)

        if decision.redis_error is not None:
            if fail_open_for(category):
                logger.error(
                    "Rate limiter Redis unavailable — failing OPEN "
                    "(category=%s path=%s): %s",
                    category.value,
                    request.url.path,
                    decision.redis_error,
                )
                return
            logger.error(
                "Rate limiter Redis unavailable — failing CLOSED "
                "(category=%s path=%s): %s",
                category.value,
                request.url.path,
                decision.redis_error,
            )
            raise ServiceUnavailableError()

        bucket = decision.most_restrictive
        if bucket is not None:
            # Attached to the eventual *successful* response too (not just
            # 429s) so well-behaved clients can see how close they are to
            # their limit before they hit it.
            response.headers["X-RateLimit-Limit"] = str(bucket.rule.limit)
            response.headers["X-RateLimit-Remaining"] = str(bucket.remaining)
            response.headers["X-RateLimit-Reset"] = str(bucket.reset_seconds)

        if not decision.allowed:
            retry_after = decision.retry_after_seconds or 1
            identity = f"user:{user.id}" if user else f"ip:{client_ip}"
            logger.warning(
                "Rate limit exceeded: category=%s layer=%s path=%s identity=%s "
                "limit=%s retry_after=%ss",
                category.value,
                bucket.rule.label if bucket else "unknown",
                request.url.path,
                identity,
                bucket.rule.limit if bucket else "?",
                retry_after,
            )
            raise RateLimitError(
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(bucket.rule.limit) if bucket else "",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                }
            )

    return Depends(_dependency)
