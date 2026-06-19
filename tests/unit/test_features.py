"""Tests for `pipeline/features/` transforms (visual + audio derivations).

Covers happy-path and at least one boundary case per function. Some legacy
internals (full `feature_engineering` evaluation flow) are intentionally
exercised via the orchestrator integration in M2's structural tests rather
than micro-tested here, because their interface is dict-shaped and brittle
to small refactors.
"""

from __future__ import annotations

import math

import pytest

from pipeline.features.transforms import (
    audio_metrics_from_raw,
    blink_data,
    gaze_data,
    jaw_data,
    loudness_level,
    pitch_expressiveness_level,
    pitch_relative_level,
    smile_data,
    wps_level,
)

# ---------- blink_data ----------


def test_blink_training_returns_scalar() -> None:
    out = blink_data(
        eyeblinkleft=0.4,
        eyeblinkright=0.4,
        eyesquintleft=0.1,
        eyesquintright=0.1,
        mode="training",
    )
    assert isinstance(out, float)
    assert 0.0 <= out <= 1.0


def test_blink_evaluation_returns_dict_with_expected_keys() -> None:
    # closure = 0.8 * 0.8 + 0.0 * 0.2 = 0.64 > 0.5 ⇒ blinking
    out = blink_data(
        eyeblinkleft=0.8,
        eyeblinkright=0.8,
        eyesquintleft=0.0,
        eyesquintright=0.0,
        mode="evaluation",
    )
    assert isinstance(out, dict)
    assert set(out.keys()) == {"blinking", "asymmetry", "intensity"}
    assert out["blinking"] is True


def test_blink_threshold_boundary_below_05_returns_not_blinking() -> None:
    # closure = 0.49 → just below 0.5 threshold
    out = blink_data(
        eyeblinkleft=0.6,
        eyeblinkright=0.6,
        eyesquintleft=0.0,
        eyesquintright=0.0,
        mode="evaluation",
    )
    # 0.6*0.8 + 0.0*0.2 = 0.48 → not blinking
    assert out["blinking"] is False


def test_blink_fully_closed_eyes() -> None:
    out = blink_data(
        eyeblinkleft=1.0,
        eyeblinkright=1.0,
        eyesquintleft=1.0,
        eyesquintright=1.0,
        mode="evaluation",
    )
    assert out["intensity"] == pytest.approx(1.0)
    assert out["asymmetry"] == pytest.approx(0.0)
    assert out["blinking"] is True


# ---------- gaze_data ----------


def test_gaze_center_when_inside_dead_zone() -> None:
    out = gaze_data(
        h_ratio=0.5,
        eyelookupleft=0.0,
        eyelookupright=0.0,
        eyelookdownleft=0.0,
        eyelookdownright=0.0,
        mode="evaluation",
    )
    assert out["primary_direction"] == "center"


def test_gaze_left_when_h_ratio_low() -> None:
    out = gaze_data(
        h_ratio=0.30,
        eyelookupleft=0.0,
        eyelookupright=0.0,
        eyelookdownleft=0.0,
        eyelookdownright=0.0,
        mode="evaluation",
    )
    assert out["primary_direction"] == "left"


def test_gaze_up_takes_priority() -> None:
    out = gaze_data(
        h_ratio=0.20,  # would otherwise be "left"
        eyelookupleft=0.8,
        eyelookupright=0.8,
        eyelookdownleft=0.0,
        eyelookdownright=0.0,
        mode="evaluation",
    )
    assert out["primary_direction"] == "up"


def test_gaze_right_when_h_ratio_high() -> None:
    out = gaze_data(
        h_ratio=0.70,  # well above center+dead_zone
        eyelookupleft=0.0,
        eyelookupright=0.0,
        eyelookdownleft=0.0,
        eyelookdownright=0.0,
        mode="evaluation",
    )
    assert out["primary_direction"] == "right"


def test_gaze_down_priority() -> None:
    out = gaze_data(
        h_ratio=0.5,
        eyelookupleft=0.0,
        eyelookupright=0.0,
        eyelookdownleft=0.8,
        eyelookdownright=0.8,
        mode="evaluation",
    )
    assert out["primary_direction"] == "down"


def test_gaze_training_returns_magnitude() -> None:
    out = gaze_data(
        h_ratio=0.5,
        eyelookupleft=0.3,
        eyelookupright=0.3,
        eyelookdownleft=0.0,
        eyelookdownright=0.0,
        mode="training",
    )
    assert isinstance(out, float)
    assert out >= 0


# ---------- jaw_data ----------


def test_jaw_open_threshold() -> None:
    out_closed = jaw_data(
        jaw_open=0.2, jaw_left=0.0, jaw_right=0.0, jaw_forward=0.0, mode="evaluation"
    )
    out_open = jaw_data(
        jaw_open=0.5, jaw_left=0.0, jaw_right=0.0, jaw_forward=0.0, mode="evaluation"
    )
    assert out_closed["is_open"] is False
    assert out_open["is_open"] is True


