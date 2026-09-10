"""Semantic search entry point. Not implemented yet.

Composes: embed(query) -> vector store search -> hydrate rows -> rank.
Sits above the store so callers never deal with raw embeddings.
"""

from app.core.exceptions import NotImplementedYetError
from app.vector.base import VectorMatch


async def semantic_search(
    query: str,
    *,
    top_k: int = 10,
    filters: dict | None = None,
) -> list[VectorMatch]:
    raise NotImplementedYetError("Semantic search is not implemented yet.")
