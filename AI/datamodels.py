from src.utils.datamodels import *
from pydantic import BaseModel, Field
from typing import Tuple, Literal

class VisualState(BaseModel):
    status: Literal["baseline", "anomalous"] = Field(
        description=""
    )

class VisualReport(BaseModel):
    time_range : Tuple[float, float] = Field(
        ...,
        description="Time frame (start, end) in secs"
        )
    
    

class AudioReport(BaseModel):
    time_range : Tuple[float, float] = Field(
        ...,
        description="Time frame (start, end) in secs"
        )
    
    report : str = Field(
        ...,
        description="Short and Crisp report for the audio data"
        )
    
class VocabReport(BaseModel):
    time_range : Tuple[float, float] = Field(
        ...,
        description="Time frame (start, end) in secs"
        )
    
    report : str = Field(
        ...,
        description="Short and Crisp report for the vocabulary data"
        )
    

class VisualData(BaseModel):
    blink_data : Blink = Field(
        ..., 
        description="User's Blinking data for the given timestamp"
        )
    gaze_data : Gaze = Field(
        ..., 
        description="User's Gaze data for the given timestamp"
        )
    jaw_data : Jaw = Field(
        ...,
        description="User's Jaw movement data for the given timestamp"
        )
    smile_data : Smile = Field(
        ...,
        description="User's Smiling data for the given timestamp"
        )
    
class AudioData(BaseModel):
    loudness_data : LoudnessState = Field(
        ...,
        description="User's Loudeness data for the given timestamp"
        )
    average_pitch_data : PitchState = Field(
        ...,
        description="User's Average Pitch data for the given timestamp"
        )
    pitch_std_data : PitchStd = Field(
        ..., description="User's Pitch standard deviation for the given timestamp"
        )
    
