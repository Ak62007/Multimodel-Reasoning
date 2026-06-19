"""SQLModel tables. The Job row is the durable per-analysis record."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlmodel import Field, SQLModel

JobStatus = Literal["queued", "running", "succeeded", "failed"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Job(SQLModel, table=True):
    """One analysis run — covers upload through final report."""

    id: str = Field(primary_key=True)
    filename: str
    upload_path: str  # absolute path to the stored upload
    is_test_input: bool = Field(default=False)  # True if the upload is a pre-computed parquet
    speaker_label: str = Field(default="auto")  # "auto" → detected at run time
    tier: str = Field(default="paid")  # "paid" = full depth; "free" = lean single-call path

    status: str = Field(default="queued", index=True)  # JobStatus literal
    current_stage: str | None = Field(default=None)
    progress: float = Field(default=0.0)
    error: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)

    # LLM token usage for the agent chain (counts only — never any key/content).
    input_tokens: int | None = Field(default=None)
    output_tokens: int | None = Field(default=None)
    total_tokens: int | None = Field(default=None)

    @property
    def duration_sec(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at or _utc_now()
        # Datetimes read back from SQLite are tz-naive but represent UTC;
        # coerce both sides so we never mix naive/aware in the subtraction.
        start = self.started_at if self.started_at.tzinfo else self.started_at.replace(tzinfo=UTC)
        end = end if end.tzinfo else end.replace(tzinfo=UTC)
        return (end - start).total_seconds()


__all__ = ["Job", "JobStatus"]
