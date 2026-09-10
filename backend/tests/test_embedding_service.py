"""Exercises `EmbeddingService` against a fake generator and a fake
in-memory repository — no real Supabase call, no real model load. Confirms
the lifecycle rules from the product spec independent of the actual model
or database:

  * an embedding is generated only when missing (never on every request if
    a valid one already exists);
  * "changed" data (simulated here the same way the real invalidation
    trigger — supabase/schema/022_recommendation_embedding_invalidation.sql
    — represents it: embedding cleared back to NULL) is treated exactly
    like "missing", and regenerates from whatever the current field values
    are, not stale ones;
  * an empty/meaningless document never gets embedded;
  * a generation or save failure is isolated — swallowed, logged, and never
    leaves a partially-written record — rather than propagating and taking
    the caller down with it;
  * a wrong-dimension vector is rejected before it would ever reach the
    `vector(384)` column;
  * two concurrent calls for the same user/opportunity only generate once.

`get_supabase`/`get_admin_supabase` are monkeypatched to return an opaque
sentinel — EmbeddingService only ever passes that value through to the
(fake) repository, never touches it itself, so a real Supabase client was
never needed here in the first place.
"""

import asyncio

from app.core.exceptions import NotFoundError
from app.services.embedding_service import EmbeddingService

FAKE_CLIENT = object()


class FakeEmbeddingGenerator:
    """Duck-types EmbeddingGenerator/BaseEmbedder — dimensions is read
    directly by EmbeddingService's dimension guard, same as the real one
    reading settings.EMBEDDING_DIMENSIONS."""

    def __init__(
        self,
        *,
        dimensions: int = 384,
        fail: bool = False,
        vector: list[float] | None = None,
    ):
        self.dimensions = dimensions
        self.model = "fake-model"
        self.fail = fail
        self.vector = vector
        self.embed_calls: list[str] = []
        self.embed_batch_calls: list[list[str]] = []
        # Bumped inside embed()/embed_batch() while "in flight" — used by
        # the dedup tests to assert two concurrent calls only ever have one
        # in-flight generation at a time for the same key.
        self.max_concurrent_calls = 0
        self._in_flight = 0

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        self._in_flight += 1
        self.max_concurrent_calls = max(self.max_concurrent_calls, self._in_flight)
        try:
            # Yield control so a genuinely concurrent second call (if the
            # caller doesn't actually serialize them) would interleave here.
            await asyncio.sleep(0)
            if self.fail:
                raise RuntimeError("simulated embedding failure")
            return list(self.vector) if self.vector is not None else [0.1] * self.dimensions
        finally:
            self._in_flight -= 1

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_batch_calls.append(list(texts))
        if self.fail:
            raise RuntimeError("simulated embedding batch failure")
        if self.vector is not None:
            return [list(self.vector) for _ in texts]
        return [[0.1] * self.dimensions for _ in texts]


class FakeEmbeddingRepository:
    """Duck-types EmbeddingRepository. Profiles/opportunities are plain
    dicts keyed by id; embeddings are tracked in separate dicts so "row
    exists but embedding is NULL" and "row doesn't exist at all" stay
    distinguishable, same as the real schema."""

    def __init__(self):
        self.profiles: dict[str, dict] = {}
        self.profile_embeddings: dict[str, list[float] | None] = {}
        self.opportunities: dict[str, dict] = {}
        self.opportunity_embeddings: dict[str, list[float] | None] = {}
        self.save_profile_calls: list[tuple[str, list[float]]] = []
        self.save_opportunity_calls: list[tuple[str, list[float]]] = []
        self.fail_profile_save_for: set[str] = set()
        self.fail_opportunity_save_for: set[str] = set()

    def add_profile(
        self, user_id: str, fields: dict, *, embedding: list[float] | None = None
    ):
        self.profiles[user_id] = fields
        self.profile_embeddings[user_id] = embedding

    def add_opportunity(
        self, opportunity_id: str, fields: dict, *, embedding: list[float] | None = None
    ):
        self.opportunities[opportunity_id] = {"id": opportunity_id, **fields}
        self.opportunity_embeddings[opportunity_id] = embedding

    # -- profiles ----------------------------------------------------------

    def get_profile_for_embedding(self, client, user_id: str) -> dict | None:
        return self.profiles.get(user_id)

    def has_profile_embedding(self, client, user_id: str) -> bool:
        if user_id not in self.profile_embeddings:
            raise NotFoundError("Profile not found.")
        return self.profile_embeddings[user_id] is not None

    def save_profile_embedding(self, client, user_id: str, embedding: list[float]) -> None:
        if user_id in self.fail_profile_save_for:
            raise RuntimeError("simulated save failure")
        self.profile_embeddings[user_id] = embedding
        self.save_profile_calls.append((user_id, embedding))

    # -- opportunities ------------------------------------------------------

    def has_opportunity_embedding(self, client, opportunity_id: str) -> bool:
        return self.opportunity_embeddings.get(opportunity_id) is not None

    def get_opportunity_for_embedding(self, client, opportunity_id: str) -> dict | None:
        return self.opportunities.get(opportunity_id)

    def save_opportunity_embedding(
        self, client, opportunity_id: str, embedding: list[float]
    ) -> None:
        if opportunity_id in self.fail_opportunity_save_for:
            raise RuntimeError("simulated save failure")
        self.opportunity_embeddings[opportunity_id] = embedding
        self.save_opportunity_calls.append((opportunity_id, embedding))

    def get_opportunities_missing_embedding(self, client, limit: int) -> list[dict]:
        missing = [
            self.opportunities[oid]
            for oid, embedding in self.opportunity_embeddings.items()
            if embedding is None and oid in self.opportunities
        ]
        return missing[:limit]


