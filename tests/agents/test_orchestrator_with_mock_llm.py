"""End-to-end agent chain tests using the stub LLM provider.

The agentic layer is tested with `LLM_PROVIDER=stub` so the tests are
deterministic and free. The stub builds schema-correct outputs from each
window's anomaly content, exercising the orchestrator wiring (window selection,
observer fan-out, Window Analyst field notes — none dropped — and the
Weaver → Editor synthesis).
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
from agents.schemas import FinalReport, WindowAnalysis
from agents.windows import select_windows
from pipeline.io.parquet import load_df_parquet_safe

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_master_df.parquet"


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """All agent-chain tests run against the stub provider — never the real LLM."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")


@pytest.fixture
def master_df() -> pd.DataFrame:
    return load_df_parquet_safe(FIXTURE)


# --------------------------------------------------------------------------
# Window selection
# --------------------------------------------------------------------------


def test_select_windows_finds_two_engineered_ranges(master_df: pd.DataFrame) -> None:
    """The committed fixture has engineered anomalies at [5.0-6.0] blink and
    [22.0-23.5] audio. Window selection should surface both as active windows."""
    windows = select_windows(master_df)
    assert len(windows) >= 2
    starts = [round(w.start, 1) for w in windows]
    assert any(5.0 <= s <= 6.0 for s in starts), starts
    assert any(22.0 <= s <= 23.5 for s in starts), starts


def test_select_windows_modality_tags(master_df: pd.DataFrame) -> None:
    windows = select_windows(master_df)
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
async def test_build_report_keeps_all_windows(master_df: pd.DataFrame) -> None:
    """No window is dropped: every selected window yields a WindowAnalysis with
    a non-empty narrative (the whole point of the rewrite)."""
    journal, final = await build_report(master_df, speaker_label="B", transcript_df=None)
    assert isinstance(final, FinalReport)
    assert len(journal) == len(select_windows(master_df))
    for note in journal:
        assert isinstance(note, WindowAnalysis)
        assert note.narrative, "every window must have a narrative"
    # journal is chronological
    assert [n.time_start for n in journal] == sorted(n.time_start for n in journal)


@pytest.mark.asyncio
async def test_build_report_produces_highlights_from_active_windows(
    master_df: pd.DataFrame,
) -> None:
    """The active (anomaly) windows should surface as signals → highlights."""
    journal, final = await build_report(master_df, speaker_label="B")
    assert any(note.signals for note in journal), "active windows should yield signals"
    assert final.highlights, "highlights should be drawn from the journal's signals"
    for h in final.highlights:
        assert h.ts_start <= h.ts_end


@pytest.mark.asyncio
async def test_build_report_returns_final_report_even_with_no_windows() -> None:
    """An empty master_df still produces a baseline FinalReport — the API
    contract is that `/api/jobs/{id}/report` always returns something."""
    empty = pd.DataFrame()
    journal, final = await build_report(empty, speaker_label="B")
    assert journal == []
    assert isinstance(final, FinalReport)
    assert final.headline  # the stub fills a baseline headline


@pytest.mark.asyncio
async def test_build_report_invokes_on_window_done(master_df: pd.DataFrame) -> None:
    """The optional `on_window_done` callback is the hook the backend uses to
    stream per-window notes as they complete."""
    seen: list[WindowAnalysis] = []

    def cb(note: WindowAnalysis) -> None:
        seen.append(note)

    journal, _ = await build_report(master_df, speaker_label="B", on_window_done=cb)
    assert len(seen) == len(journal)


@pytest.mark.asyncio
async def test_build_report_with_transcript_populates_spoken_content(
    master_df: pd.DataFrame,
) -> None:
    """When transcript data is available, the slice flows into each window's
    `spoken_excerpt` and into the signals' `spoken_content`."""
    transcript = pd.DataFrame(
        [{"start": 0.0, "end": 30.0, "text": "claim about ML expertise", "speaker": "B"}]
    )
    journal, _ = await build_report(master_df, speaker_label="B", transcript_df=transcript)
    spoken = [n for n in journal if n.signals]
    assert spoken, "expected at least one window with signals"
    for note in spoken:
        assert "ML expertise" in note.spoken_excerpt
        for s in note.signals:
            assert s.spoken_content
