"""Window slicing helpers shared by every agent module.

A :class:`WindowSlice` packages everything an agent needs to reason about
a single analysis window: the time range, the rows of the master
dataframe inside that range, and the transcript slice (if any). The
slicing functions live here rather than in each agent module so that the
formatting / data extraction logic is testable in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class WindowSlice:
    """A snapshot of the master dataframe for one analysis window."""

    start: float
    end: float
    speaker: str
    rows: pd.DataFrame
    transcript_rows: pd.DataFrame | None

    @property
    def spoken_text(self) -> str:
        """Concatenated speaker text inside the window."""
        if self.transcript_rows is not None and "text_concat" in self.transcript_rows.columns:
            chunks = [
                str(t)
                for t in self.transcript_rows["text_concat"].tolist()
                if isinstance(t, str) and t
            ]
            if chunks:
                return " ".join(chunks)
        # Fall back to whatever the master rows carry.
        if "text_concat" in self.rows.columns:
            chunks = [str(t) for t in self.rows["text_concat"].tolist() if isinstance(t, str) and t]
            return " ".join(chunks)
        return ""

    def extract_visual_anomalies(self) -> list[dict[str, Any]]:
        return self._extract_anomalies(
            (
                ("blinking_data", "Blink"),
                ("gaze_data", "Gaze"),
                ("jaw_movement_data", "Jaw"),
                ("smile_data", "Smile"),
            )
        )

    def extract_audio_anomalies(self) -> list[dict[str, Any]]:
        return self._extract_anomalies(
            (
                ("loudness_data", "Loudness"),
                ("average_pitch_data", "Pitch"),
                ("pitch_standard_deviation", "Expressiveness"),
            )
        )

    def extract_vocab_anomalies(self) -> list[dict[str, Any]]:
        return self._extract_anomalies(
            (
                ("words_per_sec", "SpeakingRate"),
                ("filler_words_usage", "FillerUsage"),
                ("pauses_taken", "Pauses"),
            )
        )

    def _extract_anomalies(
        self,
        columns: tuple[tuple[str, str], ...],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for col, feature_type in columns:
            if col not in self.rows.columns:
                continue
            for i, cell in enumerate(self.rows[col]):
                if not isinstance(cell, dict):
                    continue
                if not cell.get("is_anomalous"):
                    continue
                t = float(self.rows.iloc[i].get("Time", 0.0))
                out.append(
                    {
                        "time": t,
                        "feature_type": feature_type,
                        "rz_score": float(cell.get("rz_score", 0.0)),
                        "is_sustained": bool(cell.get("continuous_anomaly", False)),
                    }
                )
        return out


def slice_window(
    master_df: pd.DataFrame,
    start: float,
    end: float,
    speaker: str,
    transcript_df: pd.DataFrame | None = None,
) -> WindowSlice:
    """Return a :class:`WindowSlice` covering ``[start, end]`` of the master."""
    rows = master_df.loc[(master_df["Time"] >= start) & (master_df["Time"] <= end)].copy()
    transcript_rows: pd.DataFrame | None = None
    if transcript_df is not None and "Time" in transcript_df.columns:
        transcript_rows = transcript_df.loc[
            (transcript_df["Time"] >= start) & (transcript_df["Time"] <= end)
        ].copy()
    return WindowSlice(
        start=start,
        end=end,
        speaker=speaker,
        rows=rows,
        transcript_rows=transcript_rows,
    )


def format_visual_input(slice_: WindowSlice) -> str:
    return _format_input(
        slice_,
        title="Visual",
        anomalies=slice_.extract_visual_anomalies(),
    )


def format_audio_input(slice_: WindowSlice) -> str:
    return _format_input(
        slice_,
        title="Audio",
        anomalies=slice_.extract_audio_anomalies(),
    )


def format_vocab_input(slice_: WindowSlice) -> str:
    return _format_input(
        slice_,
        title="Vocabulary",
        anomalies=slice_.extract_vocab_anomalies(),
    )


def _format_input(
    slice_: WindowSlice,
    *,
    title: str,
    anomalies: list[dict[str, Any]],
) -> str:
    lines = [
        f"# {title} window",
        f"Time range: {slice_.start:.2f}s - {slice_.end:.2f}s",
        f"Speaker: {slice_.speaker}",
        "",
    ]
    if anomalies:
        lines.append("Anomalies inside this window:")
        for a in anomalies:
            sustained = " [sustained]" if a["is_sustained"] else ""
            lines.append(
                f"  - t={a['time']:.2f}s  {a['feature_type']}  rz={a['rz_score']:+.2f}{sustained}"
            )
    else:
        lines.append("No anomalies detected inside this window.")
    lines.append("")
    spoken = slice_.spoken_text
    if spoken:
        lines.append("Transcript inside this window:")
        lines.append(f'  "{spoken}"')
    return "\n".join(lines)


def format_pattern_detector_input(
    slice_: WindowSlice,
    visual: object,
    audio: object,
    vocab: object,
) -> str:
    """Bundle the three observations + spoken content for the Pattern Detector."""
    return (
        f"# Analysis window\n"
        f"Time range: {slice_.start:.2f}s - {slice_.end:.2f}s\n"
        f"Speaker: {slice_.speaker}\n\n"
        f"## Visual observation\n{visual}\n\n"
        f"## Audio observation\n{audio}\n\n"
        f"## Vocabulary observation\n{vocab}\n\n"
        f'## What the candidate was saying\n"{slice_.spoken_text}"\n'
    )
