"""Visual observer. Internal — output not exposed via API.

Renamed from `VisualAnalysisReport` to `VisualObservation` per spec §9.5.
Stub mode short-circuits before the LLM call.
"""

from __future__ import annotations

import logging

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents._usage import record_run_usage
from agents.prompts import VISUAL_PROMPT
from agents.schemas import VisualAnomalyEvent, VisualObservation

_log = logging.getLogger(__name__)


def _format_input(
    start: float, end: float, events: list[VisualAnomalyEvent], raw_summary: str
) -> str:
    lines = [f"Time range: {start:.2f}–{end:.2f}s.", f"Raw signals: {raw_summary or 'n/a'}"]
    if not events:
        lines.append("No visual anomalies detected.")
        return "\n".join(lines)
    for ev in events:
        lines.append(
            f"- [{ev.feature_type}] {ev.behavioral_tag} at "
            f"{ev.timestamp_start:.2f}–{ev.timestamp_end:.2f}s, "
            f"intensity={ev.intensity_score:.2f}, sustained={ev.is_sustained}"
        )
    return "\n".join(lines)


async def run_visual_observer(
    start: float,
    end: float,
    events: list[VisualAnomalyEvent],
    *,
    raw_summary: str = "",
    settings: AgentSettings | None = None,
) -> VisualObservation:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_visual(start, end, events, raw_summary)

    agent = make_agent(
        system_prompt=VISUAL_PROMPT, output_type=VisualObservation, settings=settings
    )
    user_msg = _format_input(start, end, events, raw_summary)

    async def _call() -> VisualObservation:
        result = await agent.run(user_msg)
        record_run_usage(result)
        # pydantic-ai's generic typing of `output` is `str` by default;
        # we know the agent was bound to VisualObservation in make_agent.
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="visual_observer")


__all__ = ["run_visual_observer"]
