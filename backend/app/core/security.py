"""Supabase JWT verification.

Supabase Auth (Google OAuth) issues the token; the browser stores the session
and forwards the access token as `Authorization: Bearer <jwt>`. This module
verifies that token so FastAPI can trust the caller's identity.

This is authentication *plumbing*, not business logic — it has to exist before
any protected route can be written. It deliberately contains no domain rules.
"""

from datetime import datetime, timezone
from functools import lru_cache

import jwt
from jwt import PyJWKClient, PyJWTError

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthenticatedUser:
    """The subset of Supabase JWT claims the application cares about."""

    __slots__ = ("id", "email", "role", "provider", "claims")

    def __init__(self, claims: dict):
        self.claims = claims
        self.id: str = claims.get("sub", "")
        self.email: str | None = claims.get("email")
        self.role: str = claims.get("role", "authenticated")
        self.provider: str | None = (claims.get("app_metadata") or {}).get("provider")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AuthenticatedUser id={self.id} email={self.email}>"


@lru_cache
def _jwks_client() -> PyJWKClient | None:
    """Supabase publishes whatever asymmetric keys it's currently signing
    with at this well-known URL. Only consulted for tokens whose header says
    they were signed with an asymmetric algorithm (ES256/RS256) — newer
    Supabase projects can rotate to these instead of a single static HS256
    secret ("JWT Signing Keys" in Project Settings -> API). PyJWKClient
    caches the fetched keys itself and only re-fetches on a cache miss (e.g.
    after a rotation introduces a new `kid`), so this being process-cached
    via lru_cache just avoids rebuilding the client object per request.
    """
    if not settings.SUPABASE_URL:
        return None
    jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def decode_token(token: str) -> dict:
    """Decode and validate a Supabase-issued JWT.

    Supabase projects sign access tokens either symmetrically (HS256, a
    single shared secret copied from the dashboard) or asymmetrically
    (ES256/RS256, a rotating key pair published via JWKS), depending on how
    the project's JWT Signing Keys are configured. Rather than assume one,
    this reads the algorithm the token's own header declares and verifies
    accordingly, so it works unmodified against either kind of project.

    Raises UnauthorizedError on any failure so callers never have to
    distinguish between the many PyJWT error subclasses. The real
    PyJWTError is logged at debug level (not returned to the client) so a
    misconfigured secret/URL is diagnosable from the server logs.
    """
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        logger.debug("Rejected token: unreadable header (%s)", exc)
        raise UnauthorizedError("Invalid authentication token.") from exc

    algorithm = header.get("alg") or settings.SUPABASE_JWT_ALGORITHM

    if algorithm.startswith("HS"):
        if not settings.SUPABASE_JWT_SECRET:
            raise UnauthorizedError(
                "Auth is not configured on the server (SUPABASE_JWT_SECRET is unset)."
            )
        signing_key: str = settings.SUPABASE_JWT_SECRET
    else:
        client = _jwks_client()
        if client is None:
            raise UnauthorizedError(
                "Auth is not configured on the server (SUPABASE_URL is unset)."
            )
        try:
            signing_key = client.get_signing_key_from_jwt(token).key
        except PyJWTError as exc:
            logger.debug("Rejected token: JWKS lookup failed (%s)", exc)
            raise UnauthorizedError("Invalid authentication token.") from exc

    try:
        return jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Session expired. Please sign in again.") from exc
    except PyJWTError as exc:
        logger.debug("Rejected token: signature/claims check failed (%s)", exc)
        raise UnauthorizedError("Invalid authentication token.") from exc


def verify_token(token: str) -> AuthenticatedUser:
    """Decode a token and wrap the claims in an AuthenticatedUser."""
    claims = decode_token(token)

    if not claims.get("sub"):
        raise UnauthorizedError("Token is missing a subject claim.")

    return AuthenticatedUser(claims)


def token_expiry(claims: dict) -> datetime | None:
    exp = claims.get("exp")
    if exp is None:
        return None
    return datetime.fromtimestamp(exp, tz=timezone.utc)
