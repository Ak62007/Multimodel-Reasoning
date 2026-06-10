"""Health-check router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.config import Settings
from backend.app.deps import get_settings_dep
from backend.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings_dep)) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)
