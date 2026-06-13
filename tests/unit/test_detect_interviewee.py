"""Unit tests for the interviewee auto-detection heuristic."""

from __future__ import annotations

import pandas as pd

from pipeline.features.linguistic import detect_interviewee


def _utterances(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["speaker", "start", "end"])


def test_picks_speaker_with_most_total_time() -> None:
    # A asks short questions; B gives long answers → B is the interviewee.
    df = _utterances(
        [
            ("A", 0.0, 2.0),
            ("B", 2.0, 20.0),
            ("A", 20.0, 23.0),
            ("B", 23.0, 50.0),
        ]
    )
    assert detect_interviewee(df) == "B"


def test_total_time_beats_turn_count() -> None:
    # A takes many short turns but B holds the floor far longer overall.
    df = _utterances(
        [("A", t, t + 0.5) for t in range(0, 10)] + [("B", 10.0, 60.0)]
    )
    assert detect_interviewee(df) == "B"


def test_falls_back_when_empty() -> None:
    assert detect_interviewee(pd.DataFrame()) == "B"


def test_falls_back_when_no_speaker_column() -> None:
    df = pd.DataFrame({"start": [0.0], "end": [1.0], "text": ["hi"]})
    assert detect_interviewee(df) == "B"


def test_custom_fallback() -> None:
    assert detect_interviewee(pd.DataFrame(), fallback="A") == "A"


def test_ignores_null_speakers() -> None:
    df = pd.DataFrame(
        {
            "speaker": ["A", None, "C"],
            "start": [0.0, 1.0, 2.0],
            "end": [1.0, 30.0, 40.0],
        }
    )
    # The long None-speaker utterance is dropped; C (38s) beats A (1s).
    assert detect_interviewee(df) == "C"
