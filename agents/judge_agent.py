"""Judge agent. Public output: ``FinalReport``."""

from __future__ import annotations

from agents._runtime import get_model_id, use_stub
from agents._stub import stub_final_report
from agents.prompts import JUDGE_PROMPT
from agents.schemas import FinalReport, IntegratedBehavioralReport


async def run_judge(
    reports: list[IntegratedBehavioralReport],
    *,
    model: str | None = None,
) -> FinalReport:
    """Synthesise per-window ``IntegratedBehavioralReport``s into a ``FinalReport``."""
    if use_stub():
        return stub_final_report(reports)

    from pydantic_ai import Agent

    agent: Agent[None, FinalReport] = Agent(
        f"groq:{get_model_id(model)}",
        output_type=FinalReport,
        system_prompt=JUDGE_PROMPT,
    )
    bundle = "\n\n".join(
        f"# Window {i + 1} ({r.time_range_start:.1f}s - {r.time_range_end:.1f}s)\n"
        f"{r.model_dump_json(indent=2)}"
        for i, r in enumerate(reports)
    )
    result = await agent.run(bundle)
    return result.output
