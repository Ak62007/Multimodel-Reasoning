"""Group anomalous time ranges from a master dataframe into analysis windows.

A window is a ``(start_s, end_s)`` pair. The Pattern Detector runs once
per window; the orchestrator decides which windows to keep based on
whether the resulting :class:`agents.schemas.IntegratedBehavioralReport`
actually contains any insights.

Selection strategy
------------------

1. Walk every Pydantic-decoded cell in the master dataframe.
2. Collect non-None ``part_of_anomalous_range`` lists from each modality.
3. Convert each list into a ``(min, max)`` window.
4. Merge overlapping or near-adjacent (``gap_tolerance`` seconds apart)
   windows into a single window.
5. Apply optional padding around each window so the LLM sees a little
   context before/after the anomaly.

Long stretches with no anomalies produce no windows (the spec is explicit
about not emitting empty windows).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


# Object columns in the master dataframe that may carry anomaly metadata.
_MASTER_DATA_COLUMNS: tuple[str, ...] = (
    "blinking_data",
    "gaze_data",
    "jaw_movement_data",
    "smile_data",
    "loudness_data",
    "average_pitch_data",
    "pitch_standard_deviation",
    "words_per_sec",
    "filler_words_usage",
    "pauses_taken",
)


@dataclass(frozen=True)
class AnalysisWindow:
    """A ``(start_s, end_s)`` analysis window keyed for the Pattern Detector."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    def as_tuple(self) -> tuple[float, float]:
        return (self.start, self.end)


def select_windows(
    master_df: pd.DataFrame,
    *,
    gap_tolerance: float = 1.0,
    pad: float = 0.0,
) -> list[AnalysisWindow]:
    """Select analysis windows from anomalous ranges in ``master_df``.

    Args:
        master_df: The pipeline's master dataframe (per-row Pydantic dicts).
        gap_tolerance: Adjacent windows separated by no more than this many
            seconds are merged. Default 1.0 s (per §9.4).
        pad: Optional seconds of padding to apply before and after each
            window. Default 0.0.

    Returns:
        A chronologically-sorted list of merged, non-overlapping windows.
    """
    raw: list[tuple[float, float]] = []
    for col in _MASTER_DATA_COLUMNS:
        if col not in master_df.columns:
            continue
        for cell in master_df[col]:
            window = _window_from_cell(cell)
            if window is not None:
                raw.append(window)

    if not raw:
        logger.info("No anomalous windows detected in master dataframe.")
        return []

    raw.sort()
    merged: list[tuple[float, float]] = []
    cur_start, cur_end = raw[0]
    for start, end in raw[1:]:
        if start - cur_end <= gap_tolerance:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    if pad > 0:
        merged = [(max(0.0, s - pad), e + pad) for s, e in merged]

    logger.info(
        "Selected %d analysis windows (gap=%.1fs, pad=%.1fs)",
        len(merged),
        gap_tolerance,
        pad,
    )
    return [AnalysisWindow(start=s, end=e) for s, e in merged]


def _window_from_cell(cell: object) -> tuple[float, float] | None:
    """Pull a ``(min, max)`` range out of a single cell, if it has one."""
    if not isinstance(cell, dict):
        return None
    raw_range = cell.get("part_of_anomalous_range")
    if not isinstance(raw_range, list) or not raw_range:
        return None
    try:
        floats = [float(t) for t in raw_range]
    except (TypeError, ValueError):
        return None
    if not floats:
        return None
    return (min(floats), max(floats))
