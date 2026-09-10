"""Embedding lifecycle for profiles and opportunities.

Orchestration only: build the canonical text (app/ai/embeddings/generator),
run it through the model, persist via EmbeddingRepository. The "only
generate when missing/changed" rule from the product spec is enforced here,
not by the caller — every method below checks first and no-ops if an
embedding already exists, so recommendation_service.py (or a future worker
task, see app/workers/tasks/embeddings.py) can call these on every request
without it turning into "regenerate embeddings on every request".

"Changed" itself isn't tracked by a hash/timestamp column (there wasn't one
to work with — profiles.embedding / opportunities.embedding are plain
columns, not a dedicated table with source_hash the way schema/
006_ai_embeddings.sql's now-unused design had). Instead, an UPDATE trigger
(supabase/schema/022_recommendation_embedding_invalidation.sql) sets
`embedding = NULL` whenever one of the fields build_profile_document() /
build_opportunity_document() actually reads is changed. That turns "did the
relevant content change?" into the same question as "is it missing?",
which is exactly what has_profile_embedding()/has_opportunity_embedding()
and get_opportunities_missing_embedding() below are already answering.

Two robustness properties every method here is written to guarantee:

  * A generation or write failure never leaves a record partially updated
    or corrupted, and never takes down the caller. Each attempt is wrapped
    in its own try/except: on failure the embedding column is simply left
    however it already was (NULL if it was missing, unchanged if this was
    a re-embed) and the method returns as if nothing needed doing. The
    request that triggered it (e.g. GET /recommendations/for-you) keeps
    going — semantic retrieval just skips whatever didn't get embedded,
    the same as it already does for a genuinely-not-yet-embedded row.
    Callers must NOT assume a `True`/`>0` return means "the whole batch
    succeeded" or a `False`/`0` return means "something is wrong" — both
    are also the normal outcome for "nothing to do" or "already current".

  * Duplicate concurrent generation for the same id is avoided within this
    process via a per-key asyncio.Lock (see _lock_for): if two requests
    for the same user (or the same opportunity backfill window) land at
    close to the same time, the second one blocks on the lock, then
    re-checks "does this already have an embedding now?" before doing any
    work, so only one of them actually calls the model. This is an
    in-process guard, not a distributed one — this project runs without
    Redis/a task queue today (ENABLE_BACKGROUND_WORKERS is off by default,
    see app/core/config.py), so a cross-process/cross-replica lock isn't
    available without adding that infrastructure. Even without it, a
    duplicate generation across two different worker processes is
    wasteful, not unsafe: the model is deterministic, so both computations
    produce (near-)identical vectors and the last write simply wins —
    never a corrupted or mixed value.
"""

import asyncio

