"""API DTOs (request / response Pydantic models).

These are deliberately small and serialised straight out of
``backend.app.models.JobRecord``. The agent layer's schemas
(``agents.schemas.IntegratedBehavioralReport`` / ``FinalReport``)
are re-exported as-is.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agents.schemas import FinalReport, IntegratedBehavioralReport

JobStatusLiteral = Literal["queued", "running", "succeeded", "failed"]


class Job(BaseModel):
    """Public representation of a job (matches §7.2)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: JobStatusLiteral
    current_stage: str | None = None
    progress: float = 0.0
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    duration_sec: float | None = None


class JobList(BaseModel):
    items: list[Job]
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str


class ReportResponse(BaseModel):
    markdown: str
    structured: FinalReport


class LogsResponse(BaseModel):
    lines: list[str]


SegmentsResponse = list[IntegratedBehavioralReport]
