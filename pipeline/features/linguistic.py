"""Linguistic features per 0.5-second window: words-per-second, filler %,
pause %.

Computed by binning whisper-timestamped word-level results into the same
time grid as the face/audio streams.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)

# whisper-timestamped marks disfluencies (uh, um, ...) with a trailing `[*]`.
# Treat any token containing this marker, or matching a small filler set,
# as a filler.
_FILLER_TOKENS = {"uh", "um", "uhm", "er", "hmm", "ah", "like", "you know"}


def is_filler(token: str) -> bool:
    t = token.strip().lower().strip(".,!?")
    return "[*]" in t or t in _FILLER_TOKENS


def words_to_windows(whisper_segments: pd.DataFrame, window_size: float = 0.5) -> pd.DataFrame:
    """Flatten whisper segments into a per-window dataframe.

    Returns columns: `Time` (window start), `words` (list[str]), `text_concat`
    (joined string), `wps`, `filler_percentage`, `pause_percent_pr`.

    `pause_percent_pr` is 1.0 for completely-silent windows (no words bound to
    that window), 0.0 otherwise — a coarse but workable proxy that matches the
    legacy notebook's bookkeeping for `PausePercentageIncrease`.
    """
    rows: list[dict] = []
    if whisper_segments.empty:
        return pd.DataFrame(
            columns=["Time", "words", "text_concat", "wps", "filler_percentage", "pause_percent_pr"]
        )

    # Flatten word list out of every segment
    flat_words: list[dict] = []
    for _, seg in whisper_segments.iterrows():
        seg_words = seg.get("words") or []
        for w in seg_words:
            # whisper-timestamped word records: {"text": ..., "start": ..., "end": ..., "confidence": ...}
            start = float(w.get("start", w.get("begin", 0.0)))
            flat_words.append({"start": start, "text": str(w.get("text", ""))})

    if not flat_words:
        return pd.DataFrame(
            columns=["Time", "words", "text_concat", "wps", "filler_percentage", "pause_percent_pr"]
        )

    max_time = max(w["start"] for w in flat_words) + window_size
    grid = np.arange(0, max_time + window_size, window_size)

    for t in grid:
        bucket = [w for w in flat_words if t <= w["start"] < t + window_size]
        words_list = [w["text"] for w in bucket]
        n = len(words_list)
        n_fillers = sum(1 for w in words_list if is_filler(w))
        rows.append(
            {
                "Time": round(float(t), 2),
                "words": words_list,
                "text_concat": " ".join(words_list).strip(),
                "wps": n / window_size,
                "filler_percentage": (n_fillers / n) if n else 0.0,
                "pause_percent_pr": 0.0 if n else 1.0,
            }
        )

    return pd.DataFrame(rows)


def assign_speakers(
    target: pd.DataFrame, utterances: pd.DataFrame, time_col: str = "Time"
) -> pd.DataFrame:
    """Inject a `speaker` column into `target` from utterances.

    Utterances `start`/`end` must be in **seconds** (the AssemblyAI loader
    normalizes from milliseconds at its boundary). Rows whose `Time` falls in
    `[start, end)` get tagged with that utterance's speaker label; rows outside
    any utterance get None.
    """
    target = target.copy()
    target["speaker"] = None
    if utterances.empty:
        return target

    for _, row in utterances[["start", "end", "speaker"]].iterrows():
        mask = (target[time_col] >= row["start"]) & (target[time_col] < row["end"])
        target.loc[mask, "speaker"] = row["speaker"]
    return target


def detect_interviewee(utterances: pd.DataFrame, *, fallback: str = "B") -> str:
    """Heuristically pick which diarized speaker is the interviewee.

    In an interview the interviewer asks short questions and the interviewee
    gives the long answers, so the interviewee holds the floor for far more
    total time. We sum each speaker's speaking duration and take the max,
    breaking ties on utterance count. Falls back to `fallback` when there is no
    usable diarization (empty / single-speaker / missing `speaker` column).
    """
    if utterances is None or utterances.empty or "speaker" not in utterances.columns:
        return fallback
    df = utterances.dropna(subset=["speaker"])
    if df.empty:
        return fallback

    durations = (df["end"].astype(float) - df["start"].astype(float)).clip(lower=0.0)
    by_speaker = (
        pd.DataFrame({"speaker": df["speaker"].astype(str), "dur": durations})
        .groupby("speaker")["dur"]
        .agg(total="sum", turns="count")
        .sort_values(["total", "turns"], ascending=False)
    )
    if by_speaker.empty:
        return fallback
    winner = str(by_speaker.index[0])
    _log.info(
        "Interviewee auto-detection: %s",
        ", ".join(
            f"{spk}={row.total:.1f}s/{int(row.turns)}turns" for spk, row in by_speaker.iterrows()
        ),
    )
    return winner


def get_speaker_segments(utterances: pd.DataFrame, speaker: str) -> list[tuple[float, float]]:
    """Return `[(start_sec, end_sec), ...]` for one speaker. Utterances must be in seconds."""
    if utterances.empty:
        return []
    matched = utterances[utterances["speaker"] == speaker]
    return [(float(r["start"]), float(r["end"])) for _, r in matched.iterrows()]


__all__ = [
    "assign_speakers",
    "detect_interviewee",
    "get_speaker_segments",
    "is_filler",
    "words_to_windows",
]
