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
from agents._usage import record_run_usage
from agents.prompts import WINDOW_ANALYST_PROMPT, WINDOW_ANALYST_SOLO_PROMPT
from agents.schemas import (
    AudioAnomalyEvent,
    AudioObservation,
    VisualAnomalyEvent,
    VisualObservation,
    VocabObservation,
    VocabularyAnomalyEvent,
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
        record_run_usage(result)
        out: WindowAnalysis = result.output  # type: ignore[assignment]
        # The LLM may not echo temporal context perfectly; pin it to the truth.
        out.time_start = window.start
        out.time_end = window.end
        out.phase = window.phase  # type: ignore[assignment]
        out.position_pct = window.position_pct
        return out

    return await with_retries(_call, label="window_analyst")


def _format_events(title: str, events: list, empty: str) -> str:
    if not events:
        return f"# {title}\n{empty}"
    lines = [f"# {title}"]
    for ev in events:
        lines.append(
            f"- [{ev.feature_type}] {ev.behavioral_tag} at "
            f"{ev.timestamp_start:.2f}–{ev.timestamp_end:.2f}s, "
            f"intensity={ev.intensity_score:.2f}, sustained={ev.is_sustained}"
        )
    return "\n".join(lines)


def _format_solo_input(
    window: AnalysisWindow,
    visual_events: list[VisualAnomalyEvent],
    audio_events: list[AudioAnomalyEvent],
    vocab_events: list[VocabularyAnomalyEvent],
    visual_raw: str,
    audio_raw: str,
    vocab_raw: str,
    transcript: str,
) -> str:
    pos = f"{window.position_pct * 100:.0f}%"
    kind = "baseline/calm" if window.is_baseline else "active (anomalies present)"
    return (
        f"# Window {window.index + 1} of {window.total} — {kind}\n"
        f"Time range: {window.start:.2f}–{window.end:.2f}s.\n"
        f"Interview phase: {window.phase} (~{pos} through the interview).\n\n"
        f"## Raw signal summaries\n"
        f"- Face: {visual_raw or 'n/a'}\n"
        f"- Voice: {audio_raw or 'n/a'}\n"
        f"- Speech: {vocab_raw or 'n/a'}\n\n"
        f"{_format_events('Face anomalies', visual_events, 'None — face at baseline.')}\n\n"
        f"{_format_events('Voice anomalies', audio_events, 'None — voice at baseline.')}\n\n"
        f"{_format_events('Speech anomalies', vocab_events, 'None — speech fluent.')}\n\n"
        f"# Transcript (what they were saying)\n{transcript or '[no transcript available]'}\n"
    )


async def run_window_analyst_solo(
    window: AnalysisWindow,
    visual_events: list[VisualAnomalyEvent],
    audio_events: list[AudioAnomalyEvent],
    vocab_events: list[VocabularyAnomalyEvent],
    *,
    visual_raw: str = "",
    audio_raw: str = "",
    vocab_raw: str = "",
    transcript: str = "",
    settings: AgentSettings | None = None,
) -> WindowAnalysis:
    """Free-tier path: one LLM call per window (no separate observer calls).

    Reads the raw multimodal signals directly and produces a WindowAnalysis in a
    single pass — ~4x fewer calls than the observers→analyst flow, so a free-tier
    API key can actually finish a run.
    """
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_window_analysis(
            window.start,
            window.end,
            window.phase,
            window.position_pct,
            _stub.stub_visual(window.start, window.end, visual_events, visual_raw),
            _stub.stub_audio(window.start, window.end, audio_events, audio_raw),
            _stub.stub_vocab(window.start, window.end, vocab_events, vocab_raw),
            transcript,
        )

    agent = make_agent(
        system_prompt=WINDOW_ANALYST_SOLO_PROMPT, output_type=WindowAnalysis, settings=settings
    )
    user_msg = _format_solo_input(
        window,
        visual_events,
        audio_events,
        vocab_events,
        visual_raw,
        audio_raw,
        vocab_raw,
        transcript,
    )

    async def _call() -> WindowAnalysis:
        result = await agent.run(user_msg)
        record_run_usage(result)
        out: WindowAnalysis = result.output  # type: ignore[assignment]
        out.time_start = window.start
        out.time_end = window.end
        out.phase = window.phase  # type: ignore[assignment]
        out.position_pct = window.position_pct
        return out

    return await with_retries(_call, label="window_analyst_solo")


__all__ = ["run_window_analyst", "run_window_analyst_solo"]
