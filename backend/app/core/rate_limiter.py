"""Redis-backed, atomic, distributed rate limiting.

Algorithm: fixed window counter, one Redis key per (identity, endpoint
category, window). Chosen deliberately over the alternatives:

* Sliding window log (a Redis sorted set per key, ZADD+ZREMRANGEBYSCORE+
  ZCARD per request) is more precise at the window boundary but costs
  O(log n) memory/CPU per request and a growing sorted set per identity —
  unnecessary precision for abuse control (as opposed to, say, billing) on
  an app this size.
* Token bucket is a better fit when you need to model a steady refill rate
  *and* a distinct burst allowance as two separate numbers. Every limit in
  this app is expressed as "N requests per window" already (see
  app/core/config.py's RATE_LIMIT_* settings) — a fixed window gives that
  directly with one counter, no extra bucket-state bookkeeping.

Fixed window's known trade-off — a client can send up to ~2x the limit
across a window boundary (N requests at the end of window 1, N more at the
start of window 2) — is an accepted trade-off for abuse control here: it
still bounds sustained throughput and cost to the configured rate, it's
trivial to reason about and monitor, and it's a single INCR-shaped
operation instead of a sorted set per identity.

Atomicity: incrementing a counter and setting its expiry are NOT one
operation in plain `INCR` + `EXPIRE` — a process can crash (or, under
concurrent requests, race) between the two, leaving a key with no TTL that
then counts forever instead of resetting. This module runs both inside a
single Lua script, which Redis executes atomically (no other command can
interleave), so the increment and the expiry decision always happen
together. The same script also lets multiple *different* keys (e.g. an
IP-layer bucket and a user-layer bucket checked together for a layered
limit) be incremented in one atomic round trip, so a race between two
concurrent requests can never increment one key but not the other.
"""

import logging
import math
import time
from dataclasses import dataclass

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# KEYS[1..N]  = the counter keys to increment, one per rate-limit rule
# ARGV[1..N]  = the corresponding window length in milliseconds
#
# For each key: INCR it; if this is the first hit in a fresh window (count
# == 1), set its expiry. Also self-heals a key that somehow exists with no
# TTL (should never happen given the above, but a corrupted/pre-existing
# key must not be allowed to count forever) by re-arming its expiry rather
# than trusting it's already correct. Returns a flat
# [count_1, ttl_ms_1, count_2, ttl_ms_2, ...] array — the limit itself is
# never passed into Lua; comparing count to limit is left to Python so the
# script stays generic and easy to unit-test independent of any policy.
_INCR_WITH_TTL_SCRIPT = """
local out = {}
for i = 1, #KEYS do
    local key = KEYS[i]
    local window_ms = tonumber(ARGV[i])
    local count = redis.call('INCR', key)
    local ttl = redis.call('PTTL', key)
    if count == 1 or ttl < 0 then
        redis.call('PEXPIRE', key, window_ms)
        ttl = window_ms
    end
    out[#out + 1] = count
    out[#out + 1] = ttl
end
return out
"""


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    """One bucket to check: a Redis key, its limit, and its window."""

    key: str
    limit: int
    window_seconds: int
    # Human-readable, used only in logs/observability — e.g. "ai:user",
    # "ai:ip" — so a violation log line says *which* layer tripped without
    # exposing the raw Redis key (which embeds the caller's identity).
    label: str


@dataclass(frozen=True, slots=True)
class BucketState:
    rule: RateLimitRule
    count: int
    ttl_ms: int

    @property
    def exceeded(self) -> bool:
        return self.count > self.rule.limit

    @property
    def remaining(self) -> int:
        return max(0, self.rule.limit - self.count)

    @property
    def reset_seconds(self) -> int:
        return max(1, math.ceil(self.ttl_ms / 1000))


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    buckets: tuple[BucketState, ...]
    # None when Redis itself failed rather than a limit being exceeded —
    # callers use this to distinguish "abuse" from "infra failure" in logs
    # and in the fail-open/fail-closed decision.
    redis_error: Exception | None = None

    @property
    def most_restrictive(self) -> BucketState | None:
        """The bucket to report in X-RateLimit-* headers / Retry-After:
        whichever is closest to (or over) its own limit. Stable even when
        multiple layered buckets are exceeded at once (e.g. both the
        per-user and per-IP AI limits) — always reports the tightest one.
        """
        if not self.buckets:
            return None
        return min(self.buckets, key=lambda b: b.remaining)

    @property
    def retry_after_seconds(self) -> int | None:
        exceeded = [b for b in self.buckets if b.exceeded]
        if not exceeded:
            return None
        # Conservative: the caller must wait for the LONGEST-lived exceeded
        # bucket to clear, not the shortest.
        return max(b.reset_seconds for b in exceeded)


class RateLimiter:
    """Thin wrapper around the Lua script above plus policy application.

    Deliberately holds no state of its own beyond the Redis client — every
    call is self-contained, which is what makes it safe to share across
    concurrent requests and (via the same Redis instance) across multiple
    FastAPI worker processes/machines.
    """

    def __init__(self, redis_client: "redis.Redis | None"):
        self._redis = redis_client

    async def check_many(self, rules: list[RateLimitRule]) -> RateLimitDecision:
        """Atomically increments every rule's counter and reports whether
        ANY of them is now over its limit. All counters are incremented
        together in one round trip regardless of outcome — a request that
        gets denied by one layer still consumes its slot in the others,
        which is what makes retrying-immediately not a way to dodge the
        other layer's count.
        """
        if self._redis is None:
            return RateLimitDecision(
                allowed=True,
                buckets=(),
                redis_error=RuntimeError("Redis is not configured (REDIS_URL unset)"),
            )

        keys = [rule.key for rule in rules]
        args = [rule.window_seconds * 1000 for rule in rules]

        try:
            start = time.monotonic()
            raw = await self._redis.eval(_INCR_WITH_TTL_SCRIPT, len(keys), *keys, *args)
            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > 250:
                logger.warning("Rate limiter Redis round trip took %.0fms (slow)", elapsed_ms)
        except RedisError as exc:
            logger.error("Rate limiter Redis call failed: %s", exc, exc_info=True)
            return RateLimitDecision(allowed=True, buckets=(), redis_error=exc)

        buckets = tuple(
            BucketState(rule=rule, count=int(raw[2 * i]), ttl_ms=int(raw[2 * i + 1]))
            for i, rule in enumerate(rules)
        )
        allowed = not any(b.exceeded for b in buckets)
        return RateLimitDecision(allowed=allowed, buckets=buckets)
