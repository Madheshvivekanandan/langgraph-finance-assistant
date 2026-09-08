"""Health endpoint."""

from fastapi import APIRouter

from app.schemas.health_out import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness check")
def get_health() -> HealthOut:
    """Report that the API process is up. Deliberately does not touch the database."""
    return HealthOut(status="ok")
