"""SQLModel engine + session factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import Settings

_engines: dict[Path, Engine] = {}


def _build_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False so the FastAPI app + BackgroundTasks can share it
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


def get_engine(settings: Settings) -> Engine:
    """Returns a cached engine keyed by `db_path` so tests can swap DBs cleanly."""
    if settings.db_path not in _engines:
        _engines[settings.db_path] = _build_engine(settings.db_path)
    return _engines[settings.db_path]


@contextmanager
def session_scope(settings: Settings) -> Iterator[Session]:
    """Context-managed session for use outside FastAPI dependency injection
    (e.g. inside BackgroundTasks)."""
    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


def reset_engine_cache() -> None:
    """Test hook: drop cached engines so a new `db_path` is picked up cleanly."""
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


__all__ = ["get_engine", "reset_engine_cache", "session_scope"]
