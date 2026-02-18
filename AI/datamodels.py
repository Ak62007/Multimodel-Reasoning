# from src.utils.datamodels import *
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class VisualAnomalyEvent(BaseModel):
    """A distinct behavioral event detected within the time range."""
    timestamp_start: float = Field(..., description="Start time of the specific anomaly event.")
    timestamp_end: float = Field(..., description="End time of the specific anomaly event.")
    feature_type: Literal["Blink", "Gaze", "Jaw", "Smile"] = Field(..., description="The facial feature involved.")
    behavioral_tag: str = Field(..., description="Psychological interpretation (e.g., 'Rapid Blinking', 'Jaw Clench', 'Fixed Stare').")
    intensity_score: float = Field(..., description="The max absolute rz_score observed during this event (indicates severity).")
    is_sustained: bool = Field(..., description="True if this was a continuous anomaly (state shift), False if it was a micro-expression.")

class VisualAnalysisReport(BaseModel):
    """The final summarized report from the Visual Agent."""
    time_range_start: float
    time_range_end: float
    
    
    overall_visual_state: Literal["Baseline", "Low_Stress", "High_Stress", "Deceptive_Cluster", "Emotional_Breakthrough"] = Field(
        ..., description="The holistic classification of the subject's behavior during this window."
    )
    
    detected_anomalies: List[VisualAnomalyEvent] = Field(
        default_factory=list, 
        description="List of all specific anomalous events identified. Empty list implies normal behavior."
    )
    
    contradiction_context: str = Field(
        ..., 
        description="A concise narrative summary explicitly highlighting what *changed*. "
                    "Example: 'Subject maintained baseline until t=78s, where a sustained high-intensity blink cluster (rz=3.7) occurred, coincident with jaw micro-movements.'"
    )
    
class AudioAnomalyEvent(BaseModel):
    """A distinct paralinguistic event detected within the time range."""
    timestamp_start: float = Field(..., description="Start time of the specific anomaly event.")
    timestamp_end: float = Field(..., description="End time of the specific anomaly event.")
    feature_type: Literal["Loudness", "Pitch", "Expressiveness"] = Field(..., description="The acoustic dimension involved.")
    
    behavioral_tag: str = Field(
        ..., 
        description="Psychological interpretation. Examples: 'Sudden Whisper', 'Monotone Dissociation', 'High-Pitch Stress', 'Vocal Fry'."
    )
    
    intensity_score: float = Field(
        ..., 
        description="The max absolute rz_score observed during this event. Higher = more intense deviation."
    )
    
    is_sustained: bool = Field(
        ..., 
        description="True if this was a continuous anomaly (state shift), False if it was a momentary break."
    )

class AudioAnalysisReport(BaseModel):
    """The final summarized report from the Audio Agent."""
    time_range_start: float
    time_range_end: float
    
    # The "Vibe" of the voice
    overall_vocal_state: Literal[
        "Baseline_Calm", 
        "Suppressed/Timid", 
        "Aggressive/Dominant", 
        "Stressed/Tight", 
        "Robotic/Rehearsed", 
        "Volatile"
    ] = Field(
        ..., description="The holistic classification of the subject's vocal demeanor during this window."
    )
    
    # Detailed breakdown
    detected_anomalies: List[AudioAnomalyEvent] = Field(
        default_factory=list, 
        description="List of all specific paralinguistic anomalies identified. Empty list implies normal speech."
    )
    
    # Synthesis for the next agent
    contradiction_context: str = Field(
        ..., 
        description="A concise narrative summary explicitly highlighting acoustic shifts. "
                    "Example: 'Subject's volume dropped significantly (rz=-18) at 57s, transitioning into a whisper while pitch flattened, suggesting sudden hesitation or secrecy.'"
    )
    
