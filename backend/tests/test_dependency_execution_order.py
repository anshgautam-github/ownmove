"""Empirically proves the FastAPI dependency execution ORDER for the four
scenarios explicitly asked about, rather than asserting it from FastAPI's
docs. Each dependency in the real chain is wrapped (not replaced — the
real function still runs, we just record when) so the recorded order is
exactly what a real request experiences:

    rate_limit() [OptionalUser -> verify_token if a token is present]
        -> RateLimiter.check_many() [the actual Redis/Lua call]
        -> (route's own) CurrentUser -> verify_token again
        -> route handler body (where authorization/ownership checks and
           any RLS-scoped Supabase calls would run)

This also settles the one thing worth flagging: verify_token() runs TWICE
per authenticated request on a route that is both rate-limited AND
authenticated — once for `rate_limit()`'s OptionalUser, once for the
route's own CurrentUser. Both independently verify the full JWT signature;
neither is a bypass of the other, but it's a real, visible cost worth
knowing about (see RATE_LIMITING.md).

Route used: GET /api/v1/profiles/me — AUTH_READ rate limit, requires
CurrentUser, scaffold raises NotImplementedYetError as the first line of
the handler body (a stand-in for "authorization/ownership checks and any
RLS-scoped DB call would happen here").
"""

import time

import fakeredis
import jwt
import pytest

import app.api.deps as deps_module
from app.core.config import settings
from app.core.exceptions import NotImplementedYetError

_TEST_JWT_SECRET = "test-secret"


