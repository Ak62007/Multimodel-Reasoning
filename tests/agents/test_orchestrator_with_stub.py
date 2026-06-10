"""End-to-end agent-orchestrator tests using the deterministic stub provider.

These tests exercise the full chain (windows -> three observers ->
pattern detector -> judge) without making any LLM calls, by forcing
``LLM_PROVIDER=stub``.
"""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from agents import build_report
from agents._stub import (
    stub_audio_observation,
    stub_integrated_report,
    stub_visual_observation,
    stub_vocab_observation,
)
from agents._window_slice import WindowSlice, slice_window
from agents.audio_agent import run_audio_observer
from agents.judge_agent import run_judge
from agents.profiler_agent import run_pattern_detector
from agents.schemas import (
    AudioObservation,
    FinalReport,
    IntegratedBehavioralReport,
    VisualObservation,
    VocabObservation,
)
from agents.visual_agent import run_visual_observer
from agents.vocab_agent import run_vocab_observer
from agents.windows import select_windows


@pytest.fixture(autouse=True)
def force_stub_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file runs against the stub backend."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")


# ---------------------------------------------------------------------------
# Window selection
# ---------------------------------------------------------------------------


def test_select_windows_finds_fixture_anomalies(
    tiny_master_df: pd.DataFrame, fixture_meta: dict
) -> None:
    windows = select_windows(tiny_master_df)
    assert len(windows) == 2
    # Both fixture ranges are recovered.
    starts = sorted(w.start for w in windows)
    ends = sorted(w.end for w in windows)
    assert starts == [
        min(fixture_meta["blink_anomaly_range"]),
        min(fixture_meta["pitch_anomaly_range"]),
    ]
    assert ends == [
        max(fixture_meta["blink_anomaly_range"]),
        max(fixture_meta["pitch_anomaly_range"]),
    ]


def test_select_windows_empty_when_no_anomalies() -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "blinking_data": [
                {"part_of_anomalous_range": None},
                {"part_of_anomalous_range": None},
                {"part_of_anomalous_range": None},
            ],
        }
    )
    assert select_windows(df) == []


def test_select_windows_merges_adjacent_ranges() -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0],
            "blinking_data": [{"part_of_anomalous_range": [5.0, 5.5, 6.0]}],
            "loudness_data": [{"part_of_anomalous_range": [6.5, 7.0]}],
        }
    )
    windows = select_windows(df, gap_tolerance=1.0)
    assert len(windows) == 1
    assert windows[0].start == 5.0
    assert windows[0].end == 7.0


# ---------------------------------------------------------------------------
# Individual agent functions dispatching to the stub
# ---------------------------------------------------------------------------


def _make_slice(tiny_master_df: pd.DataFrame, start: float, end: float) -> WindowSlice:
    return slice_window(master_df=tiny_master_df, start=start, end=end, speaker="B")


def test_visual_agent_routes_to_stub(tiny_master_df: pd.DataFrame) -> None:
    slice_ = _make_slice(tiny_master_df, 5.0, 7.0)
    result = asyncio.run(run_visual_observer(slice_))
    assert isinstance(result, VisualObservation)
    assert result.time_range_start == 5.0
    # Stub recognises the blink anomalies in the fixture.
    assert len(result.detected_anomalies) >= 1


def test_audio_agent_routes_to_stub(tiny_master_df: pd.DataFrame) -> None:
    slice_ = _make_slice(tiny_master_df, 18.0, 21.0)
    result = asyncio.run(run_audio_observer(slice_))
    assert isinstance(result, AudioObservation)
    assert len(result.detected_anomalies) >= 1


def test_vocab_agent_routes_to_stub(tiny_master_df: pd.DataFrame) -> None:
    slice_ = _make_slice(tiny_master_df, 0.0, 30.0)
    result = asyncio.run(run_vocab_observer(slice_))
    assert isinstance(result, VocabObservation)


