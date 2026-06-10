"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.io.parquet import load_df_parquet_safe

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MASTER_FIXTURE = FIXTURE_DIR / "tiny_master_df.parquet"
TRANSCRIPT_FIXTURE = FIXTURE_DIR / "tiny_transcript.parquet"
META_FIXTURE = FIXTURE_DIR / "meta.json"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    """Absolute path to ``tests/fixtures``."""
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def fixture_meta() -> dict:
    """Parsed ``meta.json`` describing the master fixture."""
    return json.loads(META_FIXTURE.read_text())


@pytest.fixture(scope="session")
def tiny_master_df() -> pd.DataFrame:
    """The deterministic 60-row master dataframe used by every test that
    needs the per-row Pydantic-decodable cells."""
    return load_df_parquet_safe(str(MASTER_FIXTURE))


@pytest.fixture(scope="session")
def tiny_transcript_df() -> pd.DataFrame:
    """Transcript slice aligned with ``tiny_master_df`` on ``Time``."""
    return load_df_parquet_safe(str(TRANSCRIPT_FIXTURE))