def _service(*, generator: FakeEmbeddingGenerator | None = None):
    generator = generator or FakeEmbeddingGenerator()
    repository = FakeEmbeddingRepository()
    service = EmbeddingService(generator=generator, repository=repository)
    return service, generator, repository


def _patch_supabase(monkeypatch):
    monkeypatch.setattr(
        "app.services.embedding_service.get_supabase", lambda access_token=None: FAKE_CLIENT
    )
    monkeypatch.setattr("app.services.embedding_service.get_admin_supabase", lambda: FAKE_CLIENT)


_PROFILE_FIELDS = {
    "target_role": "Software Engineer",
    "target_company": "Acme Corp",
    "career_interests": ["Backend"],
    "current_skills": ["Python"],
    "headline": "Aspiring engineer",
    "bio": "I like building things.",
    "degree": "B.Tech",
    "branch": "CSE",
    "major": "Computer Science",
}

_OPPORTUNITY_FIELDS = {
    "title": "Backend Engineering Intern",
    "organization": "Acme Corp",
    "category": "internships",
    "description": "Work on backend systems.",
    "tags": ["python", "backend"],
    "duration": "3 months",
}


# ---------------------------------------------------------------------------
# embed_profile
# ---------------------------------------------------------------------------


async def test_embed_profile_missing_embedding_generates_and_saves(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=None)

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is True
    assert len(generator.embed_calls) == 1
    assert "Software Engineer" in generator.embed_calls[0]
    assert repository.profile_embeddings["u1"] is not None
    assert len(repository.profile_embeddings["u1"]) == generator.dimensions


async def test_embed_profile_existing_embedding_is_a_noop(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=[0.2] * 384)

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is False
    assert generator.embed_calls == []
    assert repository.save_profile_calls == []
    # Untouched — still the original embedding, not regenerated.
    assert repository.profile_embeddings["u1"] == [0.2] * 384


async def test_embed_profile_changed_data_is_treated_like_missing(monkeypatch):
    # Simulates what the real invalidation trigger does: a relevant field
    # changed, so the embedding column was cleared back to NULL. The next
    # call must regenerate from the CURRENT field values, not stale ones.
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=[0.2] * 384)

    # Field change + trigger firing, represented directly:
    repository.profiles["u1"] = {**_PROFILE_FIELDS, "target_role": "Data Scientist"}
    repository.profile_embeddings["u1"] = None

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is True
    assert len(generator.embed_calls) == 1
    assert "Data Scientist" in generator.embed_calls[0]
    assert "Software Engineer" not in generator.embed_calls[0]


