"""Structural smoke tests for the M2 orchestrator pieces.

Full end-to-end testing with a real interview video lives in M3 (tiny fixture
parquet) and a manual run documented in DECISIONS.md. These tests verify the
pure-Python glue (merge, smoothing, anomaly detection wiring) works on
synthetic frames.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.anomaly import (
    get_anomalous_time_ranges,
    robust_zscore,
    smooth_and_rz_audio,
    smooth_and_rz_visual,
)
from pipeline.features.linguistic import (
    assign_speakers,
    get_speaker_segments,
    is_filler,
    words_to_windows,
)
from pipeline.merge import merge_streams
from pipeline.orchestrator import STAGES, PipelineConfig, PipelineResult


def test_stages_match_spec() -> None:
    expected = [
        "extracting_frames",
        "extracting_audio",
        "extracting_face_features",
        "extracting_audio_features",
        "transcribing",
        "merging",
        "feature_engineering",
        "anomaly_detection",
        "building_master_df",
    ]
    assert list(STAGES) == expected


def test_pipeline_config_defaults() -> None:
    cfg = PipelineConfig()
    assert cfg.speaker_label == "B"
    assert cfg.window_size_sec == 0.5
    assert cfg.enable_assemblyai is True
    assert cfg.enable_whisper is True
    assert cfg.frames_per_second == 1


def test_pipeline_result_has_required_fields() -> None:
    assert {"job_id", "paths", "master_df_path"}.issubset(PipelineResult.__dataclass_fields__)


def test_is_filler() -> None:
    assert is_filler("um")
    assert is_filler("Uh.")
    assert is_filler("hello [*]")
    assert not is_filler("interview")
    assert not is_filler("python")


def test_words_to_windows_empty() -> None:
    df = words_to_windows(pd.DataFrame(), window_size=0.5)
    assert list(df.columns) == [
        "Time",
        "words",
        "text_concat",
        "wps",
        "filler_percentage",
        "pause_percent_pr",
    ]


def test_words_to_windows_aligns_to_grid() -> None:
    whisper_df = pd.DataFrame(
        [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello um world",
                "words": [
                    {"start": 0.0, "end": 0.3, "text": "hello"},
                    {"start": 0.4, "end": 0.5, "text": "um"},
                    {"start": 0.7, "end": 1.0, "text": "world"},
                ],
            }
        ]
    )
    out = words_to_windows(whisper_df, window_size=0.5)
    # window 0.0 should have hello + um (filler), window 0.5 has world
    win0 = out[out["Time"] == 0.0].iloc[0]
    win05 = out[out["Time"] == 0.5].iloc[0]
    assert "hello" in win0["text_concat"]
    assert win0["filler_percentage"] > 0  # "um" counted
    assert win05["text_concat"] == "world"
    assert win05["pause_percent_pr"] == 0.0


def test_assign_speakers_assigns_by_interval() -> None:
    target = pd.DataFrame({"Time": [0.0, 0.5, 1.0, 1.5]})
    # Contract: utterances are in seconds (AssemblyAI loader normalizes ms→sec at boundary).
    utt = pd.DataFrame(
        [{"start": 0.0, "end": 1.0, "speaker": "A"}, {"start": 1.0, "end": 2.0, "speaker": "B"}]
    )
    out = assign_speakers(target, utt)
    assert out.loc[0, "speaker"] == "A"
    assert out.loc[1, "speaker"] == "A"
    assert out.loc[2, "speaker"] == "B"
    assert out.loc[3, "speaker"] == "B"


def test_get_speaker_segments_filters_by_label() -> None:
    utt = pd.DataFrame(
        [
            {"start": 0.0, "end": 0.5, "speaker": "A"},
            {"start": 0.5, "end": 1.5, "speaker": "B"},
            {"start": 1.5, "end": 2.0, "speaker": "A"},
        ]
    )
    segs = get_speaker_segments(utt, speaker="B")
    assert segs == [(0.5, 1.5)]


def test_merge_streams_inner_joins_on_time() -> None:
    face_df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "eyeBlinkLeft": [0.1, 0.2, 0.3],
            "eyeBlinkRight": [0.1, 0.2, 0.3],
            "h_ratio": [0.5, 0.5, 0.5],
        }
    )
    audio_df = pd.DataFrame(
        {
            "Time": [0.0, 0.5, 1.0],
            "audio_rms": [0.01, 0.02, 0.03],
            "audio_pitch_avg": [120.0, 130.0, 140.0],
            "audio_pitch_var": [4.0, 5.0, 6.0],
            "is_silent": [False, False, False],
        }
    )
    merged = merge_streams(face_df, audio_df, pd.DataFrame(), pd.DataFrame())
    assert len(merged) == 3
    assert "audio_rms" in merged.columns
    assert "h_ratio" in merged.columns
    assert "speaker" in merged.columns  # always added, even if all None


def test_robust_zscore_constant_returns_zero() -> None:
    out = robust_zscore(pd.Series([1.0, 1.0, 1.0, 1.0]))
    assert (out == 0.0).all()


def test_robust_zscore_separates_outliers() -> None:
    rng = np.random.default_rng(0)
    base = pd.Series(rng.normal(0, 1, 50))
    spiked = pd.concat([base, pd.Series([20.0])], ignore_index=True)
    out = robust_zscore(spiked)
    assert abs(out.iloc[-1]) > 5  # the outlier has a huge robust z


def test_smooth_and_rz_visual_adds_smooth_and_rz_columns() -> None:
    df = pd.DataFrame(
        {
            "blink_intensity": np.linspace(0, 1, 10),
            "gaze_magnitude": np.linspace(0, 2, 10),
            "jaw_magnitude": np.linspace(0, 3, 10),
            "smile_intensity": np.linspace(0, 0.5, 10),
        }
    )
    out = smooth_and_rz_visual(df)
    for col in ("blink_intensity", "gaze_magnitude", "jaw_magnitude", "smile_intensity"):
        assert f"{col}_smooth" in out.columns
        assert f"{col}_smooth_rz" in out.columns


def test_smooth_and_rz_audio_filters_by_speaker() -> None:
    df = pd.DataFrame(
        {
            "speaker": ["B"] * 8 + ["A"] * 2,
            "loudness_db": np.linspace(-30, -10, 10),
            "pitch_relative_st": np.linspace(-1, 1, 10),
            "pitch_expressiveness_st": np.linspace(0, 5, 10),
            "wps": np.linspace(0, 4, 10),
        }
    )
    out = smooth_and_rz_audio(df, speaker="B")
    # Speaker A rows should have NaN smoothed values
    assert out.loc[8, "loudness_db_smooth"] != out.loc[8, "loudness_db_smooth"]  # NaN != NaN


def test_anomalous_time_ranges_clusters_consecutive_points() -> None:
    times = pd.DataFrame({"Time": [0.5, 1.0, 1.5, 5.0, 5.5]})
    ranges = get_anomalous_time_ranges(times, min=0.5, max=2.0)
    # First three are consecutive ⇒ one range; last two are consecutive ⇒ another
    assert len(ranges) == 2
    assert all(isinstance(r, list) for r in ranges)
