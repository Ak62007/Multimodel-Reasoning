"""Smoke tests that exercise the M1 scaffolding only.

Replaced by real coverage in M3.
"""

from __future__ import annotations


def test_pipeline_package_imports() -> None:
    import pipeline

    assert pipeline.__version__


def test_agents_package_imports() -> None:
    import agents


def test_backend_app_imports() -> None:
    from backend.app.main import app

    assert app.title == "MMR"
