"""Public surface of the agentic layer.

::

    master_df                                      transcript_df (optional)
        │                                                  │
        ▼                                                  │
    agents.windows.select_windows  ◄───────────────────────┘
        │
        │  per analysis window (bounded concurrency)
        ▼
    visual_observer  audio_observer  vocab_observer    (internal scaffolding)
        └──────────────────┬──────────────────┘
                           ▼
                   pattern_detector  →  IntegratedBehavioralReport
                           │
                  (filtered for non-empty windows)
                           ▼
                       judge_agent  →  FinalReport

Per §9 the only publicly-returned values are the list of non-empty
``IntegratedBehavioralReport``s and the final ``FinalReport``. The three
observer outputs are internal scaffolding for the Pattern Detector.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import pandas as pd

from agents._runtime import get_max_concurrency, with_retry
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
from agents.windows import AnalysisWindow, select_windows

logger = logging.getLogger(__name__)


async def build_report(
    master_df: pd.DataFrame,
    speaker_label: str = "B",
    transcript_df: pd.DataFrame | None = None,
    *,
    model: str | None = None,
    on_window_done: Callable[[IntegratedBehavioralReport], None] | None = None,
    max_concurrency: int | None = None,
) -> tuple[list[IntegratedBehavioralReport], FinalReport]:
    """Run the agent chain over the master dataframe.

    Args:
        master_df: Master dataframe produced by ``pipeline.orchestrator``.
        speaker_label: AssemblyAI label of the candidate (default ``"B"``).
        transcript_df: Optional transcript dataframe keyed on ``Time``.
        model: Override the Groq model id (defaults to ``LLM_MODEL`` env).
        on_window_done: Optional callback invoked with each successful
            (non-empty) per-window report as it completes - useful for
            streaming progress into a UI.
        max_concurrency: Override the bounded concurrency. Defaults to
            ``AGENT_MAX_CONCURRENCY`` env, then 4.

    Returns:
        ``(non_empty_reports, final_report)`` where ``non_empty_reports``
        is sorted chronologically. Per §9.4, windows whose Pattern
        Detector found no meaningful pattern (``key_insights == []``)
        are silently dropped.
    """
    windows = select_windows(master_df)
    if not windows:
        logger.info("No anomalous windows - emitting empty report bundle.")
        empty_final = await with_retry(
            lambda: run_judge([], model=model),
            label="judge",
        )
        return [], empty_final

    limit = max_concurrency or get_max_concurrency()
    semaphore = asyncio.Semaphore(limit)

    async def process_window(window: AnalysisWindow) -> IntegratedBehavioralReport | None:
        async with semaphore:
            return await _process_single_window(
                master_df=master_df,
                transcript_df=transcript_df,
                window=window,
                speaker_label=speaker_label,
                model=model,
            )

    raw_results = await asyncio.gather(
        *(process_window(w) for w in windows),
        return_exceptions=True,
    )

    reports: list[IntegratedBehavioralReport] = []
    for window, result in zip(windows, raw_results, strict=True):
        if isinstance(result, BaseException):
            logger.exception(
                "Window %.1fs-%.1fs errored; marking as errored and continuing.",
                window.start,
                window.end,
                exc_info=result,
            )
            continue
        if result is None:
            continue
        if not result.key_insights:
            continue
        reports.append(result)
        if on_window_done is not None:
            try:
                on_window_done(result)
            except Exception:
                logger.exception("on_window_done callback raised - continuing.")

    reports.sort(key=lambda r: r.time_range_start)

    final = await with_retry(
        lambda: run_judge(reports, model=model),
        label="judge",
    )
    logger.info(
        "Agent chain complete: %d non-empty windows, %d total insights.",
        len(reports),
        sum(len(r.key_insights) for r in reports),
    )
    return reports, final


async def _process_single_window(
    *,
    master_df: pd.DataFrame,
    transcript_df: pd.DataFrame | None,
    window: AnalysisWindow,
    speaker_label: str,
    model: str | None,
) -> IntegratedBehavioralReport:
    slice_ = slice_window(
        master_df=master_df,
        start=window.start,
        end=window.end,
        speaker=speaker_label,
        transcript_df=transcript_df,
    )

    visual_task = with_retry(
        lambda: run_visual_observer(slice_, model=model),
        label="visual_observer",
    )
    audio_task = with_retry(
        lambda: run_audio_observer(slice_, model=model),
        label="audio_observer",
    )
    vocab_task = with_retry(
        lambda: run_vocab_observer(slice_, model=model),
        label="vocab_observer",
    )
    visual, audio, vocab = await asyncio.gather(visual_task, audio_task, vocab_task)
    assert isinstance(visual, VisualObservation)
    assert isinstance(audio, AudioObservation)
    assert isinstance(vocab, VocabObservation)

    return await with_retry(
        lambda: run_pattern_detector(slice_, visual, audio, vocab, model=model),
        label="pattern_detector",
    )


# Re-export the slice / window helpers so ``from agents.orchestrator
# import WindowSlice`` keeps working for the few backend callers in M5.
__all__ = [
    "WindowSlice",
    "build_report",
]
