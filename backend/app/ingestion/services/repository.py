"""Supabase I/O for `public.opportunities` ingestion writes — the ONLY file
allowed to talk to Supabase for opportunity ingestion.
`OpportunityService` is the only caller; no agent/crawler ever imports this
directly (see `app/ingestion/README.md`'s "No crawler talks to Supabase"
section — this file is the enforcement point for that rule).

Uses the SERVICE-ROLE client (`app.db.supabase.get_admin_supabase()`), not a
user-scoped one: `opportunities` is curated content, "readable by any
signed-in user, writable by nobody through the API" (see
`backend/README.md`'s "Why RLS is not optional"). An ingestion job is
trusted background work — the same category as batch embeddings or
seeding — not a user-driven request, so it bypasses RLS deliberately rather
than needing a policy that would otherwise have to grant some other write
path.
"""

from datetime import datetime

from supabase import Client

from app.core.exceptions import ExternalServiceError


class OpportunityRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_by_source_and_source_id(self, source: str, source_id: str) -> dict | None:
        """The strong identity lookup — see
        `supabase/schema/025_opportunities_ingestion_source_id_rename.sql`'s
        unique index on `(source, source_id)` (originally added, under the
        column name `external_id`, by `005_opportunities_v2.sql`)."""
        # NOTE: postgrest-py's `maybe_single()` returns `None` outright on
        # zero matching rows (not a response object with `data=None`) — see
        # the same gotcha documented in every other repository in this repo
        # (e.g. `career_simulation/services/repository.py`).
        response = (
            self._client.table("opportunities")
            .select("*")
            .eq("source", source)
            .eq("source_id", source_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def get_by_fingerprint(self, fingerprint: str) -> dict | None:
        """The content-based, cross-source identity lookup — see
        `supabase/schema/019_opportunities_ingestion.sql`."""
        response = (
            self._client.table("opportunities")
            .select("*")
            .eq("fingerprint", fingerprint)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def insert(self, row: dict) -> dict:
        response = self._client.table("opportunities").insert(row).execute()
        if not response.data:
            raise ExternalServiceError("Failed to insert opportunity.")
        return response.data[0]

    def update(self, opportunity_id: str, row: dict) -> dict:
        response = self._client.table("opportunities").update(row).eq("id", opportunity_id).execute()
        if not response.data:
            raise ExternalServiceError(f"Failed to update opportunity '{opportunity_id}'.")
        return response.data[0]

    def set_enrichment_status(self, opportunity_id: str, *, status: str, queued_at: datetime | None = None) -> dict:
        update: dict = {"enrichment_status": status}
        if queued_at is not None:
            update["enrichment_queued_at"] = queued_at.isoformat()

        response = self._client.table("opportunities").update(update).eq("id", opportunity_id).execute()
        if not response.data:
            raise ExternalServiceError(f"Failed to update enrichment status for '{opportunity_id}'.")
        return response.data[0]

    def count_pending_enrichment(self) -> int:
        """Backs a simple "how much enrichment work is outstanding" check —
        uses `count="exact", head=True"` so it's a single fast COUNT query,
        not a full row fetch."""
        response = (
            self._client.table("opportunities")
            .select("id", count="exact", head=True)
            .neq("enrichment_status", "completed")
            .execute()
        )
        return response.count or 0
