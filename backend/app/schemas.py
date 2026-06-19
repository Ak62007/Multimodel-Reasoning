"""API request/response Pydantic schemas (not to be confused with the per-frame
models in `pipeline.schemas` or the agent output models in `agents.schemas`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_serializer

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
    tier: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    @field_serializer("created_at", "updated_at")
    def _serialize_utc(self, dt: datetime) -> str:
        # Datetimes read back from SQLite are tz-naive but represent UTC. Without
        # an explicit offset the browser parses them as *local* time, which on a
        # UTC+5:30 client makes a just-started job's elapsed timer jump to ~330m.
        # Always emit an offset so the client parses the correct instant.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()


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
