"""Schema round-trip tests for `agents/schemas.py`.

Includes the post-M4 changes: `CrossModalInsight.pattern_type` and
`significance`, `IntegratedBehavioralReport.overall_window_tone`, the
`*Observation` rename of the internal observer outputs.
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
    VocabObservation,
    VocabularyAnomalyEvent,
)


def test_visual_observation_round_trip() -> None:
    obs = VisualObservation(
        time_range_start=5.0,
        time_range_end=10.0,
        overall_visual_state="Low_Stress",
        detected_anomalies=[
            VisualAnomalyEvent(
                timestamp_start=6.0,
                timestamp_end=8.0,
                feature_type="Blink",
                behavioral_tag="Rapid Blinking",
                intensity_score=3.4,
                is_sustained=True,
            )
        ],
        contradiction_context="Brief eyelid cluster around 6-8s while otherwise calm.",
    )
    assert VisualObservation(**obs.model_dump()) == obs


def test_audio_observation_rejects_bad_state() -> None:
    with pytest.raises(ValidationError):
        AudioObservation(
            time_range_start=0.0,
            time_range_end=1.0,
            overall_vocal_state="loud_panic",  # type: ignore[arg-type]
            contradiction_context="x",
        )


def test_vocab_observation_with_events() -> None:
    obs = VocabObservation(
        time_range_start=0.0,
        time_range_end=2.0,
        overall_verbal_state="Cognitively_Overloaded",
        detected_anomalies=[
            VocabularyAnomalyEvent(
                timestamp_start=0.5,
                timestamp_end=1.5,
                feature_type="FillerUsage",
                behavioral_tag="Stalling/Hesitation",
                intensity_score=1.0,
                is_sustained=False,
            )
        ],
        contradiction_context="Filler cluster + slowed cadence",
    )
    assert obs.detected_anomalies[0].feature_type == "FillerUsage"


def test_cross_modal_insight_three_pattern_types() -> None:
    for pat in ("Strength", "Concern", "Notable"):
        ins = CrossModalInsight(
            timestamp_start=1.0,
            timestamp_end=2.0,
            spoken_content="I worked on the ML stack [*]",
            modalities_involved=["Visual", "Audio"],
            pattern_type=pat,  # type: ignore[arg-type]
            significance="Medium",
            observation="Vocal tightening with averted gaze.",
            interpretation="Possible discomfort with the topic.",
        )
        assert ins.pattern_type == pat


def test_cross_modal_insight_rejects_legacy_suspicion_level_key() -> None:
    with pytest.raises(ValidationError):
        # `suspicion_level` was the old name; the schema now requires
        # `pattern_type` + `significance` instead.
        CrossModalInsight(
            timestamp_start=0.0,
            timestamp_end=1.0,
            spoken_content="x",
            modalities_involved=["Visual"],
            pattern_type="Concern",
            significance="Medium",
            observation="x",
            # `interpretation` missing — should ValidationError
        )  # type: ignore[call-arg]


def test_integrated_report_overall_window_tone_enum() -> None:
    for tone in (
        "Strong_Positive",
        "Authentic",
        "Mostly_Authentic",
        "Mixed_Signals",
        "Concerning",
    ):
        r = IntegratedBehavioralReport(
            time_range_start=0.0,
            time_range_end=5.0,
            overall_window_tone=tone,  # type: ignore[arg-type]
            executive_summary="A short summary.",
            key_insights=[],
        )
        assert r.overall_window_tone == tone


def test_integrated_report_rejects_legacy_credibility_value() -> None:
    with pytest.raises(ValidationError):
        IntegratedBehavioralReport(
            time_range_start=0.0,
            time_range_end=5.0,
            overall_window_tone="High Credibility (Authentic)",  # legacy literal  # type: ignore[arg-type]
            executive_summary="x",
            key_insights=[],
        )


def test_audio_anomaly_event_intensity() -> None:
    ev = AudioAnomalyEvent(
        timestamp_start=12.0,
        timestamp_end=12.5,
        feature_type="Loudness",
        behavioral_tag="Sudden Whisper",
        intensity_score=2.8,
        is_sustained=False,
    )
    assert AudioAnomalyEvent(**ev.model_dump()) == ev


def test_final_report_round_trip() -> None:
    r = FinalReport(
        executive_summary="Solid candidate overall.",
        behavioral_strengths="They were calm and articulate when discussing prior work.",
        vulnerabilities_and_triggers="Stress under deep-technical questions.",
        areas_for_improvement="Practice technical explanations aloud.",
    )
    assert FinalReport(**r.model_dump()) == r
