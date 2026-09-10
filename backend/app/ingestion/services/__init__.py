"""`IngestionService` — the framework's top-level entrypoint for RUNNING
agents. `OpportunityService` — the framework's ONLY entrypoint for
PERSISTING what they produce. Together they're the two "clean APIs" the
rest of the backend should call; nothing else in `app.ingestion` talks to
Supabase.
"""

from app.ingestion.services.ingestion_service import IngestionService
from app.ingestion.services.opportunity_service import OpportunityService
from app.ingestion.services.repository import OpportunityRepository

__all__ = ["IngestionService", "OpportunityService", "OpportunityRepository"]
