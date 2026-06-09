"""Diarized transcription via AssemblyAI.

Produces one row per utterance with `text`, `start`, `end`, `confidence`,
`speaker`, `channel`, `words`, `translated_texts`. `start`/`end` are in
milliseconds — the merge step rescales to seconds.
"""

from __future__ import annotations

import logging
from pathlib import Path

import assemblyai as aai
import pandas as pd

_log = logging.getLogger(__name__)


def get_utterances_data(api_key: str, audio_path: str | Path) -> pd.DataFrame:
    aai.settings.api_key = api_key

    _log.info("Uploading audio to AssemblyAI: %s", audio_path)
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(
        str(audio_path), config=aai.TranscriptionConfig(speaker_labels=True)
    )

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

    _log.info("AssemblyAI transcription complete: %d utterances", len(transcript.utterances))
    # AssemblyAI returns milliseconds; normalize to seconds at the boundary so
    # downstream merge/feature code can treat all timestamps uniformly.
    utt_rows = [
        {
            "text": utt.text,
            "start": utt.start / 1000.0,
            "end": utt.end / 1000.0,
            "confidence": utt.confidence,
            "speaker": utt.speaker,
            "channel": utt.channel,
            "words": utt.words,
            "translated_texts": utt.translated_texts,
        }
        for utt in transcript.utterances
    ]
    return pd.DataFrame(utt_rows)
