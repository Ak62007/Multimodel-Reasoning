"""Application configuration loaded from environment variables.

Implemented properly in M5. M1 ships the module so the §6 layout is in
place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Minimal settings stub. Replaced by ``pydantic-settings`` in M5."""

    app_version: str = "0.1.0"
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    assemblyai_api_key: str | None = None
    agent_max_concurrency: int = 4
    max_upload_mb: int = 500


def get_settings() -> Settings:
    """Return process settings. Reads a tiny set of env vars for now."""
    return Settings(
        llm_provider=os.environ.get("LLM_PROVIDER", "groq"),
        llm_model=os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        assemblyai_api_key=os.environ.get("ASSEMBLYAI_API_KEY"),
        agent_max_concurrency=int(os.environ.get("AGENT_MAX_CONCURRENCY", "4")),
        max_upload_mb=int(os.environ.get("MAX_UPLOAD_MB", "500")),
    )
