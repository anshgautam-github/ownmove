"""Embedding generation.

Local model (sentence-transformers/all-MiniLM-L6-v2, 384-dim) — no API key,
no network call per request, just CPU inference in-process. That means the
one thing this module has to get right that an API-backed embedder wouldn't
is not blocking the event loop: `SentenceTransformer.encode()` is a
synchronous, CPU-bound call, so `embed`/`embed_batch` below run it on a
worker thread via `asyncio.to_thread` rather than awaiting it directly.

The model itself is loaded lazily (first call, not import time) and cached
as a module-level singleton — loading it is the expensive part (reading
~90MB off disk into memory), encoding a batch of short strings after that
is fast. `app/main.py`'s lifespan hook warms this up at process startup so
the first real request isn't the one that pays for it.
"""

import asyncio
from functools import lru_cache

from app.ai.embeddings.base import BaseEmbedder
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingUnavailableError(AppError):
    """The embedding model/library isn't available in this environment."""

    status_code = 503
    code = "embedding_unavailable"
    message = (
        "The embedding model is not available on this server. "
        "Install the `sentence-transformers` extra (see requirements.txt)."
    )


@lru_cache
def _load_model():
    """Process-wide singleton. `lru_cache` on a zero-arg function is a cheap
    way to get "compute once, reuse forever" without a manual global +
    threading.Lock — the first caller pays the load cost, everyone after
    gets the cached object, and it's still lazy (only loads if something
    actually calls this).
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - exercised only when the
        # optional heavy dependency genuinely isn't installed.
        raise EmbeddingUnavailableError(
            "sentence-transformers is not installed. Run "
            "`pip install -r requirements.txt` in backend/."
        ) from exc

    kwargs = (
        {"cache_folder": settings.EMBEDDING_MODEL_CACHE_DIR}
        if settings.EMBEDDING_MODEL_CACHE_DIR
        else {}
    )
    logger.info("Loading embedding model %s", settings.DEFAULT_EMBEDDING_MODEL)
    model = SentenceTransformer(settings.DEFAULT_EMBEDDING_MODEL, **kwargs)
    logger.info("Embedding model loaded (dim=%d)", model.get_sentence_embedding_dimension())
    return model


class EmbeddingGenerator(BaseEmbedder):
    def __init__(self):
        self.model = settings.DEFAULT_EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed(self, text: str) -> list[float]:
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _encode() -> list[list[float]]:
            model = _load_model()
            # normalize_embeddings=True: standard practice for retrieval
            # with sentence-transformers models (what they're benchmarked/
            # typically used with) and makes cosine and dot-product
            # equivalent. Not required for pgvector's cosine operator to be
            # *correct* (it computes true cosine similarity regardless of
            # input scale), just consistent with how this model family is
            # meant to be used.
            embeddings = model.encode(
                list(texts),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return embeddings.tolist()

        return await asyncio.to_thread(_encode)


def build_profile_document(profile: dict) -> str:
    """Flatten a profile row into the text that gets embedded for semantic
    matching against opportunities.

    Pure and deterministic — same reasoning as build_opportunity_document
    below: safe to unit-test, safe to re-run when the model changes, and
    the exact function the "has this profile's embedding-relevant content
    changed?" invalidation trigger (supabase/schema — see
    022_recommendation_embedding_invalidation.sql) has to agree with about
    which fields matter.
    """
    parts = [
        profile.get("target_role"),
        profile.get("target_company"),
        " ".join(profile.get("career_interests") or []),
        " ".join(profile.get("current_skills") or []),
        profile.get("headline"),
        profile.get("bio"),
        profile.get("degree"),
        profile.get("branch"),
        profile.get("major"),
    ]
    return "\n".join(part for part in parts if part)


def build_opportunity_document(opportunity: dict) -> str:
    """Flatten an opportunity row into the text that gets embedded.

    Pure and deterministic, so it is safe to unit-test and to re-run when the
    embedding model changes.
    """
    parts = [
        opportunity.get("title"),
        opportunity.get("organization"),
        opportunity.get("category"),
        opportunity.get("description"),
        " ".join(opportunity.get("tags") or []),
        opportunity.get("duration"),
    ]
    return "\n".join(part for part in parts if part)
