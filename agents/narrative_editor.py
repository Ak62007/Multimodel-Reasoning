"""Narrative Editor — final synthesis stage.

Turns the Pattern Weaver's structured `WeaverDraft` into the polished,
human-facing `FinalReport` (headline, overview, behavioral arc, the timestamped
highlights, recurring threads, and coaching notes).
"""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents._usage import record_run_usage
from agents.prompts import NARRATIVE_EDITOR_PROMPT
from agents.schemas import FinalReport, WeaverDraft


def _format_input(draft: WeaverDraft) -> str:
    return (
        f"# Headline\n{draft.headline}\n\n"
        f"# Arc notes\n{draft.arc_notes}\n\n"
        f"# Candidate highlights ({len(draft.highlights)})\n"
        f"{draft.model_dump_json(include={'highlights'}, indent=2)}\n\n"
        f"# Threads ({len(draft.threads)})\n"
        f"{draft.model_dump_json(include={'threads'}, indent=2)}\n"
    )


async def run_narrative_editor(
    draft: WeaverDraft,
    *,
    settings: AgentSettings | None = None,
) -> FinalReport:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_narrative_editor(draft)

    agent = make_agent(
        system_prompt=NARRATIVE_EDITOR_PROMPT, output_type=FinalReport, settings=settings
    )
    user_msg = _format_input(draft)

    async def _call() -> FinalReport:
        result = await agent.run(user_msg)
        record_run_usage(result)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="narrative_editor")


__all__ = ["run_narrative_editor"]
