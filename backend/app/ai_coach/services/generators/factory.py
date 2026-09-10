"""Picks a generator based on configuration — mirrors every other Career AI
module's `factory.py` exactly. Set OPENAI_API_KEY and the very next request
uses LangGraphCoachGenerator instead of MockCoachGenerator;
`coach_service.py` calls `get_coach_generator()` and never imports either
concrete class directly.
"""

from functools import lru_cache

from app.ai_coach.services.generators.base import BaseCoachGenerator
from app.ai_coach.services.generators.mock_generator import MockCoachGenerator
from app.core.config import settings


@lru_cache
def get_coach_generator() -> BaseCoachGenerator:
    if settings.OPENAI_API_KEY:
        # Imported lazily so environments without OPENAI_API_KEY set never pay
        # the import cost or risk an ImportError for a path they don't use.
        from app.ai_coach.services.generators.langgraph_generator import LangGraphCoachGenerator

        return LangGraphCoachGenerator()

    return MockCoachGenerator()
