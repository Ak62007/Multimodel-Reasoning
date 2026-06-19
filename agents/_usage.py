"""Per-run LLM token accounting.

A tiny context-local accumulator so a whole `build_report` run can report how
many tokens it spent without changing every runner's return signature. Each
agent runner calls `record_run_usage(result)`; a caller wraps the run in
`capture_usage()` to read the totals afterwards.

Implementation note: the accumulator is a *mutable* object stored in a
ContextVar. `capture_usage()` is entered in the synchronous caller before
`asyncio.run(...)`; the event loop and its child tasks copy the context but all
share the same object reference, so their `record_run_usage` mutations are
visible to the caller once the run completes.
"""

from __future__ import annotations

import contextvars
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


_current: contextvars.ContextVar[UsageTotals | None] = contextvars.ContextVar(
    "mmr_usage_totals", default=None
)


@contextmanager
def capture_usage() -> Iterator[UsageTotals]:
    """Collect token usage for all agent runs inside the block."""
    totals = UsageTotals()
    token = _current.set(totals)
    try:
        yield totals
    finally:
        _current.reset(token)


def record_run_usage(result: Any) -> None:
    """Add one pydantic-ai run result's usage to the active accumulator (if any)."""
    totals = _current.get()
    if totals is None:
        return
    try:
        usage = result.usage()
    except Exception:  # never let accounting break a run
        _log.debug("Could not read usage from run result", exc_info=True)
        return
    totals.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
    totals.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
    totals.requests += int(getattr(usage, "requests", 0) or 0)


__all__ = ["UsageTotals", "capture_usage", "record_run_usage"]
