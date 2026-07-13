import datetime

from fastapi import APIRouter

import schemas

router = APIRouter(tags=["health"])


@router.get("/health", response_model=schemas.HealthCheckResponse)
def health_check() -> schemas.HealthCheckResponse:
    """Liveness probe for load balancers and Render health checks."""
    return schemas.HealthCheckResponse(
        status="ok",
        timestamp=datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    )
