"""Supabase I/O for profile_analysis — the only file in this feature that
imports the Supabase client directly.

Always constructed with a user-scoped client (`db.supabase.get_supabase(
access_token=...)`), never the service-role client: profiles, experiences,
and profile_analysis are all rows the requesting user owns, so this should
run under the same Row Level Security every direct-from-browser query does,
not bypass it. See policies/004_rls_profile_analysis.sql.
"""

from supabase import Client

from app.core.exceptions import ExternalServiceError, NotFoundError


class ProfileAnalysisRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_profile(self, profile_id: str) -> dict:
        response = (
            self._client.table("profiles").select("*").eq("id", profile_id).maybe_single().execute()
        )
        if not response.data:
            raise NotFoundError("Complete your profile before running Profile Analysis.")
        return response.data

    def get_experiences(self, profile_id: str) -> list[dict]:
        # Explicit, total ordering matters here even though nothing downstream
        # displays this order: ProfileContext.to_prompt_text() renders
        # experiences in whatever order this query returns them, and that
        # text is what the LLM call needs to be byte-identical across two
        # analyses of an unchanged profile (see langgraph_generator.py's
        # _DETERMINISTIC_SEED). Without an ORDER BY, Postgres is free to
        # return the same rows in a different order on a later call even if
        # nothing changed, which would silently break that determinism
        # upstream of the model entirely. `id` as a tiebreaker makes the
        # order total (created_at alone isn't unique enough to guarantee it).
        response = (
            self._client.table("experiences")
            .select("*")
            .eq("profile_id", profile_id)
            .order("created_at")
            .order("id")
            .execute()
        )
        return response.data or []

    def get_latest_analysis(self, profile_id: str) -> dict | None:
        response = (
            self._client.table("profile_analysis")
            .select("*")
            .eq("profile_id", profile_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_score_history(self, profile_id: str, limit: int = 24) -> list[dict]:
        """Every past analysis's headline score, oldest first — powers the
        Profile Timeline section. `profile_analysis` is append-only (a new
        row per run, never updated in place), so this is just reading that
        history back; `.order("id")` breaks ties for runs saved in the same
        second, same reasoning as get_experiences() above. Fetches
        newest-first under the hood (so `limit` bounds it to the most recent
        runs on a long-lived profile) then reverses to oldest-first, which is
        the order a left-to-right timeline needs.
        """
        response = (
            self._client.table("profile_analysis")
            .select("overall_score,created_at")
            .eq("profile_id", profile_id)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        rows = response.data or []
        return list(reversed(rows))

    def next_version(self, profile_id: str) -> int:
        """1 for a profile's first analysis, else one more than its latest."""
        latest = self.get_latest_analysis(profile_id)
        if latest is None:
            return 1
        return (latest.get("analysis_version") or 1) + 1

    def save_analysis(self, row: dict) -> dict:
        response = self._client.table("profile_analysis").insert(row).execute()
        if not response.data:
            raise ExternalServiceError("Failed to save the generated analysis.")
        return response.data[0]
