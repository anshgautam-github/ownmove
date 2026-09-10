"""Exercises `GET /api/v1/recommendations/for-you` through a real FastAPI
TestClient — the actual auth dependency chain (api/deps.py -> core/
security.py), the actual global error-handling middleware (middleware/
error_handler.py), and the actual route wiring in api/v1/routes/
recommendations.py all run for real. Only the one call that would otherwise
hit a live Supabase project — `RecommendationService.recommend_for_user` —
is swapped out for a fake at the module boundary
(`app.api.v1.routes.recommendations._service`), the same pattern
tests/test_recommendation_service.py uses one layer down for the business
logic itself.

Together the two files cover every item in the /for-you endpoint audit:
  1. authenticates the current user correctly            -> this file
  2. gets the correct profile id from the authenticated
     user (never from client-supplied input)          -> this file
  3. generates the profile embedding only when needed -> test_embedding_service.py
  4. retrieves the hybrid candidate pool               -> test_recommendation_service.py
  5. ranks via the existing ranking system    -> test_ranking.py / test_recommendation_service.py
  6. returns the final ranked opportunities   -> this file + test_recommendation_service.py
  7. never exposes another user's profile data -> this file (RLS/user-scoped
                                                    client; see recommendation_repository.py)
  8. never exposes internal embedding vectors  -> this file
  9. never exposes private Supabase/service-role info -> this file
  10. handles a missing profile gracefully                  -> this file
  11. handles an empty recommendation result gracefully     -> this file
  12. never leaks stack traces on error                     -> this file
"""

import time

import jwt

from app.core.exceptions import NotFoundError
from app.schemas.opportunity import Opportunity
from app.schemas.recommendation import MatchReason, RecommendationResponse, RecommendedOpportunity

# Matches conftest.py's os.environ.setdefault("SUPABASE_JWT_SECRET", ...) —
# the same secret the app's own JWT verification (core/security.py) reads,
# so tokens signed here are genuinely valid against the real auth code path.
_TEST_JWT_SECRET = "test-secret"


def _make_token(user_id: str = "test-user-id", *, expired: bool = False) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now - 60 if expired else now + 3600,
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


class FakeRecommendationService:
    """Duck-types RecommendationService — only recommend_for_user is
    exercised by GET /for-you, so that's all this needs to implement."""

    def __init__(self, *, response: RecommendationResponse | None = None, exception=None):
        self._response = response
        self._exception = exception
        self.calls: list[tuple[str, str]] = []

    async def recommend_for_user(self, *, user_id: str, access_token: str):
        self.calls.append((user_id, access_token))
        if self._exception is not None:
            raise self._exception
        return self._response


def _install_fake_service(monkeypatch, fake: FakeRecommendationService) -> None:
    monkeypatch.setattr("app.api.v1.routes.recommendations._service", fake)


def _empty_response() -> RecommendationResponse:
    return RecommendationResponse(
        items=[], generated_at="2026-01-01T00:00:00+00:00", model="hybrid-v1:x"
    )


def _sample_opportunity(**overrides) -> Opportunity:
    fields = {
        "id": "o1",
        "category": "internships",
        "title": "Backend Engineering Intern",
        "organization": "Acme Corp",
        "logo_url": None,
        "description": "Work on backend systems.",
        "location": None,
        "is_remote": True,
        "apply_url": "https://example.com/apply",
        "tags": ["python", "backend"],
        "eligible_years": [],
        "duration": "3 months",
        "application_deadline": None,
        "posted_at": None,
    }
    fields.update(overrides)
    return Opportunity(**fields)


# ---------------------------------------------------------------------------
# 1. authentication
# ---------------------------------------------------------------------------


def test_for_you_requires_auth(client):
    response = client.get("/api/v1/recommendations/for-you")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_for_you_rejects_malformed_token(client):
    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_for_you_rejects_expired_token(client):
    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": f"Bearer {_make_token(expired=True)}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# 2 & 7. correct profile id from the token; never from client input
# ---------------------------------------------------------------------------


