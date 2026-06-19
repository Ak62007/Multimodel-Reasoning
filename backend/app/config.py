"""Application settings loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings. Override via env vars; see `.env.example` for the full list."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "MMR"
    app_version: str = "0.1.0"

    # Paths
    data_root: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    processed_dir: Path = Path("data/processed")
    db_path: Path = Path("data/mmr.db")

    # Upload limits
    max_upload_mb: int = 500
    allowed_video_extensions: tuple[str, ...] = (".mp4", ".mov", ".avi", ".webm")
    # Test mode also accepts pre-computed master_df parquet for fast end-to-end tests.
    allowed_test_extensions: tuple[str, ...] = (".parquet",)

    # LLM (mirrored from agents/_settings.py so the backend can validate
    # before kicking off a job).
    llm_provider: Literal["groq", "openai", "anthropic", "google-gla", "stub"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    # Pipeline
    assemblyai_api_key: str | None = None
    speaker_label: str = "auto"
    face_landmarker_path: Path = Path("models/face_landmarker.task")
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"

    # Agents
    agent_max_concurrency: int = 4

    # Observability — when set, pydantic-ai runs are sent to Logfire (token
    # usage, traces). Unset = silent no-op, so dev/CI are unaffected.
    logfire_token: str | None = None

    # Test mode
    mmr_test_mode: bool = False

    # CORS (Vite dev server default)
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton; tests reset by clearing the lru_cache."""
    return Settings()


__all__ = ["Settings", "get_settings"]
