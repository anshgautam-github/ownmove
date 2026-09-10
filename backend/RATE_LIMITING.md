# Rate limiting

This document explains the rate limiting added to the FastAPI backend: what
it protects, what it deliberately does *not* protect (because something
else already does), how it's configured, and how it behaves in production
and under Redis failure.

## Architectural rule this respects

**Supabase Auth remains the sole authentication provider.** Nothing in this
document introduces custom authentication, password hashing, JWT
generation, refresh tokens, or session management. Rate limiting sits
*after* authentication in the request pipeline and is a distinct concern
from both authentication and authorization:

```
Supabase Auth (signup/login/OAuth/session) -> Supabase-issued JWT
  -> FastAPI verifies the JWT (app/core/security.py, unchanged)
  -> CurrentUser / OptionalUser (app/api/deps.py, unchanged)
  -> rate limiting (app/api/deps.py::rate_limit(), NEW)
  -> route handler's own authorization / IDOR / RLS checks (unchanged)
```

Rate limiting is keyed off the identity JWT verification already
established — it never re-implements or duplicates auth. See
`AUTH_SECURITY_AUDIT.md` for the authentication/authorization audit this
work builds on top of, unchanged.

## What's protected by what

| Surface | Protected by | Notes |
|---|---|---|
| Signup, login, Google OAuth, password recovery | **Supabase Auth's own abuse protection** (Supabase dashboard: Auth → Rate Limits) | Not this codebase's concern. There is no `/login` or `/signup` route in this FastAPI app — the frontend talks to Supabase Auth directly (`frontend/src/lib/supabaseClient`). Building a FastAPI login limiter here would protect an endpoint that doesn't exist. |
| Every FastAPI route under `/api/v1/*` | **This rate limiter** (`app/core/rate_limiter.py` + `app/core/rate_limit_policy.py`, applied per-route via `app/api/deps.py::rate_limit()`) | Distributed, Redis-backed, atomic. See below. |
| Row-level data access (who can read/write which `profiles`/`opportunities`/etc. row) | **PostgreSQL Row Level Security**, unchanged | Rate limiting bounds *how often*; RLS (and the app-layer `.eq(id).eq(profile_id)` filtering already in place — see `AUTH_SECURITY_AUDIT.md`) bounds *what*. Rate limiting never substitutes for authorization. |
| `/api/v1/health` | **Nothing** — deliberately exempt | See "Never rate-limited" below. |

## Why Redis, and why a Lua script (atomicity)

Rate limits must be enforced correctly across multiple Uvicorn/Gunicorn
worker processes and, in production, multiple instances/containers behind
a load balancer. An in-memory counter (a plain Python dict) is invisible
across processes — each worker would enforce its own separate limit, so
the *effective* limit would be `configured_limit × worker_count`, silently
wrong. Redis is the shared state every worker and instance can see.

`INCR key` followed by a separate `EXPIRE key` is **not** atomic: a
process can be interrupted between the two calls (or two concurrent
requests can race), leaving a key that was incremented but never got a
TTL — it would then count forever instead of resetting each window. This
implementation (`app/core/rate_limiter.py`) runs the increment and the
expiry decision inside a single Lua script, which Redis executes as one
atomic unit — no other command, including a concurrent request's own
script invocation, can interleave partway through. The same script also
increments *multiple* keys (used for AI's layered user+IP check) in one
round trip, so a race between two concurrent requests can never increment
one of the two keys but not the other.

### Algorithm: fixed window, not sliding-window-log or token bucket

Every limit in this app is naturally expressed as "N requests per window"
(see the Configuration table below) — a fixed-window counter gives that
directly with a single `INCR`. The alternatives were considered and
rejected for this app specifically:

- **Sliding window log** (a Redis sorted set per identity, `ZADD` +
  `ZREMRANGEBYSCORE` + `ZCARD` per request) is more precise at the window
  boundary, at the cost of `O(log n)` work and a growing sorted set per
  identity. That precision matters for billing-grade metering; it's
  unnecessary for abuse control here.
- **Token bucket** earns its complexity when a *steady refill rate* and a
  *separate burst allowance* need to be two different numbers. Nothing in
  this app's limits needs that distinction.

Fixed window's known trade-off — a client can send up to ~2x the
configured limit across a window boundary (N requests at the very end of
window 1, N more at the very start of window 2) — is accepted here: it
still bounds sustained throughput and cost to the configured rate, it's a
single counter per identity, and it's trivial to reason about and monitor.

## Rate limit key selection (who a limit applies to)

- **Authenticated requests** are keyed by the verified JWT's `sub` (the
  Supabase user id) — never by anything the client sends unauthenticated
  (no client-supplied user id is ever trusted for this or anything else in
  this API).
