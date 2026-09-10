"""Security-relevant response headers every response gets, regardless of
route. This backend serves JSON only (no HTML templates, no server-rendered
pages), so CSP/frame-ancestors matter most at the frontend's own hosting
layer (wherever the SPA is served), not here -- but the handful of headers
below are cheap, unconditional, and correct for any API backend.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.is_production:
            # Only meaningful once the deployment actually terminates TLS
            # (Render/Vercel-style hosting does this by default, but this
            # header should only ever be sent over a connection that really
            # is HTTPS).
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
