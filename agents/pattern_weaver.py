"""Pattern Weaver — first synthesis stage.

Reads the full chronological journal of `WindowAnalysis` notes and finds the
cross-window story: recurring threads, the behavioral arc, and the handful of
timestamped highlights worth re-watching. Emits a structured `WeaverDraft` that
the Narrative Editor turns into prose.
"""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents.prompts import PATTERN_WEAVER_PROMPT
from agents.schemas import WeaverDraft, WindowAnalysis


def _format_input(analyses: list[WindowAnalysis]) -> str:
    if not analyses:
        return "The interview produced no analysis windows (no usable signal)."
    n = len(analyses)
    lines = [f"Interview journal — {n} window(s), in order:\n"]
    for i, a in enumerate(analyses, 1):
        lines.append(
            f"## Window {i}/{n} · {a.time_start:.1f}–{a.time_end:.1f}s · "
            f"{a.phase} (~{a.position_pct * 100:.0f}%) · interest={a.window_interest}"
        )
        if a.spoken_excerpt:
            lines.append(f'Said: "{a.spoken_excerpt}"')
        lines.append(f"Reads — visual: {a.visual_read} | audio: {a.audio_read} | verbal: {a.verbal_read}")
        lines.append(f"Narrative: {a.narrative}")
        for s in a.signals:
            lines.append(
                f"  • [{s.kind}/{s.relation}/{s.significance}] "
                f"{s.timestamp_start:.1f}–{s.timestamp_end:.1f}s ({', '.join(s.modalities)}) "
                f"{s.headline} — {s.interpretation}"
            )
        lines.append("")
    return "\n".join(lines)


async def run_pattern_weaver(
    analyses: list[WindowAnalysis],
    *,
    settings: AgentSettings | None = None,
) -> WeaverDraft:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_pattern_weaver(analyses)

    agent = make_agent(
        system_prompt=PATTERN_WEAVER_PROMPT, output_type=WeaverDraft, settings=settings
    )
    user_msg = _format_input(analyses)

    async def _call() -> WeaverDraft:
        result = await agent.run(user_msg)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="pattern_weaver")


__all__ = ["run_pattern_weaver"]
