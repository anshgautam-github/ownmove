"""User profile management.

Service layer: owns business rules, orchestrates repositories, AI chains
and the vector store. Routes stay thin; workers reuse the same methods.
Not implemented yet.
"""

from app.core.exceptions import NotImplementedYetError


class ProfileService:
    async def get_profile(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def update_profile(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def compute_strength(self, *args, **kwargs):
        raise NotImplementedYetError()

    async def analyse_profile(self, *args, **kwargs):
        raise NotImplementedYetError()

