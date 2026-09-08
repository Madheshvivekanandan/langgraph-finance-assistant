"""Response schema for the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    """Liveness signal returned by GET /api/v1/health."""

    status: Literal["ok"]
