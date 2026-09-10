"""Liveness / readiness probes. The only fully implemented route so far.

Deliberately carries NO rate-limit dependency (see app/api/deps.py's
`rate_limit()`) and no auth. Deployment platforms and load balancers poll
this on a fixed, often sub-minute interval to decide whether to keep
routing traffic here at all — rate-limiting or auth-gating it would risk
the platform concluding a healthy instance is down.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
