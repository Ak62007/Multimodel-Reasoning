"""Visual observer agent. Internal scaffolding for the Pattern Detector."""

from __future__ import annotations

from agents._runtime import get_model_spec, use_stub
from agents._stub import stub_visual_observation
from agents._window_slice import WindowSlice, format_visual_input
from agents.prompts import VISUAL_PROMPT
from agents.schemas import VisualObservation


async def run_visual_observer(
    slice_: WindowSlice,
    *,
    model: str | None = None,
) -> VisualObservation:
    """Produce a :class:`VisualObservation` for ``slice_``.

    When ``LLM_PROVIDER=stub`` is set, returns the deterministic stub
    output. Otherwise dispatches to Groq via ``pydantic-ai``.
    """
    if use_stub():
        return stub_visual_observation(slice_)

    # pydantic-ai is imported lazily so that test runs with
    # ``LLM_PROVIDER=stub`` do not need the optional Groq path.
    from pydantic_ai import Agent

    agent: Agent[None, VisualObservation] = Agent(
        get_model_spec(model),
        output_type=VisualObservation,
        system_prompt=VISUAL_PROMPT,
    )
    result = await agent.run(format_visual_input(slice_))
    return result.output
