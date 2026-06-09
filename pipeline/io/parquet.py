import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


def _is_scalar_na(x):
    """Return True if x is considered NA (handles array-like pd.isna results)."""
    try:
        res = pd.isna(x)
        # if pd.isna returned a scalar boolean
        if isinstance(res, (bool, np.bool_)):
            return bool(res)
        # if pd.isna returned an array-like, consider it NA only if all elements are NA
        return bool(np.all(res))
    except Exception:
        return False


def _jsonify_cell(x):
    """Convert a single cell to a JSON-string if it's not NaN/None. Handles numpy types/arrays."""
    if _is_scalar_na(x):
        return None  # Return None instead of x to ensure consistent type

    # numpy arrays -> convert to python list first
    if isinstance(x, np.ndarray):
        return json.dumps(x.tolist())

    # numpy scalar (e.g. np.int64) -> get python scalar then dump
    if isinstance(x, (np.generic,)):
        return json.dumps(x.item())

    # attempt normal json dump, fallback to string if object isn't serializable
    try:
        return json.dumps(x)
    except (TypeError, OverflowError):
        return json.dumps(str(x))


def save_df_parquet_safe(df: pd.DataFrame, path: str | Path) -> None:
    """Save a DataFrame to Parquet while preserving object-typed columns.

    Object columns are JSON-encoded and a sidecar `<path>.schema.json` records
    which columns to JSON-decode on load. Pydantic `.model_dump()` dicts and
    nested lists round-trip cleanly through this pair.
    """
    path = str(path)
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

    _log.info("Saved parquet: %s (+ %s)", path, schema_path)


def load_df_parquet_safe(path: str | Path) -> pd.DataFrame:
    """Load a parquet written by `save_df_parquet_safe`, restoring object columns."""
    path = str(path)
    df = pd.read_parquet(path=path, engine="pyarrow")

    schema_path = path + ".schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    for col, col_type in schema.items():
        if col_type == "json":
            df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) else None)

    return df
