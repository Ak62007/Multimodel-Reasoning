"""Stub provider for deterministic agent outputs.

When `LLM_PROVIDER=stub`, every agent runner returns a canned Pydantic
instance derived directly from its structured input — no LLM call is made.
Used by the test suite (no token cost, no flakiness) and by the backend
in `MMR_TEST_MODE=1`.

The stub outputs are intentionally simple but schema-correct so downstream
consumers (Pattern Detector → Judge → frontend) get sensible data.
"""

from __future__ import annotations

import pandas as pd

from agents.schemas import (
    AudioObservation,
    CrossModalInsight,
    FinalReport,
    IntegratedBehavioralReport,
    VisualObservation,
    VocabObservation,
)


def _summary_from_anomalies(label: str, n: int) -> str:
    if n == 0:
        return f"{label} baseline — no anomalies observed."
    return f"{label} showed {n} anomalous event{'s' if n != 1 else ''} during this window."


def stub_visual(start: float, end: float, events: list) -> VisualObservation:
    return VisualObservation(
        time_range_start=start,
        time_range_end=end,
        overall_visual_state="Baseline" if not events else "Low_Stress",
        detected_anomalies=events,
        contradiction_context=_summary_from_anomalies("Visual", len(events)),
    )


def stub_audio(start: float, end: float, events: list) -> AudioObservation:
    return AudioObservation(
        time_range_start=start,
        time_range_end=end,
        overall_vocal_state="Baseline_Calm" if not events else "Stressed/Tight",
        detected_anomalies=events,
        contradiction_context=_summary_from_anomalies("Vocal", len(events)),
    )


def stub_vocab(start: float, end: float, events: list) -> VocabObservation:
    return VocabObservation(
        time_range_start=start,
        time_range_end=end,
        overall_verbal_state="Baseline_Fluent" if not events else "Cognitively_Overloaded",
        detected_anomalies=events,
        contradiction_context=_summary_from_anomalies("Verbal", len(events)),
    )


def stub_pattern_detector(
    start: float,
    end: float,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
) -> IntegratedBehavioralReport:
    """Build a single CrossModalInsight if 2+ modalities had anomalies.

    Keeps the orchestrator's "drop empty windows" path exercised — windows
    with only a single modality's anomalies return empty `key_insights`.
    """
    active_modalities: list = []
    if visual.detected_anomalies:
        active_modalities.append("Visual")
    if audio.detected_anomalies:
        active_modalities.append("Audio")
    if vocab.detected_anomalies:
        active_modalities.append("Verbal")

    if len(active_modalities) < 2:
        return IntegratedBehavioralReport(
            time_range_start=start,
            time_range_end=end,
            overall_window_tone="Authentic",
            executive_summary="No cross-modal pattern detected in this window.",
            key_insights=[],
        )

    insight = CrossModalInsight(
        timestamp_start=start,
        timestamp_end=end,
        spoken_content=(transcript[:120].strip() or "[no transcript]"),
        modalities_involved=active_modalities,  # type: ignore[arg-type]
        pattern_type="Concern" if len(active_modalities) >= 3 else "Notable",
        significance="Medium",
        observation=(
            f"Anomalies aligned across {', '.join(active_modalities)} during this window."
        ),
        interpretation=("Multiple modalities deviated together, suggesting a coachable moment."),
    )
    return IntegratedBehavioralReport(
        time_range_start=start,
        time_range_end=end,
        overall_window_tone="Concerning" if len(active_modalities) >= 3 else "Mixed_Signals",
        executive_summary=(
            f"Cross-modal alignment across {', '.join(active_modalities)} marks this "
            "window as worth attention."
        ),
        key_insights=[insight],
    )


def stub_judge(reports: list[IntegratedBehavioralReport]) -> FinalReport:
    n_windows = len(reports)
    n_concerns = sum(
        sum(1 for ins in r.key_insights if ins.pattern_type == "Concern") for r in reports
    )
    n_strengths = sum(
        sum(1 for ins in r.key_insights if ins.pattern_type == "Strength") for r in reports
    )
    return FinalReport(
        executive_summary=(
            f"Across {n_windows} analysis window(s), the candidate showed "
            f"{n_concerns} concern-pattern(s) and {n_strengths} strength-pattern(s). "
            "This is a stub-mode summary; run with LLM_PROVIDER=groq for real coaching."
        ),
        behavioral_strengths=(
            "**Stub mode.** Real strengths would be aggregated from each window's "
            "Strength patterns."
        ),
        vulnerabilities_and_triggers=(
            "**Stub mode.** Real triggers would be grouped by topic theme across "
            "windows with Concern patterns."
        ),
        areas_for_improvement=(
            "**Stub mode.** Real coaching actions would be tailored to the specific "
            "concern patterns observed."
        ),
    )


__all__ = [
    "stub_audio",
    "stub_judge",
    "stub_pattern_detector",
    "stub_visual",
    "stub_vocab",
]


# Avoid an unused-import lint when this module is consumed via re-export.
_ = pd
