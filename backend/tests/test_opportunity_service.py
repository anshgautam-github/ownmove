"""Exercises `OpportunityService` against a fake in-memory repository and a
fake job queue — no real Supabase call, no real background worker. Confirms
the service's own responsibilities (validation, fingerprinting, duplicate
detection, insert/update, stats, enrichment queueing) independent of
whether an agent or a script is the caller.
"""

from datetime import datetime

from app.core.exceptions import ExternalServiceError
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.services.opportunity_service import OpportunityService
from app.ingestion.utils.fingerprint import generate_fingerprint


class FakeOpportunityRepository:
    """Duck-types `OpportunityRepository`'s interface — `OpportunityService`
    never checks the concrete type, only calls methods on it."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.fail_source_ids: set[str] = set()
        self._next_id = 1

    def get_by_source_and_source_id(self, source: str, source_id: str) -> dict | None:
        for row in self.rows.values():
            if row.get("source") == source and row.get("source_id") == source_id:
                return row
        return None

    def get_by_fingerprint(self, fingerprint: str) -> dict | None:
        for row in self.rows.values():
            if row.get("fingerprint") == fingerprint:
                return row
        return None

    def insert(self, row: dict) -> dict:
        if row.get("source_id") in self.fail_source_ids:
            raise ExternalServiceError(f"simulated insert failure for {row.get('source_id')}")
        row_id = f"row-{self._next_id}"
        self._next_id += 1
        stored = {"id": row_id, "enrichment_status": "pending", **row}
        self.rows[row_id] = stored
        return stored

    def update(self, opportunity_id: str, row: dict) -> dict:
        existing = self.rows.get(opportunity_id)
        if existing is None:
            raise ExternalServiceError(f"no such row {opportunity_id}")
        existing.update(row)
        return existing

    def set_enrichment_status(
        self, opportunity_id: str, *, status: str, queued_at: datetime | None = None
    ) -> dict:
        existing = self.rows.get(opportunity_id)
        if existing is None:
            raise ExternalServiceError(f"no such row {opportunity_id}")
        existing["enrichment_status"] = status
        if queued_at is not None:
            existing["enrichment_queued_at"] = queued_at.isoformat()
        return existing

    def count_pending_enrichment(self) -> int:
        return sum(1 for row in self.rows.values() if row.get("enrichment_status") != "completed")


class FakeQueue:
    def __init__(self):
        self.enqueued: list[tuple[str, dict]] = []

    async def enqueue(self, task: str, /, **payload) -> str:
        self.enqueued.append((task, payload))
        return f"fake-{len(self.enqueued)}"


def _opportunity(**overrides) -> NormalizedOpportunity:
    defaults = {
        "category": "programs",
        "title": "AWS Cloud Clubs Captain",
        "organization": "Amazon Web Services",
        "apply_url": "https://builder.aws.com/community/student-builder-groups",
        "source": "aws-cloud-clubs",
        "source_id": "aws-cloud-clubs-captain",
    }
    defaults.update(overrides)
    return NormalizedOpportunity(**defaults)


def _service() -> tuple[OpportunityService, FakeOpportunityRepository, FakeQueue]:
    repository = FakeOpportunityRepository()
    queue = FakeQueue()
    service = OpportunityService(repository=repository, queue=queue)
    return service, repository, queue


def test_fingerprint_is_deterministic_and_content_based():
    a = _opportunity(source="source-a", source_id="a-1", apply_url="https://example.com/apply?utm_source=x")
    b = _opportunity(source="source-b", source_id="b-1", apply_url="https://example.com/apply/")

    assert generate_fingerprint(a) == generate_fingerprint(b)

    c = _opportunity(source="source-a", source_id="a-1", title="A Completely Different Program")
    assert generate_fingerprint(a) != generate_fingerprint(c)


def test_validate_rejects_empty_title():
    service, _, _ = _service()
    opportunity = _opportunity(title="")

    result = service.validate(opportunity)

    assert result.is_valid is False
    assert any(issue.field == "title" for issue in result.errors)


async def test_find_duplicate_prefers_source_source_id_over_fingerprint():
    service, repository, _ = _service()
    first = _opportunity()
    await service.save_opportunity(first)

    # Same (source, source_id), different content -> different fingerprint,
    # but still the same real-world listing per the source's own identity.
    changed = _opportunity(title="AWS Cloud Clubs Captain (Updated Title)")
    duplicate = service.find_duplicate(changed)

    assert duplicate is not None
    assert duplicate["source"] == "aws-cloud-clubs"
    assert len(repository.rows) == 1


async def test_save_opportunity_creates_and_queues_enrichment():
    service, repository, queue = _service()

    result = await service.save_opportunity(_opportunity())

    assert result.outcome == "created"
    assert result.opportunity_id is not None
    assert len(repository.rows) == 1
    assert queue.enqueued == [("enrich_opportunity", {"opportunity_id": result.opportunity_id})]
    assert service.get_stats().created == 1
    assert service.get_stats().queued_for_enrichment == 1


async def test_save_opportunity_updates_on_second_call_without_requeueing():
    service, repository, queue = _service()
    first = await service.save_opportunity(_opportunity())

    second = await service.save_opportunity(
        _opportunity(title="AWS Cloud Clubs Captain (Refreshed)")
    )

    assert second.outcome == "updated"
    assert second.opportunity_id == first.opportunity_id
    assert len(repository.rows) == 1
    assert len(queue.enqueued) == 1  # not re-queued on update
    assert service.get_stats().created == 1
    assert service.get_stats().updated == 1


async def test_save_opportunity_rejects_invalid_without_writing():
    service, repository, queue = _service()

    result = await service.save_opportunity(
        _opportunity(title="", apply_url=None, description=None)
    )

    assert result.outcome == "rejected"
    assert result.issues
    assert repository.rows == {}
    assert queue.enqueued == []
    assert service.get_stats().rejected == 1


async def test_save_batch_isolates_errors_and_aggregates_stats():
    service, repository, _ = _service()
    repository.fail_source_ids = {"e2"}
    batch = [
        _opportunity(source_id="e1", title="Program One"),
        _opportunity(source_id="e2", title="Program Two"),
        _opportunity(source_id="e3", title="Program Three"),
    ]

    result = await service.save_batch(batch)

    assert result.total == 3
    assert result.created == 2
    assert result.errors == 1
    assert [r.outcome for r in result.results] == ["created", "error", "created"]
    assert service.get_stats().created == 2
    assert service.get_stats().errors == 1


async def test_mark_for_enrichment_updates_row_and_enqueues():
    service, repository, queue = _service()
    row = repository.insert({"source": "manual", "source_id": None, "title": "Manual Row"})

    await service.mark_for_enrichment(row["id"])

    assert repository.rows[row["id"]]["enrichment_status"] == "pending"
    assert "enrichment_queued_at" in repository.rows[row["id"]]
    assert queue.enqueued == [("enrich_opportunity", {"opportunity_id": row["id"]})]
    assert service.get_stats().queued_for_enrichment == 1


async def test_update_opportunity_does_not_requeue_enrichment():
    service, repository, queue = _service()
    created = await service.save_opportunity(_opportunity())
    assert len(queue.enqueued) == 1

    result = await service.update_opportunity(
        created.opportunity_id, _opportunity(title="Manually Corrected Title")
    )

    assert result.outcome == "updated"
    assert len(queue.enqueued) == 1  # unchanged
    assert repository.rows[created.opportunity_id]["title"] == "Manually Corrected Title"


def test_reset_stats():
    service, _, _ = _service()
    service.stats.created = 5

    service.reset_stats()

    assert service.get_stats().created == 0
    assert service.get_stats().total_processed == 0


# ---------------------------------------------------------------------------
# max_success_count -- the "B" semantics for a per-source daily save cap
# (see OpportunityService.save_batch()'s docstring): stop once
# created + updated reaches the target, not once every candidate has been
# attempted.
# ---------------------------------------------------------------------------


async def test_save_batch_stops_once_max_success_count_reached():
    service, repository, _ = _service()
    batch = [
        _opportunity(source_id=f"p{i}", title=f"Program {i}", apply_url=f"https://example.com/{i}")
        for i in range(5)
    ]

    result = await service.save_batch(batch, max_success_count=3)

    assert result.total == 5
    assert result.created == 3
    assert result.skipped == 2
    assert len(result.results) == 3  # skipped items don't get a result entry
    assert len(repository.rows) == 3


async def test_save_batch_max_success_count_counts_updates_too():
    service, repository, _ = _service()
    # Pre-populate 2 rows so the first 2 items in the next batch resolve as
    # "updated", not "created" -- the cap must count BOTH toward its target.
    await service.save_opportunity(
        _opportunity(source_id="p0", title="Program 0", apply_url="https://example.com/0")
    )
    await service.save_opportunity(
        _opportunity(source_id="p1", title="Program 1", apply_url="https://example.com/1")
    )
    assert len(repository.rows) == 2

    batch = [
        _opportunity(source_id=f"p{i}", title=f"Program {i} (refreshed)", apply_url=f"https://example.com/{i}")
        for i in range(4)
    ]

    result = await service.save_batch(batch, max_success_count=3)

    assert result.updated == 2  # p0, p1 (already existed)
    assert result.created == 1  # p2 (the 3rd success, then the cap stops)
    assert result.skipped == 1  # p3 never attempted
    assert len(repository.rows) == 3


async def test_save_batch_invalid_candidates_do_not_count_against_the_cap():
    service, repository, _ = _service()
    batch = [
        _opportunity(source_id="bad", title=""),  # rejected by validate()
        _opportunity(source_id="p0", title="Program 0", apply_url="https://example.com/0"),
        _opportunity(source_id="p1", title="Program 1", apply_url="https://example.com/1"),
    ]

    result = await service.save_batch(batch, max_success_count=2)

    assert result.rejected == 1
    assert result.created == 2  # both good candidates still got saved
    assert result.skipped == 0
    assert len(repository.rows) == 2


async def test_save_batch_max_success_count_none_means_unlimited():
    service, repository, _ = _service()
    batch = [
        _opportunity(source_id=f"p{i}", title=f"Program {i}", apply_url=f"https://example.com/{i}")
        for i in range(5)
    ]

    result = await service.save_batch(batch, max_success_count=None)

    assert result.created == 5
    assert result.skipped == 0
    assert len(repository.rows) == 5


# ---------------------------------------------------------------------------
# preview_opportunity() / preview_batch() -- the dry-run path: must resolve
# identically to the real path but never write.
# ---------------------------------------------------------------------------


def test_preview_opportunity_reports_would_create_without_writing():
    service, repository, queue = _service()

    result = service.preview_opportunity(_opportunity())

    assert result.outcome == "would_create"
    assert result.opportunity_id is None
    assert repository.rows == {}
    assert queue.enqueued == []
    # A preview must not perturb the service's own cumulative stats either --
    # it isn't a real ingestion event.
    assert service.get_stats().created == 0


async def test_preview_opportunity_reports_would_update_for_an_existing_row():
    service, repository, _ = _service()
    created = await service.save_opportunity(_opportunity())

    result = service.preview_opportunity(_opportunity(title="AWS Cloud Clubs Captain (Refreshed)"))

    assert result.outcome == "would_update"
    assert result.opportunity_id == created.opportunity_id
    assert len(repository.rows) == 1  # unchanged -- still just the real save above
    assert repository.rows[created.opportunity_id]["title"] == "AWS Cloud Clubs Captain"


def test_preview_opportunity_reports_rejected_same_as_save_would():
    service, _, _ = _service()

    result = service.preview_opportunity(_opportunity(title="", apply_url=None, description=None))

    assert result.outcome == "rejected"
    assert result.issues


def test_preview_batch_respects_max_success_count():
    service, repository, _ = _service()
    batch = [
        _opportunity(source_id=f"p{i}", title=f"Program {i}", apply_url=f"https://example.com/{i}")
        for i in range(5)
    ]

    preview = service.preview_batch(batch, max_success_count=2)

    assert preview.created == 2
    assert preview.skipped == 3
    assert repository.rows == {}  # dry run -- nothing written regardless of the cap


async def test_preview_batch_matches_save_batch_for_the_same_input():
    # Not a hypothetical guarantee -- run both against the same fresh
    # service+repository and assert the per-item outcomes agree (modulo the
    # would_/real outcome label), since both share `_resolve()`.
    service, repository, _ = _service()
    batch = [
        _opportunity(source_id=f"p{i}", title=f"Program {i}", apply_url=f"https://example.com/{i}")
        for i in range(4)
    ]

    preview = service.preview_batch(batch)
    assert repository.rows == {}
    assert preview.created == 4

    real = await service.save_batch(batch)

    assert real.created == 4
    assert len(repository.rows) == 4
    assert {r.source_id for r in preview.results} == {r.source_id for r in real.results}
