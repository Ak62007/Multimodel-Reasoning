"""Pattern Detector (formerly "Profiler") — public output.

Consumes the three observer outputs + transcript slice for one window and
returns an `IntegratedBehavioralReport`. Selectively reports only meaningful
cross-modal patterns (Strength / Concern / Notable); empty `key_insights`
means the orchestrator silently drops the window from the public report.
"""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents.prompts import PATTERN_DETECTOR_PROMPT
from agents.schemas import (
    AudioObservation,
    IntegratedBehavioralReport,
    VisualObservation,
    VocabObservation,
)


def _format_input(
    start: float,
    end: float,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
) -> str:
    return (
        f"# Window\nTime range: {start:.2f}–{end:.2f}s.\n\n"
        f"# Visual observer\n{visual.model_dump_json(indent=2)}\n\n"
        f"# Audio observer\n{audio.model_dump_json(indent=2)}\n\n"
        f"# Vocab observer\n{vocab.model_dump_json(indent=2)}\n\n"
        f"# Transcript slice\n{transcript or '[no transcript available]'}\n"
    )


async def run_pattern_detector(
    start: float,
    end: float,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
    *,
    settings: AgentSettings | None = None,
) -> IntegratedBehavioralReport:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_pattern_detector(start, end, visual, audio, vocab, transcript)

    agent = make_agent(
        system_prompt=PATTERN_DETECTOR_PROMPT,
        output_type=IntegratedBehavioralReport,
        settings=settings,
    )
    user_msg = _format_input(start, end, visual, audio, vocab, transcript)

    async def _call() -> IntegratedBehavioralReport:
        result = await agent.run(user_msg)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="pattern_detector")


__all__ = ["run_pattern_detector"]
