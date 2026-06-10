"""Agentic interpretation layer.

This package owns the LLM-driven side of MMR: it consumes the master
dataframe produced by :mod:`pipeline.orchestrator` and produces (a) a list
of per-window cross-modal pattern reports and (b) a final executive
coaching report.

Only :class:`agents.schemas.IntegratedBehavioralReport` and
:class:`agents.schemas.FinalReport` are exposed via the API. The three
internal observer outputs (visual / audio / vocab) are scaffolding for the
Pattern Detector and are not part of the public surface.
"""

from __future__ import annotations

from agents.orchestrator import build_report
from agents.schemas import (
    CrossModalInsight,
    FinalReport,
    IntegratedBehavioralReport,
)

__all__ = [
    "CrossModalInsight",
    "FinalReport",
    "IntegratedBehavioralReport",
    "build_report",
]
