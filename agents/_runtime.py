"""Runtime helpers shared by every agent module.

This module owns the provider switch (``LLM_PROVIDER=stub`` vs Groq),
retry/backoff logic, and the bounded-concurrency Semaphore.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


DEFAULT_LLM_PROVIDER = "groq"
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_BACKOFF_CAP = 8.0


def use_stub() -> bool:
    """Return ``True`` iff the agents should bypass Groq."""
    return os.environ.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower() == "stub"


def get_model_id(model: str | None = None) -> str:
    """Return the Groq model identifier to use.

    Order of precedence: explicit argument > ``LLM_MODEL`` env > default.
    """
    if model:
        return model
    env = os.environ.get("LLM_MODEL")
    if env:
        return env
    return DEFAULT_LLM_MODEL


def get_max_concurrency() -> int:
    """Return the bounded concurrency for the orchestrator (default 4)."""
    return int(os.environ.get("AGENT_MAX_CONCURRENCY", "4"))


async def with_retry[T](
    coro_factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_cap: float = DEFAULT_BACKOFF_CAP,
    label: str = "agent",
) -> T:
    """Run ``coro_factory`` with exponential-backoff retries.

    The factory is invoked anew on every attempt because awaitables are
    single-use. Backoff: ``base * 2**attempt`` + jitter, capped at ``cap``.
    """
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt == attempts - 1:
                logger.exception("%s failed after %d attempts", label, attempts)
                raise
            delay = min(backoff_cap, backoff_base * (2**attempt))
            delay += random.uniform(0.0, delay)
            logger.warning(
                "%s attempt %d/%d failed (%s) - retrying in %.2fs",
                label,
                attempt + 1,
                attempts,
                exc.__class__.__name__,
                delay,
            )
            await asyncio.sleep(delay)
    # Unreachable, but keeps mypy happy.
    raise RuntimeError(f"{label}: retries exhausted") from last_exc
