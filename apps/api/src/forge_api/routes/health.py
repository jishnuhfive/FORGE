from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["ok"]
    service: Literal["forge-api"]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Process liveness only; this does not claim external-service readiness."""
    return HealthResponse(status="ok", service="forge-api")
