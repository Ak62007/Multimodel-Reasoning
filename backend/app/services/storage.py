"""File-system helpers for one analysis job."""

from __future__ import annotations

import shutil
from pathlib import Path

from pipeline.io.paths import PipelinePaths


def job_paths(processed_root: Path, job_id: str) -> PipelinePaths:
    return PipelinePaths(root=processed_root, job_id=job_id)


def save_upload(
    upload_filename: str,
    upload_bytes_iter,
    *,
    dest_dir: Path,
    job_id: str,
) -> Path:
    """Stream an upload to `dest_dir/{job_id}{ext}` and return the path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(upload_filename).suffix.lower()
    dest = dest_dir / f"{job_id}{ext}"
    with dest.open("wb") as f:
        for chunk in upload_bytes_iter:
            f.write(chunk)
    return dest


def remove_job_artefacts(processed_root: Path, job_id: str) -> None:
    """Delete the job's processed dir and its upload (if present)."""
    job_dir = processed_root / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def tail_log_file(log_path: Path, n: int) -> list[str]:
    """Return the last `n` lines of a job log; empty list if no log yet."""
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return [ln.rstrip("\n") for ln in lines[-n:]]


__all__ = ["job_paths", "remove_job_artefacts", "save_upload", "tail_log_file"]
