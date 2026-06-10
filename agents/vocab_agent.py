"""Vocabulary observer agent. Internal scaffolding for the Pattern Detector."""

from __future__ import annotations

from agents._runtime import get_model_id, use_stub
from agents._stub import stub_vocab_observation
from agents._window_slice import WindowSlice, format_vocab_input
from agents.prompts import VOCABULARY_PROMPT
from agents.schemas import VocabObservation


async def run_vocab_observer(
    slice_: WindowSlice,
    *,
    model: str | None = None,
) -> VocabObservation:
    """Produce a :class:`VocabObservation` for ``slice_``."""
    if use_stub():
        return stub_vocab_observation(slice_)

    from pydantic_ai import Agent

    agent: Agent[None, VocabObservation] = Agent(
        f"groq:{get_model_id(model)}",
        output_type=VocabObservation,
        system_prompt=VOCABULARY_PROMPT,
    )
    result = await agent.run(format_vocab_input(slice_))
    return result.output
