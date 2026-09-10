"""Opportunity catalogue access.

Service layer: owns business rules, orchestrates repositories, AI chains
and the vector store. Routes stay thin; workers reuse the same methods.
Not implemented yet.
"""

from app.core.exceptions import NotImplementedYetError


class OpportunityService:
    async def list_opportunities(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def get_opportunity(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def search(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def save_for_user(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def unsave_for_user(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def list_saved(self, *args, **kwargs):
        raise NotImplementedYetError()

