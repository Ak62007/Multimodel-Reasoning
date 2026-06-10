"""Whisper-timestamped transcription with disfluency detection.

Returns one row per Whisper *segment* with word-level timestamps inside
``words`` (a list of dicts). The merge step flattens this into per-word
rows aligned onto the master time grid.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
import whisper_timestamped as wp

logger = logging.getLogger(__name__)


def get_whisper_data(
    audio_path: str | Path,
    model_size: str | None = None,
    lang: str | None = None,
    device: str | None = None,
) -> pd.DataFrame:
    """Run Whisper-timestamped on ``audio_path``.

    Args:
        audio_path: Path to the WAV file.
        model_size: Whisper model size (``tiny``, ``small``, …). Falls back
            to ``WHISPER_MODEL_SIZE`` env var, then ``small``.
        lang: Optional language hint. ``None`` lets Whisper auto-detect.
        device: ``cpu``, ``cuda``, ``mps``. Falls back to ``WHISPER_DEVICE``
            env var, then ``cpu``.

    Returns:
        Dataframe with one row per Whisper segment.
    """
    model_size = model_size or os.environ.get("WHISPER_MODEL_SIZE", "small")
    device = device or os.environ.get("WHISPER_DEVICE", "cpu")

    logger.info("Loading Whisper model: size=%s device=%s", model_size, device)
    audio = wp.load_audio(file=str(audio_path))
    model = wp.load_model(model_size, device=device)

    result = wp.transcribe_timestamped(
        model=model,
        audio=audio,
        language=lang,
        detect_disfluencies=True,
    )

    segments = pd.DataFrame(result["segments"])
    logger.info("Whisper produced %d segments", len(segments))
    return segments
