"""Health/liveness probe."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.config import Settings, get_settings
from backend.app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)
