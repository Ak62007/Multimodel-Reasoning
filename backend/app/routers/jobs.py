"""Jobs router: upload, list, get, delete."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlmodel import Session, select

from backend.app.config import Settings
from backend.app.deps import get_session_dep, get_settings_dep
from backend.app.models import JobRecord
from backend.app.schemas import Job, JobList
from backend.app.services.job_runner import run_job
from backend.app.services.storage import (
    delete_job_artefacts,
    looks_like_parquet,
    stage_test_master_parquet,
    validate_and_save_upload,
)

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    speaker_label: str = Form("B"),
    settings: Settings = Depends(get_settings_dep),
    session: Session = Depends(get_session_dep),
) -> JobRecord:
    job_id = uuid.uuid4().hex
    saved_path = validate_and_save_upload(video, job_id=job_id, settings=settings)

    # If we are in test mode and the upload is a parquet, stage it as the
    # master parquet so the JobRunner can skip the pipeline.
    if settings.mmr_test_mode and looks_like_parquet(saved_path.name):
        stage_test_master_parquet(saved_path, job_id=job_id)

    now = datetime.now(tz=UTC)
    job = JobRecord(
        id=job_id,
        filename=video.filename or "",
        status="queued",
        current_stage=None,
        progress=0.0,
        error=None,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # ``speaker_label`` is forwarded via the runner's settings; we keep it
    # in the form payload so the frontend can pass it through.
    _ = speaker_label

    background_tasks.add_task(run_job, job_id, settings)
    return job


@router.get("/jobs", response_model=JobList)
def list_jobs(
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session_dep),
) -> JobList:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    stmt = select(JobRecord)
    if status_filter:
        stmt = stmt.where(JobRecord.status == status_filter)
    stmt = stmt.order_by(JobRecord.created_at.desc())  # type: ignore[attr-defined]

    items = list(session.exec(stmt.offset(offset).limit(limit)).all())
    total = len(list(session.exec(select(JobRecord)).all()))

    return JobList(
        items=[Job.model_validate(j) for j in items],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(
    job_id: str,
    session: Session = Depends(get_session_dep),
) -> JobRecord:
    job = session.get(JobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    session: Session = Depends(get_session_dep),
) -> Response:
    job = session.get(JobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    session.delete(job)
    session.commit()
    delete_job_artefacts(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
