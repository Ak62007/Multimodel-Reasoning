"""Align face / audio-technical / linguistic / utterance streams on the
0.5-second master timeline.

Exact-join on `Time` after each stream is binned to the same window grid.
Speaker labels are layered on by `pipeline.features.linguistic.assign_speakers`.
"""

from __future__ import annotations

import logging

import pandas as pd

from pipeline.features.linguistic import assign_speakers, words_to_windows

_log = logging.getLogger(__name__)


def merge_streams(
    face_df: pd.DataFrame,
    audio_df: pd.DataFrame,
    whisper_df: pd.DataFrame,
    utterances_df: pd.DataFrame,
    *,
    window_size: float = 0.5,
) -> pd.DataFrame:
    """Combine face, audio, whisper-derived linguistic, and utterance speaker
    labels into one master raw dataframe keyed by `Time` (window start, sec).

    The result columns:
    - `Time` (sec)
    - face blendshapes + `h_ratio`/`v_ratio`
    - `audio_rms`, `audio_pitch_avg`, `audio_pitch_var`, `is_silent`
    - `words`, `text_concat`, `wps`, `filler_percentage`, `pause_percent_pr`
    - `speaker`
    """
    if face_df is None or face_df.empty:
        raise ValueError("face_df is empty — face feature extraction failed.")
    if audio_df is None or audio_df.empty:
        raise ValueError("audio_df is empty — audio feature extraction failed.")

    # Round to 2 decimal places to avoid floating-point joins missing matches.
    face_df = face_df.copy()
    audio_df = audio_df.copy()
    face_df["Time"] = face_df["Time"].round(2)
    audio_df["Time"] = audio_df["Time"].round(2)

    av_merged = pd.merge(left=face_df, right=audio_df, on="Time", how="inner")

    # Linguistic features
    word_windows = words_to_windows(whisper_df, window_size=window_size)
    if not word_windows.empty:
        word_windows["Time"] = word_windows["Time"].round(2)
        avw_merged = pd.merge(left=av_merged, right=word_windows, on="Time", how="left")
    else:
        avw_merged = av_merged.copy()
        avw_merged["words"] = [[] for _ in range(len(avw_merged))]
        avw_merged["text_concat"] = ""
        avw_merged["wps"] = 0.0
        avw_merged["filler_percentage"] = 0.0
        avw_merged["pause_percent_pr"] = 1.0

    # Speaker labels
    avw_merged = assign_speakers(avw_merged, utterances_df, time_col="Time")
    avw_merged = avw_merged.sort_values("Time").reset_index(drop=True)

    _log.info(
        "Merged streams: %d rows × %d cols (window=%.2fs)",
        len(avw_merged),
        avw_merged.shape[1],
        window_size,
    )
    return avw_merged


__all__ = ["merge_streams"]
