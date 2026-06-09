"""Audio observer. Internal — output not exposed via API."""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents.prompts import AUDIO_PROMPT
from agents.schemas import AudioAnomalyEvent, AudioObservation


def _format_input(start: float, end: float, events: list[AudioAnomalyEvent]) -> str:
    if not events:
        return f"Time range: {start:.2f}–{end:.2f}s.\nNo audio anomalies detected."
    lines = [f"Time range: {start:.2f}–{end:.2f}s."]
    for ev in events:
        lines.append(
            f"- [{ev.feature_type}] {ev.behavioral_tag} at "
            f"{ev.timestamp_start:.2f}–{ev.timestamp_end:.2f}s, "
            f"intensity={ev.intensity_score:.2f}, sustained={ev.is_sustained}"
        )
    return "\n".join(lines)


async def run_audio_observer(
    start: float,
    end: float,
    events: list[AudioAnomalyEvent],
    *,
    settings: AgentSettings | None = None,
) -> AudioObservation:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_audio(start, end, events)

    agent = make_agent(system_prompt=AUDIO_PROMPT, output_type=AudioObservation, settings=settings)
    user_msg = _format_input(start, end, events)

    async def _call() -> AudioObservation:
        result = await agent.run(user_msg)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="audio_observer")


__all__ = ["run_audio_observer"]
