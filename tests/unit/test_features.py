"""Tests for ``pipeline.features.{transforms,smoothing,linguistic}``."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pipeline.features.linguistic import compute_linguistic_features
from pipeline.features.smoothing import (
    AUDIO_SPANS,
    VISUAL_SPANS,
    apply_smoothing_rz,
    robust_zscore,
)
from pipeline.features.transforms import (
    audio_metrics_from_raw,
    blink_data,
    blink_intensity_only,
    compute_raw_features,
    feature_engineering,
    gaze_data,
    gaze_magnitude_only,
    get_speaker_timings,
    jaw_data,
    jaw_magnitude_only,
    loudness_level,
    pitch_expressiveness_level,
    pitch_relative_level,
    smile_data,
    smile_intensity_only,
    wps_level,
)

# ---------------------------------------------------------------------------
# Per-row transforms
# ---------------------------------------------------------------------------


class TestBlink:
    def test_low_intensity(self) -> None:
        d = blink_data(0.05, 0.05, 0.0, 0.0)
        assert d["is_blinking"] is False
        assert d["intensity"] < 0.5

    def test_fully_closed_eye(self) -> None:
        d = blink_data(1.0, 1.0, 0.5, 0.5)
        assert d["is_blinking"] is True
        assert math.isclose(float(d["intensity"]), 0.9)
        assert d["asymmetry"] == 0.0

    def test_asymmetric_blink(self) -> None:
        d = blink_data(1.0, 0.0, 0.0, 0.0)
        assert float(d["asymmetry"]) > 0.5

    def test_intensity_only_helper_matches_full(self) -> None:
        full = blink_data(0.4, 0.4, 0.1, 0.1)
        intensity = blink_intensity_only(0.4, 0.4, 0.1, 0.1)
        assert math.isclose(float(full["intensity"]), intensity)


class TestGaze:
    def test_center(self) -> None:
        d = gaze_data(
            h_ratio=0.5,
            eye_look_up_left=0.0,
            eye_look_up_right=0.0,
            eye_look_down_left=0.0,
            eye_look_down_right=0.0,
        )
        assert d["primary_direction"] == "center"

    def test_looking_up(self) -> None:
        d = gaze_data(
            h_ratio=0.5,
            eye_look_up_left=0.5,
            eye_look_up_right=0.5,
            eye_look_down_left=0.0,
            eye_look_down_right=0.0,
        )
        assert d["primary_direction"] == "up"

    def test_looking_down(self) -> None:
        d = gaze_data(
            h_ratio=0.5,
            eye_look_up_left=0.0,
            eye_look_up_right=0.0,
            eye_look_down_left=0.5,
            eye_look_down_right=0.5,
        )
        assert d["primary_direction"] == "down"

    def test_looking_left(self) -> None:
        d = gaze_data(
            h_ratio=0.3,
            eye_look_up_left=0.0,
            eye_look_up_right=0.0,
            eye_look_down_left=0.0,
            eye_look_down_right=0.0,
        )
        assert d["primary_direction"] == "left"

    def test_looking_right(self) -> None:
        d = gaze_data(
            h_ratio=0.7,
            eye_look_up_left=0.0,
            eye_look_up_right=0.0,
            eye_look_down_left=0.0,
            eye_look_down_right=0.0,
        )
        assert d["primary_direction"] == "right"

    def test_magnitude_increases_with_look(self) -> None:
        baseline = gaze_magnitude_only(0.5, 0.0, 0.0, 0.0, 0.0)
        looking = gaze_magnitude_only(0.5, 0.6, 0.6, 0.0, 0.0)
        assert looking > baseline


class TestJaw:
    def test_open_jaw(self) -> None:
        d = jaw_data(jaw_open=0.5, jaw_left=0.0, jaw_right=0.0, jaw_forward=0.0)
        assert d["is_open"] is True

    def test_closed_jaw(self) -> None:
        d = jaw_data(jaw_open=0.1, jaw_left=0.0, jaw_right=0.0, jaw_forward=0.0)
        assert d["is_open"] is False

    def test_lateral_movement(self) -> None:
        d = jaw_data(jaw_open=0.0, jaw_left=0.1, jaw_right=0.3, jaw_forward=0.0)
        assert math.isclose(float(d["lateral"]), 0.2)

    def test_magnitude_combines_components(self) -> None:
        mag = jaw_magnitude_only(jaw_open=0.4, jaw_left=0.1, jaw_right=0.2, jaw_forward=0.05)
        # jaw_open + |jaw_right - jaw_left| + jaw_forward = 0.4 + 0.1 + 0.05 = 0.55
        assert math.isclose(mag, 0.55)


class TestSmile:
    def test_neutral(self) -> None:
        d = smile_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert d["is_smiling"] is False
        assert d["intensity"] == 0.0

    def test_smiling(self) -> None:
        d = smile_data(0.7, 0.7, 0.2, 0.2, 0.1, 0.1)
        assert d["is_smiling"] is True

    def test_asymmetric(self) -> None:
        d = smile_data(0.8, 0.2, 0.0, 0.0, 0.0, 0.0)
        assert float(d["asymmetry"]) > 0.4

    def test_intensity_only_helper_matches_full(self) -> None:
        full = smile_data(0.4, 0.4, 0.1, 0.1, 0.05, 0.05)
        intensity = smile_intensity_only(0.4, 0.4, 0.1, 0.1)
        assert math.isclose(float(full["intensity"]), intensity)


# ---------------------------------------------------------------------------
# audio_metrics_from_raw boundaries
# ---------------------------------------------------------------------------


class TestAudioMetrics:
    def test_silence_yields_negative_loudness(self) -> None:
        m = audio_metrics_from_raw(audio_rms=0.0, pitch_avg_hz=0.0, pitch_var_hz2=0.0)
        assert m["is_voiced"] is False
        assert float(m["loudness_db"]) < -100  # near-silence is way below 0 dB
        assert float(m["pitch_relative_st"]) == 0.0
        assert float(m["pitch_expressiveness_st"]) == 0.0

    def test_voiced_uses_speaker_median(self) -> None:
        m = audio_metrics_from_raw(
            audio_rms=0.1,
            pitch_avg_hz=200.0,
            pitch_var_hz2=25.0,
            speaker_median_pitch_hz=160.0,
        )
        # 12*log2(200/160) ≈ 3.86 semitones above the speaker median
        assert m["is_voiced"] is True
        assert math.isclose(float(m["pitch_relative_st"]), 3.86, abs_tol=0.05)
        # sqrt(25) = 5 semitones of expressiveness
        assert math.isclose(float(m["pitch_expressiveness_st"]), 5.0, abs_tol=0.01)

    def test_voiced_without_speaker_median(self) -> None:
        m = audio_metrics_from_raw(
            audio_rms=0.1,
            pitch_avg_hz=180.0,
            pitch_var_hz2=4.0,
            speaker_median_pitch_hz=None,
        )
        assert m["is_voiced"] is True
        assert float(m["pitch_relative_st"]) == 0.0

    def test_voiced_with_zero_median(self) -> None:
        m = audio_metrics_from_raw(
            audio_rms=0.1,
            pitch_avg_hz=180.0,
            pitch_var_hz2=4.0,
            speaker_median_pitch_hz=0.0,
        )
        assert float(m["pitch_relative_st"]) == 0.0


# ---------------------------------------------------------------------------
# Categorical level helpers
# ---------------------------------------------------------------------------


class TestLevels:
    @pytest.mark.parametrize(
        ("rz", "expected"),
        [
            (-5.0, "very_quiet"),
            (-3.0, "quiet"),
            (0.5, "normal"),
            (3.0, "loud"),
            (5.0, "very_loud"),
        ],
    )
    def test_loudness_level(self, rz: float, expected: str) -> None:
        assert loudness_level(rz) == expected

    @pytest.mark.parametrize(
        ("rz", "expected"),
        [
            (-4.0, "much_lower"),
            (-2.0, "lower"),
            (0.0, "normal"),
            (2.0, "higher"),
            (4.0, "much_higher"),
        ],
    )
    def test_pitch_relative_level(self, rz: float, expected: str) -> None:
        assert pitch_relative_level(rz) == expected

    @pytest.mark.parametrize(
        ("rz", "expected"),
        [
            (-3.0, "flat"),
            (-1.0, "slightly_expressive"),
            (1.0, "expressive"),
            (3.0, "highly_expressive"),
        ],
    )
    def test_pitch_expressiveness_level(self, rz: float, expected: str) -> None:
        assert pitch_expressiveness_level(rz) == expected

    @pytest.mark.parametrize(
        ("rz", "expected"),
        [
            (-4.0, "very_slow"),
            (-2.0, "slow"),
            (0.0, "normal"),
            (2.0, "fast"),
            (4.0, "very_fast"),
        ],
    )
    def test_wps_level(self, rz: float, expected: str) -> None:
        assert wps_level(rz) == expected


# ---------------------------------------------------------------------------
# get_speaker_timings
# ---------------------------------------------------------------------------


def test_get_speaker_timings_returns_intervals() -> None:
    df = pd.DataFrame({"Time": [0.0, 1.0, 2.0, 3.0, 4.0], "speaker": ["A", "A", "B", "B", "A"]})
    timings = get_speaker_timings(df, speaker="B")
    assert timings == [(2.0, 4.0)]


def test_get_speaker_timings_no_speaker_returns_empty() -> None:
    df = pd.DataFrame({"Time": [0.0, 1.0], "speaker": [None, None]})
    assert get_speaker_timings(df, speaker="B") == []


# ---------------------------------------------------------------------------
# Linguistic features
# ---------------------------------------------------------------------------


def _build_merged_for_linguistic() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            "speaker": ["B"] * 7,
            "words": [
                ["hi"],
                ["there"],
                ["[*]"],  # filler
                [],  # pause
                ["thanks"],
                [],  # pause
                ["[*]"],  # filler
            ],
            "text_concat": ["hi", "there", "[*]", "", "thanks", "", "[*]"],
        }
    )


def test_compute_linguistic_features_adds_three_columns() -> None:
    merged = _build_merged_for_linguistic()
    out = compute_linguistic_features(merged, speaker="B")
    for col in ("wps", "filler_percentage", "pause_percent_pr"):
        assert col in out.columns


def test_wps_excludes_filler_token() -> None:
    merged = _build_merged_for_linguistic()
    out = compute_linguistic_features(merged, speaker="B")
    # "[*]" rows produce wps == 0; "hi"/"there"/"thanks" produce wps == 2.0
    assert math.isclose(out.loc[2, "wps"], 0.0)
    assert math.isclose(out.loc[0, "wps"], 2.0)


def test_filler_percentage_increases() -> None:
    merged = _build_merged_for_linguistic()
    out = compute_linguistic_features(merged, speaker="B")
    # Cumulative — should be non-decreasing along speaker rows.
    series = out["filler_percentage"].to_numpy()
    assert all(
        series[i] <= series[i + 1] or math.isclose(series[i], series[i + 1])
        for i in range(len(series) - 1)
    )


def test_pause_percentage_increases_at_pause_rows() -> None:
    merged = _build_merged_for_linguistic()
    out = compute_linguistic_features(merged, speaker="B")
    series = out["pause_percent_pr"].to_numpy()
    assert series[-1] > series[0]


def test_compute_linguistic_features_handles_empty_dataframe() -> None:
    """Empty dataframe must produce empty linguistic columns without crashing."""
    df = pd.DataFrame({"Time": [], "speaker": [], "words": [], "text_concat": []})
    out = compute_linguistic_features(df, speaker="B")
    assert out.empty


def test_compute_linguistic_features_handles_zero_total_duration() -> None:
    """``Time`` of all-zero must not divide by zero."""
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.0, 0.0],
            "speaker": ["B", "B", "B"],
            "words": [[], [], []],
            "text_concat": ["", "", ""],
        }
    )
    out = compute_linguistic_features(df, speaker="B")
    assert (out["pause_percent_pr"] == 0.0).all()


def test_wps_treats_non_list_words_as_zero() -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "speaker": ["B", "B", "B"],
            "words": [["hi"], None, ["[*]"]],
            "text_concat": ["hi", "", "[*]"],
        }
    )
    out = compute_linguistic_features(df, speaker="B")
    assert out.loc[1, "wps"] == 0.0


def test_compute_linguistic_features_handles_zero_total_words() -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "speaker": ["A", "A", "A"],
            "words": [[], [], []],
            "text_concat": ["", "", ""],
        }
    )
    out = compute_linguistic_features(df, speaker="B")
    assert (out["filler_percentage"] == 0.0).all()


# ---------------------------------------------------------------------------
# Smoothing + robust-z
# ---------------------------------------------------------------------------


def test_robust_zscore_handles_zero_mad() -> None:
    series = pd.Series([1.0, 1.0, 1.0, 1.0])
    out = robust_zscore(series)
    assert (out == 0.0).all()


def test_robust_zscore_centers_at_median() -> None:
    rng = np.random.default_rng(seed=0)
    arr = rng.normal(0.0, 1.0, size=1000)
    series = pd.Series(arr)
    rz = robust_zscore(series)
    # The median of the rz-transformed series should be ~0.
    assert abs(float(rz.median())) < 0.05


def test_apply_smoothing_rz_emits_all_features() -> None:
    rng = np.random.default_rng(seed=0)
    n = 40
    df = pd.DataFrame(
        {
            "Time": np.arange(0.0, n * 0.5, 0.5),
            "speaker": ["B"] * n,
            "blink_intensity": rng.uniform(0.0, 0.3, size=n),
            "gaze_magnitude": rng.uniform(0.0, 0.5, size=n),
            "jaw_magnitude": rng.uniform(0.0, 0.4, size=n),
            "smile_intensity": rng.uniform(0.0, 0.3, size=n),
            "loudness_db": rng.uniform(-30.0, -10.0, size=n),
            "pitch_relative_st": rng.normal(0.0, 1.5, size=n),
            "pitch_expressiveness_st": rng.uniform(0.0, 10.0, size=n),
            "wps": rng.uniform(0.0, 4.0, size=n),
        }
    )
    out = apply_smoothing_rz(df, speaker="B")
    for feature in list(VISUAL_SPANS) + list(AUDIO_SPANS):
        assert f"{feature}_smooth_rz" in out.columns


def test_apply_smoothing_rz_skips_missing_column(caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "speaker": ["B"] * 3,
            "blink_intensity": [0.1, 0.2, 0.3],
            # only one feature present — every other column should be skipped
        }
    )
    with caplog.at_level("WARNING"):
        out = apply_smoothing_rz(df, speaker="B")
    assert "blink_intensity_smooth_rz" in out.columns
    assert any("Missing" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# compute_raw_features end-to-end
# ---------------------------------------------------------------------------


def _build_minimal_merged(n: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(seed=0)
    blendshape_cols = {
        c: rng.uniform(0.0, 0.3, size=n)
        for c in [
            "eyeBlinkLeft",
            "eyeBlinkRight",
            "eyeSquintLeft",
            "eyeSquintRight",
            "eyeLookUpLeft",
            "eyeLookUpRight",
            "eyeLookDownLeft",
            "eyeLookDownRight",
            "jawOpen",
            "jawLeft",
            "jawRight",
            "jawForward",
            "mouthSmileLeft",
            "mouthSmileRight",
            "cheekSquintLeft",
            "cheekSquintRight",
            "mouthStretchLeft",
            "mouthStretchRight",
        ]
    }
    return pd.DataFrame(
        {
            "Time": np.arange(0.0, n * 0.5, 0.5),
            "h_ratio": np.full(n, 0.5),
            "audio_rms": np.full(n, 0.1),
            "audio_pitch_avg": np.full(n, 180.0),
            "audio_pitch_var": np.full(n, 9.0),
            "is_silent": [False] * n,
            "speaker": ["B"] * n,
            "words": [[]] * n,
            "text_concat": [""] * n,
            "wps": np.zeros(n),
            "filler_percentage": np.zeros(n),
            "pause_percent_pr": np.zeros(n),
            **blendshape_cols,
        }
    )


def test_compute_raw_features_produces_expected_columns() -> None:
    merged = _build_minimal_merged()
    raw = compute_raw_features(merged, speaker_median_pitch=160.0, speaker="B")
    for col in (
        "Time",
        "blink_intensity",
        "gaze_magnitude",
        "jaw_magnitude",
        "smile_intensity",
        "loudness_db",
        "pitch_relative_st",
        "pitch_expressiveness_st",
    ):
        assert col in raw.columns
    assert len(raw) == len(merged)


def test_compute_raw_features_nans_audio_for_other_speaker() -> None:
    merged = _build_minimal_merged()
    merged["speaker"] = ["A"] * len(merged)
    raw = compute_raw_features(merged, speaker_median_pitch=160.0, speaker="B")
    assert raw["loudness_db"].isna().all()
    assert raw["pitch_relative_st"].isna().all()


# ---------------------------------------------------------------------------
# feature_engineering full pass
# ---------------------------------------------------------------------------


def test_feature_engineering_builds_master_cells() -> None:
    merged = _build_minimal_merged(n=10)
    raw = compute_raw_features(merged, speaker_median_pitch=160.0, speaker="B")
    smoothed = apply_smoothing_rz(raw, speaker="B")
    empty_anom: dict[str, list[float]] = {}
    empty_c_anom: dict[str, list[list[float]]] = {}
    master = feature_engineering(
        merged=merged,
        smoothed_rz=smoothed,
        anomalies=empty_anom,
        c_anomalies=empty_c_anom,
        speaker="B",
    )
    assert "blinking_data" in master.columns
    assert isinstance(master.loc[0, "blinking_data"], dict)
    assert isinstance(master.loc[0, "loudness_data"], dict)


def test_feature_engineering_marks_anomalous_row() -> None:
    merged = _build_minimal_merged(n=8)
    raw = compute_raw_features(merged, speaker_median_pitch=160.0, speaker="B")
    smoothed = apply_smoothing_rz(raw, speaker="B")
    anomalies = {"blink_intensity_smooth_rz": [1.5]}
    c_anomalies = {"blink_intensity_smooth_rz": [[1.0, 1.5, 2.0]]}
    master = feature_engineering(
        merged=merged,
        smoothed_rz=smoothed,
        anomalies=anomalies,
        c_anomalies=c_anomalies,
        speaker="B",
    )
    flagged = master.loc[master["Time"] == 1.5, "blinking_data"].iloc[0]
    assert flagged["is_anomalous"] is True
    assert flagged["continuous_anomaly"] is True
    assert flagged["part_of_anomalous_range"] == [1.0, 1.5, 2.0]


def test_feature_engineering_other_speaker_gets_nan_audio() -> None:
    merged = _build_minimal_merged(n=6)
    merged["speaker"] = ["A"] * len(merged)
    raw = compute_raw_features(merged, speaker_median_pitch=160.0, speaker="B")
    smoothed = apply_smoothing_rz(raw, speaker="B")
    master = feature_engineering(
        merged=merged,
        smoothed_rz=smoothed,
        anomalies={},
        c_anomalies={},
        speaker="B",
    )
    assert master["loudness_data"].isna().all()
    assert master["words_per_sec"].isna().all()
