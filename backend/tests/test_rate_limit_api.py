"""Rate limiting exercised through the REAL FastAPI request path: a real
`TestClient(create_app())`, real routes, the real `rate_limit()` dependency
in `app/api/deps.py`, the real JWT verification chain, and the real global
error-handling middleware. Only the Redis backend is swapped for an
in-memory `fakeredis` instance (with Lua/`EVAL` support via `lupa`, so the
actual atomic script in app/core/rate_limiter.py runs for real) — the same
"swap the boundary, not the code path" approach test_recommendations_api.py
already uses for its one external dependency.

The shared `client` fixture in conftest.py runs with RATE_LIMIT_ENABLED=false
so every *other* test in this suite is unaffected by rate limiting (see the
comment there). This file uses its own `rl_app` fixture that turns rate
limiting back on, scoped to just these tests, with a fresh fakeredis
instance per test so tests never share counters.

Routes used as stand-ins for each category (their business logic is
irrelevant here — only whether the rate-limit dependency lets the request
through to the handler matters):
  * GET   /api/v1/profiles/me       -> AUTH_READ  (scaffold, raises 501)
  * PATCH /api/v1/profiles/me       -> AUTH_WRITE (scaffold, raises 501)
  * GET   /api/v1/recommendations/for-you -> AI_EXPENSIVE (service faked -> 200)
  * GET   /api/v1/health            -> no rate-limit dependency at all
"""

import time
from concurrent.futures import ThreadPoolExecutor

import fakeredis
import jwt
import pytest

import app.api.deps as deps_module
import app.core.rate_limit_policy as rate_limit_policy
from app.core.config import settings
from app.schemas.recommendation import RecommendationResponse

_TEST_JWT_SECRET = "test-secret"  # matches conftest.py's SUPABASE_JWT_SECRET


def _make_token(user_id: str = "test-user-id") -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


def _auth_headers(user_id: str = "test-user-id") -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


def _empty_recommendation_response() -> RecommendationResponse:
    return RecommendationResponse(items=[], generated_at="2026-01-01T00:00:00+00:00", model="test")


