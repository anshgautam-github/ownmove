"""Attaches a correlation id to every request.

Lets a single user action be traced across API logs, background jobs and AI
provider calls. Echoed back as the X-Request-ID response header.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ContextVar so any code in the request's async context can read the id
# without it being threaded through every function signature.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Honour an upstream id (load balancer / gateway) if provided.
        rid = request.headers.get(HEADER) or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        request.state.request_id = rid

        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        response.headers[HEADER] = rid
        return response


def get_request_id() -> str:
    return request_id_ctx.get()
