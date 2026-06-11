"""Audio observer agent. Internal scaffolding for the Pattern Detector."""

from __future__ import annotations

from agents._runtime import get_model_spec, use_stub
from agents._stub import stub_audio_observation
from agents._window_slice import WindowSlice, format_audio_input
from agents.prompts import AUDIO_PROMPT
from agents.schemas import AudioObservation


async def run_audio_observer(
    slice_: WindowSlice,
    *,
    model: str | None = None,
) -> AudioObservation:
    """Produce an :class:`AudioObservation` for ``slice_``."""
    if use_stub():
        return stub_audio_observation(slice_)

    from pydantic_ai import Agent

    agent: Agent[None, AudioObservation] = Agent(
        get_model_spec(model),
        output_type=AudioObservation,
        system_prompt=AUDIO_PROMPT,
    )
    result = await agent.run(format_audio_input(slice_))
    return result.output
