"""Judge — final executive coaching report.

Takes the chronological list of per-window cross-modal pattern reports and
synthesises a four-section markdown report (executive summary, behavioral
strengths, vulnerabilities & triggers, areas for improvement).
"""

from __future__ import annotations

from agents import _stub
from agents._provider import make_agent
from agents._retry import with_retries
from agents._settings import AgentSettings, get_agent_settings
from agents.prompts import JUDGE_PROMPT
from agents.schemas import FinalReport, IntegratedBehavioralReport


def _format_input(reports: list[IntegratedBehavioralReport]) -> str:
    if not reports:
        return "No cross-modal patterns were detected across the entire interview."
    lines = [f"Cross-modal patterns detected across the interview ({len(reports)} windows):\n"]
    for i, r in enumerate(reports, 1):
        lines.append(f"## Window {i} ({r.time_range_start:.2f}–{r.time_range_end:.2f}s)")
        lines.append(f"Tone: {r.overall_window_tone}")
        lines.append(f"Summary: {r.executive_summary}")
        for ins in r.key_insights:
            lines.append(
                f"  - [{ins.pattern_type}/{ins.significance}] "
                f"({', '.join(ins.modalities_involved)}) "
                f'"{ins.spoken_content}" → {ins.observation} '
                f"(interpretation: {ins.interpretation})"
            )
        lines.append("")
    return "\n".join(lines)


async def run_judge(
    reports: list[IntegratedBehavioralReport],
    *,
    settings: AgentSettings | None = None,
) -> FinalReport:
    settings = settings or get_agent_settings()
    if settings.llm_provider == "stub":
        return _stub.stub_judge(reports)

    agent = make_agent(system_prompt=JUDGE_PROMPT, output_type=FinalReport, settings=settings)
    user_msg = _format_input(reports)

    async def _call() -> FinalReport:
        result = await agent.run(user_msg)
        return result.output  # type: ignore[return-value]

    return await with_retries(_call, label="judge")


__all__ = ["run_judge"]
