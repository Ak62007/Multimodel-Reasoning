"""MMR data pipeline.

Modules:
- video: frame extraction, face landmark/blendshape extraction
- audio: waveform extraction, librosa features, transcription
- features: raw → interpretable feature transforms, linguistic metrics
- anomaly: RRCF anomaly detection and continuous-range grouping
- io: parquet round-trip helpers and path conventions
- schemas: Pydantic models for per-frame containers (Blink, Gaze, ...)
- merge: aligns the four streams onto one timeline
- orchestrator: end-to-end runner (video path → final master parquet)
"""

__version__ = "0.1.0"
