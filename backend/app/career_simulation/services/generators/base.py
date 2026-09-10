"""Generator interface — same seam as
`app.career_roadmap.services.generators.base.BaseRoadmapGenerator` and
`app.profile_analysis.services.generators.base.BaseAnalysisGenerator`.
`simulation_service.py` only ever calls `generator.generate(context)` or
`generator.compare(context_a, context_b)` through this interface; which
concrete class it holds is decided once, in factory.py, based on whether an
OpenAI API key is configured.
"""

from abc import ABC, abstractmethod

from app.career_simulation.schemas.simulation import ComparisonResult, SimulationResult
from app.career_simulation.utils.context import SimulationContext


class BaseSimulationGenerator(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, context: SimulationContext) -> SimulationResult:
        """Evaluate ONE hypothetical action against the given profile and
        target role."""

    @abstractmethod
    async def compare(self, context_a: SimulationContext, context_b: SimulationContext) -> ComparisonResult:
        """Evaluate two hypothetical actions against the SAME current
        profile and SAME target role, independently first, then produce a
        head-to-head verdict on top. `context_a`/`context_b` share the same
        `target_role` — only `simulation_type`/`scenario_title`/
        `scenario_input` differ between them."""
