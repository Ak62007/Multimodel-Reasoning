"""Shared fixtures for the API test suite.

Every API test gets a brand-new app + SQLite DB + isolated data dir so
side-effects don't leak between tests. ``MMR_TEST_MODE=1`` is forced so
the JobRunner skips the heavy pipeline.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.db import init_db, reset_engine_cache
from backend.app.main import create_app


@pytest.fixture
def api_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Per-test :class:`Settings` rooted at an isolated tmp directory."""
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATA_ROOT", str(data_root))
    monkeypatch.setenv("UPLOAD_DIR", str(data_root / "uploads"))
    monkeypatch.setenv("PROCESSED_DIR", str(data_root / "processed"))
    monkeypatch.setenv("MMR_DB_URL", f"sqlite:///{data_root / 'mmr.db'}")
    monkeypatch.setenv("MMR_TEST_MODE", "1")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("APP_VERSION", "0.1.0-test")

    # pipeline.io.paths captures DATA_ROOT/UPLOAD_DIR/PROCESSED_DIR at import
    # time; reload so this test sees the monkeypatched values.
    import importlib

    import pipeline.io.paths as paths_module

    importlib.reload(paths_module)

    # Settings is also cached via lru_cache; clear it.
    get_settings.cache_clear()
    reset_engine_cache()

    settings = Settings()
    init_db(settings)
    return settings


@pytest.fixture
def app(api_settings: Settings) -> FastAPI:
    return create_app(settings=api_settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
