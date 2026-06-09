"""Tiny exponential-backoff wrapper for agent calls.

Per spec §9.4: each agent call gets 3 retries with exponential backoff.
On final failure the orchestrator marks the window errored and continues.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

_log = logging.getLogger(__name__)


async def with_retries[T](
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    label: str = "agent",
) -> T:
    """Call `fn` up to `max_attempts` times with exponential backoff.

    Re-raises the last exception if every attempt fails — the orchestrator
    catches that at the window level.
    """
    delay = base_delay
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt == max_attempts:
                _log.error("%s failed after %d attempts: %s", label, max_attempts, e)
                raise
            _log.warning(
                "%s attempt %d/%d failed (%s) — retrying in %.1fs",
                label,
                attempt,
                max_attempts,
                e,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
    raise last_exc  # type: ignore[misc]  # unreachable, but appeases the type checker


__all__ = ["with_retries"]
