"""Generator interface.

The one seam that makes "replace mock AI logic with OpenAI without changing
the frontend" literally true: `analysis_service.py` only ever calls
`generator.generate(context)` through this interface. Which concrete class
it holds is decided once, in factory.py, based on whether an OpenAI API key
is configured — nothing else in the request path knows or cares.
"""

from abc import ABC, abstractmethod

from app.profile_analysis.schemas.analysis import AnalysisContent
from app.profile_analysis.utils.context import ProfileContext


class BaseAnalysisGenerator(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, context: ProfileContext) -> AnalysisContent:
        """Produce a full analysis for the given profile context.

        Implementations MUST run their result through
        `utils.scoring.reconcile()` before returning — see that module's
        docstring for why. The service layer trusts whatever comes back from
        `generate()` as already clamped and internally consistent; it does
        not call reconcile() a second time.
        """