def test_for_you_ignores_client_supplied_user_id(client, monkeypatch):
    fake = FakeRecommendationService(
        response=_empty_response()
    )
    _install_fake_service(monkeypatch, fake)

    response = client.get(
        "/api/v1/recommendations/for-you?user_id=someone-elses-id",
        headers={"Authorization": f"Bearer {_make_token(user_id='real-user-id')}"},
    )

    assert response.status_code == 200
    # The service was only ever called with the id from the verified JWT —
    # the query param has no effect (the route doesn't even declare it).
    assert fake.calls == [("real-user-id", fake.calls[0][1])]


# ---------------------------------------------------------------------------
# 6, 8, 9. successful recommendations: shape, no embeddings, no secrets
# ---------------------------------------------------------------------------


def test_for_you_returns_ranked_opportunities(client, monkeypatch):
    canned = RecommendationResponse(
        items=[
            RecommendedOpportunity(
                opportunity=_sample_opportunity(id="o1"),
                score=0.87,
                reasons=[
                    MatchReason(
                        factor="semantic",
                        weight=0.45,
                        detail="87% semantically similar to your profile",
                    ),
                    MatchReason(
                        factor="skill_overlap",
                        weight=0.10,
                        detail="Matches 1 of your skills: python",
                    ),
                ],
            ),
            RecommendedOpportunity(
                opportunity=_sample_opportunity(id="o2"), score=0.42, reasons=[]
            ),
        ],
        generated_at="2026-01-01T00:00:00+00:00",
        model="hybrid-v1:sentence-transformers/all-MiniLM-L6-v2",
    )
    fake = FakeRecommendationService(response=canned)
    _install_fake_service(monkeypatch, fake)

    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": f"Bearer {_make_token(user_id='u1')}"},
    )

    assert response.status_code == 200
    body = response.json()

    assert [item["opportunity"]["id"] for item in body["items"]] == ["o1", "o2"]
    assert body["items"][0]["score"] == 0.87
    assert body["items"][0]["reasons"][0]["factor"] == "semantic"
    assert body["model"] == "hybrid-v1:sentence-transformers/all-MiniLM-L6-v2"
    assert fake.calls[0][0] == "u1"

    # 8/9: no embedding vector, no Supabase/service-role internals anywhere
    # in the response, structurally (Opportunity never declares the field,
    # so it can't be serialized) and textually (belt and suspenders).
    for item in body["items"]:
        assert "embedding" not in item["opportunity"]
        assert "search_vector" not in item["opportunity"]
    assert "service_role" not in response.text.lower()
    assert "supabase_service_role_key" not in response.text.lower()


# ---------------------------------------------------------------------------
# 11. empty recommendations handled gracefully
# ---------------------------------------------------------------------------


def test_for_you_empty_recommendations_returns_200_with_empty_list(client, monkeypatch):
    fake = FakeRecommendationService(
        response=_empty_response()
    )
    _install_fake_service(monkeypatch, fake)

    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    # Still a well-formed response, not a stripped-down "empty" shape the
    # frontend would have to special-case.
    assert "generated_at" in body
    assert "model" in body


# ---------------------------------------------------------------------------
# 10. missing profile handled gracefully
# ---------------------------------------------------------------------------


def test_for_you_missing_profile_returns_clean_404(client, monkeypatch):
    fake = FakeRecommendationService(
        exception=NotFoundError("Complete your profile before requesting recommendations.")
    )
    _install_fake_service(monkeypatch, fake)

    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["detail"] == "Complete your profile before requesting recommendations."
    assert "request_id" in body
    assert "Traceback" not in response.text


# ---------------------------------------------------------------------------
# 12. backend/database errors never leak internals or stack traces
# ---------------------------------------------------------------------------


def test_for_you_unexpected_backend_error_returns_opaque_500(client, monkeypatch):
    # Deliberately "juicy" so the assertions below actually prove the
    # message is scrubbed, not just coincidentally absent.
    fake = FakeRecommendationService(
        exception=RuntimeError("connection to postgres://admin:hunter2@10.0.0.5:5432 failed")
    )
    _install_fake_service(monkeypatch, fake)

    response = client.get(
        "/api/v1/recommendations/for-you",
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["detail"] == "Something went wrong."
    assert "hunter2" not in response.text
    assert "10.0.0.5" not in response.text
    assert "postgres://" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
