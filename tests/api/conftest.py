"""Pytest fixtures for backend API tests.

Every test gets a freshly-initialised SQLite DB in a `tmp_path` and runs
the agentic layer with `LLM_PROVIDER=stub` so it never hits Groq.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.db import reset_engine_cache
from backend.app.main import app


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Per-test settings: isolated data dirs + DB, stub LLM, test mode on."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("MMR_TEST_MODE", "1")
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "mmr.db"))
    get_settings.cache_clear()
    reset_engine_cache()
    s = get_settings()
    yield s
    get_settings.cache_clear()
    reset_engine_cache()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """TestClient that runs FastAPI BackgroundTasks synchronously after the
    response — perfect for asserting on the fully-resolved job."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tiny_parquet_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "tiny_master_df.parquet"
