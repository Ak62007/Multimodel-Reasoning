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
    """Return the bare model identifier (no provider prefix).

    Order of precedence: explicit argument > ``LLM_MODEL`` env > default.
    A leading ``"<provider>:"`` prefix is stripped if present so the
    return value is always just the model id (e.g. ``llama-3.3-70b-versatile``
    or ``gpt-4o-mini``).
    """
    raw = model or os.environ.get("LLM_MODEL") or DEFAULT_LLM_MODEL
    return raw.split(":", 1)[1] if ":" in raw else raw


def get_model_spec(model: str | None = None) -> str:
    """Return the fully-qualified ``"<provider>:<model_id>"`` for pydantic-ai.

    - If the caller / ``LLM_MODEL`` already carries a ``"<provider>:"``
      prefix (e.g. ``openai:gpt-4o-mini``, ``anthropic:claude-haiku-4-5``,
      ``google-gla:gemini-1.5-flash``, ``groq:llama-3.1-8b-instant``),
      it is returned verbatim.
    - Otherwise the value is treated as a Groq model id for backwards
      compatibility with the original ``LLM_MODEL=llama-3.3-70b-versatile``
      shape and ``"groq:"`` is prepended.

    This lets the user swap providers in ``.env`` alone (provided the
    matching API key env var is also set) — no code change required.
    """
    raw = model or os.environ.get("LLM_MODEL") or DEFAULT_LLM_MODEL
    return raw if ":" in raw else f"groq:{raw}"


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
