"""Vocabulary observer. Internal — output not exposed via API."""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents._usage import record_run_usage
from agents.prompts import VOCABULARY_PROMPT
from agents.schemas import VocabObservation, VocabularyAnomalyEvent


def _format_input(
    start: float, end: float, events: list[VocabularyAnomalyEvent], raw_summary: str
) -> str:
    lines = [f"Time range: {start:.2f}–{end:.2f}s.", f"Raw signals: {raw_summary or 'n/a'}"]
    if not events:
        lines.append("No verbal anomalies detected.")
        return "\n".join(lines)
    for ev in events:
        lines.append(
            f"- [{ev.feature_type}] {ev.behavioral_tag} at "
            f"{ev.timestamp_start:.2f}–{ev.timestamp_end:.2f}s, "
            f"intensity={ev.intensity_score:.2f}, sustained={ev.is_sustained}"
        )
    return "\n".join(lines)


async def run_vocab_observer(
    start: float,
    end: float,
    events: list[VocabularyAnomalyEvent],
    *,
    raw_summary: str = "",
    settings: AgentSettings | None = None,
) -> VocabObservation:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_vocab(start, end, events, raw_summary)

    agent = make_agent(
        system_prompt=VOCABULARY_PROMPT, output_type=VocabObservation, settings=settings
    )
    user_msg = _format_input(start, end, events, raw_summary)

    async def _call() -> VocabObservation:
        result = await agent.run(user_msg)
        record_run_usage(result)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="vocab_observer")


__all__ = ["run_vocab_observer"]
