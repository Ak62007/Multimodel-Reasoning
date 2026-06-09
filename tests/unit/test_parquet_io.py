"""Round-trip tests for `pipeline/io/parquet.py`.

The save/load pair must preserve object columns containing Pydantic dicts
(per-frame Blink/Gaze/... shapes) and nested lists (continuous-anomaly
ranges) — that's the load-bearing contract for both the agentic layer and
the API serialisation step.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.io.parquet import load_df_parquet_safe, save_df_parquet_safe
from pipeline.schemas import Blink, LoudnessState

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_master_df.parquet"


def test_round_trip_plain_columns(tmp_path: Path) -> None:
    p = tmp_path / "plain.parquet"
    df = pd.DataFrame({"Time": [0.0, 0.5, 1.0], "value": [1.5, 2.5, 3.5]})
    save_df_parquet_safe(df, p)
    out = load_df_parquet_safe(p)
    pd.testing.assert_frame_equal(out.reset_index(drop=True), df.reset_index(drop=True))


def test_round_trip_pydantic_dict_columns(tmp_path: Path) -> None:
    p = tmp_path / "dicts.parquet"
    blink = Blink(
        intensity=0.4,
        asymmetry=0.0,
        is_blinking=False,
        rz_score=0.5,
        is_anomalous=False,
        continuous_anomaly=False,
        part_of_anomalous_range=None,
    ).model_dump()
    loudness = LoudnessState(
        level="loud",
        rz_score=2.8,
        is_anomalous=True,
        continuous_anomaly=True,
        part_of_anomalous_range=[5.0, 5.5, 6.0],
    ).model_dump()
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5],
            "blinking_data": [blink, blink],
            "loudness_data": [loudness, None],
        }
    )
    save_df_parquet_safe(df, p)
    out = load_df_parquet_safe(p)

    assert out.loc[0, "blinking_data"] == blink
    assert out.loc[0, "loudness_data"] == loudness
    # None / NaN must round-trip too — the agentic layer relies on missing
    # audio rows being None for non-target speakers.
    assert out.loc[1, "loudness_data"] is None


def test_sidecar_schema_records_column_types(tmp_path: Path) -> None:
    p = tmp_path / "with_schema.parquet"
    df = pd.DataFrame({"Time": [0.0], "blinking_data": [{"intensity": 0.1}]})
    save_df_parquet_safe(df, p)
    schema = json.loads(Path(str(p) + ".schema.json").read_text())
    assert schema == {"Time": "normal", "blinking_data": "json"}


def test_round_trip_numpy_scalars_in_object_column(tmp_path: Path) -> None:
    p = tmp_path / "np_scalars.parquet"
    df = pd.DataFrame(
        {
            "Time": [0.0, 0.5],
            "score": [np.float64(1.5), np.int64(7)],  # object dtype
        }
    )
    df["score"] = df["score"].astype(object)
    save_df_parquet_safe(df, p)
    out = load_df_parquet_safe(p)
    assert out.loc[0, "score"] == 1.5
    assert out.loc[1, "score"] == 7


def test_committed_fixture_loads_with_expected_shape() -> None:
    """The committed tiny_master_df fixture stays loadable through the round-trip."""
    assert FIXTURE.exists(), "Run tests/fixtures/_generate_tiny_master_df.py to regenerate"
    df = load_df_parquet_safe(FIXTURE)
    assert len(df) == 60
    assert set(df.columns) >= {
        "Time",
        "speaker",
        "blinking_data",
        "gaze_data",
        "jaw_movement_data",
        "smile_data",
        "loudness_data",
        "average_pitch_data",
        "pitch_standard_deviation",
        "words_per_sec",
        "filler_words_usage",
        "pauses_taken",
    }
    # blinking_data is always populated; loudness_data is None for non-B rows.
    first_blink = df.loc[0, "blinking_data"]
    assert isinstance(first_blink, dict)
    assert {"intensity", "rz_score", "is_anomalous", "part_of_anomalous_range"}.issubset(
        first_blink
    )


def test_committed_fixture_contains_engineered_anomalies() -> None:
    df = load_df_parquet_safe(FIXTURE)
    blink_anom = df["blinking_data"].apply(lambda b: bool(b and b.get("is_anomalous")))
    loud_anom = df["loudness_data"].apply(lambda x: bool(x and x.get("is_anomalous")))
    assert blink_anom.sum() >= 3  # the [5.0, 5.5, 6.0] cluster
    assert loud_anom.sum() >= 3  # the [22.0, 22.5, 23.0, 23.5] cluster


def test_load_missing_schema_sidecar_raises(tmp_path: Path) -> None:
    p = tmp_path / "no_sidecar.parquet"
    df = pd.DataFrame({"x": [1, 2, 3]})
    # Write a parquet without our schema sidecar.
    df.to_parquet(p, engine="pyarrow")
    with pytest.raises(FileNotFoundError):
        load_df_parquet_safe(p)


def test_round_trip_numpy_array_in_object_column(tmp_path: Path) -> None:
    """_jsonify_cell must lower numpy arrays to lists."""
    p = tmp_path / "np_arr.parquet"
    df = pd.DataFrame({"Time": [0.0], "arr": [np.array([1, 2, 3])]})
    df["arr"] = df["arr"].astype(object)
    save_df_parquet_safe(df, p)
    out = load_df_parquet_safe(p)
    assert out.loc[0, "arr"] == [1, 2, 3]


def test_round_trip_unserializable_falls_back_to_string(tmp_path: Path) -> None:
    """_jsonify_cell's exception path: non-JSON-serializable object is str()-encoded."""

    class _Bag:
        def __repr__(self) -> str:
            return "<Bag>"

    p = tmp_path / "bag.parquet"
    df = pd.DataFrame({"Time": [0.0], "thing": [_Bag()]})
    df["thing"] = df["thing"].astype(object)
    save_df_parquet_safe(df, p)
    out = load_df_parquet_safe(p)
    assert out.loc[0, "thing"] == "<Bag>"
