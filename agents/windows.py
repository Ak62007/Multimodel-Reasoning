"""Group the master timeline into analysis windows for the agent chain.

Two kinds of window are produced:

1. **Active windows** — contiguous spans containing at least one anomalous
   event in any modality (adjacent ranges, gap ≤ 1s, are merged).
2. **Baseline windows** — short calm spans sampled from the quiet gaps so the
   agents establish a baseline and the synthesis stage can reason about the
   *arc* of the interview (calm → trigger → recovery), not just the spikes.

Every window carries temporal context (`phase`, `position_pct`, `index`,
`total`) so the Window Analyst knows *where in the interview* it sits. The
total number of windows is capped (`MAX_WINDOWS`) to bound LLM cost; baseline
windows are dropped first and any truncation is logged (never silent).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

_log = logging.getLogger(__name__)

# Hard cap on total windows fed to the agent chain (cost control).
MAX_WINDOWS = 50
# How many baseline probes to spread across the interview.
BASELINE_SAMPLES = 10
# Length (seconds) of each sampled baseline window.
BASELINE_LEN = 3.0

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
    """One block of timeline to feed to the agent chain."""

    start: float
    end: float
    rows: pd.DataFrame  # slice of master_df covering [start, end]
    modalities_with_anomalies: set[str] = field(default_factory=set)
    is_baseline: bool = False
    # Temporal context (filled in once the full window list is known).
    phase: str = "Opening"
    position_pct: float = 0.0
    index: int = 0
    total: int = 0

    @property
    def duration(self) -> float:
        return self.end - self.start


def _phase_for(pct: float) -> str:
    if pct < 0.10:
        return "Opening"
    if pct < 0.35:
        return "Early"
    if pct < 0.65:
        return "Middle"
    if pct < 0.90:
        return "Late"
    return "Closing"


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


def _slice_rows(master_df: pd.DataFrame, start: float, end: float) -> pd.DataFrame:
    mask = (master_df["Time"] >= start) & (master_df["Time"] <= end)
    return master_df.loc[mask].copy().reset_index(drop=True)


def _overlaps_any(start: float, end: float, spans: list[tuple[float, float]]) -> bool:
    return any(start <= e and s <= end for s, e in spans)


def _sample_baseline_windows(
    master_df: pd.DataFrame,
    duration: float,
    active_spans: list[tuple[float, float]],
) -> list[AnalysisWindow]:
    """Probe evenly across the interview; keep probes that fall in quiet gaps."""
    if duration <= 0:
        return []
    windows: list[AnalysisWindow] = []
    taken: list[tuple[float, float]] = list(active_spans)
    half = BASELINE_LEN / 2.0
    for i in range(BASELINE_SAMPLES):
        centre = duration * (i + 0.5) / BASELINE_SAMPLES
        start = max(0.0, centre - half)
        end = min(duration, centre + half)
        if end <= start:
            continue
        if _overlaps_any(start, end, taken):
            continue
        rows = _slice_rows(master_df, start, end)
        if rows.empty:
            continue
        windows.append(
            AnalysisWindow(
                start=round(start, 2),
                end=round(end, 2),
                rows=rows,
                modalities_with_anomalies=set(),
                is_baseline=True,
            )
        )
        taken.append((start, end))
    return windows


def _evenly_subsample(items: list[AnalysisWindow], k: int) -> list[AnalysisWindow]:
    """Keep `k` items evenly spaced across the list (preserving order)."""
    if k <= 0:
        return []
    if len(items) <= k:
        return items
    step = len(items) / k
    return [items[int(i * step)] for i in range(k)]


def select_windows(master_df: pd.DataFrame, *, gap: float = 1.0) -> list[AnalysisWindow]:
    """Return the analysis windows for the agent chain (active + baseline).

    The orchestrator iterates over the returned windows and runs the three
    observers + Window Analyst for each. None are dropped downstream.
    """
    if master_df.empty or "Time" not in master_df.columns:
        return []

    duration = float(master_df["Time"].max())

    # 1. Active (anomaly) windows.
    merged = _merge_overlapping(_extract_ranges(master_df), gap=gap)
    active: list[AnalysisWindow] = [
        AnalysisWindow(
            start=start,
            end=end,
            rows=_slice_rows(master_df, start, end),
            modalities_with_anomalies=mods,
            is_baseline=False,
        )
        for start, end, mods in merged
    ]
    active_spans = [(w.start, w.end) for w in active]

    # 2. Baseline windows sampled from the quiet gaps.
    baseline = _sample_baseline_windows(master_df, duration, active_spans)

    # 3. Cap total (drop baseline first, then subsample active if still over).
    if len(active) + len(baseline) > MAX_WINDOWS:
        keep_baseline = max(0, MAX_WINDOWS - len(active))
        dropped = len(baseline) - keep_baseline
        baseline = _evenly_subsample(baseline, keep_baseline)
        if len(active) > MAX_WINDOWS:
            _log.warning(
                "Capping windows: %d active exceeds MAX_WINDOWS=%d — subsampling active.",
                len(active),
                MAX_WINDOWS,
            )
            active = _evenly_subsample(sorted(active, key=lambda w: w.start), MAX_WINDOWS)
            baseline = []
        elif dropped > 0:
            _log.warning(
                "Capping windows: dropped %d baseline window(s) to fit MAX_WINDOWS=%d.",
                dropped,
                MAX_WINDOWS,
            )

    # 4. Sort + assign temporal context.
    windows = sorted(active + baseline, key=lambda w: w.start)
    total = len(windows)
    for i, w in enumerate(windows):
        w.index = i
        w.total = total
        w.position_pct = round(w.start / duration, 4) if duration > 0 else 0.0
        w.phase = _phase_for(w.position_pct)

    _log.info(
        "Selected %d analysis windows (%d active, %d baseline) from %d rows",
        total,
        sum(1 for w in windows if not w.is_baseline),
        sum(1 for w in windows if w.is_baseline),
        len(master_df),
    )
    return windows


__all__ = ["MAX_WINDOWS", "AnalysisWindow", "select_windows"]
