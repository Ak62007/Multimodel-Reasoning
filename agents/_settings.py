"""Settings for the agentic layer.

Reads from env via pydantic-settings. The backend re-exports its own
`Settings` over in `backend/app/config.py`; this is the pipeline-side view.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Stub-vs-real gate only. The *actual* provider is derived from the
    # `llm_model` prefix (e.g. "google-gla:gemini-2.5-flash" -> Gemini).
    llm_provider: Literal["groq", "openai", "anthropic", "google-gla", "stub"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    agent_max_concurrency: int = 4


def get_agent_settings() -> AgentSettings:
    return AgentSettings()


__all__ = ["AgentSettings", "get_agent_settings"]
