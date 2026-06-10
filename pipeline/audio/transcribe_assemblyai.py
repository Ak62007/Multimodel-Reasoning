"""AssemblyAI speaker-diarised transcription.

Produces a per-utterance dataframe with text, start/end (in **milliseconds**,
to match AssemblyAI's payload), speaker label, words, and confidence. The
merge step converts the timestamps to seconds and aligns them onto the
master time grid.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import assemblyai as aai
import pandas as pd

logger = logging.getLogger(__name__)


def get_utterances_data(
    audio_path: str | Path,
    *,
    api_key: str | None = None,
) -> pd.DataFrame:
    """Transcribe ``audio_path`` with speaker diarisation enabled.

    Args:
        audio_path: Path to the WAV file.
        api_key: AssemblyAI API key. If ``None``, reads ``ASSEMBLYAI_API_KEY``
            from the environment.

    Returns:
        Dataframe with one row per utterance. Empty dataframe if the audio
        produces no utterances.

    Raises:
        RuntimeError: If the API call fails.
        ValueError: If no API key is available.
    """
    key = api_key or os.environ.get("ASSEMBLYAI_API_KEY")
    if not key:
        raise ValueError(
            "AssemblyAI API key is missing — set ASSEMBLYAI_API_KEY or pass api_key explicitly"
        )

    aai.settings.api_key = key
    logger.info("Submitting %s to AssemblyAI for transcription", audio_path)

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(
        str(audio_path),
        config=aai.TranscriptionConfig(speaker_labels=True),
    )

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"Transcription failed: {transcript.error}")

    rows: list[dict[str, object]] = []
    for utt in transcript.utterances or []:
        rows.append(
            {
                "text": utt.text,
                "start": utt.start,
                "end": utt.end,
                "confidence": utt.confidence,
                "speaker": utt.speaker,
                "channel": utt.channel,
                "words": utt.words,
                "translated_texts": utt.translated_texts,
            }
        )

    logger.info("Received %d utterances from AssemblyAI", len(rows))
    return pd.DataFrame(rows)
