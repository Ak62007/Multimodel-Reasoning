"""Glue between FastAPI BackgroundTasks and `pipeline.orchestrator` + `agents.orchestrator`.

Implemented in M5. The structure is designed so the executor can be swapped
to Celery/RQ/Arq later without touching the routers.
"""

from __future__ import annotations

__all__: list[str] = []
