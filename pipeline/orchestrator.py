"""End-to-end pipeline orchestrator.

Maps `(video_path, job_id) → master.parquet`. Stages match spec §7's
`current_stage` enum so the backend can stream progress.

Usage (CLI):
    python -m pipeline.orchestrator <video_path> [--job-id ID] [--speaker B]
        [--data-root data] [--face-model models/face_landmarker.task]
        [--no-transcribe-assemblyai] [--no-transcribe-whisper]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline._logging import configure_logging
from pipeline.anomaly import (
    adaptive_n_sigma,
    get_anomalous_time_ranges,
    get_threshold_mad,
    run_rrcf,
    smooth_and_rz_audio,
    smooth_and_rz_visual,
)
from pipeline.audio.extract import extract_audio
from pipeline.audio.technical import analyze_audio_layers
from pipeline.audio.transcribe_assemblyai import get_utterances_data
from pipeline.audio.transcribe_whisper import get_whisper_data
from pipeline.features.linguistic import detect_interviewee, get_speaker_segments
from pipeline.features.transforms import compute_speaker_median_pitch, feature_engineering
from pipeline.io.parquet import save_df_parquet_safe
from pipeline.io.paths import PipelinePaths
from pipeline.merge import merge_streams
from pipeline.video.face_features import face_analysis_data
from pipeline.video.frame_extractor import extract_frames

_log = logging.getLogger(__name__)


# Canonical stage names — must match spec §7 / backend's `current_stage` enum.
STAGES = (
    "extracting_frames",
    "extracting_audio",
    "extracting_face_features",
    "extracting_audio_features",
    "transcribing",
    "merging",
    "feature_engineering",
    "anomaly_detection",
    "building_master_df",
)

# Columns RRCF runs over (already smoothed + robust-z-scored).
_RZ_VISUAL = [
    "blink_intensity_smooth_rz",
    "gaze_magnitude_smooth_rz",
    "jaw_magnitude_smooth_rz",
    "smile_intensity_smooth_rz",
]
_RZ_AUDIO = [
    "loudness_db_smooth_rz",
    "pitch_relative_st_smooth_rz",
    "pitch_expressiveness_st_smooth_rz",
    "wps_smooth_rz",
]

# Linguistic features are categorical: `is_anomalous` derives directly from
# `filler_percentage > 0` and `pause_percent_pr == 1.0` per the legacy
# bookkeeping (see `pipeline/features/transforms.py`).
_CATEGORICAL_FEATURES = ("filler_percentage", "pause_percent_pr")


ProgressCallback = Callable[[str, float], None]


@dataclass
class PipelineConfig:
    """Runtime configuration for one analysis job."""

    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    data_root: Path = Path("data/processed")
    speaker_label: str = "B"
    face_model_path: Path = Path("models/face_landmarker.task")
    frames_per_second: int = 1
    window_size_sec: float = 0.5

    # External services
    assemblyai_api_key: str | None = None
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"

    # Stage toggles (useful for testing without API keys / for partial reruns)
    enable_assemblyai: bool = True
    enable_whisper: bool = True


@dataclass
class PipelineResult:
    """Output paths produced by a successful pipeline run."""

    job_id: str
    paths: PipelinePaths
    master_df_path: Path
    speaker_label: str = "B"


def _resolve_speaker(requested: str, utterances_df: pd.DataFrame) -> str:
    """Resolve the interviewee label. An explicit label wins; ``"auto"`` (or
    blank) triggers heuristic detection from the diarized utterances."""
    if requested and requested.strip().lower() != "auto":
        return requested
    detected = detect_interviewee(utterances_df)
    _log.info("Auto-detected interviewee speaker label: %s", detected)
    return detected


def _emit(progress_cb: ProgressCallback | None, stage: str, frac: float) -> None:
    if progress_cb is not None:
        try:
            progress_cb(stage, frac)
        except Exception:
            _log.exception("Progress callback raised")


def _detect_per_feature(
    df: pd.DataFrame,
    rz_columns: list[str],
) -> tuple[dict[str, list[float]], dict[str, list[list[float]]]]:
    """RRCF + adaptive MAD threshold + continuous-range grouping per column."""
    anomalies: dict[str, list[float]] = {}
    c_anomalies: dict[str, list[list[float]]] = {}

    for col in rz_columns:
        if col not in df.columns:
            _log.warning("anomaly detection: column %s missing — skipping", col)
            anomalies[col] = []
            c_anomalies[col] = []
            continue

        series = df[col].dropna()
        if series.empty:
            anomalies[col] = []
            c_anomalies[col] = []
            continue

        features = series.to_numpy().reshape(-1, 1)
        scores = np.asarray(run_rrcf(features))
        n_sigma = adaptive_n_sigma(scores)
        threshold = get_threshold_mad(scores, n_sigma=n_sigma)

        mask = scores > threshold
        anomalous_times = df.loc[series.index[mask], "Time"].astype(float).tolist()
        anomalies[col] = anomalous_times

        time_df = pd.DataFrame({"Time": anomalous_times}).reset_index(drop=True)
        c_anomalies[col] = get_anomalous_time_ranges(time_df, min=0.5, max=2.0)

    return anomalies, c_anomalies


def _detect_categorical(
    df: pd.DataFrame,
) -> tuple[dict[str, list[float]], dict[str, list[list[float]]]]:
    """Categorical anomaly bookkeeping for filler %, pause %.

    A row is "anomalous" if `filler_percentage > 0` / `pause_percent_pr >= 1.0`.
    Matches the legacy notebook's bookkeeping so `feature_engineering` can
    consume the same shape of dict.
    """
    anomalies: dict[str, list[float]] = {}
    c_anomalies: dict[str, list[list[float]]] = {}
    for col in _CATEGORICAL_FEATURES:
        if col not in df.columns:
            anomalies[col] = []
            c_anomalies[col] = []
            continue
        if col == "filler_percentage":
            mask = df[col].fillna(0) > 0.0
        else:  # pause_percent_pr
            mask = df[col].fillna(0) >= 1.0
        anomalous_times = df.loc[mask, "Time"].astype(float).tolist()
        anomalies[col] = anomalous_times
        time_df = pd.DataFrame({"Time": anomalous_times}).reset_index(drop=True)
        c_anomalies[col] = get_anomalous_time_ranges(time_df, min=0.5, max=2.0)
    return anomalies, c_anomalies


def run_pipeline(
    video_path: str | Path,
    config: PipelineConfig | None = None,
    *,
    progress_cb: ProgressCallback | None = None,
) -> PipelineResult:
    """Run the full pipeline end-to-end.

    Reports progress through `progress_cb(stage_name, fraction_0_to_1)`.
    Returns a `PipelineResult` whose `master_df_path` points at the final
    Pydantic-dict parquet.
    """
    config = config or PipelineConfig()
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    paths = PipelinePaths(root=config.data_root, job_id=config.job_id)
    paths.ensure_dirs()

    n_stages = len(STAGES)

    def _stage_started(name: str, idx: int) -> None:
        _log.info("[stage %d/%d] %s", idx + 1, n_stages, name)
        _emit(progress_cb, name, idx / n_stages)

    # 1. extracting_frames
    _stage_started("extracting_frames", 0)
    extract_frames(video_path, paths.frames_dir, nof_ps=config.frames_per_second)

    # 2. extracting_audio
    _stage_started("extracting_audio", 1)
    audio_path = extract_audio(video_path, output_path=paths.audio_wav)
    if audio_path is None:
        raise RuntimeError("Video has no audio track — cannot continue.")

    # 3. extracting_face_features
    _stage_started("extracting_face_features", 2)
    if not config.face_model_path.exists():
        raise FileNotFoundError(
            f"MediaPipe face_landmarker model not found at {config.face_model_path}. "
            "Download `face_landmarker.task` from MediaPipe and place it there."
        )
    face_df = face_analysis_data(
        model_path=str(config.face_model_path), images_path=str(paths.frames_dir)
    )
    save_df_parquet_safe(face_df, paths.face_features_parquet)

    # 4. extracting_audio_features
    _stage_started("extracting_audio_features", 3)
    audio_df = analyze_audio_layers(audio_path, segment_length=config.window_size_sec)
    if audio_df is None:
        raise RuntimeError("Audio feature extraction returned None.")
    save_df_parquet_safe(audio_df, paths.audio_features_parquet)

    # 5. transcribing
    _stage_started("transcribing", 4)
    utterances_df = pd.DataFrame()
    whisper_df = pd.DataFrame()
    if config.enable_assemblyai:
        if not config.assemblyai_api_key:
            raise RuntimeError(
                "AssemblyAI enabled but ASSEMBLYAI_API_KEY is not set. "
                "Set the env var or pass enable_assemblyai=False."
            )
        utterances_df = get_utterances_data(config.assemblyai_api_key, audio_path)
        save_df_parquet_safe(utterances_df, paths.utterances_parquet)
    if config.enable_whisper:
        whisper_df = get_whisper_data(
            str(audio_path),
            model_size=config.whisper_model_size,
            device=config.whisper_device,
        )
        save_df_parquet_safe(whisper_df, paths.whisper_parquet)

    # 6. merging
    _stage_started("merging", 5)
    merged = merge_streams(
        face_df=face_df,
        audio_df=audio_df,
        whisper_df=whisper_df,
        utterances_df=utterances_df,
        window_size=config.window_size_sec,
    )
    save_df_parquet_safe(merged, paths.merged_parquet)

    # Resolve which diarized speaker is the interviewee. When the caller passes
    # "auto" (the default from the UI) we infer it from who holds the floor
    # longest; an explicit label still wins. Everything downstream — pitch
    # normalization, audio anomaly smoothing, the agent transcript filter — keys
    # off this single resolved label.
    speaker = _resolve_speaker(config.speaker_label, utterances_df)

    # 7. feature_engineering (training mode → raw transformed metrics)
    _stage_started("feature_engineering", 6)
    speaker_segments = get_speaker_segments(utterances_df, speaker=speaker)
    speaker_median_pitch = (
        compute_speaker_median_pitch(audio_path=str(audio_path), speaker_segments=speaker_segments)
        if speaker_segments
        else 0.0
    )
    trained = feature_engineering(
        c_anomalies=None,
        anomalies=None,
        df=merged,
        norm_rz_df=None,
        speaker_median_pitch=speaker_median_pitch or 0.0,
        speaker=speaker,
        mode="training",
    )
    enriched = pd.concat([merged.reset_index(drop=True), trained.reset_index(drop=True)], axis=1)

    # 8. anomaly_detection
    _stage_started("anomaly_detection", 7)
    enriched = smooth_and_rz_visual(enriched)
    enriched = smooth_and_rz_audio(enriched, speaker=speaker)

    visual_anom, visual_c_anom = _detect_per_feature(enriched, _RZ_VISUAL)
    audio_anom, audio_c_anom = _detect_per_feature(enriched, _RZ_AUDIO)
    cat_anom, cat_c_anom = _detect_categorical(enriched)

    anomalies = {**visual_anom, **audio_anom, **cat_anom}
    c_anomalies = {**visual_c_anom, **audio_c_anom, **cat_c_anom}

    # 9. building_master_df (evaluation mode → Pydantic-dict columns)
    _stage_started("building_master_df", 8)
    master_rows = feature_engineering(
        c_anomalies=c_anomalies,
        anomalies=anomalies,
        df=enriched,
        norm_rz_df=enriched,
        speaker_median_pitch=speaker_median_pitch or 0.0,
        speaker=speaker,
        mode="evaluation",
    )
    master_df = pd.concat(
        [enriched[["Time", "speaker"]].reset_index(drop=True), master_rows.reset_index(drop=True)],
        axis=1,
    )
    save_df_parquet_safe(master_df, paths.master_parquet)

    _emit(progress_cb, "building_master_df", 1.0)
    _log.info("Pipeline complete. Master parquet at %s", paths.master_parquet)

    return PipelineResult(
        job_id=config.job_id,
        paths=paths,
        master_df_path=paths.master_parquet,
        speaker_label=speaker,
    )


def _parse_argv(argv: list[str]) -> tuple[Path, PipelineConfig]:
    parser = argparse.ArgumentParser(description="MMR end-to-end pipeline")
    parser.add_argument("video_path", type=Path)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--speaker", default="B")
    parser.add_argument("--data-root", type=Path, default=Path("data/processed"))
    parser.add_argument("--face-model", type=Path, default=Path("models/face_landmarker.task"))
    parser.add_argument("--fps", type=int, default=1)
    parser.add_argument("--window-size", type=float, default=0.5)
    parser.add_argument("--no-transcribe-assemblyai", action="store_true")
    parser.add_argument("--no-transcribe-whisper", action="store_true")
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--whisper-device", default="cpu")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    cfg = PipelineConfig(
        job_id=args.job_id or uuid.uuid4().hex[:12],
        data_root=args.data_root,
        speaker_label=args.speaker,
        face_model_path=args.face_model,
        frames_per_second=args.fps,
        window_size_sec=args.window_size,
        assemblyai_api_key=os.environ.get("ASSEMBLYAI_API_KEY"),
        enable_assemblyai=not args.no_transcribe_assemblyai,
        enable_whisper=not args.no_transcribe_whisper,
        whisper_model_size=args.whisper_model,
        whisper_device=args.whisper_device,
    )
    return args.video_path, cfg


def main(argv: list[str] | None = None) -> int:
    # Best-effort `.env` autoload for ad-hoc CLI use. The backend (M5) loads
    # config via pydantic-settings instead and does not depend on this.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    argv = argv if argv is not None else sys.argv[1:]
    video_path, config = _parse_argv(argv)

    configure_logging(level=logging.INFO)
    result = run_pipeline(video_path, config)
    sys.stdout.write(str(result.master_df_path) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STAGES",
    "PipelineConfig",
    "PipelineResult",
    "run_pipeline",
]
