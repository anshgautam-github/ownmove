"""Generator interface — same seam as
`app.profile_analysis.services.generators.base.BaseAnalysisGenerator`.
`roadmap_service.py` only ever calls `generator.generate(context)` through
this interface; which concrete class it holds is decided once, in
factory.py, based on whether an OpenAI API key is configured.
"""

from abc import ABC, abstractmethod

from app.career_roadmap.schemas.roadmap import RoadmapContent
from app.career_roadmap.utils.context import RoadmapContext


class BaseRoadmapGenerator(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, context: RoadmapContext) -> RoadmapContent:
        """Produce a full roadmap for the given context. Unlike
        profile_analysis's generators, there is no separate reconcile() step
        here — implementations are responsible for their own internally
        consistent output (see schemas/roadmap.py's module docstring)."""
