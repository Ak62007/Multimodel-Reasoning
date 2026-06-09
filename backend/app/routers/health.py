"""Health/liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

from pipeline import __version__ as pipeline_version

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": pipeline_version}
