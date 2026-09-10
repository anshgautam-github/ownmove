"""Embedding background tasks. Not implemented yet."""

from app.core.exceptions import NotImplementedYetError


async def embed_opportunity(opportunity_id: str) -> None:
    raise NotImplementedYetError()


async def backfill_opportunity_embeddings() -> None:
    """Re-embed the whole corpus, e.g. after an embedding model change."""
    raise NotImplementedYetError()
