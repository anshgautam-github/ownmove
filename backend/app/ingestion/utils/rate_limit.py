"""Rate limiting abstraction.

A `Protocol` so tests (and a source with genuinely no limit) can use a
no-op limiter without the pipeline caring which one it got, plus one real
asyncio token-bucket implementation for production use.
"""

import asyncio
import time
from typing import Protocol, runtime_checkable

from app.ingestion.models.config import RateLimitConfig


@runtime_checkable
class RateLimiter(Protocol):
    async def acquire(self) -> None:
        """Block (if necessary) until it is OK to make one more request."""
        ...


class NullRateLimiter:
    """No-op limiter — local dev, tests, or a source with no meaningful
    rate limit of its own."""

    async def acquire(self) -> None:
        return None


class TokenBucketRateLimiter:
    """`requests_per_second` tokens refill continuously, up to `burst`
    capacity; `acquire()` waits until a token is available.

    The pipeline shares ONE instance across every concurrent `extract()`
    call for a given agent (see `AgentContext`), so bursts are bounded
    across the whole run, not just per-call. Safe for concurrent callers via
    an internal `asyncio.Lock`.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        config = config or RateLimitConfig()
        self._rate = config.requests_per_second
        self._capacity = float(config.burst)
        self._tokens = self._capacity
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated_at
                self._updated_at = now
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)

                if self._tokens >= 1:
                    self._tokens -= 1
                    return

                wait_seconds = (1 - self._tokens) / self._rate

            await asyncio.sleep(wait_seconds)


def build_rate_limiter(config: RateLimitConfig | None) -> RateLimiter:
    """`config=None` opts an agent out of rate limiting entirely (rare —
    most sources should set a `RateLimitConfig`); anything else gets a real
    token bucket."""
    if config is None:
        return NullRateLimiter()
    return TokenBucketRateLimiter(config)
