"""Integration tests for `pipeline.features.transforms.feature_engineering`.

`feature_engineering` is the legacy ~200-line function that produces the
Pydantic-dict columns the agentic layer consumes. We exercise both modes
(training / evaluation) end-to-end on a small synthetic dataframe so its
branches are covered without needing the full pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.features.transforms import (
    compute_speaker_median_pitch,
    feature_engineering,
    get_speaker_timings,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _make_raw_df(n: int = 8, speaker: str = "B") -> pd.DataFrame:
    """Build a synthetic merged-style dataframe with every column feature_engineering reads."""
    rng = np.random.default_rng(0)
    times = [round(i * 0.5, 2) for i in range(n)]
    rows = []
    for i, t in enumerate(times):
        row = {
            "Time": t,
            "speaker": speaker if i % 4 != 0 else "A",
            # Visual blendshapes
            "eyeBlinkLeft": float(rng.uniform(0.0, 0.3)),
            "eyeBlinkRight": float(rng.uniform(0.0, 0.3)),
            "eyeSquintLeft": float(rng.uniform(0.0, 0.1)),
            "eyeSquintRight": float(rng.uniform(0.0, 0.1)),
            "eyeLookDownLeft": float(rng.uniform(0.0, 0.2)),
            "eyeLookDownRight": float(rng.uniform(0.0, 0.2)),
            "eyeLookUpLeft": float(rng.uniform(0.0, 0.2)),
            "eyeLookUpRight": float(rng.uniform(0.0, 0.2)),
            "h_ratio": 0.5 + float(rng.uniform(-0.05, 0.05)),
            "jawOpen": float(rng.uniform(0.0, 0.3)),
            "jawForward": float(rng.uniform(0.0, 0.1)),
            "jawLeft": float(rng.uniform(0.0, 0.05)),
            "jawRight": float(rng.uniform(0.0, 0.05)),
            "mouthSmileLeft": float(rng.uniform(0.0, 0.2)),
            "mouthSmileRight": float(rng.uniform(0.0, 0.2)),
            "mouthStretchLeft": float(rng.uniform(0.0, 0.1)),
            "mouthStretchRight": float(rng.uniform(0.0, 0.1)),
            "cheekSquintLeft": float(rng.uniform(0.0, 0.1)),
            "cheekSquintRight": float(rng.uniform(0.0, 0.1)),
            # Audio raw
            "audio_rms": float(rng.uniform(0.001, 0.05)),
            "audio_pitch_avg": float(rng.uniform(150.0, 250.0)),
            "audio_pitch_var": float(rng.uniform(1.0, 30.0)),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _make_rz_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Pretend the smoothing + RZ stage has already run — populate *_smooth_rz columns."""
    df = raw_df.copy()
    n = len(df)
    rng = np.random.default_rng(1)
    for col in (
        "blink_intensity_smooth_rz",
        "gaze_magnitude_smooth_rz",
        "jaw_magnitude_smooth_rz",
        "smile_intensity_smooth_rz",
        "loudness_db_smooth_rz",
        "pitch_relative_st_smooth_rz",
        "pitch_expressiveness_st_smooth_rz",
        "wps_smooth_rz",
    ):
        df[col] = rng.normal(0, 0.5, n)
    return df


def test_feature_engineering_training_produces_scalar_columns() -> None:
    """Training mode returns dataframe of scalar features for downstream smoothing."""
    raw = _make_raw_df(n=10)
    out = feature_engineering(
        c_anomalies=None,
        anomalies=None,
        df=raw,
        norm_rz_df=None,
        speaker_median_pitch=200.0,
        speaker="B",
        mode="training",
    )
    assert len(out) == 10
    expected_cols = {
        "blink_intensity",
        "gaze_magnitude",
        "jaw_magnitude",
        "smile_intensity",
        "loudness_db",
        "pitch_relative_st",
        "pitch_expressiveness_st",
    }
    assert expected_cols.issubset(out.columns)
    # Non-B rows have NaN audio metrics
    speakers = raw["speaker"].tolist()
    for i, sp in enumerate(speakers):
        if sp != "B":
            assert np.isnan(out.iloc[i]["loudness_db"])


