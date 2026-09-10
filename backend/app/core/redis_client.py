"""Shared async Redis connection.

One client for the whole process, reused everywhere Redis is needed —
currently just `app/core/rate_limiter.py`, but this is deliberately not
named `rate_limit_redis.py` so a future consumer (the background job queue
in `app/workers/queue.py`, which is currently an in-memory stand-in; a
cache) reuses this same connection instead of opening a second one.

Mirrors the shape of `app/db/supabase.py`'s two-client pattern: a small
`lru_cache`d factory, config validated once, `None` (not an exception) when
Redis isn't configured at all so callers can implement their own
fail-open/fail-closed policy instead of the app crashing at import time.
"""

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings


@lru_cache
def get_redis() -> "redis.Redis | None":
    """The shared Redis client, or `None` if `REDIS_URL` isn't set.

    `redis.asyncio.Redis` is connection-pooled and safe to share across
    requests/coroutines internally — this does not open a new TCP
    connection per call, `from_url()` just constructs the client and its
    pool; the actual connection is made lazily on first command.

    Deliberately does NOT raise if Redis is unreachable — that only
    surfaces on first actual command (e.g. inside
    `RateLimiter.check_many()`), which is where fail-open/fail-closed policy
    is decided per rate-limit tier. A missing/bad `REDIS_URL` should not
    prevent the rest of the app from starting.
    """
    if not settings.REDIS_URL:
        return None

    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
        # Rate limiting must never become the slow part of a request; a
        # wedged Redis should fail fast so the caller's fail-open/closed
        # policy kicks in quickly rather than the request hanging.
        retry_on_timeout=False,
    )
