"""Centralized path resolution for pipeline artefacts.

Every pipeline component derives its file system paths from this module so
that runtime directories can be relocated by setting environment variables
(``DATA_ROOT``, ``UPLOAD_DIR``, ``PROCESSED_DIR``, ``FACE_LANDMARKER_PATH``)
without touching code.

The single source of truth for the *layout* of a per-job working directory
is :class:`JobPaths`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_path(key: str, default: Path) -> Path:
    """Read ``key`` from the environment, falling back to ``default``."""
    raw = os.environ.get(key)
    return Path(raw).expanduser() if raw else default


REPO_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = _env_path("DATA_ROOT", REPO_ROOT / "data")
UPLOADS_DIR: Path = _env_path("UPLOAD_DIR", DATA_DIR / "uploads")
PROCESSED_DIR: Path = _env_path("PROCESSED_DIR", DATA_DIR / "processed")
MODELS_DIR: Path = REPO_ROOT / "models"

FACE_LANDMARKER_PATH: Path = _env_path(
    "FACE_LANDMARKER_PATH",
    MODELS_DIR / "face_landmarker.task",
)


@dataclass(frozen=True)
class JobPaths:
    """Resolved paths for a single pipeline run.

    A ``JobPaths`` instance is produced by :func:`for_job` (used by the
    backend, keyed by job id) or by :func:`for_video` (used by the
    ``python -m pipeline.orchestrator`` CLI, keyed by video filename).
    """

    workdir: Path
    frames_dir: Path
    audio_path: Path
    face_features_path: Path
    audio_technical_path: Path
    utterances_path: Path
    whisper_path: Path
    merged_path: Path
    features_raw_path: Path
    features_smoothed_path: Path
    master_path: Path
    log_path: Path

    def ensure_dirs(self) -> None:
        """Create the working directories on disk. Idempotent."""
        for d in (
            self.workdir,
            self.frames_dir,
            self.workdir / "parquet",
        ):
            d.mkdir(parents=True, exist_ok=True)


def for_job(job_id: str) -> JobPaths:
    """Build per-job paths under ``PROCESSED_DIR / job_id``."""
    return _build_paths(PROCESSED_DIR / job_id)


def for_video(video_path: str | Path) -> JobPaths:
    """Build per-video paths under ``PROCESSED_DIR / <video_stem>``.

    Used by the ``python -m pipeline.orchestrator`` CLI when there is no
    job id (M2 acceptance flow).
    """
    stem = Path(video_path).stem or "video"
    return _build_paths(PROCESSED_DIR / stem)


def _build_paths(workdir: Path) -> JobPaths:
    parquet = workdir / "parquet"
    return JobPaths(
        workdir=workdir,
        frames_dir=workdir / "frames",
        audio_path=workdir / "audio.wav",
        face_features_path=parquet / "face_features.parquet",
        audio_technical_path=parquet / "audio_technical.parquet",
        utterances_path=parquet / "utterances.parquet",
        whisper_path=parquet / "whisper.parquet",
        merged_path=parquet / "merged.parquet",
        features_raw_path=parquet / "features_raw.parquet",
        features_smoothed_path=parquet / "features_smoothed_rz.parquet",
        master_path=parquet / "master.parquet",
        log_path=workdir / "pipeline.log",
    )