def test_feature_engineering_evaluation_produces_pydantic_dict_columns() -> None:
    """Evaluation mode returns the per-row Pydantic-dict columns the agents consume."""
    raw = _make_raw_df(n=8)
    rz_df = _make_rz_df(raw)

    sample = json.loads((FIXTURES_DIR / "sample_anomaly_dicts.json").read_text())

    out = feature_engineering(
        c_anomalies=sample["c_anomalies"],
        anomalies=sample["anomalies"],
        df=rz_df,
        norm_rz_df=rz_df,
        speaker_median_pitch=200.0,
        speaker="B",
        mode="evaluation",
    )

    expected_cols = {
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
    }
    assert expected_cols.issubset(out.columns)
    # Speaker B rows have all audio dicts populated
    for i, sp in enumerate(rz_df["speaker"].tolist()):
        if sp == "B":
            assert isinstance(out.iloc[i]["loudness_data"], dict)
            assert "level" in out.iloc[i]["loudness_data"]
        else:
            # Non-B rows have NaN audio dicts (compatibility shape — None in master_df)
            val = out.iloc[i]["loudness_data"]
            assert (val is None) or (isinstance(val, float) and np.isnan(val))


def test_get_speaker_timings_returns_intervals_for_target_speaker() -> None:
    """Legacy helper: rebuilds (start, end) intervals from a Time-indexed
    `speaker` column. Order matters; this is fragile to NaN handling."""
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
            "speaker": ["A", "A", "B", "B", "B", "A"],
        }
    )
    intervals = get_speaker_timings(df, speaker="B")
    # B speaks from t=1.0 onward; this helper closes on each transition.
    # Expect at least one interval starting at 1.0.
    starts = [iv[0] for iv in intervals]
    assert any(s == 1.0 for s in starts)


def test_compute_speaker_median_pitch_mocked(monkeypatch) -> None:
    """Mock librosa so we don't need a real audio file. Verifies pitch
    aggregation across multiple speaker segments and the round() at the end."""
    import pipeline.features.transforms as tf

    def _fake_load(audio_path, sr):
        # 1-second of "audio" sampled at 16k
        return np.zeros(16000), 16000

    def _fake_pyin(y, fmin, fmax, sr):
        # 100 frames with f0 alternating between 200 and 220 Hz
        f0 = np.array([200.0, 220.0] * 50)
        return f0, np.ones_like(f0, dtype=bool), None

    def _fake_times_like(f0, sr):
        return np.linspace(0, 1, len(f0))

    monkeypatch.setattr(tf.librosa, "load", _fake_load)
    monkeypatch.setattr(tf.librosa, "pyin", _fake_pyin)
    monkeypatch.setattr(tf.librosa, "times_like", _fake_times_like)

    median = compute_speaker_median_pitch(
        audio_path="ignored", speaker_segments=[(0.0, 0.5), (0.5, 1.0)]
    )
    assert median == 210.0  # median of {200, 220}


def test_feature_engineering_evaluation_marks_engineered_anomalies() -> None:
    """The synthetic c_anomalies range [22.0, 22.5, 23.0, 23.5] should mark rows
    at those Times as anomalous in the loudness column."""
    raw = _make_raw_df(n=50)  # covers 0–24.5s
    rz_df = _make_rz_df(raw)
    sample = json.loads((FIXTURES_DIR / "sample_anomaly_dicts.json").read_text())

    out = feature_engineering(
        c_anomalies=sample["c_anomalies"],
        anomalies=sample["anomalies"],
        df=rz_df,
        norm_rz_df=rz_df,
        speaker_median_pitch=200.0,
        speaker="B",
        mode="evaluation",
    )

    # Find a B-speaker row at one of the engineered anomalous times (22.0, 22.5, ...)
    flagged = []
    for i, t in enumerate(rz_df["Time"]):
        if t in (22.0, 22.5, 23.0, 23.5) and rz_df.iloc[i]["speaker"] == "B":
            loud = out.iloc[i]["loudness_data"]
            if isinstance(loud, dict):
                flagged.append(loud["is_anomalous"])
    assert any(flagged), "No engineered anomalous loudness rows were flagged"
