"""Window Analyst — the per-window field note (public output).

Consumes the three observer reads + the transcript slice + the window's
temporal context, and produces one `WindowAnalysis`: a free-form narrative plus
0..n discrete `Signal`s. Unlike the old Pattern Detector there is NO empty-drop
gate — every analysed window yields a note, and single-modality / "interesting"
findings are welcome.
"""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents.prompts import WINDOW_ANALYST_PROMPT
from agents.schemas import (
    AudioObservation,
    VisualObservation,
    VocabObservation,
    WindowAnalysis,
)
from agents.windows import AnalysisWindow


def _format_input(
    window: AnalysisWindow,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
) -> str:
    pos = f"{window.position_pct * 100:.0f}%"
    kind = "baseline/calm" if window.is_baseline else "active (anomalies present)"
    return (
        f"# Window {window.index + 1} of {window.total} — {kind}\n"
        f"Time range: {window.start:.2f}–{window.end:.2f}s.\n"
        f"Interview phase: {window.phase} (~{pos} through the interview).\n\n"
        f"# Visual observer\n{visual.model_dump_json(indent=2)}\n\n"
        f"# Audio observer\n{audio.model_dump_json(indent=2)}\n\n"
        f"# Vocab observer\n{vocab.model_dump_json(indent=2)}\n\n"
        f"# Transcript (what they were saying)\n{transcript or '[no transcript available]'}\n"
    )


async def run_window_analyst(
    window: AnalysisWindow,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
    *,
    settings: AgentSettings | None = None,
) -> WindowAnalysis:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_window_analysis(
            window.start,
            window.end,
            window.phase,
            window.position_pct,
            visual,
            audio,
            vocab,
            transcript,
        )

    agent = make_agent(
        system_prompt=WINDOW_ANALYST_PROMPT, output_type=WindowAnalysis, settings=settings
    )
    user_msg = _format_input(window, visual, audio, vocab, transcript)

    async def _call() -> WindowAnalysis:
        result = await agent.run(user_msg)
        out: WindowAnalysis = result.output  # type: ignore[assignment]
        # The LLM may not echo temporal context perfectly; pin it to the truth.
        out.time_start = window.start
        out.time_end = window.end
        out.phase = window.phase  # type: ignore[assignment]
        out.position_pct = window.position_pct
        return out

    return await with_retries(_call, label="window_analyst")


__all__ = ["run_window_analyst"]
