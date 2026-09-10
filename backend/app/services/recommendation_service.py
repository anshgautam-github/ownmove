"""Opportunity recommendation engine — "For You".

Orchestration only: this is the read-top-to-bottom entry point for the
whole feature (embed -> retrieve -> merge -> rank -> respond), everything
it calls out to has its own narrower docstring (app/services/embedding_
service.py, recommendation_repository.py, ranking.py). Same shape as
app/profile_analysis/services/analysis_service.py.

Product rules this file (and what it calls) enforces — see the ranking
weights in ranking.py for the "how much each signal counts" half of this:
  * NOT an eligibility engine — never filters on graduation year, location,
    citizenship, GPA, or application requirements. is_active and a clearly-
    expired application_deadline are the only hard filters, both applied
    inside the SQL functions in supabase/schema/
    021_recommendation_functions.sql, not here.
  * Embeddings are generated lazily (missing profile embedding, missing/
    backlog of opportunity embeddings), never unconditionally on every
    request — see EmbeddingService.
  * No LLM, no trained ranking model — ranking.py's weighted blend only.
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.supabase import get_supabase
from app.schemas.opportunity import Opportunity
from app.schemas.recommendation import RecommendationResponse, RecommendedOpportunity
from app.services import ranking
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_repository import RecommendationRepository

logger = get_logger(__name__)

MODEL_VERSION = f"hybrid-v1:{settings.DEFAULT_EMBEDDING_MODEL}"


class RecommendationService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        repository: RecommendationRepository | None = None,
    ):
        self._embeddings = embedding_service or EmbeddingService()
        self._repository = repository or RecommendationRepository()

    async def recommend_for_user(
        self, *, user_id: str, access_token: str
    ) -> RecommendationResponse:
        """What `GET /recommendations/for-you` calls."""
        return await self._build_recommendations(
            user_id=user_id,
            access_token=access_token,
            opportunity_backfill_limit=settings.RECOMMENDATION_INLINE_BACKFILL_LIMIT,
            result_limit=settings.RECOMMENDATION_RESULT_LIMIT,
        )

    async def refresh_recommendations(
        self, *, user_id: str, access_token: str
    ) -> RecommendationResponse:
        """What `POST /recommendations/refresh` calls.

        Identical pipeline to recommend_for_user, just with a much larger
        opportunity-embedding backfill batch — a deliberate "catch up on
        the backlog" request rather than a signal to force-regenerate
        anything that's already current. The profile embedding itself is
        still only regenerated if actually missing (same as always): the
        invalidation trigger already guarantees it's stale exactly when it
        needs to be, so redoing it here on every manual refresh would
        violate "don't generate on every request" for no benefit.

        This runs synchronously rather than truly enqueueing a background
        job — ENABLE_BACKGROUND_WORKERS is off by default in this project
        (see app/core/config.py) — but calls the exact same
        EmbeddingService.backfill() that app/workers/tasks/embeddings.py::
        backfill_opportunity_embeddings is written to call, so wiring up a
        real queue later is a routing change, not a rewrite.
        """
        return await self._build_recommendations(
            user_id=user_id,
            access_token=access_token,
            opportunity_backfill_limit=settings.RECOMMENDATION_REFRESH_BACKFILL_LIMIT,
            result_limit=settings.RECOMMENDATION_RESULT_LIMIT,
        )

    async def score_match(
        self, *, user_id: str, opportunity_id: str, access_token: str
    ) -> RecommendedOpportunity:
        """What `POST /recommendations/match` calls — same scoring as the
        list endpoint, narrowed to one specific opportunity via both RPCs'
        p_opportunity_id parameter, so a listing outside either leg's
        top-50 can still be scored on request (e.g. the user is looking at
        it right now) rather than only ever being scorable if it happened
        to already be a top candidate.
        """
        client = get_supabase(access_token=access_token)

        await self._embeddings.embed_profile(user_id=user_id, access_token=access_token)

        profile = self._repository.get_profile_signals(client, user_id)
        if not profile:
            raise NotFoundError("Complete your profile before requesting a match score.")

        opportunity_row = self._repository.hydrate_opportunities(
            client, [opportunity_id]
        ).get(opportunity_id)
        if not opportunity_row:
            raise NotFoundError("Opportunity not found or no longer active.")

        semantic = self._repository.semantic_candidates(
            client, profile_id=user_id, match_count=1, opportunity_id=opportunity_id
        )
        query_text = ranking.build_keyword_query(profile)
        keyword = self._repository.keyword_candidates(
            client, query_text=query_text, match_count=1, opportunity_id=opportunity_id
        )

        semantic_similarity = semantic[0]["similarity"] if semantic else 0.0
        # A single-candidate batch can't be min-max normalized against
        # itself (see ranking.normalise_leg_scores) — clamping to [0, 1] is
        # the right substitute here since ts_rank is already a small
        # positive number in the common case, and this is a "did we find
        # any keyword signal at all" check for one specific pair, not a
        # ranked batch.
        keyword_relevance = min(1.0, keyword[0]["rank"]) if keyword else 0.0

        score, reasons = ranking.score_candidate(
            opportunity=opportunity_row,
            profile=profile,
            semantic_similarity=semantic_similarity,
            keyword_relevance=keyword_relevance,
        )

        return RecommendedOpportunity(
            opportunity=Opportunity(**opportunity_row), score=score, reasons=reasons
        )

    async def _build_recommendations(
        self,
        *,
        user_id: str,
        access_token: str,
        opportunity_backfill_limit: int,
        result_limit: int,
    ) -> RecommendationResponse:
        client = get_supabase(access_token=access_token)

        # Embeddings: generate only what's actually missing (both methods
        # no-op instantly if there's nothing to do — see EmbeddingService).
        await self._embeddings.embed_profile(user_id=user_id, access_token=access_token)
        await self._embeddings.backfill(limit=opportunity_backfill_limit)

        profile = self._repository.get_profile_signals(client, user_id)
        if not profile:
            raise NotFoundError("Complete your profile before requesting recommendations.")

        candidate_limit = settings.RECOMMENDATION_CANDIDATE_LIMIT
        semantic = self._repository.semantic_candidates(
            client, profile_id=user_id, match_count=candidate_limit
        )
        query_text = ranking.build_keyword_query(profile)
        keyword = self._repository.keyword_candidates(
            client, query_text=query_text, match_count=candidate_limit
        )

        semantic_by_id, keyword_by_id = ranking.merge_candidate_ids(semantic, keyword)
        candidate_ids = list(set(semantic_by_id) | set(keyword_by_id))

        used_fallback = False
        if not candidate_ids:
            # Nothing retrievable yet — most likely a brand-new profile
            # with no skills/interests/target role filled in (nothing to
            # embed, nothing to build a keyword query from). A discovery
            # platform's "For You" tab should still show *something*
            # rather than render empty.
            used_fallback = True
            fallback_rows = self._repository.fallback_recent(client, result_limit)
            opportunities = {row["id"]: row for row in fallback_rows}
            candidate_ids = list(opportunities.keys())
            semantic_by_id, keyword_by_id = {}, {}
        else:
            opportunities = self._repository.hydrate_opportunities(client, candidate_ids)

        now = datetime.now(tz=timezone.utc)

        if used_fallback:
            # Freshness-only ranking — every other component would be 0
            # anyway (no semantic/keyword signal by construction), so
            # skip straight to sorting by posted_at instead of running the
            # full weighted blend just to get the same ordering back.
            ranked = sorted(
                (
                    (opportunity_id, ranking.freshness_score(row.get("posted_at"), now=now), [])
                    for opportunity_id, row in opportunities.items()
                ),
                key=lambda row: row[1],
                reverse=True,
            )
        else:
            ranked = ranking.rank_candidates(
                opportunities=opportunities,
                profile=profile,
                semantic_by_id=semantic_by_id,
                keyword_by_id=keyword_by_id,
                now=now,
            )

        top = ranked[:result_limit]
        self._repository.upsert_recommendations(user_id, top, model_version=MODEL_VERSION)

        # Built item-by-item with per-item error isolation rather than one
        # list comprehension: `Opportunity(**row)` validates the row against
        # the schema (e.g. `category` must be one of the known enum values),
        # and a single malformed/legacy row failing that check must not 500
        # the whole response for every other, perfectly good, candidate —
        # same reasoning as EmbeddingService isolating one bad row from
        # sinking a whole backfill batch. Skipped rows are simply absent
        # from the response, not surfaced as a partial-failure signal to the
        # client — there's no "some recommendations failed" state in the
        # response schema, and there's no user-facing action to take on it.
        items: list[RecommendedOpportunity] = []
        for opportunity_id, score, reasons in top:
            try:
                items.append(
                    RecommendedOpportunity(
                        opportunity=Opportunity(**opportunities[opportunity_id]),
                        score=score,
                        reasons=reasons,
                    )
                )
            except Exception:  # noqa: BLE001 - one bad row must not break the whole response
                logger.warning(
                    "Skipping malformed opportunity %s while building recommendations for user %s",
                    opportunity_id,
                    user_id,
                    exc_info=True,
                )
                continue

        return RecommendationResponse(
            items=items, generated_at=now.isoformat(), model=MODEL_VERSION
        )
