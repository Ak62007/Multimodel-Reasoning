"""Output schemas for the agentic layer.

Three surfaces:

- **Per-modality anomaly events** (`VisualAnomalyEvent`, …) and **internal
  observer outputs** (`VisualObservation`, …) — consumed only by the Window
  Analyst. Not exposed via API.

- **Per-window field note** (`WindowAnalysis` + `Signal`) — the chronological
  "journal" the agents write as they read the interview. Surfaces via
  `/api/jobs/{id}/segments`. EVERY analysed window produces one (none are
  dropped); a calm window simply has a low-key narrative and few/no signals.

- **Final report** (`FinalReport` + `Highlight` + `Thread`) — the synthesised
  output, surfaced via `/api/jobs/{id}/report`. Its centrepiece is the
  timestamped `highlights` list so the user can jump back into the video.

`WeaverDraft` is the intermediate hand-off from the Pattern Weaver to the
Narrative Editor (structured, so pydantic-ai gets a concrete schema).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Shared vocabularies -------------------------------------------------------

Modality = Literal["Visual", "Audio", "Verbal"]
Relation = Literal["Correlation", "Contradiction", "Isolated"]
# What *kind* of interesting thing this is — deliberately not just good/bad:
#   Strength  — congruent, genuinely positive signal
#   Tell      — a leak suggesting stress / deception / over-claim
#   Tension   — modalities disagree (the classic cross-modal contradiction)
#   Quirk     — odd / idiosyncratic but not clearly good or bad
#   Shift     — a notable change of state (settling down, ramping up)
SignalKind = Literal["Strength", "Tell", "Tension", "Quirk", "Shift"]
Significance = Literal["Low", "Medium", "High"]
InterviewPhase = Literal["Opening", "Early", "Middle", "Late", "Closing"]


# --------------------------------------------------------------------------
# Per-modality anomaly events (carry through observer + analyst).
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
# Internal observer outputs. Consumed only by the Window Analyst.
# --------------------------------------------------------------------------


class VisualObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Window Analyst."""

    time_range_start: float
    time_range_end: float
    overall_visual_state: Literal[
        "Baseline", "Low_Stress", "High_Stress", "Deceptive_Cluster", "Emotional_Breakthrough"
    ]
    detected_anomalies: list[VisualAnomalyEvent] = Field(default_factory=list)
    raw_summary: str = Field(
        default="",
        description="Plain-language read of the raw (non-anomaly) signal levels this window.",
    )
    contradiction_context: str = Field(
        ...,
        description="Concise narrative highlighting what *changed* during this window.",
    )


class AudioObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Window Analyst."""

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
    raw_summary: str = Field(default="", description="Plain-language read of raw vocal levels.")
    contradiction_context: str = Field(
        ..., description="Concise narrative highlighting acoustic shifts during this window."
    )


class VocabObservation(BaseModel):
    """Internal observer output. Not exposed via API. Consumed only by the Window Analyst."""

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
    raw_summary: str = Field(default="", description="Plain-language read of raw fluency levels.")
    contradiction_context: str = Field(
        ..., description="Concise narrative highlighting fluency shifts during this window."
    )


# --------------------------------------------------------------------------
# Per-window field note (public output: the interview "journal").
# --------------------------------------------------------------------------


class Signal(BaseModel):
    """One discrete interesting finding inside a window.

    Unlike the old `CrossModalInsight`, a Signal may involve a SINGLE modality
    (a strong isolated tell still matters). `relation` records how the
    modalities relate to each other; `kind` records what sort of thing it is.
    """

    timestamp_start: float
    timestamp_end: float
    modalities: list[Modality] = Field(
        ..., description="Which modalities this signal draws on (1 or more)."
    )
    relation: Relation = Field(
        ...,
        description=(
            "Correlation: modalities agree/reinforce. Contradiction: they "
            "disagree (e.g. confident words, anxious voice). Isolated: a "
            "single-modality finding."
        ),
    )
    kind: SignalKind = Field(
        ...,
        description="Strength / Tell / Tension / Quirk / Shift — the nature of the finding.",
    )
    headline: str = Field(..., description="A short, vivid title for this moment.")
    evidence: str = Field(
        ..., description="The concrete signals behind it (the actual behaviours/values)."
    )
    spoken_content: str = Field(
        default="", description="What was being said at this moment, if known."
    )
    interpretation: str = Field(..., description="What it plausibly means — one or two sentences.")
    significance: Significance = Field(
        ..., description="How prominent / sustained this signal is."
    )


class WindowAnalysis(BaseModel):
    """One window's field note. Public output. NEVER dropped.

    Even a calm baseline window yields one of these — its narrative just says
    'steady here', which is itself useful for the temporal arc.
    """

    time_start: float
    time_end: float
    phase: InterviewPhase = Field(
        ..., description="Where in the interview this window sits."
    )
    position_pct: float = Field(
        ..., description="Fraction (0-1) of the way through the interview."
    )
    spoken_excerpt: str = Field(
        default="", description="What the candidate was saying during this window."
    )
    visual_read: str = Field(default="", description="One-line plain-language read of the face.")
    audio_read: str = Field(default="", description="One-line plain-language read of the voice.")
    verbal_read: str = Field(default="", description="One-line plain-language read of the speech.")
    narrative: str = Field(
        ...,
        description="The analyst's free-form thoughts on this window — what's interesting or odd.",
    )
    window_interest: Significance = Field(
        ..., description="How interesting this window is overall (Low/Medium/High)."
    )
    signals: list[Signal] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Final report (public output) + synthesis hand-off.
# --------------------------------------------------------------------------


class Highlight(BaseModel):
    """A 'go watch this moment' entry — the heart of the report."""

    ts_start: float
    ts_end: float
    title: str = Field(..., description="Punchy title for the moment.")
    what_happened: str = Field(..., description="What was observed across modalities.")
    why_it_matters: str = Field(..., description="Why this is worth the user's attention.")
    modalities: list[Modality] = Field(default_factory=list)
    kind: SignalKind
    significance: Significance


class Thread(BaseModel):
    """A recurring pattern that shows up across multiple windows."""

    title: str
    summary: str = Field(..., description="What the recurring pattern is.")
    relation: Relation
    occurrences: list[float] = Field(
        default_factory=list, description="Timestamps (seconds) where this thread appears."
    )
    interpretation: str = Field(..., description="What the recurrence suggests overall.")


class WeaverDraft(BaseModel):
    """Pattern Weaver → Narrative Editor hand-off (structured, pre-prose)."""

    headline: str = Field(..., description="One-line takeaway about the whole interview.")
    arc_notes: str = Field(
        ..., description="Rough notes on the behavioral arc (baseline → triggers → recovery)."
    )
    highlights: list[Highlight] = Field(default_factory=list)
    threads: list[Thread] = Field(default_factory=list)


class FinalReport(BaseModel):
    """Synthesised, human-facing report. Public output."""

    headline: str = Field(..., description="One-line takeaway about the interview.")
    overview: str = Field(..., description="Markdown: narrative summary of the whole interview.")
    behavioral_arc: str = Field(
        ..., description="Markdown: how the candidate evolved — baseline, triggers, recovery."
    )
    highlights: list[Highlight] = Field(
        default_factory=list,
        description="The timestamped moments worth re-watching. The report's centrepiece.",
    )
    threads: list[Thread] = Field(
        default_factory=list, description="Recurring cross-window patterns."
    )
    coaching_notes: str = Field(
        default="", description="Markdown: optional constructive takeaways."
    )


__all__ = [
    "AudioAnomalyEvent",
    "AudioObservation",
    "FinalReport",
    "Highlight",
    "InterviewPhase",
    "Modality",
    "Relation",
    "Signal",
    "SignalKind",
    "Significance",
    "Thread",
    "VisualAnomalyEvent",
    "VisualObservation",
    "VocabObservation",
    "VocabularyAnomalyEvent",
    "WeaverDraft",
    "WindowAnalysis",
]
