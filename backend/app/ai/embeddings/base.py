"""Embedding provider interface."""

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    model: str = ""
    dimensions: int = 0

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single string."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many strings in one call — far cheaper than looping embed()."""
