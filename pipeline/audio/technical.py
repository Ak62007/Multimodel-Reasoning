"""Per-window technical audio features (RMS loudness, pitch mean/variance,
silence flag). Produced from the extracted WAV; consumed by the merge step.
"""

from __future__ import annotations

import logging
from pathlib import Path

import librosa
import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


def analyze_audio_layers(
    audio_path: str | Path, segment_length: float = 0.5
) -> pd.DataFrame | None:
    """Window the audio at `segment_length` seconds and compute per-window RMS,
    average pitch, pitch variance, and a silence flag.

    Returns a DataFrame indexed by `Time` (window start, in seconds) with columns:
    `audio_rms`, `audio_pitch_avg`, `audio_pitch_var`, `is_silent`.

    Returns None if the audio file is missing.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        _log.error("Audio file not found: %s", audio_path)
        return None

    y, sr = librosa.load(str(audio_path), sr=None)
    total_duration = librosa.get_duration(y=y, sr=sr)

    rows: list[dict] = []

    for t in np.arange(0, total_duration, segment_length):
        start_sample = int(t * sr)
        end_sample = int((t + segment_length) * sr)
        chunk = y[start_sample:end_sample]

        if len(chunk) == 0:
            break

        # FEATURE 1: AMPLITUDE (loudness)
        rms = np.mean(librosa.feature.rms(y=chunk))

        # FEATURE 2: SILENCE DETECTION (0.005 ≈ webcam noise floor)
        is_silent = rms < 0.005

        # FEATURE 3 & 4: PITCH (mean = vocal register; variance = expressiveness)
        avg_pitch = 0
        pitch_var = 0
        if not is_silent:
            f0, _voiced_flag, _ = librosa.pyin(
                chunk,
                fmin=float(librosa.note_to_hz("C2")),
                fmax=float(librosa.note_to_hz("C5")),
                sr=sr,
                frame_length=2048,
            )
            valid_pitch = f0[~np.isnan(f0)]
            if len(valid_pitch) > 0:
                avg_pitch = np.mean(valid_pitch)
                pitch_var = np.std(valid_pitch)

        rows.append(
            {
                "Time": round(float(t), 2),
                "audio_rms": round(float(rms), 4),
                "audio_pitch_avg": round(float(avg_pitch), 2),
                "audio_pitch_var": round(float(pitch_var), 2),
                "is_silent": bool(is_silent),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("Time").reset_index(drop=True)
    return df
