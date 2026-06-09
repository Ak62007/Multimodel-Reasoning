"""Application settings loaded from environment.

Fully populated in M5. For now we only need enough to import cleanly.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings. Override via env vars; see `.env.example` for the full list."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MMR"
    data_root: Path = Path("data")
    max_upload_mb: int = 500

    # LLM
    llm_provider: str = "groq"  # "groq" | "stub"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    assemblyai_api_key: str | None = None

    # Agents
    agent_max_concurrency: int = 4

    # Test mode
    mmr_test_mode: bool = False


def get_settings() -> Settings:
    return Settings()
