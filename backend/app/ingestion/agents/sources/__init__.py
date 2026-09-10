"""Source-specific opportunity agents.

Importing this package registers every real agent with `agent_registry`
(and, for sources that opt in, a schedule with `job_registry`) as a
side effect of module import -- see each module for its own
`agent_registry.register(...)` / `job_registry.set(...)` calls, and
`app/ingestion/README.md`'s "Adding a new source" section for the pattern.

Nothing imports this package automatically at process start; something on
the actual request/trigger path has to (see `app/api/v1/routes/ingestion.py`,
which imports it at module load so registration happens once, the first
time that router is loaded) -- importing `app.ingestion.agents.registry` or
`app.ingestion.services.ingestion_service` alone does NOT register any
source, by design (the framework itself has zero knowledge of which
concrete sources exist; see that package's own docstring).
"""

from app.ingestion.agents.sources.devfolio import DevfolioAgent  # noqa: F401
from app.ingestion.agents.sources.devpost import DevpostHackathonAgent  # noqa: F401
