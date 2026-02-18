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
    

    
