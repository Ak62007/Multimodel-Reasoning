"""Reports router: segments, report, master_df, logs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session

from backend.app.deps import get_session_dep
from backend.app.models import JobRecord
from backend.app.schemas import LogsResponse, ReportResponse, SegmentsResponse
from pipeline.io.parquet import load_df_parquet_safe
from pipeline.io.paths import for_job

router = APIRouter(tags=["reports"])


def _require_succeeded(job_id: str, session: Session) -> JobRecord:
    job = session.get(JobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"job not ready (status={job.status})",
        )
    return job


@router.get("/jobs/{job_id}/segments")
def get_segments(
    job_id: str,
    session: Session = Depends(get_session_dep),
) -> SegmentsResponse:
    _require_succeeded(job_id, session)
    segments_path = for_job(job_id).workdir / "segments.json"
    if not segments_path.exists():
        return []
    data = json.loads(segments_path.read_text())
    return data


@router.get("/jobs/{job_id}/report")
def get_report(
    job_id: str,
    session: Session = Depends(get_session_dep),
) -> ReportResponse:
    _require_succeeded(job_id, session)
    workdir = for_job(job_id).workdir
    report_md = (workdir / "report.md").read_text()
    report_json = json.loads((workdir / "report.json").read_text())
    return ReportResponse(markdown=report_md, structured=report_json)


@router.get("/jobs/{job_id}/master_df", response_model=None)
def get_master_df(
    job_id: str,
    format: str = Query("parquet", pattern="^(parquet|json)$"),  # noqa: A002 — FastAPI query alias
    session: Session = Depends(get_session_dep),
) -> FileResponse | JSONResponse:
    _require_succeeded(job_id, session)
    master_path: Path = for_job(job_id).master_path
    if not master_path.exists():
        raise HTTPException(status_code=404, detail="master parquet missing")

    if format == "parquet":
        return FileResponse(
            master_path,
            media_type="application/octet-stream",
            filename=f"{job_id}_master.parquet",
        )

    df: pd.DataFrame = load_df_parquet_safe(str(master_path))
    # ``orient='records'`` is the friendliest shape for the frontend; the
    # object columns are pre-decoded to Python dicts by load_df_parquet_safe.
    payload = json.loads(df.to_json(orient="records"))
    return JSONResponse(content=payload)


@router.get("/jobs/{job_id}/logs", response_model=LogsResponse)
def get_logs(
    job_id: str,
    tail: int = 200,
    session: Session = Depends(get_session_dep),
) -> LogsResponse:
    job = session.get(JobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    tail = max(1, min(tail, 5000))

    log_path = for_job(job_id).log_path
    if not log_path.exists():
        return LogsResponse(lines=[])

    lines = log_path.read_text().splitlines()
    return LogsResponse(lines=lines[-tail:])