class VocabularyAnomalyEvent(BaseModel):
    """A distinct linguistic or cognitive event detected within the time range."""
    timestamp_start: float = Field(..., description="Start time of the specific anomaly event.")
    timestamp_end: float = Field(..., description="End time of the specific anomaly event.")
    feature_type: Literal["SpeakingRate", "FillerUsage", "Pauses"] = Field(..., description="The linguistic dimension involved.")
    
    behavioral_tag: str = Field(
        ..., 
        description="Psycholinguistic interpretation. Examples: 'High Cognitive Load', 'Rapid-Fire Defense', 'Stalling/Hesitation', 'Rehearsed Speech'."
    )
    
    intensity_score: float = Field(
        ..., 
        description="The magnitude of the deviation. Use rz_score for WPS. For categorical anomalies (Fillers/Pauses), use 1.0 for 'abnormally high'."
    )
    
    is_sustained: bool = Field(
        ..., 
        description="True if this was a continuous anomaly (state shift), False if it was a momentary slip."
    )

class VocabularyAnalysisReport(BaseModel):
    """The final summarized report from the Vocabulary Agent."""
    time_range_start: float
    time_range_end: float
    
    # The "Flow" of the speech
    overall_verbal_state: Literal[
        "Baseline_Fluent", 
        "Cognitively_Overloaded", 
        "Anxious/Rushed", 
        "Guarded/Slow", 
        "Disorganized"
    ] = Field(
        ..., description="The holistic classification of the subject's verbal fluency during this window."
    )
    
    # Detailed breakdown
    detected_anomalies: List[VocabularyAnomalyEvent] = Field(
        default_factory=list, 
        description="List of all specific linguistic anomalies identified. Empty list implies normal, fluent speech."
    )
    
    # Synthesis for the next agent
    contradiction_context: str = Field(
        ..., 
        description="A concise narrative summary explicitly highlighting fluency shifts. "
                    "Example: 'Subject's speech rate spiked (rz=2.6) at 114s, indicating anxiety, followed immediately by a cluster of abnormal pauses, suggesting they lost their train of thought or were fabricating.'"
    )


class CrossModalInsight(BaseModel):
    """
    A specific instance where behavior, voice, and words interact meaningfully.
    """
    timestamp_start: float = Field(..., description="Start time of this specific insight.")
    timestamp_end: float = Field(..., description="End time of this specific insight.")
    
    # Context: What was happening?
    spoken_content_snippet: str = Field(
        ..., 
        description="The specific text segment spoken during this time range (including [*] markers)."
    )
    topic_context: str = Field(
        ..., 
        description="Brief tag of the topic being discussed (e.g., 'Technical Explanation', 'Personal Intro', 'Answering a difficult question')."
    )
    
    # Evidence: What did we see/hear?
    active_anomalies: List[str] = Field(
        ..., 
        description="List of specific anomalies active here (e.g., ['Visual: Micro-frown', 'Audio: Pitch Drop', 'Verbal: Stutter'])."
    )
    
    # Analysis: What does it mean?
    observation_type: str = Field(
        ..., 
        description="Short category for the behavior. Examples: 'Feigned Enthusiasm', 'Cognitive Overload', 'Fabrication Leakage', 'Defensive Posturing', 'Honest Uncertainty'."
    )
    
    detailed_analysis: str = Field(
        ..., 
        description="The core reasoning. Explain the link between the text and the behavior. "
                    "Example: 'While claiming to be very interested in the field, the subject's pitch flattened and they broke eye contact, contradicting the verbal sentiment.'"
    )
    
    suspicion_level: float = Field(
        ..., 
        ge=0.0, le=10.0, 
        description="A score from 0-10 indicating how likely this indicates deception or negative concealement. 0=Truthful/Normal, 10=High Certainty Deception."
    )

class IntegratedBehavioralReport(BaseModel):
    """The Master Report for the time window."""
    time_range_start: float
    time_range_end: float
    
    # The Narrative Verdict
    executive_summary: str = Field(
        ..., 
        description="A high-level psychological profile of the subject during this segment. "
                    "Discuss their baseline demeanor, how they handled pressure, and their overall credibility."
    )
    
    # Specific Findings
    key_insights: List[CrossModalInsight] = Field(
        default_factory=list, 
        description="Chronological list of significant behavioral insights found in this window."
    )