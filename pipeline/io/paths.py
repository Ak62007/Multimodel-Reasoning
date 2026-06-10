"""Centralized path resolution for pipeline artefacts.

Implemented in M2. M1 only ships the module so downstream imports do not
break and so the layout in §6 of the spec is in place.
"""

from __future__ import annotations

from pathlib import Path

# Repository root resolved at import time. Pipelines should derive every
# other path from this anchor rather than hard-coding relative paths.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = REPO_ROOT / "data"
UPLOADS_DIR: Path = DATA_DIR / "uploads"
PROCESSED_DIR: Path = DATA_DIR / "processed"
MODELS_DIR: Path = REPO_ROOT / "models"


def job_workdir(job_id: str) -> Path:
    """Return the per-job working directory (created lazily in M2)."""
    return PROCESSED_DIR / job_id
