"""pgvector-backed store. Not implemented yet.

Rationale: the opportunity corpus already lives in Supabase Postgres, so
keeping vectors in the same database (via the pgvector extension) avoids a
second datastore, keeps RLS applicable, and lets us filter by category/tags
and rank by similarity in a single SQL query.
"""

from app.core.config import settings
from app.core.exceptions import NotImplementedYetError
from app.vector.base import BaseVectorStore, VectorMatch


class PgVectorStore(BaseVectorStore):
    def __init__(self, table: str | None = None):
        self.table = table or settings.VECTOR_TABLE

    async def upsert(self, records: list[dict]) -> int:
        raise NotImplementedYetError("pgvector upsert is not implemented yet.")

    async def search(self, embedding: list[float], **kwargs) -> list[VectorMatch]:
        raise NotImplementedYetError("pgvector search is not implemented yet.")

    async def delete(self, ids: list[str]) -> int:
        raise NotImplementedYetError("pgvector delete is not implemented yet.")
