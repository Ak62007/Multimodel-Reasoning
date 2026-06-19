"""Exponentially-weighted smoothing and robust z-score normalization.

Visual features are smoothed across the entire sequence; audio paralinguistic
features are smoothed only over rows attributed to the configured speaker, so
the median/MAD baseline reflects that person's own speech rather than a mix.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


# Per-feature EWM spans tuned empirically in the legacy notebooks.
# Visual: short spans (frame rate ~1Hz) preserve micro-expressions;
# Audio:  longer spans (windows are coarse-grained 0.5s already).
VISUAL_SPANS: dict[str, int] = {
    "blink_intensity": 3,
    "gaze_magnitude": 6,
    "jaw_magnitude": 4,
    "smile_intensity": 8,
}

AUDIO_SPANS: dict[str, int] = {
    "loudness_db": 5,
    "pitch_relative_st": 8,
    "pitch_expressiveness_st": 6,
    "wps": 6,
}


def robust_zscore(series: pd.Series) -> pd.Series:
    """Robust z-score using median and 1.4826·MAD (consistent estimator)."""
    arr = series.astype(float)
    median = np.nanmedian(arr)
    mad = np.nanmedian(np.abs(arr - median))
    if mad <= 0:
        return pd.Series(np.zeros(len(arr)), index=series.index)
    return (arr - median) / (1.4826 * mad)


def smooth_and_rz_visual(df: pd.DataFrame) -> pd.DataFrame:
    """Add `<feature>_smooth` and `<feature>_smooth_rz` columns for the four
    visual features. Operates on the entire dataframe.
    """
    df = df.copy()
    for col, span in VISUAL_SPANS.items():
        if col not in df.columns:
            _log.warning("smooth_and_rz_visual: column %s missing", col)
            continue
        smooth_col = f"{col}_smooth"
        df[smooth_col] = df[col].ewm(span=span, adjust=False).mean()
        df[f"{smooth_col}_rz"] = robust_zscore(df[smooth_col])
    return df


def smooth_and_rz_audio(df: pd.DataFrame, speaker: str) -> pd.DataFrame:
    """Add `<feature>_smooth` and `<feature>_smooth_rz` for audio features,
    restricted to rows where `speaker == speaker`.
    """
    df = df.copy()
    mask = df["speaker"] == speaker
    for col, span in AUDIO_SPANS.items():
        if col not in df.columns:
            _log.warning("smooth_and_rz_audio: column %s missing", col)
            continue
        smooth_col = f"{col}_smooth"
        df[smooth_col] = np.nan
        temp = df.loc[mask, col].ewm(span=span, adjust=False).mean()
        df.loc[temp.index, smooth_col] = temp.values
        df[f"{smooth_col}_rz"] = robust_zscore(df[smooth_col])
    return df


__all__ = [
    "AUDIO_SPANS",
    "VISUAL_SPANS",
    "robust_zscore",
    "smooth_and_rz_audio",
    "smooth_and_rz_visual",
]
