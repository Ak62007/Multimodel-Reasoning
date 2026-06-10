"""Pattern Detector agent. Public output: ``IntegratedBehavioralReport``."""

from __future__ import annotations

from agents._runtime import get_model_id, use_stub
from agents._stub import stub_integrated_report
from agents._window_slice import WindowSlice, format_pattern_detector_input
from agents.prompts import PATTERN_DETECTOR_PROMPT
from agents.schemas import (
    AudioObservation,
    IntegratedBehavioralReport,
    VisualObservation,
    VocabObservation,
)


async def run_pattern_detector(
    slice_: WindowSlice,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    *,
    model: str | None = None,
) -> IntegratedBehavioralReport:
    """Produce an :class:`IntegratedBehavioralReport` for ``slice_``.

    Consumes the three observer outputs + the transcript slice. If the
    pattern detector finds no meaningful cross-modal pattern, ``key_insights``
    is empty and the orchestrator silently drops the window.
    """
    if use_stub():
        return stub_integrated_report(slice_, visual, audio, vocab)

    from pydantic_ai import Agent

    agent: Agent[None, IntegratedBehavioralReport] = Agent(
        f"groq:{get_model_id(model)}",
        output_type=IntegratedBehavioralReport,
        system_prompt=PATTERN_DETECTOR_PROMPT,
    )
    prompt = format_pattern_detector_input(
        slice_,
        visual=visual.model_dump_json(indent=2),
        audio=audio.model_dump_json(indent=2),
        vocab=vocab.model_dump_json(indent=2),
    )
    result = await agent.run(prompt)
    return result.output
