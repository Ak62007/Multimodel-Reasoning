"""FastAPI application factory.

Implemented in M5. For now this exposes a tiny `app` so that `uvicorn
backend.app.main:app` boots and `/api/health` answers — useful while
scaffolding tests and Docker.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="MMR", version="0.1.0")
    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
