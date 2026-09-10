"""Translates exceptions into a consistent JSON error envelope.

Service-layer code raises AppError subclasses and never imports FastAPI;
this is the single place that maps them onto HTTP.

Response shape (matches what frontend/src/services/api/client.js expects):
    {"code": "not_found", "detail": "…", "request_id": "…"}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.middleware.request_id import get_request_id

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        payload = exc.to_dict() | {"request_id": get_request_id()}
        # Expected errors: log at info, they are not incidents.
        logger.info("AppError %s: %s", exc.code, exc.message)
        # Optional response headers (Retry-After, X-RateLimit-* on a
        # RateLimitError) — None for every error type that doesn't set them,
        # which JSONResponse treats the same as omitting the argument.
        return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "detail": "Request validation failed.",
                "details": exc.errors(),
                "request_id": get_request_id(),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception):
        # Unknown failure: log with traceback, return an opaque message so
        # internals are never leaked to clients.
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "detail": "Something went wrong.",
                "request_id": get_request_id(),
            },
        )
