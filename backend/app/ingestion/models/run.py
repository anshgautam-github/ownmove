"""What `IngestionPipeline.run()` (via `BaseOpportunityAgent.run()`) hands
back for one agent's execution — the framework's top-level "clean API"
return shape. No database writes happen anywhere in producing this; it is
pure in-memory reporting.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ingestion.models.opportunity import NormalizedOpportunity
from app.utils.time import utc_now

PipelineStage = Literal["discover", "extract", "normalize", "validate"]
RunStatus = Literal["success", "partial", "failed"]


class IngestionError(BaseModel):
    """One thing that went wrong at one stage, for one URL (when known).
    Collected rather than raised, so one bad listing never aborts an entire
    agent run."""

    stage: PipelineStage
    message: str
    url: str | None = None
    attempts: int = 1


class AgentRunResult(BaseModel):
    run_id: str
    source: str
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None

    discovered_count: int = 0
    extracted_count: int = 0
    normalized_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0

    # Raw candidates an agent saw from its source BEFORE its own ranking/cap
    # trimmed them down to the `discovered_count` list that actually reached
    # extract()/normalize()/validate(). `None` when an agent doesn't report
    # this distinction (most don't need to -- it only matters for a source
    # like Devpost that discovers far more than it will ever process in one
    # run); see `BaseOpportunityAgent.last_discovery_stats`.
    raw_candidate_count: int | None = None

    # Copied from `agent.config.daily_save_limit` after discover() runs --
    # see `AgentConfig.daily_save_limit`'s docstring. A caller that persists
    # `opportunities` (e.g. the ingestion route) reads this to know whether
    # to cap how many it actually saves.
    daily_save_limit: int | None = None

    opportunities: list[NormalizedOpportunity] = Field(default_factory=list)
    errors: list[IngestionError] = Field(default_factory=list)

    @property
    def status(self) -> RunStatus:
        if self.discovered_count == 0:
            return "failed" if self.errors else "success"
        if self.valid_count == 0:
            return "failed"
        if self.errors or self.invalid_count:
            return "partial"
        return "success"

    def mark_finished(self) -> "AgentRunResult":
        self.finished_at = utc_now()
        return self