from app.ai.embeddings.generator import (
    EmbeddingGenerator,
    build_opportunity_document,
    build_profile_document,
)
from app.core.logging import get_logger
from app.db.supabase import get_admin_supabase, get_supabase
from app.services.embedding_repository import EmbeddingRepository

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(
        self,
        generator: EmbeddingGenerator | None = None,
        repository: EmbeddingRepository | None = None,
    ):
        self._generator = generator or EmbeddingGenerator()
        self._repository = repository or EmbeddingRepository()
        # In-process dedup locks — see the module docstring. Keyed by
        # user_id / opportunity_id, created on first use, never explicitly
        # cleaned up: this service is constructed once per process (see
        # app/api/v1/routes/recommendations.py's module-level `_service`),
        # and the number of distinct users/opportunities that ever request
        # an embedding in a process's lifetime is bounded by real usage,
        # not by request volume — an idle asyncio.Lock is a few dozen
        # bytes, so this does not grow unbounded in practice the way a
        # per-request cache would.
        self._profile_locks: dict[str, asyncio.Lock] = {}
        self._opportunity_locks: dict[str, asyncio.Lock] = {}
        self._backfill_lock = asyncio.Lock()

    @staticmethod
    def _lock_for(registry: dict[str, asyncio.Lock], key: str) -> asyncio.Lock:
        lock = registry.get(key)
        if lock is None:
            lock = asyncio.Lock()
            registry[key] = lock
        return lock

    def _check_dimensions(self, embedding: list[float], *, context: str) -> None:
        """Defense in depth on top of the DB's own `vector(384)` column
        typing (which would already reject a wrong-length insert): catches
        a dimension mismatch in Python, with a clear log message, before
        ever attempting the write — rather than relying on a round-trip to
        Postgres to fail first. Matters most if DEFAULT_EMBEDDING_MODEL is
        ever swapped for a model with a different output size without also
        updating EMBEDDING_DIMENSIONS/the column definition.
        """
        expected = self._generator.dimensions
        if len(embedding) != expected:
            raise ValueError(
                f"Embedding for {context} has {len(embedding)} dimensions, expected {expected}."
            )

    async def embed_profile(self, *, user_id: str, access_token: str) -> bool:
        """(Re)generate this user's profile embedding if it's missing.
        Returns whether it actually generated one (False = already had a
        current embedding, the profile has no embeddable signal yet, or
        generation/saving failed — see the module docstring on why a
        failure here is swallowed rather than raised)."""
        client = get_supabase(access_token=access_token)

        if self._repository.has_profile_embedding(client, user_id):
            return False

        async with self._lock_for(self._profile_locks, user_id):
            # Re-check: a concurrent call for this same user may have
            # already generated it while this one was waiting for the lock.
            if self._repository.has_profile_embedding(client, user_id):
                return False

            profile = self._repository.get_profile_for_embedding(client, user_id)
            if not profile:
                return False

            document = build_profile_document(profile)
            if not document.strip():
                # Nothing meaningful to embed yet (a fresh profile with no
                # target role/skills/interests/headline/bio/education
                # filled in) — leave embedding NULL rather than embedding
                # an empty string into a not-actually-meaningful vector.
                # The semantic retrieval leg just skips this user until
                # they add signal; keyword + the other ranking components
                # still work.
                return False

            try:
                embedding = await self._generator.embed(document)
                self._check_dimensions(embedding, context=f"profile {user_id}")
                self._repository.save_profile_embedding(client, user_id, embedding)
            except Exception:  # noqa: BLE001 - a failed embed must never break the caller
                logger.warning(
                    "Failed to generate/save profile embedding for user %s", user_id, exc_info=True
                )
                return False

            logger.info("Generated profile embedding for user %s", user_id)
            return True

    async def embed_opportunity(self, opportunity_id: str) -> bool:
        """(Re)generate one opportunity's embedding if missing. Uses the
        admin client — opportunities are curated content, not owned by a
        particular request's caller (see EmbeddingRepository's docstring).
        """
        client = get_admin_supabase()

        if self._repository.has_opportunity_embedding(client, opportunity_id):
            return False

        async with self._lock_for(self._opportunity_locks, opportunity_id):
            if self._repository.has_opportunity_embedding(client, opportunity_id):
                return False

            opportunity = self._repository.get_opportunity_for_embedding(client, opportunity_id)
            if not opportunity:
                return False

            document = build_opportunity_document(opportunity)
            if not document.strip():
                return False

            try:
                embedding = await self._generator.embed(document)
                self._check_dimensions(embedding, context=f"opportunity {opportunity_id}")
                self._repository.save_opportunity_embedding(client, opportunity_id, embedding)
            except Exception:  # noqa: BLE001 - a failed embed must never break the caller
                logger.warning(
                    "Failed to generate/save embedding for opportunity %s",
                    opportunity_id,
                    exc_info=True,
                )
                return False

            logger.info("Generated opportunity embedding for %s", opportunity_id)
            return True

    async def backfill(self, *, limit: int) -> int:
        """Embed up to `limit` active opportunities that are still missing
        one. Called both inline (a small `limit`, ahead of answering a
        /for-you request — see RecommendationService) and from the
        explicit /recommendations/refresh endpoint (a larger `limit`) —
        see app/core/config.py's RECOMMENDATION_INLINE_BACKFILL_LIMIT /
        RECOMMENDATION_REFRESH_BACKFILL_LIMIT. Also exactly what
        app/workers/tasks/embeddings.py::backfill_opportunity_embeddings
        should call once a real background worker is running instead of
        this being driven by request traffic.

        Serialized by _backfill_lock: concurrent /for-you requests each
        trigger a backfill call, and without this, two overlapping calls
        would both fetch the same "missing" rows and embed them twice. The
        second caller waits, then re-queries — by then the first call has
        already filled some/all of that window, so it only does whatever
        work is still actually left.
        """
        if limit <= 0:
            return 0

        async with self._backfill_lock:
            client = get_admin_supabase()
            rows = self._repository.get_opportunities_missing_embedding(client, limit)
            if not rows:
                return 0

            documents = [build_opportunity_document(row) for row in rows]
            # Embeddable rows only — title is NOT NULL on public.opportunities
            # so this should be everything, but stay defensive rather than
            # assume it. Rows with no embeddable content are simply left
            # with embedding = NULL; they'll be re-considered (and
            # re-skipped) on the next backfill call rather than being
            # written as a meaningless vector.
            embeddable = [
                (row, doc) for row, doc in zip(rows, documents, strict=True) if doc.strip()
            ]
            if not embeddable:
                return 0

            try:
                vectors = await self._generator.embed_batch([doc for _, doc in embeddable])
            except Exception:  # noqa: BLE001 - one failed batch must not break the caller
                logger.warning(
                    "Embedding backfill batch failed (%d candidate rows); nothing written, "
                    "will retry on the next call.",
                    len(embeddable),
                    exc_info=True,
                )
                return 0

            embedded = 0
            for (row, _doc), vector in zip(embeddable, vectors, strict=True):
                try:
                    self._check_dimensions(vector, context=f"opportunity {row['id']}")
                    self._repository.save_opportunity_embedding(client, row["id"], vector)
                except Exception:  # noqa: BLE001 - one bad row must not sink the whole batch
                    logger.warning(
                        "Failed to save backfilled embedding for opportunity %s; skipping, "
                        "will retry on a later backfill.",
                        row["id"],
                        exc_info=True,
                    )
                    continue
                embedded += 1

            logger.info("Backfilled %d opportunity embedding(s)", embedded)
            return embedded