async def test_embed_profile_empty_profile_never_calls_generator(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    empty_fields = dict.fromkeys(_PROFILE_FIELDS, None) | {
        "career_interests": [],
        "current_skills": [],
    }
    repository.add_profile("u1", empty_fields, embedding=None)

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is False
    assert generator.embed_calls == []
    assert repository.profile_embeddings["u1"] is None
    assert repository.save_profile_calls == []


async def test_embed_profile_missing_profile_row_returns_false(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    # Profile row itself doesn't exist for this id at all, distinct from
    # "exists but empty" above — has_profile_embedding() would raise
    # NotFoundError against a real repository for a truly missing row, but
    # get_profile_for_embedding() (called after) already returns None for
    # this fake, so embed_profile must handle that gracefully. We register
    # the id in profile_embeddings (so has_profile_embedding doesn't raise)
    # but not in profiles, to isolate exactly this branch.
    repository.profile_embeddings["ghost"] = None

    generated = await service.embed_profile(user_id="ghost", access_token="token")

    assert generated is False
    assert generator.embed_calls == []


async def test_embed_profile_generation_failure_is_isolated(monkeypatch):
    _patch_supabase(monkeypatch)
    generator = FakeEmbeddingGenerator(fail=True)
    service, generator, repository = _service(generator=generator)
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=None)

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is False
    # No partial/corrupt write — embedding stays exactly as it was (NULL).
    assert repository.profile_embeddings["u1"] is None
    assert repository.save_profile_calls == []


async def test_embed_profile_save_failure_is_isolated(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=None)
    repository.fail_profile_save_for.add("u1")

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is False
    # The model call happened, but the write failed — must not be treated
    # as success, and must not silently leave a half-applied state either
    # (a single .update() call is atomic per-row, so there's nothing to
    # roll back — but the column must still read as "not embedded").
    assert repository.profile_embeddings["u1"] is None


async def test_embed_profile_rejects_wrong_dimension_vector(monkeypatch):
    _patch_supabase(monkeypatch)
    generator = FakeEmbeddingGenerator(vector=[0.1] * 42)  # wrong size on purpose
    service, generator, repository = _service(generator=generator)
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=None)

    generated = await service.embed_profile(user_id="u1", access_token="token")

    assert generated is False
    assert repository.profile_embeddings["u1"] is None
    assert repository.save_profile_calls == []


