"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlmodel import Session

from backend.app.config import Settings, get_settings
from backend.app.db import get_engine


def get_session_dep(settings: Settings = Depends(get_settings)) -> Iterator[Session]:
    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


__all__ = ["get_session_dep", "get_settings"]
