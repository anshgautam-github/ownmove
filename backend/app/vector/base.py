"""Vector store interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorMatch:
    id: str
    score: float
    metadata: dict = field(default_factory=dict)
    content: str | None = None


class BaseVectorStore(ABC):
    @abstractmethod
    async def upsert(self, records: list[dict]) -> int:
        """Insert or replace vectors. Returns the number written."""

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float | None = None,
        filters: dict | None = None,
    ) -> list[VectorMatch]:
        """Nearest-neighbour search."""

    @abstractmethod
    async def delete(self, ids: list[str]) -> int:
        """Remove vectors by id."""
