"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import Settings, get_settings
from backend.app.db import get_engine
from backend.app.routers import health, jobs, reports
from pipeline._logging import configure_logging

_log = logging.getLogger(__name__)


def _configure_observability(settings: Settings) -> None:
    """Wire pydantic-ai → Logfire when a token is configured.

    `send_to_logfire="if-token-present"` makes this a silent no-op without a
    token, so local dev, tests, and CI are unaffected.
    """
    try:
        import logfire

        logfire.configure(
            send_to_logfire="if-token-present",
            token=settings.logfire_token,
            service_name="mmr",
            console=False,
        )
        logfire.instrument_pydantic_ai()
        if settings.logfire_token:
            _log.info("Logfire instrumentation enabled.")
    except Exception:  # observability must never block startup
        _log.warning("Logfire setup skipped", exc_info=True)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=logging.INFO)
    _configure_observability(settings)
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
