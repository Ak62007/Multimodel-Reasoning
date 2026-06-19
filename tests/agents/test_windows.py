"""Unit tests for the new windowing behaviour: temporal context, baseline
sampling, and the MAX_WINDOWS cap. The anomaly-window selection itself is
covered alongside the orchestrator tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agents import windows as windows_mod
from agents.windows import MAX_WINDOWS, AnalysisWindow, select_windows
from pipeline.io.parquet import load_df_parquet_safe

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_master_df.parquet"


@pytest.fixture
def master_df() -> pd.DataFrame:
    return load_df_parquet_safe(FIXTURE)


def test_windows_carry_temporal_context(master_df: pd.DataFrame) -> None:
    ws = select_windows(master_df)
    assert ws, "expected at least the engineered anomaly windows"
    total = len(ws)
    for i, w in enumerate(ws):
        assert w.index == i
        assert w.total == total
        assert 0.0 <= w.position_pct <= 1.0
        assert w.phase in ("Opening", "Early", "Middle", "Late", "Closing")
    # Sorted chronologically and position increases with start.
    assert [w.start for w in ws] == sorted(w.start for w in ws)


def test_baseline_windows_are_sampled(master_df: pd.DataFrame) -> None:
    ws = select_windows(master_df)
    assert any(w.is_baseline for w in ws), "expected baseline windows in the quiet gaps"
    assert any(not w.is_baseline for w in ws), "expected active anomaly windows too"
    # Baseline windows carry no anomalous modalities.
    for w in ws:
        if w.is_baseline:
            assert w.modalities_with_anomalies == set()


def test_baseline_windows_do_not_overlap_active(master_df: pd.DataFrame) -> None:
    ws = select_windows(master_df)
    active = [(w.start, w.end) for w in ws if not w.is_baseline]
    for w in ws:
        if w.is_baseline:
            assert not any(w.start <= e and s <= w.end for s, e in active)


def test_phase_buckets() -> None:
    f = windows_mod._phase_for
    assert f(0.0) == "Opening"
    assert f(0.2) == "Early"
    assert f(0.5) == "Middle"
    assert f(0.8) == "Late"
    assert f(0.95) == "Closing"


def _synthetic_anomaly_df(n_ranges: int) -> pd.DataFrame:
    """Build a master_df with `n_ranges` well-separated blink anomalies."""
    rows = []
    t = 0.0
    for i in range(n_ranges):
        # each anomaly is its own isolated 0.5s blip, 5s apart → distinct windows
        center = 5.0 * (i + 1)
        for dt in (0.0, 0.5):
            tt = center + dt
            rows.append(
                {
                    "Time": tt,
                    "speaker": "B",
                    "blinking_data": {
                        "intensity": 0.9,
                        "rz_score": 3.5,
                        "is_anomalous": True,
                        "continuous_anomaly": False,
                        "part_of_anomalous_range": [center, center + 0.5],
                    },
                }
            )
        t = center
    # pad a final calm row so duration is defined
    rows.append({"Time": t + 10.0, "speaker": "B", "blinking_data": {"intensity": 0.1}})
    return pd.DataFrame(rows)


def test_max_windows_cap_truncates_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    df = _synthetic_anomaly_df(MAX_WINDOWS + 20)
    with caplog.at_level("WARNING"):
        ws = select_windows(df)
    assert len(ws) <= MAX_WINDOWS
    assert any("Capping windows" in r.message for r in caplog.records)


def test_evenly_subsample_keeps_k() -> None:
    items = [
        AnalysisWindow(start=float(i), end=float(i) + 1, rows=pd.DataFrame()) for i in range(20)
    ]
    out = windows_mod._evenly_subsample(items, 5)
    assert len(out) == 5
    assert windows_mod._evenly_subsample(items, 0) == []
    assert len(windows_mod._evenly_subsample(items[:3], 5)) == 3


def test_empty_and_degenerate_df() -> None:
    assert select_windows(pd.DataFrame()) == []
    # single row, duration 0 → no divide-by-zero, position_pct 0
    one = pd.DataFrame([{"Time": 0.0, "speaker": "B", "blinking_data": {"intensity": 0.1}}])
    ws = select_windows(one)
    assert all(w.position_pct == 0.0 for w in ws)
    _ = np  # keep import used if assertions above change
