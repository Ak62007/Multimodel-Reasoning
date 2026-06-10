"""Upload + per-job artefact storage helpers."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from backend.app.config import ALLOWED_VIDEO_MIME_TYPES, Settings
from pipeline.io.parquet import save_df_parquet_safe
from pipeline.io.paths import UPLOADS_DIR, for_job

logger = logging.getLogger(__name__)

_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".webm", ".m4v"}
_PARQUET_SUFFIXES = {".parquet"}


def looks_like_parquet(filename: str) -> bool:
    return Path(filename).suffix.lower() in _PARQUET_SUFFIXES


def looks_like_video(filename: str, content_type: str | None) -> bool:
    suffix = Path(filename).suffix.lower()
    if suffix in _VIDEO_SUFFIXES:
        return True
    return bool(content_type and content_type in ALLOWED_VIDEO_MIME_TYPES)


def validate_and_save_upload(
    upload: UploadFile,
    *,
    job_id: str,
    settings: Settings,
) -> Path:
    """Validate the upload and write it to ``data/uploads/{job_id}{ext}``.

    Raises :class:`HTTPException` 413 / 422 on size / mime errors.
    Returns the saved path.
    """
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="missing filename",
        )

    suffix = Path(upload.filename).suffix.lower()
    if settings.mmr_test_mode and suffix in _PARQUET_SUFFIXES:
        # Test-mode path: accept the pre-computed parquet without further checks.
        pass
    elif looks_like_video(upload.filename, upload.content_type):
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"unsupported upload type {upload.content_type!r}; "
                f"allowed video MIMEs: {sorted(ALLOWED_VIDEO_MIME_TYPES)}"
            ),
        )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOADS_DIR / f"{job_id}{suffix}"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    with destination.open("wb") as out:
        upload.file.seek(0)
        while chunk := upload.file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                out.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"upload exceeds {settings.max_upload_mb} MB",
                )
            out.write(chunk)
    logger.info("Saved upload for job %s -> %s (%d bytes)", job_id, destination, written)
    return destination


def stage_test_master_parquet(uploaded_path: Path, job_id: str) -> None:
    """Stage a test-mode parquet upload as the job's master parquet.

    The upload arrives without the JSON sidecar that ``save_df_parquet_safe``
    normally writes, so we re-read the parquet, decode any JSON-encoded
    string columns back into Python objects, then call
    ``save_df_parquet_safe`` to regenerate the sidecar alongside the master
    file. This means a freshly-uploaded parquet round-trips back to the
    same per-row Pydantic-dict shape the rest of the pipeline expects.
    """
    paths = for_job(job_id)
    paths.ensure_dirs()
    df = pd.read_parquet(uploaded_path)
    df = _decode_jsonish_columns(df)
    save_df_parquet_safe(df, str(paths.master_path))


def _decode_jsonish_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Decode any column whose values are JSON-encoded strings into Python dicts/lists."""
    for col in df.columns:
        series = df[col]
        if series.dtype != object and series.dtype.name not in ("string", "string[python]"):
            continue
        non_null = series.dropna()
        if non_null.empty:
            continue
        sample = non_null.iloc[0]
        if not isinstance(sample, str):
            continue
        if not sample.strip().startswith(("{", "[")):
            continue
        df[col] = series.apply(
            lambda v: (
                json.loads(v) if isinstance(v, str) and v.strip().startswith(("{", "[")) else v
            )
        )
    return df


def delete_job_artefacts(job_id: str) -> None:
    """Remove the job's processed dir + upload file. Idempotent."""
    paths = for_job(job_id)
    if paths.workdir.exists():
        shutil.rmtree(paths.workdir, ignore_errors=True)
    for ext in (".mp4", ".mov", ".avi", ".webm", ".m4v", ".parquet", ""):
        candidate = UPLOADS_DIR / f"{job_id}{ext}"
        if candidate.exists():
            candidate.unlink()
