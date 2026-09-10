"""Maps this application's actual endpoint categories onto rate-limit
rules. `app/core/rate_limiter.py` is generic (atomic Redis counters, no
opinion about what's being limited); this module is the app-specific
policy layer — the numbers and the user/IP-layering decisions were chosen
by inspecting the real routes in `app/api/v1/routes/`,
`app/profile_analysis`, `app/career_roadmap`, `app/career_simulation`, and
`app/ai_coach` (see backend/RATE_LIMITING.md for the full breakdown of
which endpoint landed in which category and why).

Four categories, deliberately not more:

* PUBLIC     — unauthenticated routes. Nothing in this API currently has
  one (every real route requires `CurrentUser`; `/health` is exempt from
  rate limiting entirely, not merely PUBLIC-classified — see
  app/api/v1/routes/health.py), but this exists so a future anonymous
  route doesn't ship with no IP-based protection by default.
* AUTH_READ  — authenticated GET/read endpoints. Cheap, DB-bound. Keyed by
  user only — every route needing this already requires CurrentUser, and a
  read-only endpoint isn't worth IP-layering.
* AUTH_WRITE — authenticated POST/PUT/PATCH/DELETE that are NOT AI/expensive
  (e.g. deleting a saved simulation). Keyed by user only, same reasoning.
* AI_EXPENSIVE — LLM calls, embedding-backed recommendations, and any
  route that spends real compute or external API cost (Profile Analysis,
  Career Roadmap, Career Simulation, AI Coach, Recommendations). Keyed by
  BOTH user and IP, layered, because a per-user-only limit is trivially
  bypassed by creating additional accounts — see RATE_LIMIT_AI_IP_* in
  app/core/config.py. Both a per-minute (burst) and a per-day (total cost
  exposure) window are enforced for the user layer.
"""

from enum import Enum

from app.core.config import settings
from app.core.rate_limiter import RateLimitRule

_ONE_MINUTE = 60
_ONE_DAY = 86_400


class RateLimitCategory(str, Enum):
    PUBLIC = "public"
    AUTH_READ = "auth_read"
    AUTH_WRITE = "auth_write"
    AI_EXPENSIVE = "ai"


def _rule(
    category: RateLimitCategory, layer: str, identity: str, limit: int, window: int
) -> RateLimitRule:
    # Window is part of the key (not just the TTL) so a per-minute and a
    # per-day rule for the same identity never share — and can't corrupt —
    # the same counter.
    key = f"rl:{category.value}:{layer}:{identity}:{window}s"
    label = f"{category.value}:{layer}"
    return RateLimitRule(key=key, limit=limit, window_seconds=window, label=label)


def build_rules(
    category: RateLimitCategory,
    *,
    user_id: str | None,
    client_ip: str,
) -> list[RateLimitRule]:
    """The rule set to check for one request. Every rule returned is
    checked atomically together (see RateLimiter.check_many) — a request
    is denied if ANY rule is exceeded.
    """
    if category is RateLimitCategory.PUBLIC:
        limit = settings.RATE_LIMIT_PUBLIC_PER_MINUTE
        return [_rule(category, "ip", client_ip, limit, _ONE_MINUTE)]

    if category is RateLimitCategory.AUTH_READ:
        identity = user_id or client_ip
        limit = settings.RATE_LIMIT_AUTH_READ_PER_MINUTE
        return [_rule(category, "user", identity, limit, _ONE_MINUTE)]

    if category is RateLimitCategory.AUTH_WRITE:
        identity = user_id or client_ip
        limit = settings.RATE_LIMIT_AUTH_WRITE_PER_MINUTE
        return [_rule(category, "user", identity, limit, _ONE_MINUTE)]

    if category is RateLimitCategory.AI_EXPENSIVE:
        identity = user_id or client_ip
        return [
            _rule(category, "user", identity, settings.RATE_LIMIT_AI_PER_MINUTE, _ONE_MINUTE),
            _rule(category, "user", identity, settings.RATE_LIMIT_AI_PER_DAY, _ONE_DAY),
            _rule(category, "ip", client_ip, settings.RATE_LIMIT_AI_IP_PER_MINUTE, _ONE_MINUTE),
            _rule(category, "ip", client_ip, settings.RATE_LIMIT_AI_IP_PER_DAY, _ONE_DAY),
        ]

    raise ValueError(f"Unhandled rate limit category: {category}")  # pragma: no cover


def fail_open_for(category: RateLimitCategory) -> bool:
    """Whether this category should let traffic through (logging loudly)
    when Redis itself is unavailable, vs. reject with 503. See
    app/core/config.py's RATE_LIMIT_FAIL_OPEN_* settings and
    backend/RATE_LIMITING.md for the reasoning.
    """
    if category is RateLimitCategory.AI_EXPENSIVE:
        return settings.RATE_LIMIT_FAIL_OPEN_AI
    return settings.RATE_LIMIT_FAIL_OPEN_DEFAULT
