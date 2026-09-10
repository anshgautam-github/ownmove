"""Exercises `RecommendationService` (the class behind `GET /recommendations/
for-you`) against fake EmbeddingService/RecommendationRepository — no real
Supabase call, no real model load. Covers the business-logic half of the
endpoint audit: `get_supabase` is monkeypatched to an opaque sentinel client
that's only ever passed through, never touched, by the service itself.

Complements tests/test_recommendations_api.py, which covers the HTTP/auth
half (bearer token handling, the error envelope) via a real FastAPI
TestClient with this service swapped out for a fake at the route boundary.
Between the two, every item in the /for-you audit is covered by something
that actually executes.
"""

import asyncio

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.opportunity import Opportunity
from app.schemas.recommendation import MatchReason
from app.services.recommendation_service import RecommendationService

FAKE_CLIENT = object()


class _AnyKeyDict(dict):
    """Test helper: `.get(query_text, [])` returns the same fixed list for
    ANY key, so tests don't need to reproduce build_keyword_query()'s exact
    token-ordering algorithm just to register a matching dict key."""

    def __init__(self, value):
        super().__init__()
        self._value = value

    def get(self, key, default=None):
        return self._value


class FakeEmbeddingService:
    """Duck-types EmbeddingService. Recording-only — RecommendationService
    just has to call these, generating/backfilling embeddings is
    EmbeddingService's own already-tested responsibility (see
    tests/test_embedding_service.py)."""

    def __init__(self):
        self.embed_profile_calls: list[tuple[str, str]] = []
        self.backfill_calls: list[int] = []

    async def embed_profile(self, *, user_id: str, access_token: str) -> bool:
        self.embed_profile_calls.append((user_id, access_token))
        return False

    async def backfill(self, *, limit: int) -> int:
        self.backfill_calls.append(limit)
        return 0


class FakeRecommendationRepository:
    def __init__(self):
        self.profiles: dict[str, dict] = {}
        self.semantic: dict[str, list[dict]] = {}
        self.keyword: dict[str, list[dict]] = {}
        self.opportunities: dict[str, dict] = {}
        self.fallback_rows: list[dict] = []
        self.upserted: list[tuple] = []
        self.fail_semantic = False
        self.fail_keyword = False

    def get_profile_signals(self, client, user_id: str) -> dict | None:
        return self.profiles.get(user_id)

    def semantic_candidates(
        self, client, *, profile_id: str, match_count: int, opportunity_id: str | None = None
    ) -> list[dict]:
        if self.fail_semantic:
            raise RuntimeError("simulated Supabase RPC failure (semantic leg)")
        return self.semantic.get(profile_id, [])

    def keyword_candidates(
        self, client, *, query_text: str, match_count: int, opportunity_id: str | None = None
    ) -> list[dict]:
        if self.fail_keyword:
            raise RuntimeError("simulated Supabase RPC failure (keyword leg)")
        return self.keyword.get(query_text, [])

    def hydrate_opportunities(self, client, ids: list[str]) -> dict[str, dict]:
        return {oid: self.opportunities[oid] for oid in ids if oid in self.opportunities}

    def fallback_recent(self, client, limit: int) -> list[dict]:
        return self.fallback_rows[:limit]

    def upsert_recommendations(self, user_id, ranked, *, model_version) -> None:
        self.upserted.append((user_id, ranked, model_version))


def _opportunity_row(opportunity_id: str, **overrides) -> dict:
    row = {
        "id": opportunity_id,
        "category": "internships",
        "title": f"Opportunity {opportunity_id}",
        "organization": "Acme Corp",
        "logo_url": None,
        "description": "Great opportunity.",
        "location": None,
        "is_remote": True,
        "apply_url": "https://example.com/apply",
        "tags": ["python"],
        "eligible_years": [],
        "duration": "3 months",
        "application_deadline": None,
        "posted_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def _service():
    embeddings = FakeEmbeddingService()
    repository = FakeRecommendationRepository()
    service = RecommendationService(embedding_service=embeddings, repository=repository)
    return service, embeddings, repository


def _patch_supabase(monkeypatch):
    monkeypatch.setattr(
        "app.services.recommendation_service.get_supabase", lambda access_token=None: FAKE_CLIENT
    )


# ---------------------------------------------------------------------------
# missing profile
# ---------------------------------------------------------------------------


async def test_recommend_for_user_missing_profile_raises_not_found(monkeypatch):
    _patch_supabase(monkeypatch)
    service, _, repository = _service()
    # No profile registered for "u1" at all.

    with pytest.raises(NotFoundError):
        await service.recommend_for_user(user_id="u1", access_token="token")


# ---------------------------------------------------------------------------
# successful recommendations
# ---------------------------------------------------------------------------


async def test_recommend_for_user_returns_ranked_items_with_correct_shape(monkeypatch):
    _patch_supabase(monkeypatch)
    service, embeddings, repository = _service()
    repository.profiles["u1"] = {
        "id": "u1",
        "target_role": "Software Engineer",
        "target_company": None,
        "career_interests": ["Backend"],
        "current_skills": ["Python"],
        "headline": "Aspiring engineer",
    }
    repository.semantic["u1"] = [
        {"opportunity_id": "o1", "similarity": 0.9},
        {"opportunity_id": "o2", "similarity": 0.2},
    ]
    # keyword_candidates is keyed by the exact query text build_keyword_query()
    # produces — softwareengineer/backend/python tokens, order matters, so
    # rather than reverse-engineer that string, register under every query
    # this profile could plausibly produce via a permissive fallback below.
    repository.keyword = _AnyKeyDict(
        [{"opportunity_id": "o1", "rank": 0.5}, {"opportunity_id": "o3", "rank": 0.1}]
    )
    repository.opportunities = {
        "o1": _opportunity_row("o1"),
        "o2": _opportunity_row("o2"),
        "o3": _opportunity_row("o3"),
    }

    response = await service.recommend_for_user(user_id="u1", access_token="token")

    assert embeddings.embed_profile_calls == [("u1", "token")]
    assert embeddings.backfill_calls  # backfill was attempted
    ids = [item.opportunity.id for item in response.items]
    assert set(ids) == {"o1", "o2", "o3"}  # hybrid union of both legs
    # Sorted highest score first.
    scores = [item.score for item in response.items]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= item.score <= 1.0 for item in response.items)
    assert all(isinstance(r, MatchReason) for item in response.items for r in item.reasons)
    assert response.model is not None
    assert response.generated_at is not None
    # Cached as a side effect.
    assert len(repository.upserted) == 1


