"""Agent chain orchestrator — wires observers + Pattern Detector + Judge.

Public surface (spec §9.3):

    async def build_report(
        master_df: pd.DataFrame,
        speaker_label: str = "B",
        transcript_df: pd.DataFrame | None = None,
        *,
        model: str | None = None,
        on_window_done: Callable | None = None,
    ) -> tuple[list[IntegratedBehavioralReport], FinalReport]
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import pandas as pd

from agents._extract import (
    extract_audio_events,
    extract_transcript_slice,
    extract_visual_events,
    extract_vocab_events,
)
from agents._settings import AgentSettings, get_agent_settings
from agents.audio_agent import run_audio_observer
from agents.judge_agent import run_judge
from agents.profiler_agent import run_pattern_detector
from agents.schemas import FinalReport, IntegratedBehavioralReport
from agents.visual_agent import run_visual_observer
from agents.vocab_agent import run_vocab_observer
from agents.windows import AnalysisWindow, select_windows

_log = logging.getLogger(__name__)


async def _process_window(
    window: AnalysisWindow,
    transcript_df: pd.DataFrame | None,
    speaker_label: str,
    settings: AgentSettings,
    sem: asyncio.Semaphore,
) -> IntegratedBehavioralReport | None:
    """Run observers + pattern detector for one window. Returns None on
    irrecoverable failure (so the orchestrator can skip the window)."""
    async with sem:
        try:
            visual_events = extract_visual_events(window.rows)
            audio_events = extract_audio_events(window.rows)
            vocab_events = extract_vocab_events(window.rows)
            transcript = extract_transcript_slice(
                transcript_df, window.start, window.end, speaker_label=speaker_label
            )

            # Run observers concurrently — they don't depend on each other.
            visual, audio, vocab = await asyncio.gather(
                run_visual_observer(window.start, window.end, visual_events, settings=settings),
                run_audio_observer(window.start, window.end, audio_events, settings=settings),
                run_vocab_observer(window.start, window.end, vocab_events, settings=settings),
            )

            report = await run_pattern_detector(
                window.start,
                window.end,
                visual,
                audio,
                vocab,
                transcript,
                settings=settings,
            )
            return report
        except Exception:
            _log.exception("Window %.2f–%.2fs failed — skipping", window.start, window.end)
            return None


async def build_report(
    master_df: pd.DataFrame,
    speaker_label: str = "B",
    transcript_df: pd.DataFrame | None = None,
    *,
    model: str | None = None,
    on_window_done: Callable[[IntegratedBehavioralReport], None] | None = None,
) -> tuple[list[IntegratedBehavioralReport], FinalReport]:
    """Run the agent chain over the final master dataframe.

    Returns `(per_window_reports, final_report)`. Per-modality observer
    outputs are NOT returned — they are internal scaffolding. Reports whose
    Pattern Detector produced empty `key_insights` are silently dropped.

    `model` (when provided) overrides `LLM_MODEL` for this call only.
    """
    settings = get_agent_settings()
    if model is not None:
        settings = settings.model_copy(update={"llm_model": model})

    windows = select_windows(master_df)
    _log.info(
        "Agent chain: %d windows, provider=%s, model=%s, concurrency=%d",
        len(windows),
        settings.llm_provider,
        settings.llm_model,
        settings.agent_max_concurrency,
    )

    if not windows:
        # Nothing to analyse — the Judge still produces a "baseline" report
        # so the API always has a FinalReport to return.
        final = await run_judge([], settings=settings)
        return [], final

    sem = asyncio.Semaphore(settings.agent_max_concurrency)
    tasks = [_process_window(w, transcript_df, speaker_label, settings, sem) for w in windows]
    raw_reports = await asyncio.gather(*tasks)

    # Drop None (errored) and reports with empty key_insights (no meaningful pattern).
    public_reports: list[IntegratedBehavioralReport] = []
    for r in raw_reports:
        if r is None:
            continue
        if not r.key_insights:
            _log.debug(
                "Dropping window %.2f–%.2fs from public output (empty key_insights)",
                r.time_range_start,
                r.time_range_end,
            )
            continue
        public_reports.append(r)
        if on_window_done is not None:
            try:
                on_window_done(r)
            except Exception:
                _log.exception("on_window_done callback raised")

    public_reports.sort(key=lambda r: r.time_range_start)

    final_report = await run_judge(public_reports, settings=settings)
    _log.info(
        "Agent chain complete: %d/%d windows produced public reports",
        len(public_reports),
        len(windows),
    )
    return public_reports, final_report


__all__ = ["build_report"]
