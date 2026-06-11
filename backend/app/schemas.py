"""API request/response Pydantic schemas (not to be confused with the per-frame
models in `pipeline.schemas` or the agent output models in `agents.schemas`)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from agents.schemas import FinalReport, WindowAnalysis


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class JobOut(BaseModel):
    """Response model for /api/jobs/{id} and friends."""

    id: str
    filename: str
    status: Literal["queued", "running", "succeeded", "failed"]
    current_stage: str | None
    progress: float
    error: str | None
    created_at: datetime
    updated_at: datetime
    duration_sec: float | None


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int


class ReportOut(BaseModel):
    markdown: str
    structured: FinalReport


class SegmentsOut(BaseModel):
    items: list[WindowAnalysis]


class LogsOut(BaseModel):
    lines: list[str]


__all__ = [
    "HealthResponse",
    "JobListOut",
    "JobOut",
    "LogsOut",
    "ReportOut",
    "SegmentsOut",
]