- **Anonymous requests** are keyed by client IP.
- Rate limiting runs on `OptionalUser`, not `CurrentUser` — it identifies
  the caller *if* a valid token is present but never itself rejects an
  unauthenticated request. That means an anonymous caller is still
  correctly IP-rate-limited even on a route that will go on to reject them
  with 401 for lacking a token — rate limiting and authentication remain
  two independent checks, run in the order shown above, and a request that
  fails one can never look like it passed the other.

### Client IP resolution and trusted-proxy handling

`X-Forwarded-For` is attacker-controlled input whenever a client can reach
this service directly — anyone can send `X-Forwarded-For: 1.2.3.4` on
every request and, if that header were trusted blindly, get a fresh
rate-limit bucket for free on every single request.

`app/core/client_ip.py` only trusts `X-Forwarded-For` for as many hops as
`TRUSTED_PROXY_HOPS` (env var, default **0**) says are real, trusted
reverse proxies in front of this service:

- `TRUSTED_PROXY_HOPS=0` (the default): `X-Forwarded-For` is ignored
  entirely; the client IP is always `request.client.host`, the direct TCP
  peer, which cannot be spoofed. Correct when FastAPI is reachable
  directly, or until the real deployment topology is confirmed.
- `TRUSTED_PROXY_HOPS=1`: exactly one trusted hop (e.g. a single load
  balancer) appends the real client IP; that appended value — the
  *rightmost* entry in the header, not the client-supplied leftmost one —
  is trusted.
- `TRUSTED_PROXY_HOPS=2`: e.g. CDN + load balancer, and so on.

