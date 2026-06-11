"""Agent chain orchestrator.

Flow:

    master_df + transcript_df
      -> select_windows()                 # active + baseline, with temporal context
      -> per window (bounded concurrency):
            visual / audio / vocab observers (parallel)  ->  Window Analyst
                -> WindowAnalysis          # always produced; never dropped
      -> journal = all WindowAnalyses, chronological
      -> Pattern Weaver(journal)           -> WeaverDraft
      -> Narrative Editor(draft)           -> FinalReport

Public surface:

    async def build_report(
        master_df, speaker_label="B", transcript_df=None,
        *, model=None, on_window_done=None,
    ) -> tuple[list[WindowAnalysis], FinalReport]
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
    summarize_audio_raw,
    summarize_visual_raw,
    summarize_vocab_raw,
)
from agents._settings import AgentSettings, get_agent_settings
from agents.audio_agent import run_audio_observer
from agents.narrative_editor import run_narrative_editor
from agents.pattern_weaver import run_pattern_weaver
from agents.schemas import FinalReport, WindowAnalysis
from agents.visual_agent import run_visual_observer
from agents.vocab_agent import run_vocab_observer
from agents.window_analyst import run_window_analyst
from agents.windows import AnalysisWindow, select_windows

_log = logging.getLogger(__name__)


async def _process_window(
    window: AnalysisWindow,
    transcript_df: pd.DataFrame | None,
    speaker_label: str,
    settings: AgentSettings,
    sem: asyncio.Semaphore,
) -> WindowAnalysis | None:
    """Observers (parallel) + Window Analyst for one window.

    Returns None only on irrecoverable failure (the window is skipped); a calm
    window still returns a populated WindowAnalysis.
    """
    async with sem:
        try:
            visual_events = extract_visual_events(window.rows)
            audio_events = extract_audio_events(window.rows)
            vocab_events = extract_vocab_events(window.rows)
            transcript = extract_transcript_slice(
                transcript_df, window.start, window.end, speaker_label=speaker_label
            )

            visual, audio, vocab = await asyncio.gather(
                run_visual_observer(
                    window.start,
                    window.end,
                    visual_events,
                    raw_summary=summarize_visual_raw(window.rows),
                    settings=settings,
                ),
                run_audio_observer(
                    window.start,
                    window.end,
                    audio_events,
                    raw_summary=summarize_audio_raw(window.rows),
                    settings=settings,
                ),
                run_vocab_observer(
                    window.start,
                    window.end,
                    vocab_events,
                    raw_summary=summarize_vocab_raw(window.rows),
                    settings=settings,
                ),
            )

            return await run_window_analyst(
                window, visual, audio, vocab, transcript, settings=settings
            )
        except Exception:
            _log.exception("Window %.2f–%.2fs failed — skipping", window.start, window.end)
            return None


async def build_report(
    master_df: pd.DataFrame,
    speaker_label: str = "B",
    transcript_df: pd.DataFrame | None = None,
    *,
    model: str | None = None,
    on_window_done: Callable[[WindowAnalysis], None] | None = None,
) -> tuple[list[WindowAnalysis], FinalReport]:
    """Run the agent chain over the master dataframe.

    Returns `(journal, final_report)` — the chronological list of per-window
    field notes and the synthesised report. `model` (when provided) overrides
    `LLM_MODEL` for this call only.
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

    journal: list[WindowAnalysis] = []
    if windows:
        sem = asyncio.Semaphore(settings.agent_max_concurrency)
        tasks = [_process_window(w, transcript_df, speaker_label, settings, sem) for w in windows]
        for note in await asyncio.gather(*tasks):
            if note is None:
                continue
            journal.append(note)
            if on_window_done is not None:
                try:
                    on_window_done(note)
                except Exception:
                    _log.exception("on_window_done callback raised")

        journal.sort(key=lambda r: r.time_start)

    draft = await run_pattern_weaver(journal, settings=settings)
    final_report = await run_narrative_editor(draft, settings=settings)
    _log.info(
        "Agent chain complete: %d window notes, %d highlight(s), %d thread(s)",
        len(journal),
        len(final_report.highlights),
        len(final_report.threads),
    )
    return journal, final_report


__all__ = ["build_report"]
