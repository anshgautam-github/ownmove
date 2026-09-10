"""`OpportunityService` — the ONLY layer allowed to talk to Supabase for
opportunity ingestion. Every agent produces `NormalizedOpportunity` objects
in memory (see `app.ingestion.pipeline`); this is the one place that
content ever gets validated a second time, deduplicated, and written.

No crawler/agent imports `OpportunityRepository`, `app.db.supabase`, or the
`supabase` package directly — see `app/ingestion/README.md`. That
separation is exactly what makes "future agents require zero database
logic" true: a new source subclasses `BaseOpportunityAgent`, returns
`NormalizedOpportunity`s from `IngestionPipeline.run()`, and hands them to
this service. It never needs to know a database exists.
"""

from dataclasses import dataclass

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.db.supabase import get_admin_supabase
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.persistence import BatchSaveResult, IngestionStats, OpportunitySaveResult
from app.ingestion.models.validation import ValidationResult
from app.ingestion.services.repository import OpportunityRepository
from app.ingestion.utils.fingerprint import generate_fingerprint
from app.ingestion.utils.validation import basic_field_checks, to_validation_result
from app.utils.time import utc_now
from app.workers.queue import JobQueue, get_queue

logger = get_logger(__name__)

_ENRICHMENT_TASK = "enrich_opportunity"


@dataclass
class _Resolution:
    """What `save_opportunity()` and `preview_opportunity()` share: the
    outcome of validating an opportunity and checking it against existing
    rows, before either one decides whether to actually write. Keeping this
    as one shared step is what guarantees a dry run and a real run make
    IDENTICAL decisions about what counts as a duplicate — a preview is
    only trustworthy if it can't disagree with what the real run would do.
    """

    validation: ValidationResult
    fingerprint: str | None
    existing: dict | None
    row: dict | None


