"""Group per-row anomaly ranges into analysis windows for the agent chain.

A "window" is a contiguous span of the master timeline that contains at
least one anomalous event in any modality. Adjacent ranges (gap ≤ 1s) are
merged so the agents see one coherent block rather than ten tiny ones.

Per spec §9.4: windows with no anomalies are skipped — the agents do nothing
when the candidate is at baseline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

_log = logging.getLogger(__name__)

# Columns whose `part_of_anomalous_range` field defines a candidate window.
_ANOMALY_COLUMNS = (
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

# Lookup of (column name in master_df) → (modality label exposed to agents).
_MODALITY_BY_COLUMN = {
    "blinking_data": "Visual",
    "gaze_data": "Visual",
    "jaw_movement_data": "Visual",
    "smile_data": "Visual",
    "loudness_data": "Audio",
    "average_pitch_data": "Audio",
    "pitch_standard_deviation": "Audio",
    "words_per_sec": "Verbal",
    "filler_words_usage": "Verbal",
    "pauses_taken": "Verbal",
}


@dataclass
class AnalysisWindow:
    """One contiguous block of anomalous timeline to feed to the agent chain."""

    start: float
    end: float
    rows: pd.DataFrame  # slice of master_df covering [start, end]
    modalities_with_anomalies: set[str] = field(default_factory=set)

    @property
    def duration(self) -> float:
        return self.end - self.start


def _extract_ranges(master_df: pd.DataFrame) -> list[tuple[float, float, str]]:
    """Return (start, end, modality) tuples for every distinct anomalous range."""
    ranges: list[tuple[float, float, str]] = []

    for col in _ANOMALY_COLUMNS:
        if col not in master_df.columns:
            continue
        modality = _MODALITY_BY_COLUMN[col]
        for cell in master_df[col]:
            if not isinstance(cell, dict):
                continue
            r: Any = cell.get("part_of_anomalous_range")
            if not r or not isinstance(r, list) or len(r) < 1:
                continue
            ranges.append((float(min(r)), float(max(r)), modality))

    # de-dup exact duplicates
    return list({(round(s, 2), round(e, 2), m) for s, e, m in ranges})


def _merge_overlapping(
    ranges: list[tuple[float, float, str]], gap: float = 1.0
) -> list[tuple[float, float, set[str]]]:
    """Merge overlapping/adjacent (gap ≤ `gap`) ranges into a single span,
    tracking which modalities contributed."""
    if not ranges:
        return []
    # Sort by start
    sorted_ranges = sorted(ranges, key=lambda r: (r[0], r[1]))
    merged: list[tuple[float, float, set[str]]] = []
    cur_s, cur_e, cur_mods = sorted_ranges[0][0], sorted_ranges[0][1], {sorted_ranges[0][2]}

    for s, e, m in sorted_ranges[1:]:
        if s <= cur_e + gap:
            cur_e = max(cur_e, e)
            cur_mods.add(m)
        else:
            merged.append((cur_s, cur_e, cur_mods))
            cur_s, cur_e, cur_mods = s, e, {m}
    merged.append((cur_s, cur_e, cur_mods))
    return merged


def select_windows(master_df: pd.DataFrame, *, gap: float = 1.0) -> list[AnalysisWindow]:
    """Return the list of analysis windows for the agent chain.

    The orchestrator iterates over the returned windows, calls the three
    observers + Pattern Detector for each, and silently drops any window
    whose pattern detection yields no meaningful insights.
    """
    if master_df.empty or "Time" not in master_df.columns:
        return []

    raw_ranges = _extract_ranges(master_df)
    merged = _merge_overlapping(raw_ranges, gap=gap)

    windows: list[AnalysisWindow] = []
    for start, end, mods in merged:
        slice_mask = (master_df["Time"] >= start) & (master_df["Time"] <= end)
        rows = master_df.loc[slice_mask].copy()
        windows.append(
            AnalysisWindow(
                start=start,
                end=end,
                rows=rows.reset_index(drop=True),
                modalities_with_anomalies=mods,
            )
        )

    _log.info("Selected %d analysis windows from %d total rows", len(windows), len(master_df))
    return windows


__all__ = ["AnalysisWindow", "select_windows"]
