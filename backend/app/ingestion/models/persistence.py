"""What `OpportunityService` hands back — the framework's second "clean
API" return shape, alongside `AgentRunResult` from `models/run.py`.
`AgentRunResult` describes what an agent produced (in memory, unsaved);
these describe what happened when that output was persisted.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ingestion.models.validation import ValidationIssue
from app.utils.time import utc_now

SaveOutcome = Literal["created", "updated", "rejected", "error", "would_create", "would_update"]


class OpportunitySaveResult(BaseModel):
    """Result of one `save_opportunity()` / `update_opportunity()` call."""

    outcome: SaveOutcome
    source: str
    source_id: str
    opportunity_id: str | None = None
    fingerprint: str | None = None
    # Populated when outcome="rejected" (failed validate()).
    issues: list[ValidationIssue] = Field(default_factory=list)
    # Populated when outcome="error" (the write itself failed).
    error_message: str | None = None


class BatchSaveResult(BaseModel):
    """Result of one `save_batch()` (or `preview_batch()`) call — its own
    self-contained summary, independent of the service's cumulative
    `IngestionStats`."""

    total: int
    created: int = 0
    updated: int = 0
    rejected: int = 0
    errors: int = 0
    # Valid opportunities that were never attempted because `max_success_count`
    # (see `OpportunityService.save_batch()`) was already reached by earlier
    # items in the batch -- distinct from `rejected` (failed validation) and
    # `errors` (a write that raised): these were simply never tried.
    skipped: int = 0
    results: list[OpportunitySaveResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None

    def mark_finished(self) -> "BatchSaveResult":
        self.finished_at = utc_now()
        return self


class IngestionStats(BaseModel):
    """Cumulative counters for one `OpportunityService` instance's
    lifetime — the "ingestion statistics" responsibility. Deliberately
    in-memory/per-instance rather than a database aggregate: a service
    constructed per script run or per scheduler tick naturally resets, which
    matches "how many did THIS run save" better than a global running total
    would. For a global, queryable total, count rows in `opportunities`
    directly (e.g. `WHERE source = ...`) — `IngestionStats` is a lightweight
    complement to that, not a replacement for it.
    """

    created: int = 0
    updated: int = 0
    rejected: int = 0
    errors: int = 0
    queued_for_enrichment: int = 0

    @property
    def total_processed(self) -> int:
        return self.created + self.updated + self.rejected + self.errors
