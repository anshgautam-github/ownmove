"""Picks a generator based on configuration — mirrors
`app.profile_analysis.services.generators.factory` exactly. Set
OPENAI_API_KEY and the very next request uses LangGraphRoadmapGenerator
instead of MockRoadmapGenerator; `roadmap_service.py` calls
`get_roadmap_generator()` and never imports either concrete class directly.
"""

from functools import lru_cache

from app.career_roadmap.services.generators.base import BaseRoadmapGenerator
from app.career_roadmap.services.generators.mock_generator import MockRoadmapGenerator
from app.core.config import settings


@lru_cache
def get_roadmap_generator() -> BaseRoadmapGenerator:
    if settings.OPENAI_API_KEY:
        # Imported lazily so environments without OPENAI_API_KEY set never pay
        # the import cost or risk an ImportError for a path they don't use.
        from app.career_roadmap.services.generators.langgraph_generator import (
            LangGraphRoadmapGenerator,
        )
        return LangGraphRoadmapGenerator()

    return MockRoadmapGenerator()
