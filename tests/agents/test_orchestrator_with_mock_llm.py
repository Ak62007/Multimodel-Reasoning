"""End-to-end agent chain tests using the stub LLM provider.

Per spec §10, the agentic layer is tested with `LLM_PROVIDER=stub` so the
tests are deterministic and free. The stub builds schema-correct outputs
from each window's anomaly content, exercising the orchestrator wiring
(window selection, observer fan-out, Pattern Detector branching on
multi-modal activity, drop-empty-windows behavior, Judge aggregation).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agents._extract import (
    extract_audio_events,
    extract_transcript_slice,
    extract_visual_events,
    extract_vocab_events,
)
from agents.orchestrator import build_report
from agents.schemas import FinalReport, IntegratedBehavioralReport
from agents.windows import select_windows
from pipeline.io.parquet import load_df_parquet_safe

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_master_df.parquet"


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """All M4 tests run against the stub provider — never the real LLM."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")


@pytest.fixture
def master_df() -> pd.DataFrame:
    return load_df_parquet_safe(FIXTURE)


# --------------------------------------------------------------------------
# Window selection
# --------------------------------------------------------------------------


def test_select_windows_finds_two_engineered_ranges(master_df: pd.DataFrame) -> None:
    """The committed fixture has engineered anomalies at [5.0-6.0] blink and
    [22.0-23.5] audio. Window selection should surface both as windows."""
    windows = select_windows(master_df)
    assert len(windows) >= 2
    starts = [round(w.start, 1) for w in windows]
    assert any(5.0 <= s <= 6.0 for s in starts), starts
    assert any(22.0 <= s <= 23.5 for s in starts), starts


def test_select_windows_modality_tags(master_df: pd.DataFrame) -> None:
    windows = select_windows(master_df)
    # The blink window covers Visual; the audio window covers Audio.
    visual_window = next(w for w in windows if 5.0 <= w.start <= 6.0)
    audio_window = next(w for w in windows if 22.0 <= w.start <= 23.5)
    assert "Visual" in visual_window.modalities_with_anomalies
    assert "Audio" in audio_window.modalities_with_anomalies


def test_select_windows_returns_empty_for_empty_df() -> None:
    assert select_windows(pd.DataFrame()) == []


# --------------------------------------------------------------------------
# Event extraction
# --------------------------------------------------------------------------


def test_extract_visual_events_finds_blink(master_df: pd.DataFrame) -> None:
    # The fixture's blink anomaly is at Time = 5.0–6.0
    slice_df = master_df[(master_df["Time"] >= 5.0) & (master_df["Time"] <= 6.0)].reset_index(
        drop=True
    )
    events = extract_visual_events(slice_df)
    assert any(ev.feature_type == "Blink" for ev in events)


def test_extract_audio_events_finds_loudness(master_df: pd.DataFrame) -> None:
    slice_df = master_df[(master_df["Time"] >= 22.0) & (master_df["Time"] <= 23.5)].reset_index(
        drop=True
    )
    events = extract_audio_events(slice_df)
    assert any(ev.feature_type in ("Loudness", "Pitch") for ev in events)


def test_extract_transcript_slice_filters_by_time_and_speaker() -> None:
    transcript = pd.DataFrame(
        [
            {"start": 0.0, "end": 1.5, "text": "Hi I'm A", "speaker": "A"},
            {"start": 1.5, "end": 3.0, "text": "I worked on ML", "speaker": "B"},
            {"start": 3.0, "end": 5.0, "text": "Tell me more", "speaker": "A"},
        ]
    )
    out = extract_transcript_slice(transcript, 1.0, 4.0, speaker_label="B")
    assert out == "I worked on ML"


def test_extract_transcript_slice_handles_missing_transcript() -> None:
    assert extract_transcript_slice(None, 0.0, 5.0) == ""
    assert extract_transcript_slice(pd.DataFrame(), 0.0, 5.0) == ""


# --------------------------------------------------------------------------
# Agent chain end-to-end (stub provider)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_report_drops_empty_windows(master_df: pd.DataFrame) -> None:
    """The stub returns empty `key_insights` for single-modality windows; the
    orchestrator should silently drop them from the public output."""
    public_reports, final = await build_report(master_df, speaker_label="B", transcript_df=None)
    assert isinstance(final, FinalReport)
    # Public output excludes the single-modality windows ⇒ count < windows-selected count.
    # The fixture's blink-only window has only Visual events ⇒ dropped.
    # The audio window has Audio events only ⇒ dropped (Pattern Detector needs ≥2 modalities).
    # In stub mode, empty key_insights drops the window. Combined window (if
    # ranges merge) could have both → kept.
    for r in public_reports:
        assert r.key_insights, "Reports with empty key_insights should have been dropped"


@pytest.mark.asyncio
async def test_build_report_returns_final_report_even_with_no_windows() -> None:
    """An empty master_df should still produce a baseline FinalReport — the
    API contract is that `/api/jobs/{id}/report` always returns something."""
    empty = pd.DataFrame()
    reports, final = await build_report(empty, speaker_label="B")
    assert reports == []
    assert isinstance(final, FinalReport)
    assert final.executive_summary  # the stub fills a baseline message


@pytest.mark.asyncio
async def test_build_report_invokes_on_window_done(master_df: pd.DataFrame) -> None:
    """The optional `on_window_done` callback is the hook the backend uses to
    stream per-window reports to the frontend as they complete."""
    seen: list[IntegratedBehavioralReport] = []

    def cb(r: IntegratedBehavioralReport) -> None:
        seen.append(r)

    public_reports, _ = await build_report(master_df, speaker_label="B", on_window_done=cb)
    assert len(seen) == len(public_reports)


@pytest.mark.asyncio
async def test_build_report_with_transcript_populates_spoken_content(
    master_df: pd.DataFrame,
) -> None:
    """When transcript data is available, the stub propagates the slice into
    each CrossModalInsight's `spoken_content`."""
    transcript = pd.DataFrame(
        [{"start": 0.0, "end": 30.0, "text": "claim about ML expertise", "speaker": "B"}]
    )
    public_reports, _ = await build_report(master_df, speaker_label="B", transcript_df=transcript)
    for r in public_reports:
        for ins in r.key_insights:
            assert ins.spoken_content  # always populated
