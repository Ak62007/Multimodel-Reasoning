"""Report endpoints: segments, final report, master_df download, logs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
from sqlmodel import Session

from agents.schemas import FinalReport, WindowAnalysis
from backend.app.config import Settings, get_settings
from backend.app.deps import get_session_dep
from backend.app.models import Job
from backend.app.schemas import LogsOut, ReportOut, SegmentsOut
from backend.app.services.storage import job_paths, tail_log_file
from pipeline.io.parquet import load_df_parquet_safe

_log = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs/{job_id}", tags=["reports"])

_OUTDATED_DETAIL = (
    "This analysis was produced by an older version of the agentic layer and its "
    "report format is no longer supported. Please re-run the analysis."
)


def _require_job(job_id: str, session: Session) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="job not found")
    return job


@router.get("/segments", response_model=SegmentsOut)
def get_segments(
    job_id: str,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session_dep),
) -> SegmentsOut:
    job = _require_job(job_id, session)
    paths = job_paths(settings.processed_dir, job_id)
    segments_path = paths.job_dir / "segments.json"
    if not segments_path.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"No segments yet — job is {job.status}",
        )
    payload = json.loads(segments_path.read_text())
    try:
        return SegmentsOut(items=[WindowAnalysis(**r) for r in payload])
    except ValidationError:
        _log.warning("Outdated segments format for job %s", job_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_OUTDATED_DETAIL) from None


@router.get("/report", response_model=ReportOut)
def get_report(
    job_id: str,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session_dep),
) -> ReportOut:
    job = _require_job(job_id, session)
    paths = job_paths(settings.processed_dir, job_id)
    report_path = paths.job_dir / "report.json"
    md_path = paths.job_dir / "report.md"
    if not report_path.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"No report yet — job is {job.status}",
        )
    try:
        structured = FinalReport(**json.loads(report_path.read_text()))
    except ValidationError:
        _log.warning("Outdated report format for job %s", job_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_OUTDATED_DETAIL) from None
    markdown = md_path.read_text() if md_path.exists() else ""
    return ReportOut(markdown=markdown, structured=structured)


@router.get("/master_df", response_model=None)
def get_master_df(
    job_id: str,
    format: str = Query(default="parquet", pattern="^(json|parquet)$"),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session_dep),
) -> JSONResponse | FileResponse:
    _require_job(job_id, session)
    paths = job_paths(settings.processed_dir, job_id)
    master_path: Path = paths.master_parquet
    if not master_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="master_df not yet produced")
    if format == "parquet":
        return FileResponse(master_path, media_type="application/octet-stream")
    df = load_df_parquet_safe(master_path)
    return JSONResponse(json.loads(df.to_json(orient="records")))


@router.get("/logs", response_model=LogsOut)
def get_logs(
    job_id: str,
    tail: int = Query(default=200, ge=1, le=10000),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session_dep),
) -> LogsOut:
    _require_job(job_id, session)
    paths = job_paths(settings.processed_dir, job_id)
    return LogsOut(lines=tail_log_file(paths.log_file, tail))


__all__ = ["router"]