class OpportunityService:
    """Takes its collaborators as constructor arguments — same
    dependency-injection convention as `IngestionService`. The process-wide
    service-role client and job queue are just the defaults; a test
    constructs this around a fake repository and a fake queue with zero
    monkeypatching (see `tests/test_opportunity_service.py`).
    """

    def __init__(
        self, *, repository: OpportunityRepository | None = None, queue: JobQueue | None = None
    ) -> None:
        self._repository = repository or OpportunityRepository(get_admin_supabase())
        self._queue = queue or get_queue()
        self.stats = IngestionStats()

    # ---- validate opportunities --------------------------------------------

    def validate(self, opportunity: NormalizedOpportunity) -> ValidationResult:
        """Re-validates before persistence, deliberately duplicating the
        check an agent's own `validate()` already ran inside the pipeline
        (see `app.ingestion.utils.validation.basic_field_checks`, the same
        function both call). This service must not assume every caller went
        through `IngestionPipeline` — a script or a future admin tool could
        hand it a `NormalizedOpportunity` directly — so it re-checks rather
        than trusting the caller."""
        return to_validation_result(basic_field_checks(opportunity))

    # ---- deterministic fingerprint generation ------------------------------

    def generate_fingerprint(self, opportunity: NormalizedOpportunity) -> str:
        return generate_fingerprint(opportunity)

    # ---- duplicate detection ------------------------------------------------

    def find_duplicate(
        self, opportunity: NormalizedOpportunity, *, fingerprint: str | None = None
    ) -> dict | None:
        """`(source, source_id)` is checked first — the strongest signal
        when present ("this exact listing, as tracked by this source").
        Falls back to the content-based fingerprint, which also catches a
        DIFFERENT source listing the SAME real-world opportunity. Returns
        the existing row (a plain dict, matching every other repository in
        this codebase) or `None`.
        """
        if opportunity.source and opportunity.source_id:
            existing = self._repository.get_by_source_and_source_id(
                opportunity.source, opportunity.source_id
            )
            if existing:
                return existing

        fingerprint = fingerprint or self.generate_fingerprint(opportunity)
        return self._repository.get_by_fingerprint(fingerprint)

    # ---- shared resolution (read-only; used by both save and preview) ------

    def _resolve(self, opportunity: NormalizedOpportunity) -> _Resolution:
        """Validate -> fingerprint -> find_duplicate -> build the row that
        would be written. 100% read-only (the fingerprint lookups are
        `SELECT`s — see `OpportunityRepository.get_by_fingerprint`/
        `get_by_source_and_source_id`) — never issues an `insert`/`update`
        itself, which is exactly what makes `preview_opportunity()` a true
        dry run rather than an approximation of one."""
        validation = self.validate(opportunity)
        if not validation.is_valid:
            return _Resolution(validation=validation, fingerprint=None, existing=None, row=None)

        fingerprint = self.generate_fingerprint(opportunity)
        existing = self.find_duplicate(opportunity, fingerprint=fingerprint)
        row = self._to_row(opportunity, fingerprint)
        return _Resolution(
            validation=validation, fingerprint=fingerprint, existing=existing, row=row
        )

    # ---- insert/update opportunities ----------------------------------------

    async def save_opportunity(self, opportunity: NormalizedOpportunity) -> OpportunitySaveResult:
        """Validate -> fingerprint -> find_duplicate -> insert or update.
        A brand-new opportunity is queued for AI enrichment automatically;
        an update to an already-known one is not (see `update_opportunity`'s
        docstring for why). Raises `ExternalServiceError` if the write
        itself fails — the same "fail loud on a single item" convention
        every other repository in this codebase follows
        (`career_simulation`'s `create_pending`/`complete`, `career_roadmap`'s
        `save_roadmap`); `save_batch()` is what isolates failures across
        many items, not this method.
        """
        resolution = self._resolve(opportunity)
        if not resolution.validation.is_valid:
            self.stats.rejected += 1
            logger.warning(
                "Rejected opportunity source=%s source_id=%s: %s",
                opportunity.source,
                opportunity.source_id,
                [issue.message for issue in resolution.validation.errors],
            )
            return OpportunitySaveResult(
                outcome="rejected",
                source=opportunity.source,
                source_id=opportunity.source_id,
                issues=resolution.validation.issues,
            )

        # guaranteed by _resolve() above
        assert resolution.fingerprint is not None
        assert resolution.row is not None

        if resolution.existing:
            updated = self._repository.update(resolution.existing["id"], resolution.row)
            self.stats.updated += 1
            logger.info(
                "Updated opportunity id=%s source=%s source_id=%s",
                updated["id"],
                opportunity.source,
                opportunity.source_id,
            )
            return OpportunitySaveResult(
                outcome="updated",
                source=opportunity.source,
                source_id=opportunity.source_id,
                opportunity_id=updated["id"],
                fingerprint=resolution.fingerprint,
            )

        created = self._repository.insert(resolution.row)
        self.stats.created += 1
        logger.info(
            "Created opportunity id=%s source=%s source_id=%s",
            created["id"],
            opportunity.source,
            opportunity.source_id,
        )
        await self.mark_for_enrichment(created["id"])
        return OpportunitySaveResult(
            outcome="created",
            source=opportunity.source,
            source_id=opportunity.source_id,
            opportunity_id=created["id"],
            fingerprint=resolution.fingerprint,
        )

    def preview_opportunity(self, opportunity: NormalizedOpportunity) -> OpportunitySaveResult:
        """The dry-run counterpart to `save_opportunity()` — runs the exact
        same validate -> fingerprint -> find_duplicate resolution (via
        `_resolve()`) but NEVER calls `insert()`/`update()`/
        `mark_for_enrichment()`, and does not touch `self.stats` (a preview
        isn't a real ingestion event). Returns `outcome="would_create"` /
        `"would_update"` instead of `"created"`/`"updated"` so a caller
        (and anyone reading the JSON response) can never mistake a preview
        result for a real write having happened. `opportunity_id` is left
        `None` for `"would_create"` (no row exists yet to have an id) and
        set to the EXISTING row's id for `"would_update"` (the row that
        would be overwritten, not a new one)."""
        resolution = self._resolve(opportunity)
        if not resolution.validation.is_valid:
            return OpportunitySaveResult(
                outcome="rejected",
                source=opportunity.source,
                source_id=opportunity.source_id,
                issues=resolution.validation.issues,
            )

        assert resolution.fingerprint is not None  # guaranteed by _resolve() above

        if resolution.existing:
            return OpportunitySaveResult(
                outcome="would_update",
                source=opportunity.source,
                source_id=opportunity.source_id,
                opportunity_id=resolution.existing.get("id"),
                fingerprint=resolution.fingerprint,
            )

        return OpportunitySaveResult(
            outcome="would_create",
            source=opportunity.source,
            source_id=opportunity.source_id,
            fingerprint=resolution.fingerprint,
        )

    async def save_batch(
        self, opportunities: list[NormalizedOpportunity], *, max_success_count: int | None = None
    ) -> BatchSaveResult:
        """Runs `save_opportunity()` per item, isolating failures — one bad
        row (a write that raises `ExternalServiceError`) is recorded as
        `outcome="error"` and the batch continues, matching
        `IngestionPipeline`'s "one bad listing never aborts the run"
        philosophy. Sequential rather than concurrent: the underlying
        Supabase calls are synchronous network I/O (same convention as
        every other repository in this codebase — see
        `career_simulation/services/repository.py`), so `asyncio.gather`
        here would add complexity without adding real parallelism.

        `max_success_count`, when given, stops attempting further items as
        soon as `created + updated` reaches it — `opportunities` is expected
        to already be in priority order (the order `IngestionPipeline`
        preserves from `discover()`'s own ranking; see that module's
        "Ordering" note), so "stop at N successes" means "the N BEST
        candidates that turned out to be valid and get saved", not an
        arbitrary subset. Items never attempted because the cap was already
        reached are counted in `result.skipped`, not `result.rejected`
        (rejected means "we tried and validate() said no") or
        `result.errors` (errors means "we tried and the write failed").
        `None` (the default) means no cap — every item is attempted, the
        framework's original behavior.
        """
        result = BatchSaveResult(total=len(opportunities))

        for opportunity in opportunities:
            already_saved = result.created + result.updated
            if max_success_count is not None and already_saved >= max_success_count:
                result.skipped += 1
                continue

            try:
                item_result = await self.save_opportunity(opportunity)
            except ExternalServiceError as exc:
                self.stats.errors += 1
                result.errors += 1
                logger.error(
                    "Error saving opportunity source=%s source_id=%s: %s",
                    opportunity.source,
                    opportunity.source_id,
                    exc,
                )
                result.results.append(
                    OpportunitySaveResult(
                        outcome="error",
                        source=opportunity.source,
                        source_id=opportunity.source_id,
                        error_message=str(exc),
                    )
                )
                continue

            result.results.append(item_result)
            if item_result.outcome == "created":
                result.created += 1
            elif item_result.outcome == "updated":
                result.updated += 1
            elif item_result.outcome == "rejected":
                result.rejected += 1

        logger.info(
            "Batch finished: %d total, %d created, %d updated, %d rejected, "
            "%d error(s), %d skipped (cap=%s)",
            result.total,
            result.created,
            result.updated,
            result.rejected,
            result.errors,
            result.skipped,
            max_success_count,
        )
        return result.mark_finished()

    def preview_batch(
        self, opportunities: list[NormalizedOpportunity], *, max_success_count: int | None = None
    ) -> BatchSaveResult:
        """The dry-run counterpart to `save_batch()` — same ordering and
        same `max_success_count` stop condition (a preview that didn't
        respect the cap would misrepresent what a real run will actually
        do), but calls `preview_opportunity()` instead of
        `save_opportunity()`, so nothing here ever writes. Synchronous
        (unlike `save_batch()`) because nothing it calls does I/O that
        needs awaiting beyond what `OpportunityRepository`'s read methods
        already do synchronously underneath `_resolve()`.
        """
        result = BatchSaveResult(total=len(opportunities))

        for opportunity in opportunities:
            already_saved = result.created + result.updated
            if max_success_count is not None and already_saved >= max_success_count:
                result.skipped += 1
                continue

            item_result = self.preview_opportunity(opportunity)
            result.results.append(item_result)
            if item_result.outcome == "would_create":
                result.created += 1
            elif item_result.outcome == "would_update":
                result.updated += 1
            elif item_result.outcome == "rejected":
                result.rejected += 1

        logger.info(
            "Dry-run batch finished: %d total, %d would-create, %d would-update, "
            "%d rejected, %d skipped (cap=%s)",
            result.total,
            result.created,
            result.updated,
            result.rejected,
            result.skipped,
            max_success_count,
        )
        return result.mark_finished()

    async def update_opportunity(
        self, opportunity_id: str, opportunity: NormalizedOpportunity
    ) -> OpportunitySaveResult:
        """Explicit update-by-id, for a caller that already knows which row
        it means to update (re-normalizing a known listing, an admin
        correction) rather than relying on `save_opportunity()`'s own
        dedupe lookup. Deliberately does NOT call `mark_for_enrichment()` —
        enrichment runs once, on creation; re-queueing on every routine
        update would mean a frequently-refreshed listing never finishes
        enriching. A caller that genuinely wants re-enrichment after an
        update should call `mark_for_enrichment()` itself.
        """
        validation = self.validate(opportunity)
        if not validation.is_valid:
            self.stats.rejected += 1
            return OpportunitySaveResult(
                outcome="rejected",
                source=opportunity.source,
                source_id=opportunity.source_id,
                issues=validation.issues,
            )

        fingerprint = self.generate_fingerprint(opportunity)
        row = self._to_row(opportunity, fingerprint)
        updated = self._repository.update(opportunity_id, row)
        self.stats.updated += 1
        logger.info("Updated opportunity id=%s (explicit update_opportunity call)", opportunity_id)
        return OpportunitySaveResult(
            outcome="updated",
            source=opportunity.source,
            source_id=opportunity.source_id,
            opportunity_id=updated["id"],
            fingerprint=fingerprint,
        )

    # ---- queue opportunities for AI enrichment ------------------------------

    async def mark_for_enrichment(self, opportunity_id: str) -> None:
        """Records `enrichment_status='pending'` on the row AND enqueues an
        `enrich_opportunity` task via `app.workers.queue.get_queue()` — the
        same queue abstraction the rest of the backend already uses (see
        `app.workers.tasks.embeddings`), rather than inventing a second
        queueing mechanism just for ingestion. The DB column is the durable
        record of "this needs enrichment" (survives a restart even with the
        in-memory dev queue); the enqueued task is what actually triggers
        work once a real queue/worker exists.
        """
        self._repository.set_enrichment_status(
            opportunity_id, status="pending", queued_at=utc_now()
        )
        await self._queue.enqueue(_ENRICHMENT_TASK, opportunity_id=opportunity_id)
        self.stats.queued_for_enrichment += 1
        logger.info("Queued opportunity id=%s for enrichment", opportunity_id)

    # ---- ingestion statistics ------------------------------------------------

    def get_stats(self) -> IngestionStats:
        """Cumulative counters since this `OpportunityService` instance was
        constructed — see `IngestionStats`'s docstring for why this is
        per-instance rather than a global running total."""
        return self.stats

    def reset_stats(self) -> None:
        self.stats = IngestionStats()

    # ---- internal ------------------------------------------------------------

    @staticmethod
    def _to_row(opportunity: NormalizedOpportunity, fingerprint: str) -> dict:
        """`NormalizedOpportunity` -> an `opportunities` row dict. Sparse by
        design: fields the agent didn't determine (None) are left out of
        the dict entirely rather than sent as explicit `None`, so an
        `update()` never nulls out a value a previous, more complete
        ingestion pass had already set. Date/datetime fields are
        `.isoformat()` strings, matching the convention every other
        repository in this codebase uses when writing to Supabase (e.g.
        `career_simulation_service.py`'s `_now_iso()`).
        """
        row: dict = {
            "category": opportunity.category,
            "title": opportunity.title,
            "is_remote": opportunity.is_remote,
            "tags": opportunity.tags,
            "eligible_years": opportunity.eligible_years,
            "source": opportunity.source,
            "source_id": opportunity.source_id,
            "fingerprint": fingerprint,
            "is_active": True,
        }
        optional_fields = {
            "organization": opportunity.organization,
            "logo_url": opportunity.logo_url,
            "description": opportunity.description,
            "location": opportunity.location,
            "apply_url": opportunity.apply_url,
            "duration": opportunity.duration,
        }
        row.update({key: value for key, value in optional_fields.items() if value is not None})

        if opportunity.application_deadline is not None:
            row["application_deadline"] = opportunity.application_deadline.isoformat()
        if opportunity.posted_at is not None:
            row["posted_at"] = opportunity.posted_at.isoformat()

        return row
