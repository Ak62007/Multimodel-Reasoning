"""Tests for the JSON-sidecar parquet round-trip in ``pipeline.io.parquet``."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.io.parquet import (
    _is_scalar_na,
    _jsonify_cell,
    load_df_parquet_safe,
    save_df_parquet_safe,
)
from pipeline.schemas import Blink

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_is_scalar_na_handles_none_and_nan() -> None:
    assert _is_scalar_na(None) is True
    assert _is_scalar_na(float("nan")) is True
    assert _is_scalar_na(0.0) is False
    assert _is_scalar_na("text") is False


def test_is_scalar_na_handles_array_like() -> None:
    arr = np.array([np.nan, np.nan])
    assert _is_scalar_na(arr) is True
    assert _is_scalar_na(np.array([1.0, np.nan])) is False


def test_is_scalar_na_swallows_unexpected_types() -> None:
    # Unhashable / unusual types should be treated as not-NA, not crash.
    class _NoIsNa:
        def __array__(self) -> np.ndarray:
            raise RuntimeError("boom")

    assert _is_scalar_na(_NoIsNa()) is False


def test_jsonify_cell_numpy_scalar() -> None:
    assert _jsonify_cell(np.int64(7)) == "7"
    assert _jsonify_cell(np.float32(2.5)) == "2.5"


def test_jsonify_cell_numpy_array() -> None:
    assert _jsonify_cell(np.array([1, 2, 3])) == "[1, 2, 3]"


def test_jsonify_cell_dict_and_list() -> None:
    assert json.loads(_jsonify_cell({"a": 1, "b": 2})) == {"a": 1, "b": 2}
    assert json.loads(_jsonify_cell([1, "x", True])) == [1, "x", True]


def test_jsonify_cell_na_returns_none() -> None:
    assert _jsonify_cell(None) is None
    assert _jsonify_cell(float("nan")) is None


def test_jsonify_cell_unserialisable_falls_back_to_str() -> None:
    class _Unhashable:
        def __repr__(self) -> str:
            return "<custom>"

    encoded = _jsonify_cell(_Unhashable())
    assert encoded is not None
    assert json.loads(encoded) == "<custom>"


# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------


def test_numeric_round_trip(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [1.5, 2.5, 3.5]})
    path = tmp_path / "numeric.parquet"
    save_df_parquet_safe(df, str(path))

    assert path.exists()
    schema = json.loads((path.parent / f"{path.name}.schema.json").read_text())
    assert schema == {"a": "normal", "b": "normal"}

    loaded = load_df_parquet_safe(str(path))
    pd.testing.assert_frame_equal(loaded, df)


def test_object_column_round_trip(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "blinking_data": [
                Blink(
                    intensity=0.1,
                    asymmetry=0.0,
                    is_blinking=False,
                    rz_score=0.0,
                    is_anomalous=False,
                    continuous_anomaly=False,
                    part_of_anomalous_range=None,
                ).model_dump(),
                Blink(
                    intensity=0.6,
                    asymmetry=0.1,
                    is_blinking=True,
                    rz_score=3.2,
                    is_anomalous=True,
                    continuous_anomaly=True,
                    part_of_anomalous_range=[0.5, 1.0],
                ).model_dump(),
                None,
            ],
        }
    )
    path = tmp_path / "objects.parquet"
    save_df_parquet_safe(df, str(path))

    schema = json.loads((path.parent / f"{path.name}.schema.json").read_text())
    assert schema["Time"] == "normal"
    assert schema["blinking_data"] == "json"

    loaded = load_df_parquet_safe(str(path))
    # First two cells round-trip identically; the None becomes None.
    assert isinstance(loaded.loc[0, "blinking_data"], dict)
    assert loaded.loc[1, "blinking_data"]["is_anomalous"] is True
    assert loaded.loc[1, "blinking_data"]["part_of_anomalous_range"] == [0.5, 1.0]
    assert loaded.loc[2, "blinking_data"] is None


def test_save_returns_none(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 2]})
    path = tmp_path / "ret.parquet"
    result = save_df_parquet_safe(df, str(path))
    assert result is None  # explicit None return per signature


def test_round_trip_with_numpy_array_in_object_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"vec": [np.array([1, 2, 3]), np.array([4, 5, 6])]})
    df["vec"] = df["vec"].astype(object)
    path = tmp_path / "arrays.parquet"
    save_df_parquet_safe(df, str(path))
    loaded = load_df_parquet_safe(str(path))
    assert loaded.loc[0, "vec"] == [1, 2, 3]


def test_round_trip_with_nan_in_object_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"obj": [{"x": 1}, float("nan"), {"y": 2}]})
    path = tmp_path / "objnan.parquet"
    save_df_parquet_safe(df, str(path))
    loaded = load_df_parquet_safe(str(path))
    assert loaded.loc[0, "obj"] == {"x": 1}
    assert loaded.loc[1, "obj"] is None
    assert loaded.loc[2, "obj"] == {"y": 2}


def test_tiny_master_fixture_round_trips(tiny_master_df: pd.DataFrame, fixture_meta: dict) -> None:
    """The committed master fixture must round-trip cleanly."""
    assert len(tiny_master_df) == fixture_meta["rows"]
    assert math.isclose(
        float(tiny_master_df["Time"].iloc[-1]) + 0.5,
        fixture_meta["duration_sec"],
    )
    # Pydantic-decoded cells survived the round-trip.
    blink = tiny_master_df["blinking_data"].iloc[20]
    assert isinstance(blink, dict)
    assert "intensity" in blink
    assert "rz_score" in blink
