"""Trusted-proxy-aware client IP resolution.

`X-Forwarded-For` is attacker-controlled input whenever the client can talk
to this service directly — anyone can send
`X-Forwarded-For: 1.2.3.4` and, if that header is trusted blindly, get a
fresh rate-limit bucket on every request for free. It is only trustworthy
for the hops a *real, trusted* reverse proxy/load balancer itself appended.

`settings.TRUSTED_PROXY_HOPS` (default 0) says how many such hops this
deployment has. With 0, this always returns `request.client.host` — the
direct TCP peer, which cannot be spoofed by the client — and every
`X-Forwarded-For`/`X-Real-IP` header is ignored entirely. Only raise it
once you've confirmed the real deployment topology (see
backend/RATE_LIMITING.md); getting it wrong in the trusting direction
makes the rate limiter trivially bypassable.
"""

from fastapi import Request

from app.core.config import settings

# A request's own connecting IP is always a safe fallback, but it can be
# `None` in some ASGI test/reverse-proxy setups — a stable placeholder
# groups those together into one bucket rather than crashing.
_UNKNOWN_IP = "unknown"


def get_client_ip(request: Request) -> str:
    hops = settings.TRUSTED_PROXY_HOPS

    if hops > 0:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Each proxy hop APPENDS the address it saw to the end of the
            # list (client, proxy1, proxy2, ...). If we trust exactly N
            # hops, the real client is N entries from the right — anything
            # to the left of that (including a value the client prepended
            # itself) is untrusted and ignored.
            chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
            if len(chain) >= hops:
                return chain[-hops]

    if request.client and request.client.host:
        return request.client.host

    return _UNKNOWN_IP