**Set this to the actual number of trusted proxy hops in front of the
deployed service — never guess in the trusting direction.** Setting it too
high (or trusting a header your load balancer doesn't actually control)
lets a client forge its own `X-Forwarded-For` and pick a fresh rate-limit
bucket on every request, defeating the limiter entirely.

## Rate limit categories and configured limits

Four categories (`app/core/rate_limit_policy.py`), chosen by inspecting
the actual routes rather than picked arbitrarily:

| Category | Applies to (actual routes) | Keyed by | Default limit | Env var(s) |
|---|---|---|---|---|
| `AUTH_READ` | Authenticated GET/read endpoints — `GET /profiles/me`, `GET /opportunities`, `GET /recommendations` list-style reads, `GET .../me/analysis`, roadmap/simulation/coach history reads, etc. | user (IP if somehow anonymous) | 120 / minute | `RATE_LIMIT_AUTH_READ_PER_MINUTE` |
| `AUTH_WRITE` | Authenticated non-AI writes — `PATCH /profiles/me`, `DELETE` a saved simulation/coach conversation, etc. | user (IP if anonymous) | 30 / minute | `RATE_LIMIT_AUTH_WRITE_PER_MINUTE` |
| `AI_EXPENSIVE` | Every LLM- or embedding-backed route: Profile Analysis create, Career Roadmap generate, Career Simulation create/compare, AI Coach create-conversation/create-message, and all of Recommendations (`for-you`, `match`, `refresh` — CPU-bound hybrid retrieval + a bounded lazy embedding backfill on every call) | **layered**: user AND IP, both checked together | 10/min & 100/day per user; 30/min & 300/day per IP | `RATE_LIMIT_AI_PER_MINUTE`, `RATE_LIMIT_AI_PER_DAY`, `RATE_LIMIT_AI_IP_PER_MINUTE`, `RATE_LIMIT_AI_IP_PER_DAY` |
| `PUBLIC` | Reserved for future anonymous routes — nothing in this API currently allows anonymous access (every real route requires `CurrentUser`) | IP | 60 / minute | `RATE_LIMIT_PUBLIC_PER_MINUTE` |

All numbers above are defaults defined in `app/core/config.py` and are
fully overridable per environment via env vars — nothing is hardcoded at
the call site; every route only ever references a `RateLimitCategory`, not
a number.

### Why AI_EXPENSIVE is layered (user *and* IP)

A per-user-only limit is trivially bypassed by creating additional
accounts (`sub` is free to obtain — signup itself isn't gated by this
codebase, see above) and spreading requests across them. The IP layer
catches that: it's deliberately looser than the per-user cap (to tolerate
legitimate shared IPs — offices, campus/mobile NAT), but it still bounds
"one attacker/script driving many accounts from one IP," which a
per-user-only limit cannot. A request is denied if **either** layer is
exceeded; both layers' counters still increment together even when the
request is ultimately denied by only one of them (see `check_many` in
`app/core/rate_limiter.py`), so retrying immediately doesn't let a caller
dodge the other layer's count.

### Never rate-limited

`GET /api/v1/health` carries no rate-limit dependency at all — not even
`PUBLIC` (see `app/api/v1/routes/health.py`). Deployment platforms and
load balancers poll this on a fixed, often sub-minute interval to decide
whether an instance stays in rotation; rate-limiting or gating it risks a
healthy instance being pulled from rotation for looking down.

## 429 responses

A denied request raises the existing `RateLimitError` (already present in
`app/core/exceptions.py` before this work, previously unused) through the
app's single existing error-handling middleware
(`app/middleware/error_handler.py`), so the body matches every other error
in this API:

```json
{"code": "rate_limited", "detail": "Too many requests. Please slow down.", "request_id": "…"}
```

with these response headers:

- `Retry-After` — seconds until the caller should retry (the longest-lived
  of any exceeded bucket, so a layered AI denial reports whichever layer
  takes longer to clear).
- `X-RateLimit-Limit`, `X-RateLimit-Remaining` (`0` on a 429),
  `X-RateLimit-Reset` — the bucket closest to (or over) its limit.

The same `X-RateLimit-*` headers are also attached to an **allowed**
request's *successful (2xx)* response, so a well-behaved client can see
how close it is before it ever gets a 429. One caveat worth knowing:
FastAPI only merges a dependency's injected `Response` headers into the
final response on that plain success path. If the route handler itself
subsequently raises some unrelated `AppError` (a 404, a scaffolded 501,
etc.) *after* having been allowed through the rate limiter, the
exception-handler middleware builds a fresh `JSONResponse` that doesn't
inherit those headers — so `X-RateLimit-*` reliably appears on an allowed
request's 2xx response and on every 429, but not on an allowed request
that then errors out for an unrelated reason. This doesn't affect the 429
case itself (`RateLimitError`'s headers are attached directly to the
raised exception, not via the injected `Response`).

## Redis failure: fail-open vs. fail-closed, explicitly

`REDIS_URL` is the same setting `ENABLE_BACKGROUND_WORKERS` already used
(previously unused by any code — see `app/core/redis_client.py`). If it's
unset, or Redis is unreachable/errors at request time, behavior is an
explicit, configured, per-category policy — never a silently swallowed
exception and never a hang:

