"""Output schemas for the agentic layer.

Two distinct surfaces:

- **Internal observer outputs** (`VisualObservation`, `AudioObservation`,
  `VocabObservation`) — consumed only by the Pattern Detector. Not exposed
  via API; not rendered in the frontend. They exist to give the Pattern
  Detector pre-digested, structured material to correlate across modalities.

- **Public outputs** (`IntegratedBehavioralReport`, `FinalReport`) — surface
  via `/api/jobs/{id}/segments` and `/api/jobs/{id}/report`.

See spec §9.5 for the schema design rationale (Strength / Concern / Notable
framing instead of binary credibility).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Per-modality anomaly events (carry through observer + pattern_detector).
# --------------------------------------------------------------------------


class VisualAnomalyEvent(BaseModel):
    """A distinct visual behavioral event the observer detected within the window."""

    timestamp_start: float
    timestamp_end: float
    feature_type: Literal["Blink", "Gaze", "Jaw", "Smile"]
    behavioral_tag: str = Field(
        ...,
        description="Psychological interpretation, e.g., 'Rapid Blinking', 'Jaw Clench', 'Fixed Stare'.",
    )
    intensity_score: float = Field(
        ..., description="Max absolute rz_score observed during this event."
    )
    is_sustained: bool = Field(
        ...,
        description="True if a sustained state shift, False if a micro-expression.",
    )


class AudioAnomalyEvent(BaseModel):
    timestamp_start: float
    timestamp_end: float
    feature_type: Literal["Loudness", "Pitch", "Expressiveness"]
    behavioral_tag: str = Field(
        ..., description="Examples: 'Sudden Whisper', 'High-Pitch Stress', 'Monotone Dissociation'."
    )
    intensity_score: float
    is_sustained: bool


class VocabularyAnomalyEvent(BaseModel):
    timestamp_start: float
    timestamp_end: float
    feature_type: Literal["SpeakingRate", "FillerUsage", "Pauses"]
    behavioral_tag: str = Field(
        ...,
        description="Examples: 'High Cognitive Load', 'Rapid-Fire Defense', 'Stalling/Hesitation'.",
    )
    intensity_score: float
    is_sustained: bool


# --------------------------------------------------------------------------
# Internal observer outputs.
# Renamed from `*AnalysisReport` per spec §9.5 to reflect their role.
# --------------------------------------------------------------------------


class VisualObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Pattern Detector."""

    time_range_start: float
    time_range_end: float
    overall_visual_state: Literal[
        "Baseline", "Low_Stress", "High_Stress", "Deceptive_Cluster", "Emotional_Breakthrough"
    ]
    detected_anomalies: list[VisualAnomalyEvent] = Field(default_factory=list)
    contradiction_context: str = Field(
        ...,
        description="Concise narrative highlighting what *changed* during this window.",
    )


class AudioObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Pattern Detector."""

    time_range_start: float
    time_range_end: float
    overall_vocal_state: Literal[
        "Baseline_Calm",
        "Suppressed/Timid",
        "Aggressive/Dominant",
        "Stressed/Tight",
        "Robotic/Rehearsed",
        "Volatile",
    ]
    detected_anomalies: list[AudioAnomalyEvent] = Field(default_factory=list)
    contradiction_context: str = Field(
        ..., description="Concise narrative highlighting acoustic shifts during this window."
    )


class VocabObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Pattern Detector."""

    time_range_start: float
    time_range_end: float
    overall_verbal_state: Literal[
        "Baseline_Fluent",
        "Cognitively_Overloaded",
        "Anxious/Rushed",
        "Guarded/Slow",
        "Disorganized",
    ]
    detected_anomalies: list[VocabularyAnomalyEvent] = Field(default_factory=list)
    contradiction_context: str = Field(
        ..., description="Concise narrative highlighting fluency shifts during this window."
    )


# --------------------------------------------------------------------------
# Public outputs (rendered on the frontend, returned by the API).
# --------------------------------------------------------------------------


class CrossModalInsight(BaseModel):
    """A meaningful cross-modal pattern within an analysis window.

    Per spec §9.5: report Strengths, Concerns, AND Notables — not just
    deception signals. Always tie the pattern to spoken content.
    """

    timestamp_start: float
    timestamp_end: float
    spoken_content: str = Field(
        ..., description="A short quote of what was being said when this pattern occurred."
    )
    modalities_involved: list[Literal["Visual", "Audio", "Verbal"]] = Field(
        ..., description="Which modalities tell the story together."
    )
    pattern_type: Literal["Strength", "Concern", "Notable"] = Field(
        ...,
        description=(
            "Strength: genuine positive (e.g., congruent confidence). "
            "Concern: possible deception, exaggeration, or distress. "
            "Notable: coachable but not necessarily negative (e.g., correct answer "
            "delivered with low-confidence body language)."
        ),
    )
    significance: Literal["Low", "Medium", "High"] = Field(
        ..., description="How prominent / sustained the pattern is. Not a semantic judgement."
    )
    observation: str = Field(..., description="One sentence: what happened across modalities.")
    interpretation: str = Field(..., description="One sentence: what it means about the candidate.")


class IntegratedBehavioralReport(BaseModel):
    """Per-window cross-modal report. Public output."""

    time_range_start: float
    time_range_end: float
    overall_window_tone: Literal[
        "Strong_Positive", "Authentic", "Mostly_Authentic", "Mixed_Signals", "Concerning"
    ] = Field(..., description="Holistic tone of this window. Drives the badge color in the UI.")
    executive_summary: str = Field(
        ..., description="Max 2 sentences summarizing this window's story."
    )
    key_insights: list[CrossModalInsight] = Field(
        default_factory=list,
        description=(
            "Cross-modal patterns found. If empty, the orchestrator drops this window "
            "silently from the public output."
        ),
    )


class FinalReport(BaseModel):
    """Executive coaching report aggregating all per-window patterns. Public output."""

    executive_summary: str = Field(..., description="3-4 sentence overall impression.")
    behavioral_strengths: str = Field(..., description="Markdown: what went well.")
    vulnerabilities_and_triggers: str = Field(..., description="Markdown: what went wrong.")
    areas_for_improvement: str = Field(..., description="Markdown: how to improve.")


__all__ = [
    "AudioAnomalyEvent",
    "AudioObservation",
    "CrossModalInsight",
    "FinalReport",
    "IntegratedBehavioralReport",
    "VisualAnomalyEvent",
    "VisualObservation",
    "VocabObservation",
    "VocabularyAnomalyEvent",
]
