"""SQLModel persistence models for the backend.

Only one persistent table is needed in v1: :class:`JobRecord`. Segments
and the final report are stored on disk per-job (JSON / Markdown /
parquet sidecar files) so the API can stream them without parsing them
through the DB.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlmodel import Field, SQLModel

JobStatus = Literal["queued", "running", "succeeded", "failed"]


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class JobRecord(SQLModel, table=True):
    """Per-upload job state. One row per ``POST /api/jobs``."""

    __tablename__ = "jobs"  # type: ignore[assignment]

    id: str = Field(primary_key=True, index=True)
    filename: str
    status: str = Field(default="queued", index=True)
    current_stage: str | None = None
    progress: float = 0.0
    error: str | None = None
    duration_sec: float | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
