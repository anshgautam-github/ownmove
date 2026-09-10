"""Typed, pipeline-internal DTOs.

Unlike the rest of the app (see `app/models/` vs `app/schemas/`), everything
here is pydantic `BaseModel`, not a database row shape — this module never
touches the database, so there is no `DBModel`/`from_attributes` concern.
`NormalizedOpportunity` deliberately mirrors
`app.schemas.opportunity.Opportunity` / `app.models.opportunity.OpportunityRow`
field-for-field (and reuses the same `OpportunityCategory` literal) so that a
future "persist" step is a trivial field-for-field mapping, not a translation
layer.
"""

from app.ingestion.models.config import AgentConfig, RateLimitConfig, RetryConfig
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.persistence import (
    BatchSaveResult,
    IngestionStats,
    OpportunitySaveResult,
    SaveOutcome,
)
from app.ingestion.models.run import AgentRunResult, IngestionError, PipelineStage
from app.ingestion.models.summary import IngestionRunSummary, build_run_summary
from app.ingestion.models.validation import ValidationIssue, ValidationResult, ValidationSeverity

__all__ = [
    "AgentConfig",
    "RateLimitConfig",
    "RetryConfig",
    "DiscoveredListing",
    "RawExtraction",
    "NormalizedOpportunity",
    "BatchSaveResult",
    "IngestionStats",
    "OpportunitySaveResult",
    "SaveOutcome",
    "AgentRunResult",
    "IngestionError",
    "PipelineStage",
    "IngestionRunSummary",
    "build_run_summary",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
]