def test_jaw_lateral_difference() -> None:
    out = jaw_data(jaw_open=0.0, jaw_left=0.0, jaw_right=0.3, jaw_forward=0.0, mode="evaluation")
    assert out["lateral"] == pytest.approx(0.3)


def test_jaw_training_returns_magnitude() -> None:
    out = jaw_data(jaw_open=0.1, jaw_left=0.05, jaw_right=0.0, jaw_forward=0.1, mode="training")
    assert isinstance(out, float)


# ---------- smile_data ----------


def test_smile_above_threshold_is_smiling() -> None:
    out = smile_data(
        mouthsmileleft=0.6,
        mouthsmileright=0.6,
        cheeksquintleft=0.2,
        cheeksquintright=0.2,
        mouthstretchleft=0.1,
        mouthstretchright=0.1,
        mode="evaluation",
    )
    assert out["is_smiling"] is True
    assert out["intensity"] > 0.3


def test_smile_neutral_face() -> None:
    out = smile_data(
        mouthsmileleft=0.0,
        mouthsmileright=0.0,
        cheeksquintleft=0.0,
        cheeksquintright=0.0,
        mouthstretchleft=0.0,
        mouthstretchright=0.0,
        mode="evaluation",
    )
    assert out["is_smiling"] is False
    assert out["intensity"] == pytest.approx(0.0)


def test_smile_training_returns_intensity() -> None:
    out = smile_data(
        mouthsmileleft=0.4,
        mouthsmileright=0.4,
        cheeksquintleft=0.1,
        cheeksquintright=0.1,
        mouthstretchleft=0.0,
        mouthstretchright=0.0,
        mode="training",
    )
    assert isinstance(out, float)


# ---------- audio_metrics_from_raw ----------


def test_audio_metrics_silence_unvoiced() -> None:
    out = audio_metrics_from_raw(audio_rms=0.0001, pitch_avg_hz=0.0, pitch_var_hz2=0.0)
    assert out["is_voiced"] is False
    assert out["pitch_relative_st"] == 0.0
    assert out["pitch_expressiveness_st"] == 0.0


def test_audio_metrics_voiced_with_baseline_pitch() -> None:
    out = audio_metrics_from_raw(
        audio_rms=0.05,
        pitch_avg_hz=200.0,
        pitch_var_hz2=100.0,
        speaker_median_pitch_hz=200.0,
    )
    assert out["is_voiced"] is True
    # exactly at baseline ⇒ 0 semitones offset
    assert out["pitch_relative_st"] == pytest.approx(0.0, abs=1e-3)
    assert out["pitch_expressiveness_st"] == pytest.approx(math.sqrt(100.0), abs=1e-3)


def test_audio_metrics_pitch_relative_one_octave_up() -> None:
    out = audio_metrics_from_raw(
        audio_rms=0.05,
        pitch_avg_hz=400.0,
        pitch_var_hz2=4.0,
        speaker_median_pitch_hz=200.0,
    )
    # one octave higher → +12 semitones
    assert out["pitch_relative_st"] == pytest.approx(12.0, abs=0.1)


def test_audio_metrics_loudness_db_grows_with_rms() -> None:
    quiet = audio_metrics_from_raw(audio_rms=0.001, pitch_avg_hz=0.0, pitch_var_hz2=0.0)
    loud = audio_metrics_from_raw(audio_rms=0.5, pitch_avg_hz=0.0, pitch_var_hz2=0.0)
    assert loud["loudness_db"] > quiet["loudness_db"]


# ---------- level helpers ----------


@pytest.mark.parametrize(
    ("rz", "expected"),
    [
        (-5.0, "very_quiet"),
        (-3.0, "quiet"),
        (0.0, "normal"),
        (2.0, "loud"),
        (5.0, "very_loud"),
    ],
)
def test_loudness_level_buckets(rz: float, expected: str) -> None:
    assert loudness_level(rz) == expected


@pytest.mark.parametrize(
    ("rz", "expected"),
    [
        (-4.0, "much_lower"),
        (-2.0, "lower"),
        (0.0, "normal"),
        (2.0, "higher"),
        (5.0, "much_higher"),
    ],
)
def test_pitch_relative_level_buckets(rz: float, expected: str) -> None:
    assert pitch_relative_level(rz) == expected


@pytest.mark.parametrize(
    ("rz", "expected"),
    [
        (-3.0, "flat"),
        (-1.0, "slightly_expressive"),
        (0.0, "expressive"),
        (3.0, "highly_expressive"),
    ],
)
def test_pitch_expressiveness_level_buckets(rz: float, expected: str) -> None:
    assert pitch_expressiveness_level(rz) == expected


@pytest.mark.parametrize(
    ("rz", "expected"),
    [(-4.0, "very_slow"), (-2.0, "slow"), (0.0, "normal"), (2.0, "fast"), (5.0, "very_fast")],
)
def test_wps_level_buckets(rz: float, expected: str) -> None:
    assert wps_level(rz) == expected