async def test_embed_profile_concurrent_calls_generate_only_once(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_profile("u1", _PROFILE_FIELDS, embedding=None)

    results = await asyncio.gather(
        service.embed_profile(user_id="u1", access_token="token"),
        service.embed_profile(user_id="u1", access_token="token"),
    )

    assert sorted(results) == [False, True]
    assert len(generator.embed_calls) == 1
    assert len(repository.save_profile_calls) == 1


# ---------------------------------------------------------------------------
# embed_opportunity
# ---------------------------------------------------------------------------


async def test_embed_opportunity_missing_embedding_generates_and_saves(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)

    generated = await service.embed_opportunity("o1")

    assert generated is True
    assert len(generator.embed_calls) == 1
    assert "Backend Engineering Intern" in generator.embed_calls[0]
    assert repository.opportunity_embeddings["o1"] is not None


async def test_embed_opportunity_existing_embedding_is_a_noop(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=[0.3] * 384)

    generated = await service.embed_opportunity("o1")

    assert generated is False
    assert generator.embed_calls == []
    assert repository.opportunity_embeddings["o1"] == [0.3] * 384


async def test_embed_opportunity_changed_data_is_treated_like_missing(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=[0.3] * 384)

    # Field change + invalidation trigger firing, represented directly:
    repository.opportunities["o1"] = {
        "id": "o1",
        **_OPPORTUNITY_FIELDS,
        "title": "Frontend Engineering Intern",
    }
    repository.opportunity_embeddings["o1"] = None

    generated = await service.embed_opportunity("o1")

    assert generated is True
    assert "Frontend Engineering Intern" in generator.embed_calls[0]
    assert "Backend Engineering Intern" not in generator.embed_calls[0]


async def test_embed_opportunity_empty_document_never_calls_generator(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    empty_fields = dict.fromkeys(_OPPORTUNITY_FIELDS, None) | {"tags": []}
    repository.add_opportunity("o1", empty_fields, embedding=None)

    generated = await service.embed_opportunity("o1")

    assert generated is False
    assert generator.embed_calls == []
    assert repository.opportunity_embeddings["o1"] is None


async def test_embed_opportunity_missing_row_returns_false(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()

    generated = await service.embed_opportunity("does-not-exist")

    assert generated is False
    assert generator.embed_calls == []


async def test_embed_opportunity_generation_failure_is_isolated(monkeypatch):
    _patch_supabase(monkeypatch)
    generator = FakeEmbeddingGenerator(fail=True)
    service, generator, repository = _service(generator=generator)
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)

    generated = await service.embed_opportunity("o1")

    assert generated is False
    assert repository.opportunity_embeddings["o1"] is None
    assert repository.save_opportunity_calls == []


async def test_embed_opportunity_concurrent_calls_generate_only_once(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)

    results = await asyncio.gather(
        service.embed_opportunity("o1"),
        service.embed_opportunity("o1"),
    )

    assert sorted(results) == [False, True]
    assert len(generator.embed_calls) == 1


# ---------------------------------------------------------------------------
# backfill
# ---------------------------------------------------------------------------


async def test_backfill_embeds_only_missing_rows(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)
    repository.add_opportunity("o2", _OPPORTUNITY_FIELDS, embedding=[0.5] * 384)
    repository.add_opportunity(
        "o3", {**_OPPORTUNITY_FIELDS, "title": "Data Intern"}, embedding=None
    )

    embedded = await service.backfill(limit=10)

    assert embedded == 2
    assert repository.opportunity_embeddings["o1"] is not None
    assert repository.opportunity_embeddings["o2"] == [0.5] * 384  # untouched
    assert repository.opportunity_embeddings["o3"] is not None
    assert len(generator.embed_batch_calls) == 1
    assert len(generator.embed_batch_calls[0]) == 2


async def test_backfill_skips_empty_documents_without_calling_generator(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    empty_fields = dict.fromkeys(_OPPORTUNITY_FIELDS, None) | {"tags": []}
    repository.add_opportunity("o1", empty_fields, embedding=None)

    embedded = await service.backfill(limit=10)

    assert embedded == 0
    assert generator.embed_batch_calls == []
    assert repository.opportunity_embeddings["o1"] is None


async def test_backfill_zero_or_negative_limit_is_a_noop(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)

    assert await service.backfill(limit=0) == 0
    assert await service.backfill(limit=-5) == 0
    assert generator.embed_batch_calls == []


async def test_backfill_batch_failure_writes_nothing(monkeypatch):
    _patch_supabase(monkeypatch)
    generator = FakeEmbeddingGenerator(fail=True)
    service, generator, repository = _service(generator=generator)
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)
    repository.add_opportunity(
        "o2", {**_OPPORTUNITY_FIELDS, "title": "Data Intern"}, embedding=None
    )

    embedded = await service.backfill(limit=10)

    assert embedded == 0
    assert repository.opportunity_embeddings["o1"] is None
    assert repository.opportunity_embeddings["o2"] is None
    assert repository.save_opportunity_calls == []


async def test_backfill_isolates_a_single_row_save_failure(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)
    repository.add_opportunity(
        "o2", {**_OPPORTUNITY_FIELDS, "title": "Data Intern"}, embedding=None
    )
    repository.fail_opportunity_save_for.add("o1")

    embedded = await service.backfill(limit=10)

    # o1's write failed and must stay unwritten; o2 must still succeed —
    # one bad row doesn't sink the whole batch.
    assert embedded == 1
    assert repository.opportunity_embeddings["o1"] is None
    assert repository.opportunity_embeddings["o2"] is not None


async def test_backfill_rejects_wrong_dimension_vectors_per_row(monkeypatch):
    _patch_supabase(monkeypatch)
    generator = FakeEmbeddingGenerator(vector=[0.1] * 42)
    service, generator, repository = _service(generator=generator)
    repository.add_opportunity("o1", _OPPORTUNITY_FIELDS, embedding=None)

    embedded = await service.backfill(limit=10)

    assert embedded == 0
    assert repository.opportunity_embeddings["o1"] is None


async def test_backfill_respects_limit(monkeypatch):
    _patch_supabase(monkeypatch)
    service, generator, repository = _service()
    for i in range(5):
        repository.add_opportunity(f"o{i}", _OPPORTUNITY_FIELDS, embedding=None)

    embedded = await service.backfill(limit=2)

    assert embedded == 2
    assert len(generator.embed_batch_calls[0]) == 2
    still_missing = sum(1 for v in repository.opportunity_embeddings.values() if v is None)
    assert still_missing == 3
