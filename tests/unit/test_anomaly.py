"""Tests for `pipeline/anomaly/` (RRCF, MAD thresholds, range grouping,
smoothing + robust z-score).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.anomaly import (
    adaptive_n_sigma,
    get_anomalous_time_ranges,
    get_threshold_mad,
    robust_zscore,
    run_rrcf,
    smooth_and_rz_audio,
    smooth_and_rz_visual,
)

# ---------- run_rrcf ----------


def test_run_rrcf_returns_one_score_per_sample() -> None:
    rng = np.random.default_rng(0)
    features = rng.normal(0, 1, (50, 1))
    scores = run_rrcf(features, num_trees=10, tree_size=64)
    assert len(scores) == 50
    assert all(isinstance(s, float | np.floating | int | np.integer) for s in scores)


def test_run_rrcf_spike_scores_higher_than_baseline() -> None:
    """A single large outlier should land in the upper quartile of scores."""
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, 49).reshape(-1, 1)
    spike = np.array([[50.0]])
    features = np.vstack([base, spike])
    scores = np.asarray(run_rrcf(features, num_trees=20, tree_size=64))
    # The spike index (last) should have a score above the 75th percentile.
    assert scores[-1] >= np.percentile(scores, 75)


# ---------- get_threshold_mad ----------


def test_get_threshold_mad_is_above_median() -> None:
    scores = [1.0, 2.0, 3.0, 4.0, 5.0]
    thr = get_threshold_mad(scores, n_sigma=3)
    assert thr > np.median(scores)


def test_get_threshold_mad_zero_variance() -> None:
    thr = get_threshold_mad([2.0] * 10, n_sigma=3)
    # MAD == 0 ⇒ threshold collapses to the median
    assert thr == pytest.approx(2.0)


# ---------- adaptive_n_sigma ----------


def test_adaptive_n_sigma_normal_distribution() -> None:
    rng = np.random.default_rng(0)
    scores = rng.normal(0, 1, 1000)
    n = adaptive_n_sigma(scores)
    assert 2.0 <= n <= 4.5


def test_adaptive_n_sigma_heavy_tail_picks_larger_value() -> None:
    rng = np.random.default_rng(1)
    scores = rng.standard_t(df=2, size=1000)  # heavy tails
    n_heavy = adaptive_n_sigma(scores)
    normal = rng.normal(0, 1, 1000)
    n_normal = adaptive_n_sigma(normal)
    assert n_heavy >= n_normal


# ---------- get_anomalous_time_ranges ----------


def test_get_anomalous_time_ranges_empty() -> None:
    assert get_anomalous_time_ranges(pd.DataFrame(columns=["Time"])) == []


def test_get_anomalous_time_ranges_single_point() -> None:
    df = pd.DataFrame({"Time": [3.5]})
    # singletons collapse to a single-element list
    assert get_anomalous_time_ranges(df) == [[3.5]]


def test_get_anomalous_time_ranges_groups_consecutive() -> None:
    df = pd.DataFrame({"Time": [0.5, 1.0, 1.5, 4.0, 4.5]})
    out = get_anomalous_time_ranges(df, min=0.5, max=2.0)
    assert len(out) == 2
    assert all(len(r) >= 2 for r in out)


def test_get_anomalous_time_ranges_drops_isolated_singletons() -> None:
    # 10.0 sits ~5s away from 5.0; the gap is outside [0.5, 2.0] so it shouldn't
    # extend the cluster, and a lonely singleton at 10.0 should be dropped.
    df = pd.DataFrame({"Time": [5.0, 5.5, 6.0, 10.0]})
    out = get_anomalous_time_ranges(df, min=0.5, max=2.0)
    # One range containing [5.0, 5.5, 6.0]; the isolated 10.0 doesn't form a range
    assert len(out) == 1
    assert out[0] == [5.0, 5.5, 6.0]


# ---------- robust_zscore + smoothing ----------


def test_robust_zscore_zero_for_constant_series() -> None:
    out = robust_zscore(pd.Series([7.0] * 10))
    assert (out == 0.0).all()


def test_robust_zscore_symmetric_around_median() -> None:
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    out = robust_zscore(s)
    # median = 3 ⇒ z(3) = 0
    assert out.iloc[2] == pytest.approx(0.0)


def test_smooth_and_rz_visual_creates_expected_columns() -> None:
    df = pd.DataFrame(
        {
            "blink_intensity": np.linspace(0, 1, 20),
            "gaze_magnitude": np.linspace(0, 2, 20),
            "jaw_magnitude": np.linspace(0, 3, 20),
            "smile_intensity": np.linspace(0, 0.5, 20),
        }
    )
    out = smooth_and_rz_visual(df)
    for c in ("blink_intensity", "gaze_magnitude", "jaw_magnitude", "smile_intensity"):
        assert f"{c}_smooth" in out.columns
        assert f"{c}_smooth_rz" in out.columns


def test_smooth_and_rz_visual_handles_missing_column() -> None:
    # The function should not raise when an expected column is missing — it
    # warns and continues. This protects the orchestrator against feature
    # extraction failures upstream.
    df = pd.DataFrame({"blink_intensity": [0.1, 0.2, 0.3]})
    out = smooth_and_rz_visual(df)
    assert "blink_intensity_smooth" in out.columns
    assert "gaze_magnitude_smooth" not in out.columns


def test_smooth_and_rz_audio_only_smooths_target_speaker() -> None:
    df = pd.DataFrame(
        {
            "speaker": ["A"] * 5 + ["B"] * 15,
            "loudness_db": np.linspace(-30, -10, 20),
            "pitch_relative_st": np.linspace(-1, 1, 20),
            "pitch_expressiveness_st": np.linspace(0, 5, 20),
            "wps": np.linspace(0, 4, 20),
        }
    )
    out = smooth_and_rz_audio(df, speaker="B")
    # Speaker A rows should have NaN smoothed values (mask excluded them)
    assert out.loc[0, "loudness_db_smooth"] != out.loc[0, "loudness_db_smooth"]  # NaN
    assert not np.isnan(out.loc[10, "loudness_db_smooth"])
