"""Generator interface — same seam as every other Career AI module's
`Base*Generator`. `coach_service.py` only ever calls
`generator.generate(context)` through this interface; which concrete class
it holds is decided once, in factory.py, based on whether an OpenAI API key
is configured.
"""

from abc import ABC, abstractmethod

from app.ai_coach.schemas.coach import CoachStructuredResponse
from app.ai_coach.utils.context import CoachContext


class BaseCoachGenerator(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, context: CoachContext) -> CoachStructuredResponse:
        """Produce one coaching turn's response for the given context."""
