"""Time-aligned merge of the four pipeline streams into a master dataframe.

Inputs
------

``face_df``        — face features, one row per video frame (~1 fps).
``audio_df``       — acoustic features, one row per 0.5 s window.
``utterances_df``  — AssemblyAI utterances (text, start ms, end ms, speaker).
``whisper_df``     — Whisper segments containing a ``words`` list-of-dicts
                     with per-word ``start`` / ``end`` / ``text``.

Output
------

A dataframe at **0.5-second resolution** whose columns include:

- ``Time`` (seconds, float)
- visual features: ``h_ratio``, ``v_ratio``, and the 52 MediaPipe blendshapes
- acoustic features: ``audio_rms``, ``audio_pitch_avg``, ``audio_pitch_var``,
  ``is_silent``
- transcript columns: ``words`` (``list[str]`` per window),
  ``text_concat`` (``str``), ``speaker`` (``str | None``)

The resolution choice (0.5 s, audio-driven) reproduces the legacy
``av_merged`` -> ``aligned_avw_merged`` step in
``legacy_notebooks/data_ana_merge.ipynb`` while keeping every audio row
intact (the legacy notebook did an inner join on ``Time`` which silently
dropped the half-second audio rows). The decision and tradeoffs are
captured in ``DECISIONS.md``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

WINDOW_SIZE_S: float = 0.5


def merge_streams(
    face_df: pd.DataFrame,
    audio_df: pd.DataFrame,
    utterances_df: pd.DataFrame,
    whisper_df: pd.DataFrame,
    *,
    window_size: float = WINDOW_SIZE_S,
) -> pd.DataFrame:
    """Align all four streams onto a ``window_size``-second time grid."""
    if audio_df.empty:
        raise ValueError("audio_df is empty — cannot align other streams")

    aligned_face = _align_face_to_audio_grid(face_df, audio_df["Time"].to_numpy())
    merged = audio_df.merge(aligned_face, on="Time", how="left", suffixes=("", "_face"))
    logger.info("Joined audio + face: %d rows x %d cols", *merged.shape)

    words_grid = _aggregate_whisper_words(whisper_df, audio_df["Time"].to_numpy(), window_size)
    merged = merged.merge(words_grid, on="Time", how="left")

    merged["speaker"] = _assign_speakers(merged["Time"].to_numpy(), utterances_df)

    logger.info(
        "Merged master at %.2fs resolution: %d rows x %d cols",
        window_size,
        *merged.shape,
    )
    return merged


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _align_face_to_audio_grid(
    face_df: pd.DataFrame,
    audio_times: np.ndarray,
) -> pd.DataFrame:
    """Resample face features (~1 fps) onto the audio's 0.5 s grid.

    Forward-fills the nearest preceding face row for each audio timestamp.
    Returns a frame whose ``Time`` column exactly equals ``audio_times``.
    """
    if face_df.empty:
        return pd.DataFrame({"Time": audio_times})

    face_sorted = face_df.sort_values("Time").reset_index(drop=True)
    target = pd.DataFrame({"Time": np.asarray(audio_times)})
    aligned = pd.merge_asof(
        target,
        face_sorted,
        on="Time",
        direction="backward",
        tolerance=1.0,
    )
    return aligned


def _aggregate_whisper_words(
    whisper_df: pd.DataFrame,
    audio_times: np.ndarray,
    window_size: float,
) -> pd.DataFrame:
    """Bin Whisper words into ``audio_times`` windows.

    Returns a frame with three columns: ``Time``, ``words`` (``list[str]``),
    ``text_concat`` (``str``).
    """
    words = _flatten_whisper_words(whisper_df)
    grid_times = np.asarray(audio_times, dtype=float)

    if words.empty:
        return pd.DataFrame(
            {
                "Time": grid_times,
                "words": [[] for _ in grid_times],
                "text_concat": ["" for _ in grid_times],
            }
        )

    out: list[dict[str, object]] = []
    half = window_size / 2.0
    for t in grid_times:
        lo = float(t) - half
        hi = float(t) + half
        mask = (words["start"] >= lo) & (words["start"] < hi)
        bin_words = words.loc[mask, "text"].astype(str).tolist()
        out.append(
            {
                "Time": float(t),
                "words": bin_words,
                "text_concat": " ".join(bin_words),
            }
        )
    return pd.DataFrame(out)


def _flatten_whisper_words(whisper_df: pd.DataFrame) -> pd.DataFrame:
    """Flatten the ``words`` lists in a Whisper segments dataframe."""
    if whisper_df.empty or "words" not in whisper_df.columns:
        return pd.DataFrame(columns=["text", "start", "end"])

    rows: list[dict[str, float | str]] = []
    for words in whisper_df["words"]:
        if not isinstance(words, list):
            continue
        for word in words:
            if not isinstance(word, dict):
                continue
            text = word.get("text")
            start = word.get("start")
            end = word.get("end")
            if text is None or start is None or end is None:
                continue
            rows.append({"text": str(text), "start": float(start), "end": float(end)})
    return pd.DataFrame(rows)


def _assign_speakers(
    times: np.ndarray,
    utterances_df: pd.DataFrame,
) -> pd.Series:
    """Return a per-row speaker label for every time in ``times``.

    AssemblyAI returns start/end in milliseconds; we convert to seconds.
    A timestamp ``t`` is assigned the speaker of any utterance with
    ``start_s <= t < end_s``.
    """
    speakers: list[str | None] = [None] * len(times)
    if utterances_df.empty:
        return pd.Series(speakers, index=range(len(times)), name="speaker")

    for _, row in utterances_df.iterrows():
        try:
            start_s = float(row["start"]) / 1000.0
            end_s = float(row["end"]) / 1000.0
        except (KeyError, TypeError, ValueError):
            continue
        speaker = row.get("speaker") if isinstance(row, dict) else row["speaker"]
        if speaker is None:
            continue
        for i, t in enumerate(times):
            if start_s <= float(t) < end_s:
                speakers[i] = str(speaker)

    return pd.Series(speakers, index=range(len(times)), name="speaker")
