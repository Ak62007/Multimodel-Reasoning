"""Job endpoints: upload, list, status, delete."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi import (
    File as FastAPIFile,
)
from sqlmodel import Session, func, select

from backend.app.config import Settings, get_settings
from backend.app.deps import get_session_dep
from backend.app.models import Job
from backend.app.schemas import JobListOut, JobOut
from backend.app.services.job_runner import run_job_blocking
from backend.app.services.key_validation import (
    KeyValidationError,
    validate_assemblyai_key,
    validate_gemini_key,
)
from backend.app.services.storage import remove_job_artefacts, save_upload

_log = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        filename=job.filename,
        status=job.status,  # type: ignore[arg-type]
        current_stage=job.current_stage,
        progress=job.progress,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        duration_sec=job.duration_sec,
        tier=job.tier,
        input_tokens=job.input_tokens,
        output_tokens=job.output_tokens,
        total_tokens=job.total_tokens,
    )


def _validate_upload(filename: str, size: int, settings: Settings) -> bool:
    """Return True if the upload is a pre-computed test parquet."""
    ext = Path(filename).suffix.lower()
    is_video = ext in settings.allowed_video_extensions
    is_test_input = settings.mmr_test_mode and ext in settings.allowed_test_extensions

    if not (is_video or is_test_input):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type {ext}. Allowed: "
            f"{settings.allowed_video_extensions}"
            + (
                f" (or {settings.allowed_test_extensions} when MMR_TEST_MODE=1)"
                if settings.mmr_test_mode
                else ""
            ),
        )

    if size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds MAX_UPLOAD_MB={settings.max_upload_mb}",
        )
    return is_test_input


async def _preflight_validate_keys(
    *,
    settings: Settings,
    is_test_input: bool,
    gemini_api_key: str | None,
    assemblyai_api_key: str | None,
) -> None:
    """Validate the effective keys that this job will use. Raises HTTP 400 with a
    friendly message on a missing-but-required or rejected key."""
    # Gemini powers the agent chain — only needed when agents make real calls.
    if settings.llm_provider != "stub":
        gemini_key = gemini_api_key or settings.gemini_api_key
        if not gemini_key:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="A Gemini API key is required to analyze the interview.",
            )
        try:
            await validate_gemini_key(gemini_key)
        except KeyValidationError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    # AssemblyAI powers transcription — skipped for the test-parquet path.
    if not is_test_input:
        aai_key = assemblyai_api_key or settings.assemblyai_api_key
        if not aai_key:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="An AssemblyAI API key is required to transcribe the audio.",
            )
        try:
            await validate_assemblyai_key(aai_key)
        except KeyValidationError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session_dep),
    video: UploadFile = FastAPIFile(...),
    speaker_label: str = Form("auto"),
    tier: str = Form("paid"),
    gemini_api_key: str | None = Form(None),
    assemblyai_api_key: str | None = Form(None),
) -> JobOut:
    job_id = uuid.uuid4().hex[:12]

    tier = tier.strip().lower()
    if tier not in ("free", "paid"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="tier must be 'free' or 'paid'."
        )

    # Read into memory once to size-check; for very large uploads we stream
    # via SpooledTemporaryFile under the hood. 500 MB is the configured cap.
    contents = await video.read()
    is_test_input = _validate_upload(video.filename or "upload", len(contents), settings)

    # Pre-flight: verify the keys we'll actually use *before* doing any work, so
    # a bad key fails fast with a clear message instead of two minutes into the
    # pipeline. Skipped when no real call will be made (stub agents / test parquet).
    await _preflight_validate_keys(
        settings=settings,
        is_test_input=is_test_input,
        gemini_api_key=gemini_api_key or None,
        assemblyai_api_key=assemblyai_api_key or None,
    )

    upload_path = save_upload(
        video.filename or f"{job_id}.bin",
        [contents],
        dest_dir=settings.upload_dir,
        job_id=job_id,
    )

    job = Job(
        id=job_id,
        filename=video.filename or upload_path.name,
        upload_path=str(upload_path),
        is_test_input=is_test_input,
        speaker_label=speaker_label,
        tier=tier,
        status="queued",
        progress=0.0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Per-request keys (BYOK) are passed straight to the worker and never
    # persisted — not on the Job row, not in logs.
    background_tasks.add_task(
        run_job_blocking,
        job_id,
        settings,
        (gemini_api_key or None),
        (assemblyai_api_key or None),
    )
    _log.info("Queued job %s (filename=%s, test_input=%s)", job_id, job.filename, is_test_input)
    return _to_out(job)


@router.get("", response_model=JobListOut)
def list_jobs(
    session: Session = Depends(get_session_dep),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobListOut:
    base = select(Job)
    if status_filter:
        base = base.where(Job.status == status_filter)
    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    rows = session.exec(
        base.order_by(Job.created_at.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
    ).all()
    return JobListOut(items=[_to_out(j) for j in rows], total=int(total))


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, session: Session = Depends(get_session_dep)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="job not found")
    return _to_out(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    session: Session = Depends(get_session_dep),
    settings: Settings = Depends(get_settings),
) -> Response:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="job not found")

    # Remove upload + processed artefacts.
    try:
        Path(job.upload_path).unlink(missing_ok=True)
    except Exception:
        _log.exception("Failed to remove upload for job %s", job_id)
    remove_job_artefacts(settings.processed_dir, job_id)

    session.delete(job)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
