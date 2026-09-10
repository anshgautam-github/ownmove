"""Supabase I/O for the "For You" hybrid recommender.

Reads (profile signals, both retrieval legs, hydration, the empty-pool
fallback) all go through a USER-SCOPED client, same reasoning as
ProfileAnalysisRepository: these are rows the requesting user is already
allowed to read under RLS (their own profile; any active opportunity), so
this runs under the same policies a direct-from-browser query would.

The one write here — caching the computed result into public.recommendations
— uses the ADMIN client instead, because policies/002_rls_ai.sql only grants
`authenticated` a SELECT policy on that table ("the user reads their own
feed, the backend writes it"); there's no INSERT/UPDATE policy for a user to
write their own recommendation rows even if they wanted to.
"""

from supabase import Client

from app.core.logging import get_logger
from app.db.supabase import get_admin_supabase
from app.schemas.recommendation import MatchReason

logger = get_logger(__name__)

# Everything ranking.py's scoring functions and build_keyword_query() read —
# never `embedding` (see embedding_repository.py's docstring on why this
# backend avoids pulling the vector's raw contents out of Postgres at all
# when it doesn't need to).
_PROFILE_SIGNAL_FIELDS = "id,target_role,target_company,career_interests,current_skills,headline"


class RecommendationRepository:
    def get_profile_signals(self, client: Client, user_id: str) -> dict | None:
        response = (
            client.table("profiles")
            .select(_PROFILE_SIGNAL_FIELDS)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def semantic_candidates(
        self,
        client: Client,
        *,
        profile_id: str,
        match_count: int,
        opportunity_id: str | None = None,
    ) -> list[dict]:
        """Calls match_opportunities_for_profile (supabase/schema/
        021_recommendation_functions.sql). Returns [] rather than raising
        if the profile has no embedding yet — the function's own `p.
        embedding is not null` guard already makes that the same as "no
        rows", this is just naming what an empty result means here."""
        response = client.rpc(
            "match_opportunities_for_profile",
            {
                "p_profile_id": profile_id,
                "p_match_count": match_count,
                "p_opportunity_id": opportunity_id,
            },
        ).execute()
        return response.data or []

    def keyword_candidates(
        self,
        client: Client,
        *,
        query_text: str,
        match_count: int,
        opportunity_id: str | None = None,
    ) -> list[dict]:
        """Calls search_opportunities_by_text. `query_text` is a
        to_tsquery-syntax OR expression from ranking.build_keyword_query()
        — see that function's docstring for why OR, and
        021_recommendation_functions.sql's comment on the "prioritize
        certain fields" nuance this leg can't fully honor without owning
        search_vector's own field weights.
        """
        if not query_text:
            return []
        response = client.rpc(
            "search_opportunities_by_text",
            {
                "p_query": query_text,
                "p_match_count": match_count,
                "p_opportunity_id": opportunity_id,
            },
        ).execute()
        return response.data or []

    def hydrate_opportunities(self, client: Client, ids: list[str]) -> dict[str, dict]:
        """Full rows for every candidate id from either retrieval leg —
        needed both to build the API response (Opportunity schema) and to
        compute the four non-retrieval ranking components (skill/interest/
        role/freshness), which all read plain columns, not the embedding.
        `is_active = true` is redundant with both RPCs already filtering it
        (defense in depth, and it's what the table's own RLS policy checks
        too), not load-bearing on its own.
        """
        if not ids:
            return {}
        response = (
            client.table("opportunities")
            .select("*")
            .in_("id", ids)
            .eq("is_active", True)
            .execute()
        )
        return {row["id"]: row for row in (response.data or [])}

    def fallback_recent(self, client: Client, limit: int) -> list[dict]:
        """Most-recently-posted active opportunities — used only when the
        hybrid pool comes back completely empty (e.g. a brand-new profile
        with no skills/interests/target role filled in yet, so there's
        nothing to embed or build a keyword query from). A discovery
        platform's "For You" tab should never just render blank; freshness
        alone is a reasonable, honest fallback until the profile has real
        signal.
        """
        response = (
            client.table("opportunities")
            .select("*")
            .eq("is_active", True)
            .order("posted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def upsert_recommendations(
        self,
        user_id: str,
        ranked: list[tuple[str, float, list[MatchReason]]],
        *,
        model_version: str,
    ) -> None:
        """Best-effort cache write into public.recommendations (schema/
        008_recommendations_events.sql — "materialized current best guess,
        overwritten in place", one row per (user, opportunity)). Delete-
        then-insert rather than a real upsert: the interesting failure mode
        isn't "this row's score changed" (an upsert on the unique
        (user_id, opportunity_id) constraint would handle that fine), it's
        "this opportunity is no longer in the top N at all" — an upsert
        alone would leave those stale rows behind forever. Not on the
        response path: this is a side-effect cache, not the source of
        truth for what /for-you returns, so a failure here is logged and
        swallowed rather than failing the request.
        """
        if not ranked:
            return
        try:
            client = get_admin_supabase()
            client.table("recommendations").delete().eq("user_id", user_id).execute()
            rows = [
                {
                    "user_id": user_id,
                    "opportunity_id": opportunity_id,
                    "score": round(score, 4),
                    "reasons": [reason.model_dump(mode="json") for reason in reasons],
                    "model_version": model_version,
                }
                for opportunity_id, score, reasons in ranked
            ]
            client.table("recommendations").insert(rows).execute()
        except Exception:  # noqa: BLE001 - a cache-write failure must never break the response
            logger.warning("Failed to cache recommendations for user %s", user_id, exc_info=True)
