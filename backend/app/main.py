"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db import get_engine
from backend.app.routers import health, jobs, reports
from pipeline._logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=logging.INFO)
    # Ensure DB tables exist before serving traffic.
    get_engine(settings)

    app = FastAPI(title="MMR", version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    return app


app = create_app()
