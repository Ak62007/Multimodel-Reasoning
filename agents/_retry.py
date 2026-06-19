"""Tiny exponential-backoff wrapper for agent calls.

Per spec §9.4: each agent call gets 3 retries with exponential backoff.
On final failure the orchestrator marks the window errored and continues.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

_log = logging.getLogger(__name__)

# Rate-limit / quota errors deserve more patience than a generic failure —
# free-tier API keys (e.g. Gemini's ~15 req/min) routinely 429 a busy run.
_RATE_LIMIT_MARKERS = ("429", "rate limit", "rate_limit", "resource_exhausted", "too many requests", "quota")
_RATE_LIMIT_ATTEMPTS = 6
_RATE_LIMIT_MIN_DELAY = 8.0
_MAX_DELAY = 30.0

# Daily-quota exhaustion is NOT recoverable within a run (it resets ~24h later),
# so we must fail fast instead of backing off — unlike a per-minute rate limit.
_DAILY_QUOTA_MARKERS = ("perday", "per day", "requests per day", "perdayperproject", "daily limit")

# Canonical user-facing messages.
RATE_LIMIT_MESSAGE = (
    "The API rate limit was reached before the analysis could finish — this is "
    "common on free-tier keys. Try a shorter clip, switch to the “Paid key” "
    "option, or wait a minute and run it again."
)
DAILY_QUOTA_MESSAGE = (
    "Your Gemini free-tier daily request quota is used up. Free keys allow only a "
    "limited number of requests per day and a full interview uses many. It resets "
    "about 24 hours later — use a paid key for a full run now, or try again tomorrow "
    "with a shorter clip."
)


class RateLimitedError(RuntimeError):
    """Raised when rate limiting (not lack of signal) prevented a usable result."""


def _is_rate_limit(exc: BaseException) -> bool:
    return any(m in str(exc).lower() for m in _RATE_LIMIT_MARKERS)


def _is_daily_quota(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(m in s or m.replace(" ", "") in s.replace(" ", "") for m in _DAILY_QUOTA_MARKERS)


async def with_retries[T](
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    label: str = "agent",
) -> T:
    """Call `fn` with exponential backoff.

    Generic failures get `max_attempts` tries. Rate-limit / quota errors get
    more tries and a longer minimum wait, so a free-tier key has a real chance
    to finish instead of every window silently failing. Re-raises the last
    exception if all attempts fail — the orchestrator catches it per-window.
    """
    delay = base_delay
    last_exc: BaseException | None = None
    attempt = 0
    while True:
        attempt += 1
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            # A daily quota won't recover mid-run — don't waste minutes retrying.
            if _is_daily_quota(e):
                _log.error("%s hit the daily quota — failing fast (no retry): %s", label, e)
                raise
            rate_limited = _is_rate_limit(e)
            cap = max(max_attempts, _RATE_LIMIT_ATTEMPTS) if rate_limited else max_attempts
            if attempt >= cap:
                _log.error("%s failed after %d attempts: %s", label, attempt, e)
                raise
            wait = min(max(delay, _RATE_LIMIT_MIN_DELAY) if rate_limited else delay, _MAX_DELAY)
            _log.warning(
                "%s attempt %d/%d failed (%s) — retrying in %.1fs",
                label,
                attempt,
                cap,
                e,
                wait,
            )
            await asyncio.sleep(wait)
            delay *= 2
    raise last_exc  # type: ignore[misc]  # unreachable, but appeases the type checker


__all__ = ["DAILY_QUOTA_MESSAGE", "RATE_LIMIT_MESSAGE", "RateLimitedError", "with_retries"]
