from pydantic import BaseModel, Field
from typing import Literal, Union

class Blink(BaseModel):
    """Eye blinking behavior extracted per time frame"""

    intensity: float = Field(
        ge=0.0, le=1.0,
        description="Normalized eyelid closure strength; 0 means fully open eyes, 1 means fully closed"
    )

    asymmetry: float = Field(
        ge=0.0, le=1.0,
        description="Absolute difference in closure between left and right eye; higher means uneven blinking"
    )

    is_blinking: bool = Field(
        ...,
        description="True if eyelid closure exceeds blink threshold (e.g., >0.5), indicating an intentional blink"
    )
    
    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of eye blink movement after temporal smoothing. "
            "Negative values indicate less-than-usual eye blink movement, positive values indicate more-than-usual eye blink movement."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=("True if blink behavior deviates significantly from the speaker’s typical blinking pattern"
                     "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))

    
class Gaze(BaseModel):
    """Head-normalized gaze direction and attention signals per frame"""

    horizontal_deviation: float = Field(
        description="Horizontal gaze offset where -1 indicates strong left, 0 centered, +1 strong right"
    )

    vertical_deviation: float = Field(
        description="Vertical gaze offset where -1 indicates down, 0 centered, +1 looking up"
    )

    primary_direction: Literal["center", "left", "right", "up", "down"] = Field(
        ...,
        description="Dominant gaze direction derived from combined horizontal and vertical deviations"
    )
    
    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of eye movement after temporal smoothing. "
            "Negative values indicate less-than-usual eye movement, positive values indicate more-than-usual eye movement."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=("True if gaze direction or movement is unusually unstable or extreme over time"
                     "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))

    
class Jaw(BaseModel):
    """Jaw movement and articulation dynamics per frame"""

    open: float = Field(
        ..., ge=0.0, le=1.0,
        description="Degree of jaw opening; 0 is fully closed, 1 is maximally open"
    )

    lateral: float = Field(
        ge=-1.0, le=1.0,
        description="Side-to-side jaw movement; -1 left, 0 centered, +1 right"
    )

    forward: float = Field(
        ge=0.0, le=1.0,
        description="Forward jaw protrusion relative to neutral position"
    )

    is_open: bool = Field(
        ...,
        description="True if jaw opening exceeds speech-relevant threshold (e.g., >0.3)"
    )
    
    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of jaw movement after temporal smoothing. "
            "Negative values indicate less-than-usual jaw movement, positive values indicate more-than-usual jaw movement."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=("True if jaw movement intensity or pattern deviates from speaker’s baseline articulation"
                     "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))

    
class Smile(BaseModel):
    """Facial smiling expression and symmetry per frame"""

    intensity: float = Field(
        ..., ge=0.0, le=1.0,
        description="Overall smile strength; 0 is neutral face, 1 is full smile"
    )

    asymmetry: float = Field(
        ge=0.0, le=1.0,
        description="Difference between left and right smile activation; higher means uneven smile"
    )

    left_intensity: float = Field(
        ge=0.0, le=1.0,
        description="Smile activation strength on the left side of the mouth"
    )

    right_intensity: float = Field(
        ge=0.0, le=1.0,
        description="Smile activation strength on the right side of the mouth"
    )

    mouth_stretch: float = Field(
        ge=0.0, le=1.0,
        description="Horizontal mouth expansion indicating smile width rather than curvature"
    )

    is_smiling: bool = Field(
        ...,
        description="True if smile intensity exceeds expression threshold (e.g., >0.3)"
    )
    
    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of smile intensity after temporal smoothing. "
            "Negative values indicate less-than-usual smile intensity, positive values indicate more-than-usual smile intensity."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=("True if smiling behavior is unusually strong, absent, or unstable for the speaker"
                     "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))

    
class LoudnessState(BaseModel):
    level: Literal[
        "very_quiet",
        "quiet",
        "normal",
        "loud",
        "very_loud"
    ] = Field(
        ...,
        description=(
            "Categorical loudness level of the speaker at this time step, "
            "computed relative to the speaker’s own median loudness. "
            "Represents perceptual vocal intensity, not raw decibels."
        )
    )

    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of loudness after temporal smoothing. "
            "Negative values indicate quieter-than-usual speech, positive values indicate louder-than-usual speech."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=(
            "True if loudness deviates abnormally from the speaker’s typical pattern "
            "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))

    
class PitchState(BaseModel):
    relative_level: Literal[
        "much_lower",
        "lower",
        "normal",
        "higher",
        "much_higher"
    ] = Field(
        ...,
        description=(
            "Relative pitch height compared to the speaker’s baseline pitch. "
            "Indicates whether the speaker is talking noticeably lower or higher than usual."
        )
    )

    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score of pitch deviation (in semitones) relative to the speaker’s median pitch. "
            "Captures sustained pitch shifts rather than short-term noise."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=(
            "True if pitch deviation is statistically unusual for the speaker, "
            "suggesting stress, excitement, uncertainty, or emphasis."
            "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))


class PitchStd(BaseModel):
    expressiveness: Literal[
        "flat",
        "slightly_expressive",
        "expressive",
        "highly_expressive"
    ] = Field(
        ...,
        description=(
            "Degree of pitch variability over a short time window. "
            "Low values indicate monotone speech; high values indicate dynamic, expressive intonation."
        )
    )

    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score of pitch variability (standard deviation) after smoothing. "
            "Higher values mean more pitch modulation than the speaker’s norm."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=(
            "True if pitch expressiveness is unusually high or low compared to the speaker’s baseline, "
            "potentially signaling emotional or cognitive shifts."
            "based on anomaly detection (e.g., RRCF or MAD threshold)."
        )
    )
    
    continuos_anomaly: bool = Field(..., description="True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames.")
    
    part_of_anomalous_range: list[float] | None = Field(
        description=("List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."))


class WPS(BaseModel):
    speaking_rate: Literal[
        "very_slow",
        "slow",
        "normal",
        "fast",
        "very_fast"
    ] = Field(
        ...,
        description=(
            "Categorical speaking rate level relative to the speaker’s baseline. "
            "Captures how slowly or quickly the speaker is talking over a short time window."
        )
    )

    rz_score: float = Field(
        ...,
        description=(
            "Robust z-score (median/MAD-based) of words-per-second after temporal smoothing. "
            "Negative values indicate slower-than-usual speech, positive values indicate faster-than-usual speech."
        )
    )

    is_anomalous: bool = Field(
        ...,
        description=(
            "True if speaking rate deviates abnormally from the speaker’s typical pattern, "
            "as determined by anomaly detection (e.g., RRCF score or MAD threshold)."
        )
    )

    continuous_anomaly: bool = Field(
        ...,
        description=(
            "True if this frame is part of a sustained speaking-rate anomaly spanning multiple consecutive frames."
        )
    )

    part_of_anomalous_range: list[float] | None = Field(
        default=None,
        description=(
            "List of timestamps (in seconds) representing the full continuous time interval "
            "to which this anomalous speaking-rate frame belongs."
        )
    )