- **`RATE_LIMIT_FAIL_OPEN_DEFAULT` (default `True`)** — applies to
  `AUTH_READ`, `AUTH_WRITE`, and `PUBLIC`. If Redis is down, these
  requests are let through (logged at `ERROR`, not silently). Rationale:
  an unrelated cache-layer outage should not take ordinary reads/writes
  down; these aren't a cost-exposure risk.
- **`RATE_LIMIT_FAIL_OPEN_AI` (default `False` — fails *closed*)** —
  applies to `AI_EXPENSIVE` specifically. If Redis is down, these requests
  are **rejected with `503 service_unavailable`** rather than let through.
  Rationale: without Redis there is no way to bound per-user/per-IP LLM or
  embedding spend, so the safer failure mode is to refuse rather than risk
  unmetered AI-provider cost until Redis recovers.

Every Redis failure is logged at `ERROR` with the category and path, so an
operator can immediately see whether requests are currently failing open
or closed and why.

## Middleware vs. dependency: why a dependency

Rate limiting is implemented as a **FastAPI dependency**
(`app/api/deps.py::rate_limit(category)`), attached per-route via
`dependencies=[rate_limit(RateLimitCategory.X)]` — not as global ASGI
middleware. (`app/middleware/rate_limit.py` is kept as a documentation
pointer to this decision and to where the real implementation lives, since
a `middleware/` module named exactly that is where a reader would
naturally look first.)

Reasoning: this API's routes have genuinely different cost profiles — a
scaffolded 501 stub costs nothing, an LLM call costs real money and
latency. The category (and therefore the limit) is a property of *the
route*, decided at the route, not a single blanket policy layered on top
of every request regardless of what it does. A dependency also composes
naturally with the existing auth dependency chain (`CurrentUser` /
`OptionalUser`), runs inside the same request-scoped dependency-injection
system already used throughout this codebase, and keeps the health
endpoint's exemption a simple omission (no dependency declared) rather
than an exclusion list some middleware has to consult.

## Configuration reference

All of the following are `pydantic-settings` fields on `Settings` in
`app/core/config.py` — set via environment variables (or `.env` locally),
same as every other setting in this app. Nothing is hardcoded at the call
site.

