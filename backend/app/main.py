"""FastAPI application factory.

``create_app`` builds an instance of the MMR backend, wires CORS,
initialises the SQLite database, and mounts all routers under ``/api``.

The function is split out so tests can build one app per test session
without paying for module-level side effects.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import Settings, get_settings
from backend.app.db import init_db
from backend.app.routers import health, jobs, reports

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        init_db(settings)
        logger.info("MMR backend ready (version=%s)", settings.app_version)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "MMR backend API. Owns the per-upload Job lifecycle, surfaces "
            "the agent-produced cross-modal segments + final coaching report, "
            "and streams the per-row Pydantic-decodable master parquet."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")

    return app


# Default ASGI export so ``uvicorn backend.app.main:app`` works directly.
app = create_app()
