"""`IngestionRunSummary` — the combined, human/operator-facing view of one
ingestion run: what `AgentRunResult` (discover/extract/normalize/validate,
in-memory) and `BatchSaveResult` (what actually got persisted, or would
have — see `OpportunityService.preview_batch()`) together produced.

Neither of those two models alone answers "did this run actually do what I
expect" — `AgentRunResult` doesn't know whether a "valid" opportunity ended
up created, updated, or capped out by `HACKATHON_DAILY_LIMIT`, and
`BatchSaveResult` doesn't know how many raw candidates a source even saw.
This is the presentation-layer model built once real production visibility
(`api/v1/routes/ingestion.py`) needed both at once — see
`build_run_summary()`.
"""

from datetime import datetime

from pydantic import BaseModel

from app.ingestion.models.persistence import BatchSaveResult, OpportunitySaveResult
from app.ingestion.models.run import AgentRunResult, IngestionError, RunStatus


class IngestionRunSummary(BaseModel):
    source: str
    dry_run: bool
    status: RunStatus

    # Raw candidates the source actually had, before any ranking/cap —
    # falls back to `selected` when an agent doesn't report the distinction
    # (see `AgentRunResult.raw_candidate_count`'s docstring), so this field
    # is always populated even for a source that doesn't rank/cap at all.
    discovered: int
    # Candidates that survived ranking + the candidate-pool cap and were
    # actually pushed through extract() / normalize() / validate().
    selected: int
    extracted: int
    normalized: int
    validated: int
    invalid: int

    # Of the valid opportunities, how many matched an existing row (by
    # `(source, source_id)` or by content fingerprint — see
    # `OpportunityService.find_duplicate()`) and were updated in place
    # rather than inserted as new. In this architecture a "duplicate" and
    # an "update" are the same event — there is no third "duplicate but
    # skipped" outcome — so `duplicates == updated` always; both are
    # reported because they answer different operator questions ("how much
    # of what I found already existed" vs. "how many rows changed").
    duplicates: int
    inserted: int
    updated: int
    # Valid opportunities never attempted because `daily_save_limit` was
    # already reached by higher-ranked candidates earlier in the batch.
    skipped_due_to_cap: int
    # Pipeline-stage failures (extract/normalize/validate raised for a
    # listing) PLUS persistence failures (a write itself raised) combined —
    # "did anything actually break in this run", full detail in
    # `pipeline_errors` / `item_errors` below.
    failed: int

    daily_save_limit: int | None
    started_at: datetime
    finished_at: datetime | None

    pipeline_errors: list[IngestionError]
    # Only outcome="error" items (persistence failures) — "rejected"
    # (failed validate()) and "would_*"/"created"/"updated" items are
    # already fully accounted for in the counters above and are not
    # repeated here to keep this small enough to actually read after a run.
    item_errors: list[OpportunitySaveResult]


def build_run_summary(
    run_result: AgentRunResult, batch_result: BatchSaveResult, *, dry_run: bool
) -> IngestionRunSummary:
    return IngestionRunSummary(
        source=run_result.source,
        dry_run=dry_run,
        status=run_result.status,
        discovered=(
            run_result.raw_candidate_count
            if run_result.raw_candidate_count is not None
            else run_result.discovered_count
        ),
        selected=run_result.discovered_count,
        extracted=run_result.extracted_count,
        normalized=run_result.normalized_count,
        validated=run_result.valid_count,
        invalid=run_result.invalid_count,
        duplicates=batch_result.updated,
        inserted=batch_result.created,
        updated=batch_result.updated,
        skipped_due_to_cap=batch_result.skipped,
        failed=len(run_result.errors) + batch_result.errors,
        daily_save_limit=run_result.daily_save_limit,
        started_at=run_result.started_at,
        finished_at=run_result.finished_at,
        pipeline_errors=run_result.errors,
        item_errors=[r for r in batch_result.results if r.outcome == "error"],
    )
