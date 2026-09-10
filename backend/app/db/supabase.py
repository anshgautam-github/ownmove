"""Server-side Supabase clients.

Two distinct clients, deliberately kept separate:

* `get_supabase()`      — anon key + the caller's JWT. All queries run AS THAT
                          USER, so Row Level Security still applies. This is
                          the default and should be used for anything acting
                          on behalf of a user.

* `get_admin_supabase()`— service-role key. BYPASSES RLS entirely. Only for
                          trusted background work (batch embeddings, seeding,
                          cross-user analytics). Never driven by user input.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings
from app.core.exceptions import AppError


def _require_config() -> None:
    if not settings.SUPABASE_URL:
        raise AppError("SUPABASE_URL is not configured.")


def get_supabase(access_token: str | None = None) -> Client:
    """Client scoped to the calling user, so RLS policies are enforced."""
    _require_config()

    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    if access_token:
        # PostgREST reads auth.uid() from this bearer token.
        client.postgrest.auth(access_token)

    return client


@lru_cache
def get_admin_supabase() -> Client:
    """Service-role client. RLS does NOT apply — handle with care."""
    _require_config()

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AppError("SUPABASE_SERVICE_ROLE_KEY is not configured.")

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
