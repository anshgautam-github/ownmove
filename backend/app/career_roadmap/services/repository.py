"""Supabase I/O for career_roadmaps + roadmap_activity — the only file in
this feature that imports the Supabase client directly.

Always constructed with a user-scoped client (`db.supabase.get_supabase(
access_token=...)`), never the service-role client: profiles, experiences,
profile_analysis, career_roadmaps and roadmap_activity are all rows the
requesting user owns, so this runs under the same Row Level Security every
direct-from-browser query does, not bypassing it. See
policies/005_rls_career_roadmap.sql.
"""

from supabase import Client

from app.core.exceptions import ExternalServiceError, NotFoundError


class CareerRoadmapRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_profile(self, user_id: str) -> dict:
        # NOTE: postgrest-py's `maybe_single()` does not return an
        # APIResponse with `data=None` when zero rows match — it returns
        # `None` outright (it catches PGRST116 "no rows" and swallows the
        # response entirely). Every `maybe_single()` call in this file must
        # guard against that `None`, not just `response.data`.
        response = (
            self._client.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
        )
        if not response or not response.data:
            raise NotFoundError("Complete your profile before generating a Career Roadmap.")
        return response.data

    def get_experiences(self, user_id: str) -> list[dict]:
        # Same total-ordering reasoning as profile_analysis's
        # get_experiences(): not required for correctness here (this
        # feature makes no determinism guarantee the way Profile Analysis
        # does), but costs nothing and keeps the prompt's experience order
        # stable across a session.
        response = (
            self._client.table("experiences")
            .select("*")
            .eq("profile_id", user_id)
            .order("created_at")
            .order("id")
            .execute()
        )
        return response.data or []

    def get_latest_profile_analysis(self, user_id: str) -> dict | None:
        """Read straight from `profile_analysis` rather than importing
        anything from `app.profile_analysis` — that module's own README
        restricts imports to its router, so this feature reads the same
        table independently instead of coupling to its service layer. Only
        a handful of fields are actually used (see utils/context.py), so an
        old-shape row (missing current fields) degrades gracefully: the
        `.get(...)` calls at the read site just return None for whatever
        isn't there, rather than raising."""
        response = (
            self._client.table("profile_analysis")
            .select("*")
            .eq("profile_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_roadmap(self, user_id: str) -> dict | None:
        """`career_roadmaps` has `unique(user_id)` — at most one row ever
        exists for a given user, so this is a lookup, not a "latest of many"
        query the way profile_analysis's history is. The common case here —
        a user who has never generated a roadmap — is exactly the zero-rows
        case where `maybe_single()` returns `None` instead of a response
        object, so that has to be checked before `.data`."""
        response = (
            self._client.table("career_roadmaps").select("*").eq("user_id", user_id).maybe_single().execute()
        )
        return response.data if response else None

    def save_roadmap(self, row: dict) -> dict:
        """Upsert on `user_id` — the first Generate Roadmap call inserts;
        every subsequent Regenerate call overwrites that same row in place
        (matching the table's `unique(user_id)` constraint and the "one
        active roadmap per user" model the feature spec describes), rather
        than accumulating history the way profile_analysis does."""
        response = (
            self._client.table("career_roadmaps").upsert(row, on_conflict="user_id").execute()
        )
        if not response.data:
            raise ExternalServiceError("Failed to save the generated roadmap.")
        return response.data[0]

    def log_activity(self, *, roadmap_id: str, user_id: str, activity_type: str, description: str) -> None:
        """Best-effort audit trail — a failure here should never fail the
        roadmap generation the user is waiting on, so this swallows any
        error rather than propagating it."""
        try:
            self._client.table("roadmap_activity").insert(
                {
                    "roadmap_id": roadmap_id,
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "description": description,
                }
            ).execute()
        except Exception:  # noqa: BLE001 - logging-only side effect, never fatal
            pass
