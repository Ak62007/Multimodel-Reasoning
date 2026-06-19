"""Round-trip tests for `pipeline/schemas.py` (per-frame container models).

Every model gets at least one baseline and one anomalous instantiation, then
round-trips through `model_dump` to confirm the JSON contract is stable —
agent code and parquet IO depend on these dicts having predictable keys.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.schemas import (
    WPS,
    Blink,
    FillerPercentageIncrease,
    Gaze,
    Jaw,
    LoudnessState,
    PausePercentageIncrease,
    PitchState,
    PitchStd,
    Smile,
)

_COMMON = {
    "is_anomalous": False,
    "continuous_anomaly": False,
    "part_of_anomalous_range": None,
}


# ---------- Visual models ----------


def test_blink_baseline_round_trip() -> None:
    b = Blink(intensity=0.1, asymmetry=0.05, is_blinking=False, rz_score=0.2, **_COMMON)
    d = b.model_dump()
    assert set(d.keys()) == {
        "intensity",
        "asymmetry",
        "is_blinking",
        "rz_score",
        "is_anomalous",
        "continuous_anomaly",
        "part_of_anomalous_range",
    }
    assert Blink(**d).model_dump() == d


def test_blink_anomalous_range_round_trip() -> None:
    b = Blink(
        intensity=0.9,
        asymmetry=0.0,
        is_blinking=True,
        rz_score=3.7,
        is_anomalous=True,
        continuous_anomaly=True,
        part_of_anomalous_range=[5.0, 5.5, 6.0],
    )
    assert b.part_of_anomalous_range == [5.0, 5.5, 6.0]
    assert Blink(**b.model_dump()).part_of_anomalous_range == [5.0, 5.5, 6.0]


def test_blink_rejects_out_of_range_intensity() -> None:
    with pytest.raises(ValidationError):
        Blink(intensity=1.5, asymmetry=0.0, is_blinking=False, rz_score=0.0, **_COMMON)


def test_gaze_primary_direction_enum() -> None:
    g = Gaze(
        horizontal_deviation=0.1,
        vertical_deviation=-0.2,
        primary_direction="left",
        rz_score=0.5,
        **_COMMON,
    )
    assert g.primary_direction == "left"
    with pytest.raises(ValidationError):
        Gaze(
            horizontal_deviation=0.0,
            vertical_deviation=0.0,
            primary_direction="sideways",  # invalid
            rz_score=0.0,
            **_COMMON,
        )


def test_jaw_baseline_and_anomalous() -> None:
    j_base = Jaw(open=0.1, lateral=0.0, forward=0.0, is_open=False, rz_score=0.1, **_COMMON)
    j_anom = Jaw(
        open=0.6,
        lateral=0.3,
        forward=0.2,
        is_open=True,
        rz_score=3.0,
        is_anomalous=True,
        continuous_anomaly=True,
        part_of_anomalous_range=[10.0, 10.5],
    )
    assert not j_base.is_anomalous
    assert j_anom.is_anomalous
    assert Jaw(**j_anom.model_dump()).rz_score == 3.0


def test_smile_baseline() -> None:
    s = Smile(
        intensity=0.2,
        asymmetry=0.05,
        left_intensity=0.2,
        right_intensity=0.25,
        mouth_stretch=0.1,
        is_smiling=False,
        rz_score=0.1,
        **_COMMON,
    )
    assert Smile(**s.model_dump()) == s


# ---------- Audio paralinguistic ----------


def test_loudness_levels_round_trip() -> None:
    for lvl in ("very_quiet", "quiet", "normal", "loud", "very_loud"):
        s = LoudnessState(level=lvl, rz_score=0.0, **_COMMON)  # type: ignore[arg-type]
        assert LoudnessState(**s.model_dump()).level == lvl


def test_loudness_rejects_bad_level() -> None:
    with pytest.raises(ValidationError):
        LoudnessState(level="MEDIUM", rz_score=0.0, **_COMMON)  # type: ignore[arg-type]


def test_pitch_state_anomalous() -> None:
    p = PitchState(
        relative_level="much_higher",
        rz_score=4.1,
        is_anomalous=True,
        continuous_anomaly=False,
        part_of_anomalous_range=[12.0],
    )
    assert p.is_anomalous
    assert PitchState(**p.model_dump()) == p


def test_pitch_std_levels() -> None:
    for lvl in ("flat", "slightly_expressive", "expressive", "highly_expressive"):
        s = PitchStd(expressiveness=lvl, rz_score=0.0, **_COMMON)  # type: ignore[arg-type]
        assert PitchStd(**s.model_dump()).expressiveness == lvl


# ---------- Verbal fluency ----------


def test_wps_speaking_rate_round_trip() -> None:
    for r in ("very_slow", "slow", "normal", "fast", "very_fast"):
        w = WPS(speaking_rate=r, rz_score=0.0, **_COMMON)  # type: ignore[arg-type]
        assert WPS(**w.model_dump()).speaking_rate == r


def test_filler_percentage_increase() -> None:
    f = FillerPercentageIncrease(
        filler_percentage_level="abnormally high",
        is_anomalous=True,
        continuous_anomaly=False,
        part_of_anomalous_range=[7.5],
    )
    assert FillerPercentageIncrease(**f.model_dump()) == f
    with pytest.raises(ValidationError):
        FillerPercentageIncrease(
            filler_percentage_level="extreme",  # type: ignore[arg-type]
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )


def test_pause_percentage_increase() -> None:
    p = PausePercentageIncrease(
        pause_percentage_level="normal",
        is_anomalous=False,
        continuous_anomaly=False,
        part_of_anomalous_range=None,
    )
    assert PausePercentageIncrease(**p.model_dump()) == p
