"""Deterministic stub provider for tests and offline development.

When ``LLM_PROVIDER=stub`` the agent orchestrator routes every call
through this module. Outputs are derived from the window's actual
anomaly content (not random), so they are stable + reproducible across
runs but still vary meaningfully with the input.

The stubs intentionally do **not** depend on pydantic-ai or Groq, so
test runs incur no network calls and no model latency.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, cast

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

# Re-exported literal aliases keep the cast() calls below readable.
_VisualState = Literal[
    "Baseline", "Low_Stress", "High_Stress", "Deceptive_Cluster", "Emotional_Breakthrough"
]
_AudioState = Literal[
    "Baseline_Calm",
    "Suppressed/Timid",
    "Aggressive/Dominant",
    "Stressed/Tight",
    "Robotic/Rehearsed",
    "Volatile",
]
_VocabState = Literal[
    "Baseline_Fluent",
    "Cognitively_Overloaded",
    "Anxious/Rushed",
    "Guarded/Slow",
    "Disorganized",
]
_WindowTone = Literal[
    "Strong_Positive", "Authentic", "Mostly_Authentic", "Mixed_Signals", "Concerning"
]

if TYPE_CHECKING:
    from agents._window_slice import WindowSlice

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observers
# ---------------------------------------------------------------------------


def stub_visual_observation(slice_: WindowSlice) -> VisualObservation:
    anomalies = slice_.extract_visual_anomalies()
    state = _visual_state(anomalies)
    events = [
        VisualAnomalyEvent(
            timestamp_start=a["time"],
            timestamp_end=a["time"] + 0.5,
            feature_type=a["feature_type"],
            behavioral_tag=_visual_tag(a),
            intensity_score=abs(a["rz_score"]),
            is_sustained=a["is_sustained"],
        )
        for a in anomalies
    ]
    context = (
        f"{len(anomalies)} visual anomaly events between {slice_.start:.1f}s and {slice_.end:.1f}s."
        if anomalies
        else "Subject visually calm across the whole window."
    )
    return VisualObservation(
        time_range_start=slice_.start,
        time_range_end=slice_.end,
        overall_visual_state=state,
        detected_anomalies=events,
        contradiction_context=context,
    )


def stub_audio_observation(slice_: WindowSlice) -> AudioObservation:
    anomalies = slice_.extract_audio_anomalies()
    state = _audio_state(anomalies)
    events = [
        AudioAnomalyEvent(
            timestamp_start=a["time"],
            timestamp_end=a["time"] + 0.5,
            feature_type=a["feature_type"],
            behavioral_tag=_audio_tag(a),
            intensity_score=abs(a["rz_score"]),
            is_sustained=a["is_sustained"],
        )
        for a in anomalies
    ]
    context = (
        f"{len(anomalies)} audio anomaly events; vocal state '{state}'."
        if anomalies
        else "Subject sounds steady and calm across the window."
    )
    return AudioObservation(
        time_range_start=slice_.start,
        time_range_end=slice_.end,
        overall_vocal_state=state,
        detected_anomalies=events,
        contradiction_context=context,
    )


def stub_vocab_observation(slice_: WindowSlice) -> VocabObservation:
    anomalies = slice_.extract_vocab_anomalies()
    state = _vocab_state(anomalies)
    events = [
        VocabAnomalyEvent(
            timestamp_start=a["time"],
            timestamp_end=a["time"] + 0.5,
            feature_type=a["feature_type"],
            behavioral_tag=_vocab_tag(a),
            intensity_score=abs(a["rz_score"]) if a["rz_score"] else 1.0,
            is_sustained=a["is_sustained"],
        )
        for a in anomalies
    ]
    context = (
        f"{len(anomalies)} linguistic anomaly events; verbal state '{state}'."
        if anomalies
        else "Subject speaks fluently with no obvious mental blocks."
    )
    return VocabObservation(
        time_range_start=slice_.start,
        time_range_end=slice_.end,
        overall_verbal_state=state,
        detected_anomalies=events,
        contradiction_context=context,
    )


# ---------------------------------------------------------------------------
# Pattern Detector
# ---------------------------------------------------------------------------


def stub_integrated_report(
    slice_: WindowSlice,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
) -> IntegratedBehavioralReport:
    """Stub pattern detector: produce one insight per modality cluster of anomalies."""
    insights: list[CrossModalInsight] = []
    modalities_present: list[str] = []

    if visual.detected_anomalies:
        modalities_present.append("Visual")
    if audio.detected_anomalies:
        modalities_present.append("Audio")
    if vocab.detected_anomalies:
        modalities_present.append("Verbal")

    if modalities_present:
        if len(modalities_present) == 3:
            pattern_type, significance = "Concern", "High"
        elif len(modalities_present) == 2:
            pattern_type, significance = "Notable", "Medium"
        else:
            pattern_type, significance = "Notable", "Low"
        modalities: list[str] = modalities_present[:]
        spoken = slice_.spoken_text or "(no transcript captured in this window)"
        insights.append(
            CrossModalInsight(
                timestamp_start=slice_.start,
                timestamp_end=slice_.end,
                spoken_content=spoken,
                modalities_involved=modalities,  # type: ignore[arg-type]
                pattern_type=pattern_type,  # type: ignore[arg-type]
                significance=significance,  # type: ignore[arg-type]
                observation=(
                    f"Across {' + '.join(modalities)} channels the subject showed "
                    f"co-occurring deviations between {slice_.start:.1f}s and {slice_.end:.1f}s."
                ),
                interpretation=(
                    "A single-modality stub signal; replace LLM_PROVIDER with `groq` "
                    "to get a real cross-modal interpretation."
                    if len(modalities_present) == 1
                    else "Multiple modalities deviating at once is more informative than any single "
                    "spike; worth flagging for follow-up."
                ),
            )
        )

    tone = _tone_for(modalities_present, slice_)
    summary = (
        f"Cross-modal activity spanning {', '.join(modalities_present)}."
        if modalities_present
        else "Baseline behaviour across the window."
    )
    return IntegratedBehavioralReport(
        time_range_start=slice_.start,
        time_range_end=slice_.end,
        overall_window_tone=tone,
        executive_summary=summary,
        key_insights=insights,
    )


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------


def stub_final_report(reports: list[IntegratedBehavioralReport]) -> FinalReport:
    total_insights = sum(len(r.key_insights) for r in reports)
    concerns = sum(1 for r in reports for i in r.key_insights if i.pattern_type == "Concern")
    strengths = sum(1 for r in reports for i in r.key_insights if i.pattern_type == "Strength")
    notables = sum(1 for r in reports for i in r.key_insights if i.pattern_type == "Notable")

    return FinalReport(
        executive_summary=(
            f"Analysed {len(reports)} cross-modal windows containing {total_insights} "
            f"pattern(s) overall ({concerns} concern, {strengths} strength, {notables} notable). "
            "This is a deterministic stub summary; replace LLM_PROVIDER with `groq` to get a real "
            "synthesis."
        ),
        behavioral_strengths=(
            "- The candidate's baseline state is broadly stable.\n"
            "- No persistent strong-negative patterns observed.\n"
            f"- {strengths} window(s) labelled as Strength."
        ),
        vulnerabilities_and_triggers=(
            f"- {concerns} Concern pattern(s) detected.\n"
            "- Topics most associated with deviations are listed below by window range:\n"
            + "\n".join(
                f"  - {r.time_range_start:.1f}s - {r.time_range_end:.1f}s: {r.executive_summary}"
                for r in reports
                if r.key_insights
            )
        ),
        areas_for_improvement=(
            "1. **Pause before answering complex questions** to reduce cognitive load.\n"
            "2. **Maintain steady vocal tone** even when uncertain.\n"
            "3. **Tie technical claims to concrete examples** to reinforce credibility."
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _visual_state(anomalies: list[dict[str, object]]) -> _VisualState:
    if not anomalies:
        return "Baseline"
    sustained = sum(1 for a in anomalies if a["is_sustained"])
    if sustained >= 3:
        return "Deceptive_Cluster"
    if sustained:
        return "High_Stress"
    return "Low_Stress"


def _audio_state(anomalies: list[dict[str, object]]) -> _AudioState:
    if not anomalies:
        return "Baseline_Calm"
    types = {a["feature_type"] for a in anomalies}
    if "Pitch" in types and "Loudness" in types:
        return "Volatile"
    if "Pitch" in types:
        return "Stressed/Tight"
    if "Loudness" in types:
        return "Suppressed/Timid"
    return "Robotic/Rehearsed"


def _vocab_state(anomalies: list[dict[str, object]]) -> _VocabState:
    if not anomalies:
        return "Baseline_Fluent"
    types = {a["feature_type"] for a in anomalies}
    if "Pauses" in types and "FillerUsage" in types:
        return "Cognitively_Overloaded"
    if "SpeakingRate" in types:
        return "Anxious/Rushed"
    if "Pauses" in types:
        return "Guarded/Slow"
    return "Disorganized"


def _visual_tag(anomaly: dict[str, object]) -> str:
    return f"{anomaly['feature_type']} deviation"


def _audio_tag(anomaly: dict[str, object]) -> str:
    return f"{anomaly['feature_type']} deviation"


def _vocab_tag(anomaly: dict[str, object]) -> str:
    return f"{anomaly['feature_type']} deviation"


def _tone_for(modalities_present: list[str], slice_: WindowSlice) -> _WindowTone:
    _ = slice_  # reserved for future tone heuristics
    if not modalities_present:
        return "Authentic"
    if len(modalities_present) == 1:
        return "Mostly_Authentic"
    if len(modalities_present) == 2:
        return "Mixed_Signals"
    return "Concerning"


__all__ = [
    "stub_audio_observation",
    "stub_final_report",
    "stub_integrated_report",
    "stub_visual_observation",
    "stub_vocab_observation",
]


_ = cast  # silence the unused-import warning
