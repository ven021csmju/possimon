import datetime

from fastapi import APIRouter

import schemas

router = APIRouter(tags=["health"])


def _utc_iso8601() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


@router.get("/health", response_model=schemas.HealthCheckResponse)
def health_check() -> schemas.HealthCheckResponse:
    """Liveness probe for load balancers, Render, and GitHub Actions wake-up."""
    return schemas.HealthCheckResponse(
        status="ok",
        timestamp=_utc_iso8601(),
    )


@router.get("/ping", response_model=schemas.PingResponse)
def ping() -> schemas.PingResponse:
    """Lightweight wake-up endpoint for external keep-alive services."""
    return schemas.PingResponse(
        message="pong",
        timestamp=_utc_iso8601(),
    )
