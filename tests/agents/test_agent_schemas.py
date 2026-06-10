"""Sanity tests for the new agent schemas.

These are intentionally lighter-touch than ``test_schemas.py`` (which
covers field-level validation in detail) - their purpose is to make
sure every observation / report type can be instantiated with the
shape the stubs / Groq backend produce.
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


def test_visual_observation_with_event() -> None:
    event = VisualAnomalyEvent(
        timestamp_start=5.0,
        timestamp_end=5.5,
        feature_type="Blink",
        behavioral_tag="rapid blinking",
        intensity_score=3.4,
        is_sustained=True,
    )
    obs = VisualObservation(
        time_range_start=5.0,
        time_range_end=7.0,
        overall_visual_state="High_Stress",
        detected_anomalies=[event],
        contradiction_context="One sustained blink cluster.",
    )
    assert obs.detected_anomalies[0].feature_type == "Blink"


def test_audio_observation_with_event() -> None:
    event = AudioAnomalyEvent(
        timestamp_start=10.0,
        timestamp_end=10.5,
        feature_type="Pitch",
        behavioral_tag="vocal tightening",
        intensity_score=2.7,
        is_sustained=False,
    )
    obs = AudioObservation(
        time_range_start=10.0,
        time_range_end=12.0,
        overall_vocal_state="Stressed/Tight",
        detected_anomalies=[event],
        contradiction_context="One brief pitch tightening.",
    )
    assert obs.overall_vocal_state == "Stressed/Tight"


def test_vocab_observation_with_event() -> None:
    event = VocabAnomalyEvent(
        timestamp_start=14.0,
        timestamp_end=14.5,
        feature_type="FillerUsage",
        behavioral_tag="filler spike",
        intensity_score=1.0,
        is_sustained=False,
    )
    obs = VocabObservation(
        time_range_start=14.0,
        time_range_end=15.0,
        overall_verbal_state="Cognitively_Overloaded",
        detected_anomalies=[event],
        contradiction_context="One filler spike.",
    )
    assert obs.overall_verbal_state == "Cognitively_Overloaded"


def test_observation_empty_anomalies_is_default() -> None:
    obs = VisualObservation(
        time_range_start=0.0,
        time_range_end=1.0,
        overall_visual_state="Baseline",
        contradiction_context="Subject visually calm.",
    )
    assert obs.detected_anomalies == []


def test_integrated_report_filterable_by_pattern_type() -> None:
    a = CrossModalInsight(
        timestamp_start=0.0,
        timestamp_end=1.0,
        spoken_content="hello",
        modalities_involved=["Visual"],
        pattern_type="Strength",
        significance="Low",
        observation="Stable behaviour.",
        interpretation="Healthy baseline.",
    )
    b = CrossModalInsight(
        timestamp_start=2.0,
        timestamp_end=3.0,
        spoken_content="thanks",
        modalities_involved=["Audio", "Verbal"],
        pattern_type="Concern",
        significance="High",
        observation="Voice tightened while answering.",
        interpretation="Possible discomfort.",
    )
    report = IntegratedBehavioralReport(
        time_range_start=0.0,
        time_range_end=3.0,
        overall_window_tone="Mixed_Signals",
        executive_summary="One strength + one concern.",
        key_insights=[a, b],
    )
    concerns = [i for i in report.key_insights if i.pattern_type == "Concern"]
    assert len(concerns) == 1
    assert concerns[0].significance == "High"


def test_final_report_round_trip() -> None:
    r = FinalReport(
        executive_summary="Holistic 3-4 sentence summary.",
        behavioral_strengths="### Strengths\n- Steady tone",
        vulnerabilities_and_triggers="### Triggers\n- Math questions",
        areas_for_improvement="1. Take a 2-second pause.",
    )
    assert FinalReport.model_validate(r.model_dump()) == r


def test_cross_modal_insight_rejects_old_field() -> None:
    """The renamed ``significance`` must reject the legacy ``suspicion_level`` key."""
    with pytest.raises(ValidationError):
        CrossModalInsight.model_validate(
            {
                "timestamp_start": 0.0,
                "timestamp_end": 1.0,
                "spoken_content": "x",
                "modalities_involved": ["Visual"],
                "pattern_type": "Notable",
                "suspicion_level": "High",  # old field name
                "observation": "x",
                "interpretation": "y",
            }
        )
