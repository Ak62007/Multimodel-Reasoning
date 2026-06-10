"""Linguistic features computed on the merged master dataframe.

The three features here are all measured at 0.5-second windows for the
target speaker (default ``"B"``):

- ``wps``                — words per second in the window (excludes the
                            Whisper disfluency token ``[*]``).
- ``filler_percentage``  — cumulative % of the speaker's total words that
                            are fillers (``[*]``), up to that point.
- ``pause_percent_pr``   — cumulative pause time as a % of total duration,
                            measured at every window where the speaker
                            said nothing.

The cumulative counters are then forward- and back-filled across the
whole timeline so every row has a value.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FILLER_TOKEN: str = "[*]"
WINDOW_SIZE_S: float = 0.5


def compute_linguistic_features(
    master_df: pd.DataFrame,
    speaker: str = "B",
    *,
    window_size: float = WINDOW_SIZE_S,
) -> pd.DataFrame:
    """Return ``master_df`` with ``wps``, ``filler_percentage`` and
    ``pause_percent_pr`` columns added (or overwritten).
    """
    df = master_df.copy()

    df["wps"] = _compute_wps(df, speaker=speaker, window_size=window_size)
    df["filler_percentage"] = _compute_filler_percentage(df, speaker=speaker)
    df["pause_percent_pr"] = _compute_pause_percentage(df, speaker=speaker, window_size=window_size)

    logger.info("Added linguistic features for speaker %s", speaker)
    return df


def _compute_wps(
    df: pd.DataFrame,
    speaker: str,
    window_size: float,
) -> pd.Series:
    """Words-per-second per window for ``speaker``. NaN elsewhere."""
    wps = pd.Series(index=df.index, dtype=float)
    mask = df["speaker"] == speaker
    for idx in df.index[mask]:
        words = df.at[idx, "words"]
        if isinstance(words, list):
            count = sum(1 for w in words if w != FILLER_TOKEN)
            wps.at[idx] = count / window_size
        else:
            wps.at[idx] = 0.0
    return wps


def _compute_filler_percentage(
    df: pd.DataFrame,
    speaker: str,
) -> pd.Series:
    """Cumulative filler % of ``speaker``'s total words.

    Same semantics as ``master_df_ana.ipynb`` — at every speaker-B row we
    record (cumulative_filler_count / total_speaker_words) * 100, then
    forward/back-fill so every row in the table has a value.
    """
    total_words = 0
    for words in df.loc[df["speaker"] == speaker, "words"]:
        if isinstance(words, list):
            total_words += len(words)

    out = pd.Series(index=df.index, dtype=float)
    if total_words == 0:
        return out.ffill().bfill().fillna(0.0)

    cnt = 0
    for idx in df.index[df["speaker"] == speaker]:
        words = df.at[idx, "words"]
        if isinstance(words, list):
            cnt += sum(1 for w in words if w == FILLER_TOKEN)
        out.at[idx] = (cnt / total_words) * 100.0

    return out.ffill().bfill().fillna(0.0)


def _compute_pause_percentage(
    df: pd.DataFrame,
    speaker: str,
    window_size: float,
) -> pd.Series:
    """Cumulative pause %% over total duration, populated at pause rows.

    A pause row is one where ``speaker == speaker`` AND ``text_concat`` is
    empty. Each such row contributes ``window_size`` to the running pause
    duration. Forward/back-filled across the dataframe afterwards.
    """
    out = pd.Series(index=df.index, dtype=float)
    if df["Time"].empty:
        return out

    total_duration = float(df["Time"].iloc[-1])
    if total_duration <= 0:
        return out.ffill().bfill().fillna(0.0)

    pause_mask = (df["speaker"] == speaker) & (df["text_concat"].fillna("") == "")
    cumulative = 0.0
    for idx in df.index[pause_mask]:
        cumulative += window_size
        out.at[idx] = (cumulative / total_duration) * 100.0

    return out.ffill().bfill().fillna(0.0)
