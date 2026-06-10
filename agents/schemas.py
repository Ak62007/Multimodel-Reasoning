"""Pydantic schemas for the MMR agentic layer.

Public surface
--------------
Only :class:`IntegratedBehavioralReport` and :class:`FinalReport` are
exposed through the FastAPI backend (M5). Everything else in this module
is internal scaffolding consumed by the Pattern Detector, not surfaced
to the frontend.

Schema changes for M4 vs. the M1 carry-over
-------------------------------------------
- ``VisualAnalysisReport`` -> :class:`VisualObservation`         (internal)
- ``AudioAnalysisReport``  -> :class:`AudioObservation`          (internal)
- ``VocabularyAnalysisReport`` -> :class:`VocabObservation`      (internal)
- :class:`CrossModalInsight` is reframed:
    * ``anomalies_detected: list[str]`` removed
    * ``modalities_involved: list[Literal["Visual", "Audio", "Verbal"]]`` added
    * ``suspicion_level`` renamed ``significance`` (neutral framing)
    * ``pattern_type: Literal["Strength", "Concern", "Notable"]`` added
    * ``behavioral_analysis`` split into ``observation`` + ``interpretation``
- :class:`IntegratedBehavioralReport`:
    * ``overall_credibility`` -> ``overall_window_tone`` with a richer
      five-state literal (Authentic / Mostly_Authentic / Mixed_Signals /
      Concerning / Strong_Positive)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Internal observer scaffolding — not exposed by the API.
# ---------------------------------------------------------------------------


class VisualAnomalyEvent(BaseModel):
    """A distinct visual event inside the analysis window."""

    timestamp_start: float = Field(..., description="Start time of the visual event.")
    timestamp_end: float = Field(..., description="End time of the visual event.")
    feature_type: Literal["Blink", "Gaze", "Jaw", "Smile"] = Field(
        ..., description="Which facial feature the event was observed on."
    )
    behavioral_tag: str = Field(
        ...,
        description="Short interpretation, e.g. 'Rapid Blinking', 'Jaw Clench', 'Fixed Stare'.",
    )
    intensity_score: float = Field(
        ..., description="Max absolute rz_score observed during the event."
    )
    is_sustained: bool = Field(
        ...,
        description="True if the anomaly was continuous; False if it was a micro-expression.",
    )


class VisualObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Pattern Detector."""

    time_range_start: float
    time_range_end: float

    overall_visual_state: Literal[
        "Baseline",
        "Low_Stress",
        "High_Stress",
        "Deceptive_Cluster",
        "Emotional_Breakthrough",
    ] = Field(
        ...,
        description="Holistic classification of the subject's visible behaviour in this window.",
    )

    detected_anomalies: list[VisualAnomalyEvent] = Field(
        default_factory=list,
        description="Specific visual events identified inside the window.",
    )

    contradiction_context: str = Field(
        ...,
        description=(
            "Narrative summary of what *changed* visually in this window. "
            "Used by the Pattern Detector to correlate with audio + verbal."
        ),
    )


class AudioAnomalyEvent(BaseModel):
    """A distinct paralinguistic event inside the analysis window."""

    timestamp_start: float = Field(..., description="Start time of the audio event.")
    timestamp_end: float = Field(..., description="End time of the audio event.")
    feature_type: Literal["Loudness", "Pitch", "Expressiveness"] = Field(
        ..., description="Which acoustic dimension the event was observed on."
    )
    behavioral_tag: str = Field(
        ...,
        description="Short interpretation, e.g. 'Sudden Whisper', 'High-Pitch Stress', 'Vocal Fry'.",
    )
    intensity_score: float = Field(
        ..., description="Max absolute rz_score observed during the event."
    )
    is_sustained: bool = Field(
        ...,
        description="True if continuous; False if it was a momentary break.",
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
    ] = Field(..., description="Holistic classification of the subject's voice in this window.")

    detected_anomalies: list[AudioAnomalyEvent] = Field(default_factory=list)

    contradiction_context: str = Field(
        ...,
        description=(
            "Narrative summary of what *changed* in the voice during this window. "
            "Used by the Pattern Detector to correlate with visual + verbal."
        ),
    )


