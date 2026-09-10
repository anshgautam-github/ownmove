"""Picks a generator based on configuration — mirrors
`app.career_roadmap.services.generators.factory` exactly. Set
OPENAI_API_KEY and the very next request uses LangGraphSimulationGenerator
instead of MockSimulationGenerator; `simulation_service.py` calls
`get_simulation_generator()` and never imports either concrete class
directly.
"""

from functools import lru_cache

from app.career_simulation.services.generators.base import BaseSimulationGenerator
from app.career_simulation.services.generators.mock_generator import MockSimulationGenerator
from app.core.config import settings


@lru_cache
def get_simulation_generator() -> BaseSimulationGenerator:
    if settings.OPENAI_API_KEY:
        # Imported lazily so environments without OPENAI_API_KEY set never pay
        # the import cost or risk an ImportError for a path they don't use.
        from app.career_simulation.services.generators.langgraph_generator import (
            LangGraphSimulationGenerator,
        )
        return LangGraphSimulationGenerator()

    return MockSimulationGenerator()
