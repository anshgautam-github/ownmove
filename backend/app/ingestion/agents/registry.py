"""The single place source-specific agents register themselves.

Adding a new source is: write the `BaseOpportunityAgent` subclass, then
either decorate it with `@agent_registry.register` or call
`agent_registry.register(MyAgent)` once at import time (see
`app/ingestion/README.md` for a full example). Nothing else in the
framework — pipeline, jobs, service — needs to change.
"""

from app.ingestion.agents.base import BaseOpportunityAgent


class AgentRegistry:
    """A plain in-memory registry. Deliberately not a singleton-only
    module-level dict: tests can construct their own `AgentRegistry()` with
    fake agents without touching the process-wide one."""

    def __init__(self) -> None:
        self._agents: dict[str, type[BaseOpportunityAgent]] = {}

    def register(self, agent_cls: type[BaseOpportunityAgent]) -> type[BaseOpportunityAgent]:
        """Usable as a decorator (`@agent_registry.register`) or called
        directly (`agent_registry.register(MyAgent)`). Returns the class
        unchanged either way, so it composes with other decorators."""
        source = agent_cls.source
        if not source:
            raise ValueError(f"{agent_cls.__name__} must set a non-empty `source` before registering.")
        existing = self._agents.get(source)
        if existing is not None and existing is not agent_cls:
            raise ValueError(
                f"Source '{source}' is already registered to {existing.__name__}; "
                f"cannot also register {agent_cls.__name__}. Source names must be unique."
            )
        self._agents[source] = agent_cls
        return agent_cls

    def unregister(self, source: str) -> None:
        self._agents.pop(source, None)

    def get(self, source: str) -> type[BaseOpportunityAgent]:
        try:
            return self._agents[source]
        except KeyError:
            raise KeyError(
                f"No agent registered for source '{source}'. Registered sources: {self.all_sources()}"
            ) from None

    def all_sources(self) -> list[str]:
        return sorted(self._agents)

    def all(self) -> list[type[BaseOpportunityAgent]]:
        return [self._agents[source] for source in self.all_sources()]

    def __contains__(self, source: str) -> bool:
        return source in self._agents

    def __len__(self) -> int:
        return len(self._agents)


# One process-wide registry — same "single seam other code goes through"
# pattern as `app.workers.queue.get_queue()`. Concrete agent modules import
# THIS instance to register; `IngestionService` reads from THIS instance to
# know what it can run.
agent_registry = AgentRegistry()
