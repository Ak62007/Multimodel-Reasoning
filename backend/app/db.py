"""SQLModel engine + session bootstrap.

A single engine per process. ``init_db`` creates the schema on startup
(SQLite, single file under ``data/mmr.db`` by default).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import Settings

_engine_cache: dict[str, Any] = {}


def get_engine(settings: Settings) -> Any:
    """Return (and lazily build) the SQLModel engine for ``settings``."""
    key = settings.mmr_db_url
    if key in _engine_cache:
        return _engine_cache[key]

    # Make sure the parent dir for SQLite files exists.
    if settings.mmr_db_url.startswith("sqlite"):
        path_part = settings.mmr_db_url.split("///")[-1]
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if settings.mmr_db_url.startswith("sqlite") else {}
    engine = create_engine(settings.mmr_db_url, connect_args=connect_args)
    _engine_cache[key] = engine
    return engine


def init_db(settings: Settings) -> None:
    """Create tables if they don't exist."""
    # Import models so their tables are registered on the metadata.
    import backend.app.models  # noqa: F401

    engine = get_engine(settings)
    SQLModel.metadata.create_all(engine)


def get_session(settings: Settings) -> Iterator[Session]:
    """Yield a SQLModel session - to be wired as a FastAPI dependency."""
    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


def reset_engine_cache() -> None:
    """Drop every cached engine. Tests use this between cases."""
    _engine_cache.clear()
