"""Timestamped transcription via `whisper-timestamped`.

We deliberately load the audio with librosa instead of `wp.load_audio` because
the latter shells out to a system `ffmpeg` binary on PATH, which is an extra
install step that's easy to miss. librosa+soundfile use moviepy's already-
bundled audio backends and produce the same `float32` mono 16 kHz waveform
that whisper-timestamped expects.
"""

from __future__ import annotations

import logging
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import whisper_timestamped as wp

_log = logging.getLogger(__name__)

_WHISPER_SAMPLE_RATE = 16_000


def get_whisper_data(
    audio_path: str | Path,
    model_size: str = "small",
    lang: str | None = None,
    device: str = "cpu",
) -> pd.DataFrame:
    audio_path = str(audio_path)
    _log.info("Loading whisper model: %s on %s", model_size, device)
    model = wp.load_model(model_size, device=device)

    _log.info("Loading audio for whisper: %s", audio_path)
    waveform, _sr = librosa.load(audio_path, sr=_WHISPER_SAMPLE_RATE, mono=True)
    waveform = waveform.astype(np.float32)

    _log.info("Running whisper transcription (%d samples)", waveform.shape[0])
    result = wp.transcribe_timestamped(
        model=model, audio=waveform, language=lang, detect_disfluencies=True
    )

    return pd.DataFrame(result["segments"])
