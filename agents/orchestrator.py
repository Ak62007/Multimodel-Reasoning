"""Agent chain orchestrator.

Implemented in M4. Public surface:

    async def build_report(
        master_df: pd.DataFrame,
        speaker_label: str = "B",
        transcript_df: pd.DataFrame | None = None,
        *,
        model: str | None = None,
        on_window_done: Callable | None = None,
    ) -> tuple[list[IntegratedBehavioralReport], FinalReport]: ...
"""

from __future__ import annotations

__all__: list[str] = []
