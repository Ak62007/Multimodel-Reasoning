"""Public surface of the agentic layer.

Implemented in M4. Returns ``(list[IntegratedBehavioralReport], FinalReport)``
when called with a master dataframe.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from agents.schemas import FinalReport, IntegratedBehavioralReport


async def build_report(
    master_df: pd.DataFrame,
    speaker_label: str = "B",
    transcript_df: pd.DataFrame | None = None,
    *,
    model: str | None = None,
    on_window_done: Callable[[IntegratedBehavioralReport], None] | None = None,
) -> tuple[list[IntegratedBehavioralReport], FinalReport]:
    """Run the agent chain over the master dataframe. Implemented in M4."""
    raise NotImplementedError("agents.orchestrator.build_report is implemented in milestone M4")
