"""Tests for ``pipeline.anomaly`` — RRCF scoring + threshold + ranges."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.anomaly.ranges import (
    adaptive_n_sigma,
    get_anomalous_time_ranges,
    get_threshold_mad,
)
from pipeline.anomaly.rrcf import MAX, MIN, get_data_ready, run_rrcf

# ---------------------------------------------------------------------------
# run_rrcf — pure-noise vs noise-with-spike
# ---------------------------------------------------------------------------


def test_run_rrcf_pure_noise_returns_finite_scores() -> None:
    """Every score must be a finite non-negative float of the right length."""
    rng = np.random.default_rng(seed=42)
    features = rng.normal(0.0, 1.0, size=(200, 1))
    scores = run_rrcf(features)
    assert len(scores) == 200
    assert all(np.isfinite(s) for s in scores)
    assert all(s >= 0 for s in scores)


def test_run_rrcf_spike_is_top_ranked() -> None:
    """A massive spike must end up in the top-decile of anomaly scores."""
    rng = np.random.default_rng(seed=7)
    features = rng.normal(0.0, 1.0, size=(200, 1))
    features[150] = 50.0
    scores = np.array(run_rrcf(features))
    # Top decile cutoff.
    cutoff = float(np.quantile(scores, 0.90))
    assert scores[150] >= cutoff


def test_run_rrcf_handles_multi_dim_features() -> None:
    rng = np.random.default_rng(seed=99)
    features = rng.normal(0.0, 1.0, size=(50, 3))
    scores = run_rrcf(features, num_trees=10, tree_size=64)
    assert len(scores) == 50


# ---------------------------------------------------------------------------
# get_data_ready — ui / ud selectors
# ---------------------------------------------------------------------------


def test_get_data_ready_ui_returns_all_rows() -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "speaker": ["A", "B", "B", "A"]})
    idx, arr = get_data_ready(df, ["a"], type="ui")
    assert len(idx) == 4
    # ffill plugged the NaN with the previous row.
    assert arr[2, 0] == 2.0


def test_get_data_ready_ud_filters_by_speaker_b() -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "speaker": ["A", "B", "B", "A"]})
    idx, arr = get_data_ready(df, ["a"], type="ud")
    assert len(idx) == 2
    assert arr.flatten().tolist() == [2.0, 3.0]


def test_get_data_ready_ud_ffills_nans() -> None:
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0, 4.0], "speaker": ["B", "B", "B", "A"]})
    _idx, arr = get_data_ready(df, ["a"], type="ud")
    assert arr[1, 0] == 1.0  # filled from the previous row


# ---------------------------------------------------------------------------
# adaptive_n_sigma — decision rules
# ---------------------------------------------------------------------------


def test_adaptive_n_sigma_normal() -> None:
    rng = np.random.default_rng(seed=0)
    n_sigma = adaptive_n_sigma(rng.normal(0.0, 1.0, size=1000))
    assert n_sigma == 2.5


def test_adaptive_n_sigma_heavy_tails() -> None:
    rng = np.random.default_rng(seed=0)
    # Mix a normal core with very heavy outliers.
    core = rng.normal(0.0, 1.0, size=800)
    outliers = rng.normal(0.0, 20.0, size=200)
    scores = np.concatenate([core, outliers])
    assert adaptive_n_sigma(scores) >= 3.5


def test_adaptive_n_sigma_right_skew() -> None:
    rng = np.random.default_rng(seed=0)
    skewed = rng.exponential(scale=1.0, size=1000)
    n_sigma = adaptive_n_sigma(skewed)
    # exponential has skew == 2 and kurtosis == 6 → falls into the
    # kurtosis-driven branch first.
    assert n_sigma >= 3.0


# ---------------------------------------------------------------------------
# get_threshold_mad
# ---------------------------------------------------------------------------


def test_get_threshold_mad_centered_distribution() -> None:
    scores = np.array([0.0] * 100 + [5.0, 6.0, 7.0])
    threshold = get_threshold_mad(scores, n_sigma=3.0)
    # median is 0, MAD is 0 → threshold = 0
    assert threshold == 0.0


def test_get_threshold_mad_scales_with_n_sigma() -> None:
    rng = np.random.default_rng(seed=0)
    scores = rng.normal(0.0, 1.0, size=1000)
    low = get_threshold_mad(scores, n_sigma=2.0)
    high = get_threshold_mad(scores, n_sigma=4.0)
    assert high > low


# ---------------------------------------------------------------------------
# get_anomalous_time_ranges — continuity logic
# ---------------------------------------------------------------------------


def test_ranges_empty_input() -> None:
    df = pd.DataFrame({"Time": []})
    assert get_anomalous_time_ranges(df) == []


def test_ranges_single_timestamp() -> None:
    df = pd.DataFrame({"Time": [5.0]})
    assert get_anomalous_time_ranges(df) == [[5.0]]


def test_ranges_continuous_window() -> None:
    df = pd.DataFrame({"Time": [5.0, 5.5, 6.0, 6.5, 7.0]})
    ranges = get_anomalous_time_ranges(df)
    assert ranges == [[5.0, 5.5, 6.0, 6.5, 7.0]]


def test_ranges_gap_too_large_splits() -> None:
    # 5.0..6.0 is one range; 30.0..31.0 is another; the 24-second gap breaks them.
    df = pd.DataFrame({"Time": [5.0, 5.5, 6.0, 30.0, 30.5, 31.0]})
    ranges = get_anomalous_time_ranges(df)
    assert ranges == [[5.0, 5.5, 6.0], [30.0, 30.5, 31.0]]


def test_ranges_singleton_in_middle_drops() -> None:
    df = pd.DataFrame({"Time": [5.0, 5.5, 6.0, 30.0, 50.0, 50.5]})
    ranges = get_anomalous_time_ranges(df)
    # 30.0 is a singleton — not emitted; 5.0..6.0 and 50.0..50.5 are emitted.
    assert ranges == [[5.0, 5.5, 6.0], [50.0, 50.5]]


def test_ranges_uses_module_constants() -> None:
    """Default min/max should be 0.5 / 2.0 from the module constants."""
    assert MIN == 0.5
    assert MAX == 2.0
