"""Per-window acoustic feature extraction.

Slices the audio file into ``segment_length``-second windows and computes:

* ``audio_rms`` — RMS energy (a proxy for loudness / volume).
* ``audio_pitch_avg`` — mean fundamental frequency in Hz over the window.
* ``audio_pitch_var`` — pitch standard deviation in Hz (expressiveness).
* ``is_silent`` — True when RMS falls below the noise floor.

The default window of 0.5 s matches the rest of the pipeline. Column names
were previously ``audio_rms(volumn)`` and ``audio_pitch_var(expressiveness)``;
those parens/typo names were retired in M2 (see DECISIONS.md).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import librosa
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def analyze_audio_layers(
    audio_path: str | Path,
    segment_length: float = 0.5,
    *,
    silence_threshold: float = 0.005,
) -> pd.DataFrame | None:
    """Extract per-window acoustic features.

    Args:
        audio_path: Path to a WAV audio file.
        segment_length: Window size in seconds. Default 0.5 s.
        silence_threshold: RMS below which a window is flagged as silent.

    Returns:
        Dataframe with one row per window, sorted by ``Time``. ``None`` if
        the audio file does not exist.
    """
    audio_path = str(audio_path)
    if not os.path.exists(audio_path):
        logger.error("Audio file not found: %s", audio_path)
        return None

    y, sr = librosa.load(audio_path, sr=None)
    total_duration = librosa.get_duration(y=y, sr=sr)

    rows: list[dict[str, float | bool]] = []

    for t in np.arange(0, total_duration, segment_length):
        start_sample = int(t * sr)
        end_sample = int((t + segment_length) * sr)
        chunk = y[start_sample:end_sample]

        if len(chunk) == 0:
            break

        rms = float(np.mean(librosa.feature.rms(y=chunk)))
        is_silent = rms < silence_threshold

        avg_pitch = 0.0
        pitch_var = 0.0
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
                avg_pitch = float(np.mean(valid_pitch))
                pitch_var = float(np.std(valid_pitch))

        rows.append(
            {
                "Time": round(float(t), 2),
                "audio_rms": round(rms, 4),
                "audio_pitch_avg": round(avg_pitch, 2),
                "audio_pitch_var": round(pitch_var, 2),
                "is_silent": is_silent,
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("Time").reset_index(drop=True)
    logger.info("Computed %d audio technical rows", len(df))
    return df