def _make_token(user_id: str = "order-test-user") -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": "order-test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def traced(monkeypatch):
    """Wraps (not replaces) verify_token, RateLimiter.check_many, and the
    handler-body marker (NotImplementedYetError) to record call order,
    then yields (client, order_list).
    """
    from fastapi.testclient import TestClient

    from app.core.rate_limiter import RateLimiter
    from app.main import create_app

    order: list[str] = []

    real_verify_token = deps_module.verify_token

    def traced_verify_token(token):
        order.append("verify_token: START")
        try:
            result = real_verify_token(token)
            order.append("verify_token: OK (signature/exp/aud/sub all checked)")
            return result
        except Exception as exc:
            order.append(f"verify_token: REJECTED ({type(exc).__name__})")
            raise

    monkeypatch.setattr(deps_module, "verify_token", traced_verify_token)

    real_check_many = RateLimiter.check_many

    async def traced_check_many(self, rules):
        order.append("RateLimiter.check_many: START (Redis Lua script)")
        decision = await real_check_many(self, rules)
        order.append(f"RateLimiter.check_many: DONE (allowed={decision.allowed})")
        return decision

    monkeypatch.setattr(RateLimiter, "check_many", traced_check_many)

    real_not_implemented_init = NotImplementedYetError.__init__

    def traced_init(self, *a, **kw):
        order.append("ROUTE HANDLER BODY reached (authorization/RLS-scoped DB calls live here)")
        real_not_implemented_init(self, *a, **kw)

    monkeypatch.setattr(NotImplementedYetError, "__init__", traced_init)

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(deps_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_READ_PER_MINUTE", 1)

    with TestClient(create_app()) as client:
        yield client, order


def _print_order(title: str, order: list[str]) -> None:
    print(f"\n=== {title} ===")
    for i, event in enumerate(order, 1):
        print(f"  {i}. {event}")


# ---------------------------------------------------------------------------
# 1. authenticated request, under the limit
# ---------------------------------------------------------------------------


def test_order_authenticated_request(traced):
    client, order = traced

    response = client.get(
        "/api/v1/profiles/me", headers={"Authorization": f"Bearer {_make_token()}"}
    )
    _print_order("1. Authenticated request, under limit", order)

    assert response.status_code == 501  # reached the handler
    assert order == [
        "verify_token: START",
        "verify_token: OK (signature/exp/aud/sub all checked)",
        "RateLimiter.check_many: START (Redis Lua script)",
        "RateLimiter.check_many: DONE (allowed=True)",
        "verify_token: START",
        "verify_token: OK (signature/exp/aud/sub all checked)",
        "ROUTE HANDLER BODY reached (authorization/RLS-scoped DB calls live here)",
    ]
    # verify_token (full JWT signature/exp/aud/sub verification) completes
    # in full — twice, independently — strictly BEFORE the rate limit
    # decision is used to gate anything and strictly BEFORE the handler
    # body (where authorization/RLS-scoped calls happen) ever runs.
    # Rate limiting never runs "instead of" or "before" authentication for
    # an authenticated caller — it runs alongside, gated by its own
    # independent JWT verification.


# ---------------------------------------------------------------------------
# 2. unauthenticated request, under the (IP) limit
# ---------------------------------------------------------------------------


def test_order_unauthenticated_request(traced):
    client, order = traced

    response = client.get("/api/v1/profiles/me")  # no Authorization header
    _print_order("2. Unauthenticated request, under IP limit", order)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    # verify_token is never called at all: with no bearer token, both
    # get_optional_user (for rate_limit) and get_current_user (for the
    # route) short-circuit before ever reaching verify_token. The rate
    # limiter still runs (keyed by IP) and allows the request through, and
    # the handler body is NEVER reached — proving the rate limiter cannot
    # let an unauthenticated caller past the auth check.
    assert order == [
        "RateLimiter.check_many: START (Redis Lua script)",
        "RateLimiter.check_many: DONE (allowed=True)",
    ]


# ---------------------------------------------------------------------------
# 3. authenticated request that exceeds the rate limit
# ---------------------------------------------------------------------------


def test_order_authenticated_request_over_limit(traced):
    client, order = traced
    headers = {"Authorization": f"Bearer {_make_token()}"}

    client.get("/api/v1/profiles/me", headers=headers)  # consumes the only slot
    order.clear()

    response = client.get("/api/v1/profiles/me", headers=headers)
    _print_order("3. Authenticated request, OVER limit", order)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    # verify_token still runs to completion FIRST (the caller's identity is
    # fully verified and used as the rate-limit key) — but the request is
    # denied at the rate-limit layer and the route's OWN CurrentUser
    # dependency, and therefore the handler body and any
    # authorization/RLS-scoped DB call, is NEVER reached. Rate limiting
    # denies the request entirely; it never proceeds far enough to touch
    # authorization or data access.
    assert order == [
        "verify_token: START",
        "verify_token: OK (signature/exp/aud/sub all checked)",
        "RateLimiter.check_many: START (Redis Lua script)",
        "RateLimiter.check_many: DONE (allowed=False)",
    ]
    assert "ROUTE HANDLER BODY reached (authorization/RLS-scoped DB calls live here)" not in order


# ---------------------------------------------------------------------------
# 4. unauthenticated request that exceeds the IP limit
# ---------------------------------------------------------------------------


def test_order_unauthenticated_request_over_ip_limit(traced):
    client, order = traced

    client.get("/api/v1/profiles/me")  # consumes the only IP slot, no token
    order.clear()

    response = client.get("/api/v1/profiles/me")
    _print_order("4. Unauthenticated request, OVER IP limit", order)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    # No token was ever presented, so verify_token never runs at all in
    # either request — the caller is denied purely on IP-bucket state
    # before authentication is ever attempted. This is the one case where
    # a request is rejected without any JWT check running (as expected: it
    # never had one to check) — and it is REJECTED, not let through data
    # access or any authorization path. The handler body is never reached.
    assert order == [
        "RateLimiter.check_many: START (Redis Lua script)",
        "RateLimiter.check_many: DONE (allowed=False)",
    ]
    assert "verify_token" not in " ".join(order)
    assert "ROUTE HANDLER BODY reached (authorization/RLS-scoped DB calls live here)" not in order
