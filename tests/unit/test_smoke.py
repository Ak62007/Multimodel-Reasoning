"""Smoke tests that exercise the M1 scaffolding only.

Real coverage lives in `test_orchestrator_pieces.py` (M2), `test_features.py`,
`test_anomaly.py`, `test_parquet_io.py`, `test_schemas.py` (M3).
"""

from __future__ import annotations


def test_pipeline_package_imports() -> None:
    import pipeline

    assert pipeline.__version__


def test_agents_package_imports() -> None:
    import agents

    assert agents.__name__ == "agents"


def test_backend_app_imports() -> None:
    from backend.app.main import app

    assert app.title == "MMR"
