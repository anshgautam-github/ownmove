"""Supabase I/O for embedding lifecycle management.

Two different trust levels, deliberately kept apart in every method here
(same reasoning as db/supabase.py):

* Profile embeddings are written with a USER-SCOPED client (the caller's
  own JWT) — a profile row is something its owner is already allowed to
  update under RLS (policies/001_rls.sql: `id = auth.uid()`), so this
  never needs to bypass it.
* Opportunity embeddings are written with the ADMIN (service-role) client
  — opportunities aren't owned by any one user, and there's no RLS policy
  granting `authenticated` write access to them at all (curated content,
  same as the ingestion pipeline). Reading which opportunities still need
  an embedding is likewise an admin/background operation, not something
  scoped to a particular caller.
"""

from supabase import Client

from app.core.exceptions import ExternalServiceError, NotFoundError

# Only what build_profile_document() actually reads — never `embedding`
# itself. There's no product reason for this backend to pull the vector's
# raw contents back out of Postgres at all; every embedding read this
# module needs ("does one already exist?") is answered by the *absence* of
# a value, not its contents, so it's simplest and safest to just never
# select the column in the first place.
_PROFILE_EMBEDDING_FIELDS = (
    "id,target_role,target_company,career_interests,current_skills,"
    "headline,bio,degree,branch,major"
)

_OPPORTUNITY_EMBEDDING_FIELDS = "id,title,organization,category,description,tags,duration"


class EmbeddingRepository:
    def get_profile_for_embedding(self, client: Client, user_id: str) -> dict | None:
        """The subset of profile fields build_profile_document() needs,
        plus a cheap `embedding IS NULL` existence check via a second,
        narrow query — see has_profile_embedding()."""
        response = (
            client.table("profiles")
            .select(_PROFILE_EMBEDDING_FIELDS)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def has_profile_embedding(self, client: Client, user_id: str) -> bool:
        response = (
            client.table("profiles").select("embedding").eq("id", user_id).maybe_single().execute()
        )
        if not response.data:
            raise NotFoundError("Profile not found.")
        return response.data.get("embedding") is not None

    def save_profile_embedding(
        self, client: Client, user_id: str, embedding: list[float]
    ) -> None:
        response = (
            client.table("profiles").update({"embedding": embedding}).eq("id", user_id).execute()
        )
        if not response.data:
            raise ExternalServiceError("Failed to save the profile embedding.")

    def has_opportunity_embedding(self, client: Client, opportunity_id: str) -> bool:
        """Mirrors has_profile_embedding(), but never raises on a missing
        row: unlike a profile (which always exists once a user is signed
        in), a caller can pass an opportunity_id that's already been
        deleted/deactivated, and embed_opportunity() already treats "not
        found" as a normal early-exit (see get_opportunity_for_embedding
        below) rather than an error condition."""
        response = (
            client.table("opportunities")
            .select("embedding")
            .eq("id", opportunity_id)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return False
        return response.data.get("embedding") is not None

    def get_opportunity_for_embedding(self, client: Client, opportunity_id: str) -> dict | None:
        response = (
            client.table("opportunities")
            .select(_OPPORTUNITY_EMBEDDING_FIELDS)
            .eq("id", opportunity_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def save_opportunity_embedding(
        self, client: Client, opportunity_id: str, embedding: list[float]
    ) -> None:
        response = (
            client.table("opportunities")
            .update({"embedding": embedding})
            .eq("id", opportunity_id)
            .execute()
        )
        if not response.data:
            raise ExternalServiceError("Failed to save the opportunity embedding.")

    def get_opportunities_missing_embedding(self, client: Client, limit: int) -> list[dict]:
        """Active opportunities with no embedding yet — either brand new,
        or invalidated by the update trigger in
        supabase/schema/022_recommendation_embedding_invalidation.sql
        after one of their embedding-relevant fields changed. Restricted
        to `is_active = true`: there's no reason to spend a model call on
        something that can never surface in a recommendation anyway.
        """
        response = (
            client.table("opportunities")
            .select(_OPPORTUNITY_EMBEDDING_FIELDS)
            .eq("is_active", True)
            .is_("embedding", "null")
            .limit(limit)
            .execute()
        )
        return response.data or []
