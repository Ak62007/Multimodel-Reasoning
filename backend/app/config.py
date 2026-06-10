"""Application configuration loaded from environment variables.

A single :class:`Settings` instance is created lazily by :func:`get_settings`
and cached for the process lifetime. Tests override it via
``app.dependency_overrides[get_settings] = ...``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from pipeline.io.paths import DATA_DIR

ALLOWED_VIDEO_MIME_TYPES: frozenset[str] = frozenset(
    {
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        # Some browsers send `application/octet-stream` for less-common
        # containers; we keep the door open and rely on extension checks.
        "application/octet-stream",
    }
)


class Settings(BaseSettings):
    """Process-wide configuration backed by environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- service identity -------------------------------------------------
    app_name: str = "MMR"
    app_version: str = "0.1.0"

    # ---- LLM ---------------------------------------------------------------
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    agent_max_concurrency: int = 4

    # ---- speech-to-text ---------------------------------------------------
    assemblyai_api_key: str | None = None

    # ---- storage + DB -----------------------------------------------------
    data_root: str = str(DATA_DIR)
    mmr_db_url: str = f"sqlite:///{DATA_DIR / 'mmr.db'}"

    # ---- upload constraints -----------------------------------------------
    max_upload_mb: int = 500

    # ---- testing -----------------------------------------------------------
    # When 1, POST /api/jobs accepts a pre-computed master parquet instead of
    # a video, and the JobRunner skips the heavy pipeline.
    mmr_test_mode: bool = False

    # ---- CORS --------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",
        "http://localhost",
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