@pytest.fixture
def rl_app(monkeypatch):
    """A TestClient with rate limiting turned ON, backed by a fresh
    fakeredis instance. `app.api.deps.get_redis` is patched at the same
    boundary `app/api/deps.py::rate_limit()` itself calls it from, so the
    dependency, the Lua script, and everything else in the request path run
    unmodified — only where the Redis connection comes from is swapped.
    """
    from fastapi.testclient import TestClient

    from app.main import create_app

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(deps_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def fake_recommendation_service(monkeypatch):
    """Recommendations' own service call would otherwise hit Supabase/the
    embedding model — faked at the same module boundary
    test_recommendations_api.py uses, so /for-you can be used purely as an
    AI_EXPENSIVE stand-in here.
    """
    from tests.test_recommendations_api import FakeRecommendationService

    fake = FakeRecommendationService(response=_empty_recommendation_response())
    monkeypatch.setattr("app.api.v1.routes.recommendations._service", fake)
    return fake


# ---------------------------------------------------------------------------
# 1 & 7. requests below the limit succeed; authenticated requests are
# keyed correctly (per-user, not globally)
# ---------------------------------------------------------------------------


def test_requests_below_limit_reach_the_handler(rl_app, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 5)

    for _ in range(5):
        response = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
        # 501 == the scaffolded handler was actually reached: the request
        # was NOT rate limited. (The route itself isn't implemented yet —
        # see app/api/v1/routes/profiles.py — that's irrelevant here.)
        assert response.status_code == 501


# ---------------------------------------------------------------------------
# 2 & 10. the over-limit request gets HTTP 429 in the existing error envelope
# ---------------------------------------------------------------------------


def test_over_limit_request_returns_429_in_the_standard_envelope(rl_app, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    first = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
    second = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())

    assert first.status_code == 501
    assert second.status_code == 429
    body = second.json()
    # Same shape as every other AppError in this app (see
    # middleware/error_handler.py's docstring) — rate limiting extends the
    # existing envelope, it doesn't invent a new one.
    assert body["code"] == "rate_limited"
    assert "detail" in body
    assert "request_id" in body


# ---------------------------------------------------------------------------
# 11. Retry-After / X-RateLimit-* headers are correct
# ---------------------------------------------------------------------------


def test_rate_limit_headers_are_correct_on_the_denied_response(rl_app, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
    denied = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())

    assert denied.status_code == 429
    assert denied.headers["X-RateLimit-Limit"] == "1"
    assert denied.headers["X-RateLimit-Remaining"] == "0"
    retry_after = int(denied.headers["Retry-After"])
    assert retry_after > 0
    assert denied.headers["X-RateLimit-Reset"] == denied.headers["Retry-After"]


def test_rate_limit_headers_are_attached_to_a_genuine_2xx_response(
    rl_app, monkeypatch, fake_recommendation_service
):
    """Uses /recommendations/for-you (200 on success, via the faked
    service) rather than the /profiles/me scaffold (which always 501s even
    when "allowed") specifically so this proves headers reach a real
    successful response.

    NOTE on a real limitation this surfaced: FastAPI only merges a
    dependency's injected `Response.headers` into the final response on the
    plain success path. When the *route handler itself* subsequently raises
    some unrelated AppError (a 404, a 501 scaffold stub, etc.) after having
    been allowed through the rate limiter, the exception-handler middleware
    builds a fresh JSONResponse that does not inherit those headers — so
    X-RateLimit-* only reliably appears on an allowed request's *2xx*
    response, not on every allowed-but-otherwise-erroring one. The 429 path
    above is unaffected, since RateLimitError's headers are attached
    directly to the exception, not via the injected Response. Documented in
    RATE_LIMITING.md.
    """
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_PER_MINUTE", 5)

    allowed = rl_app.get("/api/v1/recommendations/for-you", headers=_auth_headers())

    assert allowed.status_code == 200
    assert allowed.headers["X-RateLimit-Limit"] == "5"
    assert allowed.headers["X-RateLimit-Remaining"] == "4"
    assert int(allowed.headers["X-RateLimit-Reset"]) > 0


# ---------------------------------------------------------------------------
# 3. the counter resets after the configured window
# ---------------------------------------------------------------------------


def test_counter_resets_after_the_window_elapses(rl_app, monkeypatch):
    # The real AUTH_READ window is a hardcoded 60s in rate_limit_policy.py
    # (_ONE_MINUTE) — shortened here to 1s so this test proves reset
    # behavior through the real request path without a 60-second sleep.
    # Everything else (the dependency, the route, the Lua script, Redis)
    # runs completely unmodified.
    monkeypatch.setattr(rate_limit_policy, "_ONE_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    first = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
    second = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
    assert first.status_code == 501
    assert second.status_code == 429

    time.sleep(1.2)

    third = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())
    assert third.status_code == 501, "the bucket should have reset once its window elapsed"


# ---------------------------------------------------------------------------
# 4. different users don't share a rate-limit bucket
# ---------------------------------------------------------------------------


def test_different_users_have_independent_limits(rl_app, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    user_a_first = rl_app.get("/api/v1/profiles/me", headers=_auth_headers("user-a"))
    user_b_first = rl_app.get("/api/v1/profiles/me", headers=_auth_headers("user-b"))
    user_a_second = rl_app.get("/api/v1/profiles/me", headers=_auth_headers("user-a"))

    assert user_a_first.status_code == 501
    assert user_b_first.status_code == 501, "a different user's first request must not be consumed"
    assert user_a_second.status_code == 429, "user-a's second request should still be denied"


# ---------------------------------------------------------------------------
# 5 & 6. different IPs don't share a bucket; anonymous requests are
# rate-limited by IP, independent of (and prior to) authentication
# ---------------------------------------------------------------------------


def test_different_ips_have_independent_limits_when_anonymous(rl_app, monkeypatch):
    # TRUSTED_PROXY_HOPS=0 (the default) makes every TestClient request
    # look like the same peer, so a trusted single-hop proxy is simulated
    # here purely to give two distinct, attributable "client" IPs to test
    # with — see app/core/client_ip.py.
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    ip_a_headers = {"X-Forwarded-For": "203.0.113.10"}
    ip_b_headers = {"X-Forwarded-For": "203.0.113.20"}

    # No Authorization header anywhere in this test: these are genuinely
    # anonymous requests. Rate limiting runs before the route's own
    # CurrentUser check (see app/api/deps.py::rate_limit's docstring), so an
    # anonymous request under its IP limit reaches the auth check and is
    # correctly rejected as unauthorized — rate limiting never substitutes
    # for authentication/authorization (REQUIREMENT #14).
    ip_a_first = rl_app.get("/api/v1/profiles/me", headers=ip_a_headers)
    ip_b_first = rl_app.get("/api/v1/profiles/me", headers=ip_b_headers)
    ip_a_second = rl_app.get("/api/v1/profiles/me", headers=ip_a_headers)

    assert ip_a_first.status_code == 401
    assert ip_a_first.json()["code"] == "unauthorized"
    assert ip_b_first.status_code == 401, "a different IP's first request must not be pre-consumed"
    assert ip_a_second.status_code == 429, "IP A's second request should be rate limited, not 401"
    assert ip_a_second.json()["code"] == "rate_limited"


# ---------------------------------------------------------------------------
# 8. concurrent requests cannot bypass the limit via a race condition
# ---------------------------------------------------------------------------


def test_concurrent_requests_through_real_routes_cannot_exceed_the_limit(rl_app, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 5)
    headers = _auth_headers("race-user")

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [
            pool.submit(rl_app.get, "/api/v1/profiles/me", headers=headers) for _ in range(30)
        ]
        responses = [f.result() for f in futures]

    allowed = [r for r in responses if r.status_code == 501]
    denied = [r for r in responses if r.status_code == 429]

    assert len(allowed) == 5, "exactly the configured limit must get through under concurrency"
    assert len(denied) == 25
    assert len(allowed) + len(denied) == 30


# ---------------------------------------------------------------------------
# 9. Redis failure behaves per the documented fail-open/fail-closed policy
# ---------------------------------------------------------------------------


def test_redis_failure_fails_open_for_default_tier(rl_app, monkeypatch):
    class BrokenRedis:
        async def eval(self, *args, **kwargs):
            import redis.exceptions

            raise redis.exceptions.ConnectionError("simulated Redis outage")

    monkeypatch.setattr(deps_module, "get_redis", lambda: BrokenRedis())
    assert settings.RATE_LIMIT_FAIL_OPEN_DEFAULT is True  # the tier under test

    response = rl_app.get("/api/v1/profiles/me", headers=_auth_headers())

    # AUTH_READ fails OPEN: the request still reaches the handler (501),
    # not a 503 — an unrelated Redis outage must not take ordinary reads down.
    assert response.status_code == 501


def test_redis_failure_fails_closed_for_ai_tier(rl_app, monkeypatch, fake_recommendation_service):
    class BrokenRedis:
        async def eval(self, *args, **kwargs):
            import redis.exceptions

            raise redis.exceptions.ConnectionError("simulated Redis outage")

    monkeypatch.setattr(deps_module, "get_redis", lambda: BrokenRedis())
    assert settings.RATE_LIMIT_FAIL_OPEN_AI is False  # the tier under test

    response = rl_app.get("/api/v1/recommendations/for-you", headers=_auth_headers())

    # AI_EXPENSIVE fails CLOSED: unmetered LLM/embedding spend must not be
    # possible just because Redis is briefly unavailable.
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"
    assert fake_recommendation_service.calls == [], "the handler must never run when failing closed"


# ---------------------------------------------------------------------------
# 12. the health endpoint is never rate limited
# ---------------------------------------------------------------------------


def test_health_endpoint_is_never_rate_limited(rl_app, monkeypatch):
    # An absurdly tight limit on an unrelated category proves nothing by
    # itself; what matters is that /health carries no rate_limit dependency
    # at all (see app/api/v1/routes/health.py) — so it's unaffected
    # regardless of how many times, or how fast, it's hit.
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    for _ in range(50):
        response = rl_app.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers


# ---------------------------------------------------------------------------
# 13. AI/expensive endpoints carry a stricter limit than ordinary reads
# ---------------------------------------------------------------------------


def test_ai_endpoints_are_rate_limited_more_strictly_than_ordinary_reads(
    rl_app, monkeypatch, fake_recommendation_service
):
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_PER_MINUTE", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 100)
    headers = _auth_headers("strict-ai-user")

    ai_results = [
        rl_app.get("/api/v1/recommendations/for-you", headers=headers).status_code for _ in range(3)
    ]
    # First two within the tight AI limit succeed, the third is denied.
    assert ai_results == [200, 200, 429]

    # The same volume of requests against the generously-limited read tier,
    # for the same user, sails through — proving the AI tier's strictness
    # is a deliberate per-category policy, not a global ceiling.
    read_results = [
        rl_app.get("/api/v1/profiles/me", headers=headers).status_code for _ in range(3)
    ]
    assert read_results == [501, 501, 501]


def test_ai_endpoint_layers_a_per_ip_limit_on_top_of_the_per_user_limit(
    rl_app, monkeypatch, fake_recommendation_service
):
    """Guards against the multi-account bypass the spec calls out explicitly:
    a per-user-only limit is worthless if an attacker just mints a new
    account (a new `sub` in a freshly-signed JWT costs nothing to forge in
    a test, same as in reality) for every request. The IP-layer cap must
    catch that even though every request here uses a *different* user id.
    """
    # user layer: generous, not the one under test.
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_PER_MINUTE", 1000)
    # ip layer: the one under test.
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_IP_PER_MINUTE", 2)

    results = [
        rl_app.get(
            "/api/v1/recommendations/for-you", headers=_auth_headers(f"sybil-user-{i}")
        ).status_code
        for i in range(3)
    ]

    assert results == [200, 200, 429], "a new user id per request must not evade the shared IP cap"
