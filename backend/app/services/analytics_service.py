"""Product analytics.

Service layer: owns business rules, orchestrates repositories, AI chains
and the vector store. Routes stay thin; workers reuse the same methods.
Not implemented yet.
"""

from app.core.exceptions import NotImplementedYetError


class AnalyticsService:
    async def track(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def overview(self, *args, **kwargs):
        raise NotImplementedYetError()