class VocabAnomalyEvent(BaseModel):
    """A distinct linguistic / cognitive event inside the analysis window."""

    timestamp_start: float = Field(..., description="Start time of the linguistic event.")
    timestamp_end: float = Field(..., description="End time of the linguistic event.")
    feature_type: Literal["SpeakingRate", "FillerUsage", "Pauses"] = Field(
        ..., description="Linguistic dimension."
    )
    behavioral_tag: str = Field(
        ...,
        description="Short interpretation, e.g. 'High Cognitive Load', 'Stalling', 'Rehearsed Speech'.",
    )
    intensity_score: float = Field(
        ...,
        description="rz_score for WPS, or 1.0 for the categorical filler/pause anomalies.",
    )
    is_sustained: bool = Field(
        ...,
        description="True if continuous; False if it was a momentary slip.",
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
    ] = Field(
        ..., description="Holistic classification of the subject's verbal fluency in this window."
    )

    detected_anomalies: list[VocabAnomalyEvent] = Field(default_factory=list)

    contradiction_context: str = Field(
        ...,
        description=(
            "Narrative summary of what *changed* in the candidate's speech fluency in this window. "
            "Used by the Pattern Detector to correlate with visual + audio."
        ),
    )


# ---------------------------------------------------------------------------
# Public surface — exposed by the FastAPI backend in M5.
# ---------------------------------------------------------------------------


class CrossModalInsight(BaseModel):
    """A moment where behaviour across modalities + the spoken content tell a coherent story.

    The Pattern Detector emits these only when they are *meaningful* —
    routine spikes that have no cross-modal correlate are not reported.
    """

    timestamp_start: float
    timestamp_end: float

    spoken_content: str = Field(
        ...,
        description="What the candidate was saying during this moment (a short quote).",
    )

    modalities_involved: list[Literal["Visual", "Audio", "Verbal"]] = Field(
        ...,
        description="Which modalities co-occurred to form this pattern.",
    )

    pattern_type: Literal["Strength", "Concern", "Notable"] = Field(
        ...,
        description=(
            "What kind of pattern this is. "
            "'Strength' = signals + content reinforce credibility. "
            "'Concern' = signals contradict the content. "
            "'Notable' = coaching opportunity, neither strong nor deceptive."
        ),
    )

    significance: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Intensity of the pattern (not a moral judgement — see ``pattern_type``).",
    )

    observation: str = Field(
        ...,
        description="One sentence — what happened across the modalities.",
    )

    interpretation: str = Field(
        ...,
        description="One sentence — what the pattern says about the candidate.",
    )


class IntegratedBehavioralReport(BaseModel):
    """The Pattern Detector's output for a single analysis window. Public."""

    time_range_start: float
    time_range_end: float

    overall_window_tone: Literal[
        "Strong_Positive",
        "Authentic",
        "Mostly_Authentic",
        "Mixed_Signals",
        "Concerning",
    ] = Field(
        ...,
        description="Holistic tone of this window. Replaces the older binary 'credibility' framing.",
    )

    executive_summary: str = Field(
        ...,
        description="Maximum two sentences summarising the candidate's behaviour in this window.",
    )

    key_insights: list[CrossModalInsight] = Field(
        default_factory=list,
        description=(
            "Cross-modal patterns found in this window. "
            "Empty list means no meaningful pattern was found."
        ),
    )


class FinalReport(BaseModel):
    """The Judge agent's executive coaching report. Public."""

    executive_summary: str = Field(
        ...,
        description="Holistic 3-4 sentence overview of the candidate's interview performance.",
    )
    behavioral_strengths: str = Field(
        ...,
        description="What went well. Markdown allowed.",
    )
    vulnerabilities_and_triggers: str = Field(
        ...,
        description="What went wrong, grouped by topic / theme. Markdown allowed.",
    )
    areas_for_improvement: str = Field(
        ...,
        description="3-4 actionable pieces of coaching advice. Markdown allowed.",
    )
