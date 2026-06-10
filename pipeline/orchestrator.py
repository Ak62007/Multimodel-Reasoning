"""End-to-end pipeline orchestrator: video path → master parquet.

Implemented in M2. M1 only ships the module so the §6 layout exists and
so downstream code can already import ``pipeline.orchestrator``.
"""

from __future__ import annotations

from pathlib import Path


def run_pipeline(video_path: str | Path, *, speaker_label: str = "B") -> Path:
    """Run the full deterministic pipeline. Not yet implemented (M2)."""
    raise NotImplementedError("pipeline.orchestrator.run_pipeline is implemented in milestone M2")
