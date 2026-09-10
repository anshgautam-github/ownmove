"""Application exception hierarchy.

Domain code raises these; a single middleware translates them into HTTP
responses. That keeps service-layer code free of FastAPI/HTTP imports and
makes the same services reusable from workers and scripts.
"""


class AppError(Exception):
    """Base class for all expected, handled application errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message or self.message
        self.details = details or {}
        # Optional response headers (e.g. Retry-After, X-RateLimit-* on a
        # RateLimitError). None for every existing caller/subclass — this is
        # additive and doesn't change any current error's response shape.
        self.headers = headers
        super().__init__(self.message)

    def to_dict(self) -> dict:
        payload = {"code": self.code, "detail": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    message = "The request was malformed."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have access to this resource."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "The resource already exists."


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please slow down."


class ServiceUnavailableError(AppError):
    """Used when a dependency required to safely serve the request (e.g.
    Redis, for a fail-closed rate-limit tier) is unavailable — distinct
    from RateLimitError: this is an infrastructure failure, not the caller
    actually exceeding a limit.
    """

    status_code = 503
    code = "service_unavailable"
    message = "This operation is temporarily unavailable. Please try again shortly."


class NotImplementedYetError(AppError):
    """Used by scaffolded routes that have no implementation yet."""

    status_code = 501
    code = "not_implemented"
    message = "This endpoint is scaffolded but not implemented yet."


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
    message = "An upstream service failed."


class AIProviderError(ExternalServiceError):
    code = "ai_provider_error"
    message = "The AI provider could not complete the request."
