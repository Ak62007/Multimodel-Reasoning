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
from agents._retry import (
    DAILY_QUOTA_MESSAGE,
    RATE_LIMIT_MESSAGE,
    RateLimitedError,
    _is_daily_quota,
    _is_rate_limit,
)
from agents._settings import AgentSettings, get_agent_settings
from agents.audio_agent import run_audio_observer
from agents.narrative_editor import run_narrative_editor
from agents.pattern_weaver import run_pattern_weaver
from agents.schemas import FinalReport, WindowAnalysis
from agents.visual_agent import run_visual_observer
from agents.vocab_agent import run_vocab_observer
from agents.window_analyst import run_window_analyst, run_window_analyst_solo
from agents.windows import AnalysisWindow, select_windows

_log = logging.getLogger(__name__)

# Tier → how the per-window analysis runs:
#   "paid": 3 observers + analyst (4 calls/window) — the full-depth read.
#   "free": one combined call/window — ~4x fewer calls so a free-tier key finishes.
_FREE_CONCURRENCY = 2


async def _process_window(
    window: AnalysisWindow,
    transcript_df: pd.DataFrame | None,
    speaker_label: str,
    settings: AgentSettings,
    sem: asyncio.Semaphore,
    tier: str = "paid",
) -> WindowAnalysis | Exception:
    """One window → one WindowAnalysis. `tier` selects the full observers→analyst
    path ("paid") or the lean single-call path ("free").

    On failure returns the exception (the window is skipped) so the caller can
    tell a rate-limit wipeout apart from a genuinely calm interview.
    """
    async with sem:
        try:
            visual_events = extract_visual_events(window.rows)
            audio_events = extract_audio_events(window.rows)
            vocab_events = extract_vocab_events(window.rows)
            visual_raw = summarize_visual_raw(window.rows)
            audio_raw = summarize_audio_raw(window.rows)
            vocab_raw = summarize_vocab_raw(window.rows)
            transcript = extract_transcript_slice(
                transcript_df, window.start, window.end, speaker_label=speaker_label
            )

            if tier == "free":
                return await run_window_analyst_solo(
                    window,
                    visual_events,
                    audio_events,
                    vocab_events,
                    visual_raw=visual_raw,
                    audio_raw=audio_raw,
                    vocab_raw=vocab_raw,
                    transcript=transcript,
                    settings=settings,
                )

            visual, audio, vocab = await asyncio.gather(
                run_visual_observer(
                    window.start,
                    window.end,
                    visual_events,
                    raw_summary=visual_raw,
                    settings=settings,
                ),
                run_audio_observer(
                    window.start, window.end, audio_events, raw_summary=audio_raw, settings=settings
                ),
                run_vocab_observer(
                    window.start, window.end, vocab_events, raw_summary=vocab_raw, settings=settings
                ),
            )
            return await run_window_analyst(
                window, visual, audio, vocab, transcript, settings=settings
            )
        except Exception as e:
            _log.exception("Window %.2f–%.2fs failed — skipping", window.start, window.end)
            return e


async def build_report(
    master_df: pd.DataFrame,
    speaker_label: str = "B",
    transcript_df: pd.DataFrame | None = None,
    *,
    model: str | None = None,
    on_window_done: Callable[[WindowAnalysis], None] | None = None,
    settings: AgentSettings | None = None,
    tier: str = "paid",
) -> tuple[list[WindowAnalysis], FinalReport]:
    """Run the agent chain over the master dataframe.

    Returns `(journal, final_report)` — the chronological list of per-window
    field notes and the synthesised report. `settings` (when provided) overrides
    the env-derived settings for this call only — used to inject a per-request
    API key (BYOK). `model` (when provided) overrides `LLM_MODEL`. `tier` selects
    the full ("paid") or lean single-call-per-window ("free") analysis path.
    """
    settings = settings or get_agent_settings()
    if model is not None:
        settings = settings.model_copy(update={"llm_model": model})

    # Free tier makes one call/window and runs at lower concurrency to stay under
    # free-tier rate limits; paid tier uses the configured concurrency.
    concurrency = (
        min(_FREE_CONCURRENCY, settings.agent_max_concurrency)
        if tier == "free"
        else settings.agent_max_concurrency
    )

    windows = select_windows(master_df)
    _log.info(
        "Agent chain: %d windows, tier=%s, provider=%s, model=%s, concurrency=%d",
        len(windows),
        tier,
        settings.llm_provider,
        settings.llm_model,
        concurrency,
    )

    journal: list[WindowAnalysis] = []
    if windows:
        sem = asyncio.Semaphore(concurrency)
        tasks = [
            _process_window(w, transcript_df, speaker_label, settings, sem, tier) for w in windows
        ]
        results = await asyncio.gather(*tasks)
        failures = [r for r in results if isinstance(r, Exception)]
        for note in results:
            if not isinstance(note, WindowAnalysis):
                continue
            journal.append(note)
            if on_window_done is not None:
                try:
                    on_window_done(note)
                except Exception:
                    _log.exception("on_window_done callback raised")

        journal.sort(key=lambda r: r.time_start)

        # If rate limiting wiped out every window, fail honestly with an explicit
        # message rather than emitting a misleading "no usable signal" report.
        if not journal and failures:
            if any(_is_daily_quota(e) for e in failures):
                _log.error("All windows failed — free-tier daily quota exhausted.")
                raise RateLimitedError(DAILY_QUOTA_MESSAGE)
            if any(_is_rate_limit(e) for e in failures):
                _log.error(
                    "All %d window(s) failed; %d to rate limits — aborting.",
                    len(failures),
                    sum(_is_rate_limit(e) for e in failures),
                )
                raise RateLimitedError(RATE_LIMIT_MESSAGE)

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
