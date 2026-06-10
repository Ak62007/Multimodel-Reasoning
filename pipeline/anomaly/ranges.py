"""Threshold computation and continuous anomalous-range detection."""

from __future__ import annotations

import numpy as np
import pandas as pd


def adaptive_n_sigma(anomaly_scores: np.ndarray) -> float:
    """Pick an ``n_sigma`` for MAD thresholding based on the score distribution.

    Returns a value in roughly the ``2.5 - 4.0`` range. Heavier-tailed or
    strongly-skewed distributions get a higher ``n_sigma`` so that the
    threshold lands further out in the tail.
    """
    from scipy import stats as scipy_stats

    skewness = float(scipy_stats.skew(anomaly_scores))
    kurtosis = float(scipy_stats.kurtosis(anomaly_scores))

    if kurtosis > 5:
        return 4.0
    if kurtosis > 3:
        return 3.5
    if skewness > 1.5:
        return 3.5
    if skewness > 1.0:
        return 3.0
    return 2.5


def get_threshold_mad(scores: np.ndarray | list[float], n_sigma: float = 3.0) -> float:
    """Compute a robust threshold using the median + ``n_sigma * 1.4826 * MAD``."""
    arr = np.array(scores)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    consistent_mad = 1.4826 * mad
    return median + (n_sigma * consistent_mad)


def get_anomalous_time_ranges(
    anomalies_time: pd.DataFrame,
    min: float = 0.5,  # noqa: A002 — preserves original API
    max: float = 2.0,  # noqa: A002 — preserves original API
) -> list[list[float]]:
    """Group anomalous timestamps into continuous time ranges.

    A range is defined as two or more anomalous timestamps where consecutive
    timestamps are between ``min`` and ``max`` seconds apart.

    Args:
        anomalies_time: Dataframe with a ``Time`` column of float-typed
            timestamps in seconds.
        min: Minimum gap (inclusive) between consecutive timestamps to keep
            extending an existing range.
        max: Maximum gap (inclusive) between consecutive timestamps to keep
            extending an existing range.

    Returns:
        A list of ranges; each range is a list of timestamps (floats).
    """
    if len(anomalies_time) == 0:
        return []

    def get_val(idx: int) -> float:
        val = anomalies_time.iloc[idx]["Time"]
        return val.item() if hasattr(val, "item") else float(val)

    if len(anomalies_time) == 1:
        return [[get_val(0)]]

    continuous_ranges: list[list[float]] = []
    start = get_val(0)
    current_range: list[float] = [start]

    for i in range(1, len(anomalies_time)):
        current = get_val(i)
        if min <= (current - start) <= max:
            current_range.append(current)
            start = current
            continue

        start = current
        if len(current_range) == 1:
            current_range = [current]
            continue

        continuous_ranges.append(current_range)
        current_range = [current]

    if len(current_range) > 1:
        continuous_ranges.append(current_range)

    return continuous_ranges