def test_pattern_detector_routes_to_stub(tiny_master_df: pd.DataFrame) -> None:
    slice_ = _make_slice(tiny_master_df, 5.0, 7.0)
    v = stub_visual_observation(slice_)
    a = stub_audio_observation(slice_)
    voc = stub_vocab_observation(slice_)
    report = asyncio.run(run_pattern_detector(slice_, v, a, voc))
    assert isinstance(report, IntegratedBehavioralReport)
    assert len(report.key_insights) >= 1


def test_judge_routes_to_stub() -> None:
    final = asyncio.run(run_judge([]))
    assert isinstance(final, FinalReport)
    assert "deterministic stub" in final.executive_summary.lower()


# ---------------------------------------------------------------------------
# Full build_report chain
# ---------------------------------------------------------------------------


def test_build_report_runs_end_to_end(
    tiny_master_df: pd.DataFrame, tiny_transcript_df: pd.DataFrame
) -> None:
    reports, final = asyncio.run(
        build_report(
            tiny_master_df,
            speaker_label="B",
            transcript_df=tiny_transcript_df,
        )
    )
    assert isinstance(final, FinalReport)
    # Two anomalous windows in the fixture, each emits one insight via the stub.
    assert len(reports) == 2
    assert all(isinstance(r, IntegratedBehavioralReport) for r in reports)
    assert all(r.key_insights for r in reports)


def test_build_report_chronological_order(
    tiny_master_df: pd.DataFrame,
) -> None:
    reports, _ = asyncio.run(build_report(tiny_master_df, speaker_label="B"))
    times = [r.time_range_start for r in reports]
    assert times == sorted(times)


def test_build_report_filters_empty_windows(
    tiny_master_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the Pattern Detector emits empty insights, that window is dropped."""
    from agents import orchestrator

    async def empty_pattern_detector(
        slice_: WindowSlice,
        visual: VisualObservation,
        audio: AudioObservation,
        vocab: VocabObservation,
        *,
        model: str | None = None,
    ) -> IntegratedBehavioralReport:
        return IntegratedBehavioralReport(
            time_range_start=slice_.start,
            time_range_end=slice_.end,
            overall_window_tone="Authentic",
            executive_summary="Nothing notable.",
            key_insights=[],
        )

    monkeypatch.setattr(orchestrator, "run_pattern_detector", empty_pattern_detector)
    reports, _ = asyncio.run(build_report(tiny_master_df, speaker_label="B"))
    assert reports == []


def test_on_window_done_callback_fires(tiny_master_df: pd.DataFrame) -> None:
    seen: list[IntegratedBehavioralReport] = []

    def cb(report: IntegratedBehavioralReport) -> None:
        seen.append(report)

    reports, _ = asyncio.run(build_report(tiny_master_df, speaker_label="B", on_window_done=cb))
    assert len(seen) == len(reports)


def test_build_report_empty_master_returns_no_reports() -> None:
    empty = pd.DataFrame({"Time": [0.0, 0.5], "blinking_data": [None, None]})
    reports, final = asyncio.run(build_report(empty, speaker_label="B"))
    assert reports == []
    assert isinstance(final, FinalReport)


def test_build_report_continues_after_window_error(
    tiny_master_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single window erroring should not fail the whole job."""
    from agents import orchestrator

    call_count = {"n": 0}

    async def flaky_pattern_detector(
        slice_: WindowSlice,
        visual: VisualObservation,
        audio: AudioObservation,
        vocab: VocabObservation,
        *,
        model: str | None = None,
    ) -> IntegratedBehavioralReport:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated failure")
        return stub_integrated_report(slice_, visual, audio, vocab)

    monkeypatch.setattr(orchestrator, "run_pattern_detector", flaky_pattern_detector)

    # Disable retries by patching the runtime helper so the failure surfaces fast.
    async def _no_retry(coro_factory, *, attempts=3, **kwargs):  # type: ignore[no-untyped-def]
        return await coro_factory()

    monkeypatch.setattr(orchestrator, "with_retry", _no_retry)

    reports, _ = asyncio.run(build_report(tiny_master_df, speaker_label="B"))
    # First window errored, second one succeeded.
    assert len(reports) == 1
