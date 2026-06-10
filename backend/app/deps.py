"""FastAPI dependency providers.

These are tiny wrappers around :mod:`backend.app.config` and
:mod:`backend.app.db` so that routes only ever depend on the dependency
objects and never on module-level state directly. Tests override them
via ``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlmodel import Session

from backend.app.config import Settings, get_settings
from backend.app.db import get_session as _get_session


def get_settings_dep() -> Settings:
    """Inject the cached :class:`Settings` instance."""
    return get_settings()


def get_session_dep(settings: Settings = Depends(get_settings_dep)) -> Iterator[Session]:
    """Yield a SQLModel session bound to ``settings``."""
    yield from _get_session(settings)