| Env var | Default | Meaning |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Master on/off switch. `false` disables all rate limiting (used by the test suite's shared fixture — see Testing below). |
| `TRUSTED_PROXY_HOPS` | `0` | Number of trusted reverse-proxy hops that append to `X-Forwarded-For`. See "Client IP resolution" above. |
| `RATE_LIMIT_FAIL_OPEN_DEFAULT` | `true` | Fail-open behavior for `AUTH_READ` / `AUTH_WRITE` / `PUBLIC` when Redis is unavailable. |
| `RATE_LIMIT_FAIL_OPEN_AI` | `false` | Fail-open (`true`) vs. fail-closed (`false`, the default) for `AI_EXPENSIVE` when Redis is unavailable. |
| `RATE_LIMIT_AUTH_READ_PER_MINUTE` | `120` | `AUTH_READ` per-user limit. |
| `RATE_LIMIT_AUTH_WRITE_PER_MINUTE` | `30` | `AUTH_WRITE` per-user limit. |
| `RATE_LIMIT_AI_PER_MINUTE` | `10` | `AI_EXPENSIVE` per-user, per-minute limit. |
| `RATE_LIMIT_AI_PER_DAY` | `100` | `AI_EXPENSIVE` per-user, per-day limit. |
| `RATE_LIMIT_AI_IP_PER_MINUTE` | `30` | `AI_EXPENSIVE` per-IP, per-minute limit (layered on top of the per-user one). |
| `RATE_LIMIT_AI_IP_PER_DAY` | `300` | `AI_EXPENSIVE` per-IP, per-day limit. |
| `RATE_LIMIT_PUBLIC_PER_MINUTE` | `60` | `PUBLIC` per-IP limit (reserved; nothing currently uses this category). |
| `REDIS_URL` | *(empty)* | Shared with `ENABLE_BACKGROUND_WORKERS`. Empty means Redis is "unconfigured," handled identically to Redis being down (per the fail-open/closed policy above). |

## Testing locally

Two new test files exercise this, using the project's existing pytest
conventions (`TestClient(create_app())`, real signed JWTs matching
`conftest.py`'s `SUPABASE_JWT_SECRET`, `monkeypatch` to swap module-level
references — the same pattern `tests/test_recommendations_api.py` already
uses):

- **`tests/test_rate_limiter.py`** — the algorithm itself, directly
  against `fakeredis` (including a real `EVAL` of the actual Lua script):
  requests under the limit succeed, the over-limit request is denied, the
  counter resets after its window, different identities/layers are
  independent, keys always carry a TTL (including self-healing a key found
  with no TTL), Redis failures are reported rather than swallowed, and —
  the concurrency/atomicity guarantee specifically — firing many
  concurrent requests via `asyncio.gather` against a limit of N allows
  *exactly* N through, never more.
- **`tests/test_rate_limit_api.py`** — the same behavior through the real
  FastAPI request path (`TestClient`, real routes, real JWT verification,
  real error-handling middleware): below-limit success, 429 on the
  over-limit request in the standard error envelope, `Retry-After`/
  `X-RateLimit-*` headers, window reset, per-user isolation, per-IP
  isolation for anonymous callers (via a simulated trusted proxy hop),
  rate limiting running independently of and before authentication,
  concurrent requests via a real `ThreadPoolExecutor` unable to exceed the
  limit, both the fail-open and fail-closed Redis-failure policies,
  `/health` staying completely unaffected even under an absurdly tight
  unrelated limit, and the AI tier's stricter limit — including its
  per-IP layer specifically defeating a "new account per request"
  multi-account bypass attempt.

Both files use `fakeredis` (an in-memory, no-network Redis stand-in) with
`lupa` (a Lua interpreter) so the actual `EVAL` script runs for real in
tests, not a Python re-implementation of it — install both from
`requirements-dev.txt`:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run just the rate-limit tests:

```bash
ENVIRONMENT=local SUPABASE_JWT_SECRET=test-secret \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python3 -m pytest -q tests/test_rate_limiter.py tests/test_rate_limit_api.py
```

Run the full suite (rate limiting is **off** by default here —
`conftest.py` sets `RATE_LIMIT_ENABLED=false` for the shared `client`
fixture so every pre-existing test is unaffected; the two files above
explicitly re-enable it per-test):

```bash
ENVIRONMENT=local SUPABASE_JWT_SECRET=test-secret \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python3 -m pytest -q
```

`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` avoids a multi-minute hang: the
app's startup hook warms up a local sentence-transformers embedding model,
which otherwise retries against Hugging Face Hub on every single
`TestClient(create_app())` instantiation in an environment with no
outbound network access. Unrelated to rate limiting specifically, but
necessary for the suite to run at all in such an environment.

## Production behavior summary

- `REDIS_URL` must point at a real Redis instance reachable from every
  Uvicorn/Gunicorn worker and every instance — this is what makes the
  limiter distributed and correct across all of them, not just within one
  process.
- Set `TRUSTED_PROXY_HOPS` to match the actual number of trusted reverse
  proxies in front of the deployed service (0 if none). Getting this wrong
  in the trusting direction is a rate-limit bypass.
- A brief Redis blip fails `AUTH_READ`/`AUTH_WRITE`/`PUBLIC` open (traffic
  keeps flowing, logged at `ERROR`) and fails `AI_EXPENSIVE` closed (503s,
  logged at `ERROR`) until Redis recovers — by design, not by omission.
- `/health` is always served, rate limiting or no.
- Every limit is tunable via environment variables without a code change
  or a redeploy of route code — only the `Settings` values need to change.
