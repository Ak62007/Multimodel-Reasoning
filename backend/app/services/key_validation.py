"""Pre-flight validation of user-supplied API keys (BYOK).

Cheap, read-only checks against each provider so a bad key is caught at upload
time — with a clear message — instead of two minutes into the pipeline.

Policy: a *definitive* rejection (the provider says the key is bad/unauthorized)
raises `KeyValidationError`. A transient problem reaching the provider (timeout,
DNS, 5xx) is logged and allowed through — we don't block a real job on our own
connectivity, and the in-run error handling still catches a truly broken key.
"""

from __future__ import annotations

import logging

import httpx

_log = logging.getLogger(__name__)
_TIMEOUT = httpx.Timeout(10.0)

_GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ASSEMBLYAI_URL = "https://api.assemblyai.com/v2/transcript"

_GEMINI_HELP = "https://aistudio.google.com/app/apikey"
_ASSEMBLYAI_HELP = "https://www.assemblyai.com/dashboard/api-keys"


class KeyValidationError(Exception):
    """A user-supplied API key was definitively rejected by its provider."""


async def validate_gemini_key(api_key: str) -> None:
    """Raise KeyValidationError if Gemini rejects the key. Listing models is a
    free, generation-quota-free call on the same Google GLA API the agents use."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Key goes in the header, never the URL/query string, so it can't end
            # up in a logged request line or proxy access log.
            resp = await client.get(
                _GEMINI_MODELS_URL,
                params={"pageSize": 1},
                headers={"x-goog-api-key": api_key},
            )
    except httpx.HTTPError as e:
        _log.warning("Could not reach Gemini to validate key; allowing job (%s)", type(e).__name__)
        return
    if resp.status_code == 200:
        return
    if resp.status_code in (400, 401, 403):
        raise KeyValidationError(
            f"Your Gemini API key was rejected. Double-check it at {_GEMINI_HELP} and try again."
        )
    _log.warning("Unexpected Gemini key-check status %s; allowing job", resp.status_code)


async def validate_assemblyai_key(api_key: str) -> None:
    """Raise KeyValidationError if AssemblyAI rejects the key. Listing one past
    transcript is a cheap authenticated GET that doesn't start a transcription."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _ASSEMBLYAI_URL, params={"limit": 1}, headers={"authorization": api_key}
            )
    except httpx.HTTPError as e:
        _log.warning(
            "Could not reach AssemblyAI to validate key; allowing job (%s)", type(e).__name__
        )
        return
    if resp.status_code == 200:
        return
    if resp.status_code in (401, 403):
        raise KeyValidationError(
            "Your AssemblyAI API key was rejected. Double-check it at "
            f"{_ASSEMBLYAI_HELP} and try again."
        )
    _log.warning("Unexpected AssemblyAI key-check status %s; allowing job", resp.status_code)


__all__ = ["KeyValidationError", "validate_assemblyai_key", "validate_gemini_key"]
