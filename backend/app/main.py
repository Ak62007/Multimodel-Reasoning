"""FastAPI application factory.

Implemented properly in M5. M1 only ships a minimal app factory so the
module is importable and the §6 layout is in place.
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Create and return the FastAPI application. Implemented in M5."""
    raise NotImplementedError("backend.app.main.create_app is implemented in milestone M5")
