"""Extract per-modality anomaly events + transcript slice from one window.

Used by the agent runners to build the structured input for each observer.
Keeps the per-agent files thin and lets us unit-test the extraction logic
without touching pydantic-ai.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from agents.schemas import (
    AudioAnomalyEvent,
    VisualAnomalyEvent,
    VocabularyAnomalyEvent,
)

# Map master_df column → (event-feature label, event class).
_VISUAL_COLUMNS = {
    "blinking_data": ("Blink", VisualAnomalyEvent),
    "gaze_data": ("Gaze", VisualAnomalyEvent),
    "jaw_movement_data": ("Jaw", VisualAnomalyEvent),
    "smile_data": ("Smile", VisualAnomalyEvent),
}
_AUDIO_COLUMNS = {
    "loudness_data": ("Loudness", AudioAnomalyEvent),
    "average_pitch_data": ("Pitch", AudioAnomalyEvent),
    "pitch_standard_deviation": ("Expressiveness", AudioAnomalyEvent),
}
_VERBAL_COLUMNS = {
    "words_per_sec": ("SpeakingRate", VocabularyAnomalyEvent),
    "filler_words_usage": ("FillerUsage", VocabularyAnomalyEvent),
    "pauses_taken": ("Pauses", VocabularyAnomalyEvent),
}


def _events_from(
    rows: pd.DataFrame, column_map: Mapping[str, tuple[str, type]], default_tag: str
) -> list:
    """Walk one anomaly-column family and emit one event per anomalous range cluster."""
    out: list[Any] = []
    for col, (feature_label, klass) in column_map.items():
        if col not in rows.columns:
            continue
        anom_rows = []
        for _, cell in rows[col].items():
            if not isinstance(cell, dict):
                continue
            if not cell.get("is_anomalous"):
                continue
            anom_rows.append(cell)
        if not anom_rows:
            continue
        # One event per column, using min/max rz_score across the window.
        rz_scores = [abs(c.get("rz_score", 0.0)) for c in anom_rows]
        starts = [
            min(c["part_of_anomalous_range"]) for c in anom_rows if c.get("part_of_anomalous_range")
        ]
        ends = [
            max(c["part_of_anomalous_range"]) for c in anom_rows if c.get("part_of_anomalous_range")
        ]
        if not starts or not ends:
            continue
        sustained = any(c.get("continuous_anomaly") for c in anom_rows)
        out.append(
            klass(
                timestamp_start=float(min(starts)),
                timestamp_end=float(max(ends)),
                feature_type=feature_label,
                behavioral_tag=default_tag,
                intensity_score=float(max(rz_scores)) if rz_scores else 0.0,
                is_sustained=bool(sustained),
            )
        )
    return out


def extract_visual_events(rows: pd.DataFrame) -> list[VisualAnomalyEvent]:
    return _events_from(rows, _VISUAL_COLUMNS, default_tag="Visual anomaly")


def extract_audio_events(rows: pd.DataFrame) -> list[AudioAnomalyEvent]:
    return _events_from(rows, _AUDIO_COLUMNS, default_tag="Audio anomaly")


def extract_vocab_events(rows: pd.DataFrame) -> list[VocabularyAnomalyEvent]:
    return _events_from(rows, _VERBAL_COLUMNS, default_tag="Verbal anomaly")


def extract_transcript_slice(
    transcript_df: pd.DataFrame | None,
    start: float,
    end: float,
    *,
    speaker_label: str | None = None,
) -> str:
    """Return concatenated transcript text within `[start, end]` seconds.

    `transcript_df` is the AssemblyAI utterances dataframe (start/end in seconds).
    If `speaker_label` is given, only utterances by that speaker are included.
    Returns "" when no transcript is available — observers cope gracefully.
    """
    if transcript_df is None or transcript_df.empty:
        return ""
    df = transcript_df
    mask = (df["end"] >= start) & (df["start"] <= end)
    if speaker_label is not None and "speaker" in df.columns:
        mask &= df["speaker"] == speaker_label
    selected = df.loc[mask]
    if selected.empty:
        return ""
    return " ".join(str(t) for t in selected["text"].tolist())


__all__ = [
    "extract_audio_events",
    "extract_transcript_slice",
    "extract_visual_events",
    "extract_vocab_events",
]
