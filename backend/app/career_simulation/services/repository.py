"""Supabase I/O for career_simulations — the only file in this feature that
imports the Supabase client directly.

Always constructed with a user-scoped client (`db.supabase.get_supabase(
access_token=...)`), never the service-role client: profiles, experiences,
profile_analysis, and career_simulations are all rows the requesting user
owns, so this runs under the same Row Level Security every direct-from-
browser query does, not bypassing it. See
policies/006_rls_career_simulation.sql. `profile_id` is always sourced from
the authenticated user (`user.id` in the router/service layer), never from
client-supplied request data — see simulation_service.py.
"""

from supabase import Client

from app.core.exceptions import ExternalServiceError, NotFoundError


class CareerSimulationRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_profile(self, profile_id: str) -> dict:
        # NOTE: postgrest-py's `maybe_single()` does not return an
        # APIResponse with `data=None` when zero rows match — it returns
        # `None` outright. Every `maybe_single()` call in this file must
        # guard against that `None`, not just `response.data` (same gotcha
        # documented in career_roadmap/services/repository.py).
        response = self._client.table("profiles").select("*").eq("id", profile_id).maybe_single().execute()
        if not response or not response.data:
            raise NotFoundError("Complete your profile before running a Career Simulation.")
        return response.data

    def get_experiences(self, profile_id: str) -> list[dict]:
        response = (
            self._client.table("experiences")
            .select("*")
            .eq("profile_id", profile_id)
            .order("created_at")
            .order("id")
            .execute()
        )
        return response.data or []

    def get_latest_profile_analysis(self, profile_id: str) -> dict | None:
        """Read straight from `profile_analysis` rather than importing
        anything from `app.profile_analysis` — same independent-read
        convention `career_roadmap`'s repository follows, and for the same
        reason: that module's own README restricts imports to its router."""
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

    def create_pending(self, row: dict) -> dict:
        """Insert the initial `status='pending'` row before the generator
        runs. `career_simulations` is append-only (a new row per
        simulation/comparison), unlike `career_roadmaps`'s upsert-on-
        user_id — so this is always an insert, never an upsert."""
        response = self._client.table("career_simulations").insert(row).execute()
        if not response.data:
            raise ExternalServiceError("Failed to start the career simulation.")
        return response.data[0]

    def complete(self, simulation_id: str, profile_id: str, update: dict) -> dict:
        """Move a row from `pending` to `completed`. Filters on
        `profile_id` in addition to `id` as defense in depth — RLS already
        enforces this, but the query should never rely on RLS alone to
        catch a coding mistake that passed the wrong id."""
        response = (
            self._client.table("career_simulations")
            .update(update)
            .eq("id", simulation_id)
            .eq("profile_id", profile_id)
            .execute()
        )
        if not response.data:
            raise ExternalServiceError("Failed to save the completed career simulation.")
        return response.data[0]

    def mark_failed(self, simulation_id: str, profile_id: str) -> None:
        """Best-effort — if even this update fails (e.g. the DB is
        unreachable), the caller is already raising the original error and
        should not be masked by a secondary failure here."""
        try:
            self._client.table("career_simulations").update({"status": "failed"}).eq("id", simulation_id).eq(
                "profile_id", profile_id
            ).execute()
        except Exception:  # noqa: BLE001 - logging-only side effect, never fatal
            pass

    def get_by_id(self, simulation_id: str, profile_id: str) -> dict | None:
        response = (
            self._client.table("career_simulations")
            .select("*")
            .eq("id", simulation_id)
            .eq("profile_id", profile_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def list_recent(self, profile_id: str, limit: int = 20) -> list[dict]:
        """Newest-first — powers the "Recent Simulations" list. Deliberately
        minimal selection (no complex analytics over history, per the
        feature spec)."""
        response = (
            self._client.table("career_simulations")
            .select("id,simulation_type,target_role,scenario_title,verdict,status,created_at")
            .eq("profile_id", profile_id)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def delete_simulation(self, simulation_id: str, profile_id: str) -> None:
        """Requires a matching RLS DELETE policy on career_simulations
        (policies/009_rls_career_simulation_delete.sql) -- without one, an
        enabled-RLS table with no policy for an operation denies it
        outright, so this used to report success while deleting nothing.
        Checking `response.data` (not just the absence of an exception)
        catches exactly that silent-no-op case, matching ai_coach's
        `delete_conversation`, which already does this correctly."""
        response = (
            self._client.table("career_simulations")
            .delete()
            .eq("id", simulation_id)
            .eq("profile_id", profile_id)
            .execute()
        )
        if not response.data:
            raise NotFoundError("Simulation not found.")
