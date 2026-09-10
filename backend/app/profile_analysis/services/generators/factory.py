"""Picks a generator based on configuration — the actual mechanism behind
"replace mock AI logic with OpenAI without changing the frontend."

No env var, no code change anywhere else: set OPENAI_API_KEY and the very
next request uses LangGraphAnalysisGenerator instead of MockAnalysisGenerator.
`analysis_service.py` calls `get_analysis_generator()` and never imports
either concrete class directly.
"""

from functools import lru_cache

from app.core.config import settings
from app.profile_analysis.services.generators.base import BaseAnalysisGenerator
from app.profile_analysis.services.generators.mock_generator import MockAnalysisGenerator


@lru_cache
def get_analysis_generator() -> BaseAnalysisGenerator:
    if settings.OPENAI_API_KEY:
        # Imported lazily so environments without OPENAI_API_KEY set (and
        # therefore possibly without langchain/langgraph installed yet) never
        # pay the import cost or risk an ImportError for a path they don't use.
        from app.profile_analysis.services.generators.langgraph_generator import (
            LangGraphAnalysisGenerator,
        )

        return LangGraphAnalysisGenerator()

    return MockAnalysisGenerator()
