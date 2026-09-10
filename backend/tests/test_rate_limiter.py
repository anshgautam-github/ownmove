"""Exercises app/core/rate_limiter.py directly against a real (fake) Redis
— fakeredis's asyncio client, with Lua scripting support (`lupa`), so the
actual atomic script this module ships runs for real, not a Python
re-implementation of it. This file covers the algorithm itself; see
tests/test_rate_limit_api.py for the same behavior through a real FastAPI
request.
"""

import asyncio

import fakeredis
import pytest

from app.core.rate_limiter import RateLimitDecision, RateLimiter, RateLimitRule


@pytest.fixture
def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client


def _rule(key: str, limit: int, window: int = 60, label: str = "test") -> RateLimitRule:
    return RateLimitRule(key=key, limit=limit, window_seconds=window, label=label)


# ---------------------------------------------------------------------------
# 1. requests below the limit succeed
# ---------------------------------------------------------------------------


async def test_requests_below_limit_are_allowed(fake_redis):
    limiter = RateLimiter(fake_redis)
    rule = _rule("k1", limit=5)

    for _ in range(5):
        decision = await limiter.check_many([rule])
        assert decision.allowed is True


# ---------------------------------------------------------------------------
# 2. the request that exceeds the limit is denied
# ---------------------------------------------------------------------------


async def test_request_exceeding_limit_is_denied(fake_redis):
    limiter = RateLimiter(fake_redis)
    rule = _rule("k2", limit=3)

    results = [await limiter.check_many([rule]) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].buckets[0].count == 4
    assert results[-1].retry_after_seconds is not None
    assert results[-1].retry_after_seconds > 0


# ---------------------------------------------------------------------------
# 3. the counter resets after the configured window
# ---------------------------------------------------------------------------


async def test_counter_resets_after_window(fake_redis):
    limiter = RateLimiter(fake_redis)
    rule = _rule("k3", limit=1, window=1)  # 1-second window

    first = await limiter.check_many([rule])
    assert first.allowed is True

    second = await limiter.check_many([rule])
    assert second.allowed is False

    await asyncio.sleep(1.2)

    third = await limiter.check_many([rule])
    assert third.allowed is True, "counter should have reset once the window elapsed"


# ---------------------------------------------------------------------------
# 4 & 5. different identities (different Redis keys) do not share a bucket
# ---------------------------------------------------------------------------


async def test_different_keys_have_independent_buckets(fake_redis):
    limiter = RateLimiter(fake_redis)
    rule_a = _rule("user:aaa", limit=1)
    rule_b = _rule("user:bbb", limit=1)

    first_a = await limiter.check_many([rule_a])
    first_b = await limiter.check_many([rule_b])
    second_a = await limiter.check_many([rule_a])

    assert first_a.allowed is True
    assert first_b.allowed is True, "a different identity's first request must not be pre-consumed"
    assert second_a.allowed is False, "the first identity's second request should still be denied"


# ---------------------------------------------------------------------------
# 8. concurrent requests cannot bypass the limit via a race condition
# ---------------------------------------------------------------------------


async def test_concurrent_requests_cannot_exceed_the_limit(fake_redis):
    """The classic TOCTOU race: N coroutines all read count=0 and all decide
    "I'm allowed" before any of them writes. If check-then-increment weren't
    atomic, this would let more than `limit` requests through. Fires 50
    concurrent requests against a limit of 10 and asserts exactly 10 are
    allowed — not "at most 10", not "approximately 10".
    """
    limiter = RateLimiter(fake_redis)
    rule = _rule("race-key", limit=10)

    results = await asyncio.gather(*[limiter.check_many([rule]) for _ in range(50)])

    allowed_count = sum(1 for r in results if r.allowed)
    assert allowed_count == 10, "exactly `limit` requests must be allowed under concurrency"


# ---------------------------------------------------------------------------
# Layered (multi-key) checks — the IP+user pattern AI_EXPENSIVE uses
# ---------------------------------------------------------------------------


async def test_layered_rules_deny_if_either_bucket_is_exceeded(fake_redis):
    limiter = RateLimiter(fake_redis)
    generous_user_rule = _rule("layer:user:x", limit=100, label="user")
    strict_ip_rule = _rule("layer:ip:y", limit=1, label="ip")

    first = await limiter.check_many([generous_user_rule, strict_ip_rule])
    assert first.allowed is True

    second = await limiter.check_many([generous_user_rule, strict_ip_rule])
    assert second.allowed is False, "the IP layer alone exceeding its limit must deny the request"
    # The user-layer bucket is still reported, just not the one that denied.
    labels = {b.rule.label: b for b in second.buckets}
    assert labels["ip"].exceeded is True
    assert labels["user"].exceeded is False


async def test_layered_rules_increment_both_keys_atomically_together(fake_redis):
    """Both keys in a layered check move together in one Redis round trip —
    a concurrent request can never see one key incremented but not the
    other.
    """
    limiter = RateLimiter(fake_redis)
    rule_a = _rule("atomic:a", limit=1000, label="a")
    rule_b = _rule("atomic:b", limit=1000, label="b")

    await asyncio.gather(*[limiter.check_many([rule_a, rule_b]) for _ in range(25)])

    count_a = int(await fake_redis.get("atomic:a"))
    count_b = int(await fake_redis.get("atomic:b"))
    assert count_a == count_b == 25


# ---------------------------------------------------------------------------
# Redis keys must expire — never grow forever
# ---------------------------------------------------------------------------


async def test_key_gets_a_ttl_on_first_hit(fake_redis):
    limiter = RateLimiter(fake_redis)
    rule = _rule("ttl-key", limit=5, window=30)

    await limiter.check_many([rule])

    ttl = await fake_redis.pttl("ttl-key")
    assert 0 < ttl <= 30_000, "a fresh key must carry a TTL matching its window, not live forever"


async def test_key_missing_ttl_is_self_healed(fake_redis):
    """Defends the exact race the task description called out: INCR then a
    separate EXPIRE can leave a key with a value but no TTL if the two
    aren't atomic. Simulates that broken state directly (a key that exists
    with no expiry) and asserts the script re-arms it rather than letting
    it count forever.
    """
    await fake_redis.set("orphaned-key", 1)  # no TTL, on purpose
    assert await fake_redis.pttl("orphaned-key") == -1  # -1 == "no TTL", per Redis semantics

    limiter = RateLimiter(fake_redis)
    rule = _rule("orphaned-key", limit=5, window=30)
    await limiter.check_many([rule])

    ttl = await fake_redis.pttl("orphaned-key")
    assert ttl > 0, "a key found with no TTL must have one re-armed, not be left to grow forever"


# ---------------------------------------------------------------------------
# 9. Redis failure behaves per the documented policy — reported, not hidden
# ---------------------------------------------------------------------------


async def test_redis_unavailable_is_reported_not_silently_swallowed():
    class BrokenRedis:
        async def eval(self, *args, **kwargs):
            import redis.exceptions

            raise redis.exceptions.ConnectionError("simulated outage")

    limiter = RateLimiter(BrokenRedis())
    decision: RateLimitDecision = await limiter.check_many([_rule("x", limit=5)])

    assert decision.redis_error is not None, "a Redis failure must be visible, not swallowed"
    assert decision.buckets == (), "no bucket state is available when Redis itself failed"


async def test_unconfigured_redis_is_reported_the_same_way():
    limiter = RateLimiter(None)  # get_redis() returns None when REDIS_URL is unset
    decision = await limiter.check_many([_rule("x", limit=5)])

    assert decision.redis_error is not None
