"""Rate limiting is NOT implemented as middleware in this application.

This file previously held a no-op `RateLimitMiddleware` placeholder (never
actually registered in `app/main.py`). The real implementation lives
elsewhere, as a per-route FastAPI dependency rather than global middleware,
because different routes in this API have genuinely different cost
profiles (a 501 stub vs. an LLM call) — the applicable limit is a property
of the specific route, not one blanket policy for the whole app:

* `app/core/rate_limiter.py`      — the generic, atomic, Redis-backed
                                     limiter (fixed-window counters via a
                                     Lua script).
* `app/core/rate_limit_policy.py` — this app's actual categories and
                                     configured limits.
* `app/core/client_ip.py`         — trusted-proxy-aware client IP
                                     resolution (never blindly trusts
                                     X-Forwarded-For).
* `app/api/deps.py`'s `rate_limit(category)` — the dependency every
                                     protected route attaches via
                                     `dependencies=[rate_limit(...)]`.

See backend/RATE_LIMITING.md for the full design writeup, configured
limits, and how to test it locally.
"""
