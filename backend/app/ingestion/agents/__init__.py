"""`BaseOpportunityAgent` — the interface every opportunity source
implements — plus `AgentRegistry`, the single place new sources register
themselves so `IngestionService` can discover and run them.

No concrete, source-specific agent lives here yet (see the package-level
docstring in `app/ingestion/__init__.py`); this only ever imports the base
class and registry.
"""

from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import AgentRegistry, agent_registry

__all__ = ["AgentContext", "BaseOpportunityAgent", "AgentRegistry", "agent_registry"]
