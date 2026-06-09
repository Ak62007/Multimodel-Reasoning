"""Cover the smaller helpers in `pipeline.anomaly.rrcf`: `get_data_ready`
branches and the boundary cases of `adaptive_n_sigma`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.anomaly.rrcf import adaptive_n_sigma, get_data_ready


def test_get_data_ready_ui_returns_index_and_values() -> None:
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, np.nan, 5.0]})
    idx, arr = get_data_ready(df, ["x"], type="ui")
    assert len(idx) == 5
    # ffill replaces the NaN
    assert arr.shape == (5, 1)
    assert not np.isnan(arr).any()


def test_get_data_ready_ud_handles_nan_with_ffill() -> None:
    df = pd.DataFrame(
        {
            "speaker": ["A", "B", "B", "B"],
            "y": [10.0, 1.0, np.nan, 3.0],
        }
    )
    idx, arr = get_data_ready(df, ["y"], type="ud")
    # only B rows, NaN ffilled
    assert arr.shape[0] == 3
    assert not np.isnan(arr).any()
    assert list(idx) == [1, 2, 3]


def test_get_data_ready_ud_no_nan_skips_ffill() -> None:
    df = pd.DataFrame(
        {
            "speaker": ["B", "B", "B"],
            "y": [1.0, 2.0, 3.0],
        }
    )
    idx, arr = get_data_ready(df, ["y"], type="ud")
    assert arr.shape == (3, 1)
    assert list(idx) == [0, 1, 2]


def test_adaptive_n_sigma_skewed_distribution() -> None:
    rng = np.random.default_rng(0)
    # exponential is right-skewed
    scores = rng.exponential(scale=1.0, size=1000)
    n = adaptive_n_sigma(scores)
    assert 2.5 <= n <= 4.5


def test_adaptive_n_sigma_extreme_kurtosis() -> None:
    # Mix a tight normal with a few extreme outliers → very heavy tails
    rng = np.random.default_rng(0)
    scores = np.concatenate([rng.normal(0, 1, 1000), np.array([50.0, -50.0, 60.0, -60.0])])
    n = adaptive_n_sigma(scores)
    assert n == 4.0  # the "heavy tails" branch
