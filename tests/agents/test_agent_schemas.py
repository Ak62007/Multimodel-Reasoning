"""Schema round-trip tests for `agents/schemas.py`.

Covers the post-rewrite surface: enriched `*Observation` (with `raw_summary`),
the per-window `WindowAnalysis` + `Signal` field note, and the synthesised
`FinalReport` + `Highlight` + `Thread`. The key invariants are (a) round-trip
equality via `model_dump()` (the persistence path serialises with this), and
(b) enum/Literal validation so a stub/LLM typo surfaces loudly rather than as a
500 at the API boundary.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.schemas import (
    AudioAnomalyEvent,
    AudioObservation,
    FinalReport,
    Highlight,
    Signal,
    Thread,
    VisualAnomalyEvent,
    VisualObservation,
    VocabObservation,
    VocabularyAnomalyEvent,
    WeaverDraft,
    WindowAnalysis,
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
        raw_summary="Blink rate elevated; gaze otherwise steady.",
        contradiction_context="Brief eyelid cluster around 6-8s while otherwise calm.",
    )
    assert VisualObservation(**obs.model_dump()) == obs


def test_observation_raw_summary_defaults_empty() -> None:
    obs = AudioObservation(
        time_range_start=0.0,
        time_range_end=1.0,
        overall_vocal_state="Baseline_Calm",
        contradiction_context="x",
    )
    assert obs.raw_summary == ""


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


# --- Signal / WindowAnalysis ----------------------------------------------


def test_signal_allows_single_modality() -> None:
    """A lone-modality tell is now valid — that was the whole point of the rewrite."""
    s = Signal(
        timestamp_start=41.0,
        timestamp_end=42.0,
        modalities=["Audio"],
        relation="Isolated",
        kind="Tell",
        headline="Voice flattened",
        evidence="Expressiveness dropped 2.4σ.",
        interpretation="Possible rehearsed delivery.",
        significance="High",
    )
    assert s.modalities == ["Audio"]
    assert Signal(**s.model_dump()) == s


def test_signal_all_kinds_and_relations() -> None:
    for kind in ("Strength", "Tell", "Tension", "Quirk", "Shift"):
        for rel in ("Correlation", "Contradiction", "Isolated"):
            s = Signal(
                timestamp_start=1.0,
                timestamp_end=2.0,
                modalities=["Visual", "Audio"],
                relation=rel,  # type: ignore[arg-type]
                kind=kind,  # type: ignore[arg-type]
                headline="x",
                evidence="x",
                interpretation="x",
                significance="Low",
            )
            assert s.kind == kind and s.relation == rel


def test_signal_rejects_bad_kind() -> None:
    with pytest.raises(ValidationError):
        Signal(
            timestamp_start=0.0,
            timestamp_end=1.0,
            modalities=["Visual"],
            relation="Isolated",
            kind="Suspicious",  # type: ignore[arg-type]  # not a valid SignalKind
            headline="x",
            evidence="x",
            interpretation="x",
            significance="Low",
        )


def test_window_analysis_round_trip_with_phase() -> None:
    wa = WindowAnalysis(
        time_start=39.0,
        time_end=42.0,
        phase="Middle",
        position_pct=0.42,
        spoken_excerpt="I led the whole ML pipeline.",
        visual_read="Calm, steady gaze.",
        audio_read="Voice flattened to monotone.",
        verbal_read="Fluent, no stalling.",
        narrative="A vocal flattening stands out right on an ownership claim.",
        window_interest="High",
        signals=[
            Signal(
                timestamp_start=41.0,
                timestamp_end=42.0,
                modalities=["Audio", "Verbal"],
                relation="Contradiction",
                kind="Tell",
                headline="Monotone on a big claim",
                evidence="Expressiveness -2.4σ while claiming ownership.",
                spoken_content="I led the whole ML pipeline.",
                interpretation="Possible over-statement.",
                significance="High",
            )
        ],
    )
    assert WindowAnalysis(**wa.model_dump()) == wa


def test_window_analysis_rejects_bad_phase() -> None:
    with pytest.raises(ValidationError):
        WindowAnalysis(
            time_start=0.0,
            time_end=1.0,
            phase="Intro",  # type: ignore[arg-type]  # not a valid InterviewPhase
            position_pct=0.0,
            narrative="x",
            window_interest="Low",
        )


def test_window_analysis_defaults_empty_signals() -> None:
    wa = WindowAnalysis(
        time_start=0.0,
        time_end=1.0,
        phase="Opening",
        position_pct=0.0,
        narrative="Steady baseline.",
        window_interest="Low",
    )
    assert wa.signals == []


# --- FinalReport / Highlight / Thread / WeaverDraft -----------------------


def test_final_report_round_trip() -> None:
    r = FinalReport(
        headline="Composed but rehearsed on ownership claims.",
        overview="The candidate was steady overall…",
        behavioral_arc="Calm opening → tension mid-interview → recovery by the close.",
        highlights=[
            Highlight(
                ts_start=41.0,
                ts_end=42.0,
                title="Monotone on a big claim",
                what_happened="Voice flattened while claiming ML ownership.",
                why_it_matters="Possible over-statement worth probing.",
                modalities=["Audio", "Verbal"],
                kind="Tell",
                significance="High",
            )
        ],
        threads=[
            Thread(
                title="Vocal flattening on ownership claims",
                summary="Voice flattens whenever credit is claimed.",
                relation="Contradiction",
                occurrences=[41.0, 88.0],
                interpretation="A consistent tell around credit.",
            )
        ],
        coaching_notes="Practice claims aloud.",
    )
    assert FinalReport(**r.model_dump()) == r


def test_weaver_draft_round_trip() -> None:
    d = WeaverDraft(
        headline="x",
        arc_notes="baseline → trigger → recovery",
        highlights=[],
        threads=[],
    )
    assert WeaverDraft(**d.model_dump()) == d
