"""Unit tests for ``pipeline.schemas`` and ``agents.schemas``.

Every Pydantic model is instantiated with a realistic payload, validated
where field constraints exist, and round-tripped through
``model_dump`` / ``model_validate``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.schemas import (
    AudioAnomalyEvent,
    AudioObservation,
    CrossModalInsight,
    FinalReport,
    IntegratedBehavioralReport,
    VisualAnomalyEvent,
    VisualObservation,
    VocabAnomalyEvent,
    VocabObservation,
)
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

# ---------------------------------------------------------------------------
# pipeline.schemas
# ---------------------------------------------------------------------------


class TestBlink:
    def test_happy_path(self) -> None:
        b = Blink(
            intensity=0.4,
            asymmetry=0.05,
            is_blinking=False,
            rz_score=-0.3,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert 0.0 <= b.intensity <= 1.0
        assert not b.is_blinking

    def test_round_trip(self) -> None:
        b = Blink(
            intensity=0.6,
            asymmetry=0.2,
            is_blinking=True,
            rz_score=3.1,
            is_anomalous=True,
            continuous_anomaly=True,
            part_of_anomalous_range=[5.0, 5.5, 6.0],
        )
        dumped = b.model_dump()
        assert Blink.model_validate(dumped) == b

    def test_intensity_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            Blink(
                intensity=1.5,
                asymmetry=0.0,
                is_blinking=False,
                rz_score=0.0,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )


class TestGaze:
    def test_each_direction(self) -> None:
        for direction in ("center", "left", "right", "up", "down"):
            g = Gaze(
                horizontal_deviation=0.0,
                vertical_deviation=0.0,
                primary_direction=direction,  # type: ignore[arg-type]
                rz_score=0.0,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            assert g.primary_direction == direction

    def test_invalid_direction(self) -> None:
        with pytest.raises(ValidationError):
            Gaze(
                horizontal_deviation=0.0,
                vertical_deviation=0.0,
                primary_direction="diagonal",  # type: ignore[arg-type]
                rz_score=0.0,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )


class TestJawSmile:
    def test_jaw_happy_path(self) -> None:
        j = Jaw(
            open=0.4,
            lateral=0.1,
            forward=0.05,
            is_open=True,
            rz_score=1.0,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert j.is_open

    def test_smile_happy_path(self) -> None:
        s = Smile(
            intensity=0.5,
            asymmetry=0.1,
            left_intensity=0.55,
            right_intensity=0.45,
            mouth_stretch=0.3,
            is_smiling=True,
            rz_score=0.0,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert s.is_smiling


class TestAudioVerbal:
    @pytest.mark.parametrize("level", ["very_quiet", "quiet", "normal", "loud", "very_loud"])
    def test_loudness_levels(self, level: str) -> None:
        m = LoudnessState(
            level=level,  # type: ignore[arg-type]
            rz_score=0.0,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert m.level == level

    def test_loudness_invalid_level(self) -> None:
        with pytest.raises(ValidationError):
            LoudnessState(
                level="medium",  # type: ignore[arg-type]
                rz_score=0.0,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )

    def test_pitch_state(self) -> None:
        p = PitchState(
            relative_level="much_higher",
            rz_score=4.5,
            is_anomalous=True,
            continuous_anomaly=True,
            part_of_anomalous_range=[10.0],
        )
        assert p.is_anomalous

    def test_pitch_std(self) -> None:
        p = PitchStd(
            expressiveness="flat",
            rz_score=-3.0,
            is_anomalous=True,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert p.expressiveness == "flat"

    def test_wps(self) -> None:
        w = WPS(
            speaking_rate="very_fast",
            rz_score=3.5,
            is_anomalous=True,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        assert w.speaking_rate == "very_fast"


class TestFillerPause:
    def test_filler_round_trip(self) -> None:
        f = FillerPercentageIncrease(
            filler_percentage_level="abnormally high",
            is_anomalous=True,
            continuous_anomaly=True,
            part_of_anomalous_range=[8.0, 8.5, 9.0],
        )
        dumped = f.model_dump()
        restored = FillerPercentageIncrease.model_validate(dumped)
        assert restored == f

    def test_pause_invalid_level(self) -> None:
        with pytest.raises(ValidationError):
            PausePercentageIncrease(
                pause_percentage_level="medium",  # type: ignore[arg-type]
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )


# ---------------------------------------------------------------------------
# agents.schemas — renamed observers, new CrossModalInsight fields,
# new overall_window_tone literal.
# ---------------------------------------------------------------------------


def _vis_event() -> VisualAnomalyEvent:
    return VisualAnomalyEvent(
        timestamp_start=5.0,
        timestamp_end=7.0,
        feature_type="Blink",
        behavioral_tag="Rapid Blinking",
        intensity_score=3.4,
        is_sustained=True,
    )


def _aud_event() -> AudioAnomalyEvent:
    return AudioAnomalyEvent(
        timestamp_start=10.0,
        timestamp_end=11.5,
        feature_type="Pitch",
        behavioral_tag="Tight Pitch",
        intensity_score=2.7,
        is_sustained=False,
    )


def _voc_event() -> VocabAnomalyEvent:
    return VocabAnomalyEvent(
        timestamp_start=14.0,
        timestamp_end=15.0,
        feature_type="Pauses",
        behavioral_tag="Stalling",
        intensity_score=1.0,
        is_sustained=False,
    )


def test_visual_observation_round_trip() -> None:
    r = VisualObservation(
        time_range_start=0.0,
        time_range_end=30.0,
        overall_visual_state="Baseline",
        detected_anomalies=[_vis_event()],
        contradiction_context="Stable until ~5 s, then a brief blink cluster.",
    )
    assert VisualObservation.model_validate(r.model_dump()) == r


def test_audio_observation_round_trip() -> None:
    r = AudioObservation(
        time_range_start=0.0,
        time_range_end=30.0,
        overall_vocal_state="Baseline_Calm",
        detected_anomalies=[_aud_event()],
        contradiction_context="One brief pitch tightening at 10 s.",
    )
    assert AudioObservation.model_validate(r.model_dump()) == r


def test_vocab_observation_round_trip() -> None:
    r = VocabObservation(
        time_range_start=0.0,
        time_range_end=30.0,
        overall_verbal_state="Baseline_Fluent",
        detected_anomalies=[_voc_event()],
        contradiction_context="One pause at 14 s.",
    )
    assert VocabObservation.model_validate(r.model_dump()) == r


class TestCrossModalInsight:
    def test_round_trip(self) -> None:
        c = CrossModalInsight(
            timestamp_start=5.0,
            timestamp_end=7.0,
            spoken_content="I have a lot of experience in ML.",
            modalities_involved=["Visual", "Audio"],
            pattern_type="Concern",
            significance="High",
            observation="Pitch dropped + blinking spiked while claiming ML experience.",
            interpretation="Strong indication of overclaim regarding the specific credential.",
        )
        assert CrossModalInsight.model_validate(c.model_dump()) == c

    @pytest.mark.parametrize("pattern_type", ["Strength", "Concern", "Notable"])
    def test_each_pattern_type(self, pattern_type: str) -> None:
        c = CrossModalInsight(
            timestamp_start=0.0,
            timestamp_end=1.0,
            spoken_content="Some content.",
            modalities_involved=["Visual"],
            pattern_type=pattern_type,  # type: ignore[arg-type]
            significance="Low",
            observation="Brief micro-expression.",
            interpretation="Worth noting.",
        )
        assert c.pattern_type == pattern_type

    def test_invalid_pattern_type(self) -> None:
        with pytest.raises(ValidationError):
            CrossModalInsight(
                timestamp_start=0.0,
                timestamp_end=1.0,
                spoken_content="Some content.",
                modalities_involved=["Visual"],
                pattern_type="Suspicious",  # type: ignore[arg-type]
                significance="Low",
                observation="Brief micro-expression.",
                interpretation="Worth noting.",
            )

    def test_invalid_modality(self) -> None:
        with pytest.raises(ValidationError):
            CrossModalInsight(
                timestamp_start=0.0,
                timestamp_end=1.0,
                spoken_content="Some content.",
                modalities_involved=["Olfactory"],  # type: ignore[list-item]
                pattern_type="Notable",
                significance="Low",
                observation="Brief micro-expression.",
                interpretation="Worth noting.",
            )


class TestIntegratedBehavioralReport:
    @pytest.mark.parametrize(
        "tone",
        [
            "Strong_Positive",
            "Authentic",
            "Mostly_Authentic",
            "Mixed_Signals",
            "Concerning",
        ],
    )
    def test_each_window_tone(self, tone: str) -> None:
        r = IntegratedBehavioralReport(
            time_range_start=0.0,
            time_range_end=10.0,
            overall_window_tone=tone,  # type: ignore[arg-type]
            executive_summary="Brief summary.",
            key_insights=[],
        )
        assert r.overall_window_tone == tone

    def test_round_trip(self) -> None:
        insight = CrossModalInsight(
            timestamp_start=5.0,
            timestamp_end=7.0,
            spoken_content="I built that system end-to-end.",
            modalities_involved=["Visual", "Audio"],
            pattern_type="Concern",
            significance="Medium",
            observation="Brief nervousness while claiming sole authorship.",
            interpretation="May have overstated their solo contribution.",
        )
        r = IntegratedBehavioralReport(
            time_range_start=0.0,
            time_range_end=10.0,
            overall_window_tone="Mixed_Signals",
            executive_summary="Brief nervousness early on; otherwise calm.",
            key_insights=[insight],
        )
        assert IntegratedBehavioralReport.model_validate(r.model_dump()) == r


def test_final_report_round_trip() -> None:
    r = FinalReport(
        executive_summary="The candidate presented authentically.",
        behavioral_strengths="Strong vocal stability under technical questions.",
        vulnerabilities_and_triggers="Brief blink cluster around 5-7 s.",
        areas_for_improvement="Take a 2-second pause before answering hard questions.",
    )
    assert FinalReport.model_validate(r.model_dump()) == r
