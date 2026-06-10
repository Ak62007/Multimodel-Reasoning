"""EWM smoothing + robust-z-score normalisation.

This step takes the raw derived features (``blink_intensity``,
``gaze_magnitude``, ``jaw_magnitude``, ``smile_intensity``,
``loudness_db``, ``pitch_relative_st``, ``pitch_expressiveness_st``,
``wps``) and produces a matching ``*_smooth_rz`` column per feature.

Smoothing
    Exponentially-weighted moving average. The per-feature ``span`` values
    were tuned in ``legacy_notebooks/feature_engineering.ipynb`` and are
    preserved verbatim.

Robust-z-score
    ``(x - median) / (1.4826 * MAD)`` where ``MAD`` is the median absolute
    deviation. Returns 0 when ``MAD == 0`` to avoid div-by-zero.

Visual features are normalised over the entire series. Audio + verbal
features are normalised only over the target speaker's rows (audio metrics
are NaN for the other speaker, which would skew the median).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# EWM span (in samples) per feature — preserved from
# legacy_notebooks/feature_engineering.ipynb.
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
    """``(series - median) / (1.4826 * MAD)``; ``0`` when ``MAD == 0``."""
    arr = series.to_numpy(dtype=float)
    median = float(np.nanmedian(arr))
    mad = float(np.nanmedian(np.abs(arr - median)))
    if mad == 0 or np.isnan(mad):
        return pd.Series(np.zeros_like(arr), index=series.index)
    return pd.Series((arr - median) / (1.4826 * mad), index=series.index)


def apply_smoothing_rz(
    df: pd.DataFrame,
    speaker: str = "B",
) -> pd.DataFrame:
    """Add the eight ``*_smooth_rz`` columns expected by anomaly detection.

    Args:
        df: Dataframe containing the raw derived features.
        speaker: Speaker label whose rows define the audio/verbal baseline.

    Returns:
        A copy of ``df`` with the new columns appended.
    """
    out = df.copy()

    for feature, span in VISUAL_SPANS.items():
        if feature not in out.columns:
            logger.warning("Missing visual feature column %s — skipping", feature)
            continue
        smoothed = out[feature].ewm(span=span, adjust=False).mean()
        out[f"{feature}_smooth_rz"] = robust_zscore(smoothed)

    mask = out["speaker"] == speaker
    for feature, span in AUDIO_SPANS.items():
        if feature not in out.columns:
            logger.warning("Missing audio/verbal feature column %s — skipping", feature)
            continue
        rz = pd.Series(np.nan, index=out.index, dtype=float)
        if mask.any():
            smoothed = out.loc[mask, feature].ewm(span=span, adjust=False).mean()
            rz.loc[mask] = robust_zscore(smoothed).values
        out[f"{feature}_smooth_rz"] = rz

    logger.info(
        "Applied smoothing + robust-z to %d feature columns", len(VISUAL_SPANS) + len(AUDIO_SPANS)
    )
    return out
