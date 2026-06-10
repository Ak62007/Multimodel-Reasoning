"""Parquet persistence with a JSON sidecar for object-typed columns.

The MMR pipeline produces dataframes whose ``object`` columns hold nested
Pydantic ``model_dump()`` payloads. PyArrow cannot natively encode arbitrary
Python objects, so we JSON-encode each object cell at save time and record the
column types in a ``<path>.schema.json`` sidecar that ``load_df_parquet_safe``
uses to round-trip back to Python dicts.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _is_scalar_na(x: Any) -> bool:
    """Return ``True`` iff ``x`` is NA, handling array-like ``pd.isna`` results."""
    try:
        res = pd.isna(x)
        if isinstance(res, (bool, np.bool_)):
            return bool(res)
        return bool(np.all(res))
    except Exception:
        return False


def _jsonify_cell(x: Any) -> str | None:
    """Convert a single cell to a JSON string, or ``None`` for NA values."""
    if _is_scalar_na(x):
        return None

    if isinstance(x, np.ndarray):
        return json.dumps(x.tolist())

    if isinstance(x, np.generic):
        return json.dumps(x.item())

    try:
        return json.dumps(x)
    except (TypeError, OverflowError):
        return json.dumps(str(x))


def save_df_parquet_safe(df: pd.DataFrame, path: str) -> None:
    """Save ``df`` to ``path`` as parquet, JSON-encoding any object columns.

    A sidecar ``<path>.schema.json`` records which columns were JSON-encoded
    so :func:`load_df_parquet_safe` can round-trip them.
    """
    df = df.copy()
    schema: dict[str, str] = {}

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(_jsonify_cell)
            df[col] = df[col].astype("string")
            schema[col] = "json"
        else:
            schema[col] = "normal"

    df.to_parquet(path=path, engine="pyarrow")

    schema_path = path + ".schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f)

    logger.info("Saved parquet: %s", path)
    logger.info("Saved schema: %s", schema_path)


def load_df_parquet_safe(path: str) -> pd.DataFrame:
    """Load a parquet saved by :func:`save_df_parquet_safe`, restoring JSON cells."""
    df = pd.read_parquet(path=path, engine="pyarrow")

    schema_path = path + ".schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    for col, col_type in schema.items():
        if col_type == "json":
            df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) else None)

    return df