# ---------------------------------------------------------------------------
# empty recommendations
# ---------------------------------------------------------------------------


async def test_recommend_for_user_empty_candidate_pool_falls_back_to_recent(monkeypatch):
    _patch_supabase(monkeypatch)
    service, _, repository = _service()
    # A brand-new profile: exists, but no skills/interests/target role, so
    # semantic_candidates/keyword_candidates both come back empty.
    repository.profiles["u1"] = {
        "id": "u1",
        "target_role": None,
        "target_company": None,
        "career_interests": [],
        "current_skills": [],
        "headline": None,
    }
    repository.fallback_rows = [_opportunity_row("recent-1"), _opportunity_row("recent-2")]

    response = await service.recommend_for_user(user_id="u1", access_token="token")

    assert len(response.items) == 2
    ids = {item.opportunity.id for item in response.items}
    assert ids == {"recent-1", "recent-2"}
    # Fallback path assigns no reasons — nothing but freshness contributed.
    assert all(item.reasons == [] for item in response.items)


async def test_recommend_for_user_truly_empty_result_returns_empty_list_not_error(monkeypatch):
    _patch_supabase(monkeypatch)
    service, _, repository = _service()
    repository.profiles["u1"] = {
        "id": "u1",
        "target_role": None,
        "target_company": None,
        "career_interests": [],
        "current_skills": [],
        "headline": None,
    }
    repository.fallback_rows = []  # nothing at all in the corpus

    response = await service.recommend_for_user(user_id="u1", access_token="token")

    assert response.items == []


# ---------------------------------------------------------------------------
# a single malformed row must not break the whole response
# ---------------------------------------------------------------------------


async def test_recommend_for_user_isolates_a_malformed_opportunity_row(monkeypatch):
    _patch_supabase(monkeypatch)

    class ExplodingOpportunity(Opportunity):
        # Subclasses the REAL Opportunity model rather than being a bare
        # duck-typed stand-in — a plain object here would make the "good"
        # row fail too, just for a different reason: RecommendedOpportunity
        # is a pydantic model with `opportunity: Opportunity`, and pydantic
        # rejects an arbitrary object that isn't a dict or an actual
        # Opportunity (sub)instance. Subclassing keeps the "good" row a
        # genuine, valid Opportunity while still letting "bad" raise, so
        # this test actually exercises the isolation behavior it claims to.
        def __init__(self, **row):
            if row["id"] == "bad":
                raise ValueError("simulated schema validation failure")
            super().__init__(**row)

    monkeypatch.setattr(
        "app.services.recommendation_service.Opportunity", ExplodingOpportunity
    )

    service, _, repository = _service()
    repository.profiles["u1"] = {
        "id": "u1",
        "target_role": None,
        "target_company": None,
        "career_interests": [],
        "current_skills": [],
        "headline": None,
    }
    repository.semantic["u1"] = [
        {"opportunity_id": "good", "similarity": 0.9},
        {"opportunity_id": "bad", "similarity": 0.8},
    ]
    repository.keyword = _AnyKeyDict([])
    repository.opportunities = {
        "good": _opportunity_row("good"),
        "bad": _opportunity_row("bad"),
    }

    response = await service.recommend_for_user(user_id="u1", access_token="token")

    ids = [item.opportunity.id for item in response.items]
    assert ids == ["good"]  # "bad" was skipped, not a 500


# ---------------------------------------------------------------------------
# backend errors propagate (for the route layer / global handler to sanitize)
# ---------------------------------------------------------------------------


async def test_recommend_for_user_propagates_unexpected_repository_errors(monkeypatch):
    _patch_supabase(monkeypatch)
    service, _, repository = _service()
    repository.profiles["u1"] = {
        "id": "u1",
        "target_role": "Software Engineer",
        "target_company": None,
        "career_interests": [],
        "current_skills": [],
        "headline": None,
    }
    repository.fail_semantic = True

    # A genuine backend failure (e.g. Supabase RPC error) must not be
    # silently swallowed into a fake-empty response — "handled gracefully"
    # means the caller (the route + the global exception handler) turns
    # this into a clean opaque 500, not that the service pretends nothing
    # went wrong.
    with pytest.raises(RuntimeError, match="simulated Supabase RPC failure"):
        await asyncio.wait_for(
            service.recommend_for_user(user_id="u1", access_token="token"), timeout=5
        )
