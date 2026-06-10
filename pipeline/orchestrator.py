"""End-to-end MMR pipeline: video → master parquet.

Twelve stages run in this order — names match :data:`PIPELINE_STAGES` and
are reported via the ``stage_reporter`` callback so the FastAPI backend
(M5) can surface them as ``current_stage`` on the job record.

::

    extracting_frames
        ↓
    extracting_audio
        ↓
    extracting_face_features
        ↓
    extracting_audio_features
        ↓
    transcribing
        ↓
    merging
        ↓
    feature_engineering         # raw derived features
        ↓
    smoothing                    # EWM + robust-z
        ↓
    anomaly_detection            # RRCF + MAD threshold + ranges
        ↓
    building_master_df           # Pydantic-decodable per-row cells
        ↓
    final master parquet on disk

Run as a CLI::

    uv run python -m pipeline.orchestrator <video_path> --speaker B

That is the M2 acceptance command. The function ``run_pipeline`` is the
importable surface used by the backend job runner in M5.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.anomaly.ranges import (
    adaptive_n_sigma,
    get_anomalous_time_ranges,
    get_threshold_mad,
)
from pipeline.anomaly.rrcf import run_rrcf
from pipeline.audio.extract import extract_audio
from pipeline.audio.technical import analyze_audio_layers
from pipeline.audio.transcribe_assemblyai import get_utterances_data
from pipeline.audio.transcribe_whisper import get_whisper_data
from pipeline.features.linguistic import compute_linguistic_features
from pipeline.features.smoothing import (
    AUDIO_SPANS,
    VISUAL_SPANS,
    apply_smoothing_rz,
)
from pipeline.features.transforms import (
    compute_raw_features,
    compute_speaker_median_pitch,
    feature_engineering,
    get_speaker_timings,
)
from pipeline.io.parquet import save_df_parquet_safe
from pipeline.io.paths import FACE_LANDMARKER_PATH, for_video
from pipeline.merge import merge_streams
from pipeline.video.face_features import face_analysis_data
from pipeline.video.frame_extractor import extract_frames

logger = logging.getLogger(__name__)


PIPELINE_STAGES: tuple[str, ...] = (
    "extracting_frames",
    "extracting_audio",
    "extracting_face_features",
    "extracting_audio_features",
    "transcribing",
    "merging",
    "feature_engineering",
    "smoothing",
    "anomaly_detection",
    "building_master_df",
)


StageReporter = Callable[[str, float], None]


def _noop_reporter(stage: str, progress: float) -> None:
    pass


# Smoothed-RZ feature columns we run anomaly detection on. The two
# categorical linguistic features (filler / pause) are anomaly-flagged
# directly from their already-thresholded percentage values, not via RRCF.
_RRCF_FEATURES: tuple[str, ...] = tuple(
    [f"{name}_smooth_rz" for name in VISUAL_SPANS] + [f"{name}_smooth_rz" for name in AUDIO_SPANS]
)


def run_pipeline(
    video_path: str | Path,
    *,
    speaker_label: str = "B",
    face_landmarker_path: str | Path | None = None,
    skip_assemblyai: bool = False,
    skip_whisper: bool = False,
    stage_reporter: StageReporter | None = None,
    nof_ps: int = 1,
) -> Path:
    """Run every pipeline stage on ``video_path`` and write the master parquet.

    Args:
        video_path: Path to the source interview video.
        speaker_label: AssemblyAI speaker label of the interviewee
            (defaults to ``"B"`` — interviewer is typically ``"A"``).
        face_landmarker_path: Override the MediaPipe weights location.
            Defaults to :data:`pipeline.io.paths.FACE_LANDMARKER_PATH`.
        skip_assemblyai: Skip diarised transcription (debug/dev only;
            the resulting master parquet will have ``speaker = None`` on
            every row, so all audio features will be NaN).
        skip_whisper: Skip word-level transcription (debug/dev only).
        stage_reporter: Optional callback invoked as
            ``reporter(stage_name, progress_fraction)``. ``progress_fraction``
            is the fraction of stages completed (``0.0-1.0``).
        nof_ps: Frames-per-second to sample from the video.

    Returns:
        Path to the master parquet on disk.
    """
    reporter = stage_reporter or _noop_reporter
    paths = for_video(video_path)
    paths.ensure_dirs()
    landmarker = Path(face_landmarker_path) if face_landmarker_path else FACE_LANDMARKER_PATH

    if not landmarker.exists():
        raise FileNotFoundError(
            f"face_landmarker.task not found at {landmarker} — "
            "set FACE_LANDMARKER_PATH or drop the weights under models/."
        )

    logger.info("=== MMR pipeline starting for %s ===", video_path)
    logger.info("Workdir: %s", paths.workdir)

    # ---- 1. frames -----------------------------------------------------
    reporter("extracting_frames", 0.0)
    extract_frames(video_path=video_path, output_path=paths.frames_dir, nof_ps=nof_ps)

    # ---- 2. audio ------------------------------------------------------
    reporter("extracting_audio", 1 / len(PIPELINE_STAGES))
    audio_path = extract_audio(video_path=video_path, output_path=paths.audio_path)
    if audio_path is None:
        raise RuntimeError("Audio extraction failed — see logs")

    # ---- 3. face features ---------------------------------------------
    reporter("extracting_face_features", 2 / len(PIPELINE_STAGES))
    face_df = face_analysis_data(model_path=landmarker, images_path=paths.frames_dir)
    if face_df is None or face_df.empty:
        raise RuntimeError("Face feature extraction produced no rows")
    save_df_parquet_safe(face_df, str(paths.face_features_path))

    # ---- 4. audio technical -------------------------------------------
    reporter("extracting_audio_features", 3 / len(PIPELINE_STAGES))
    audio_df = analyze_audio_layers(audio_path=audio_path)
    if audio_df is None or audio_df.empty:
        raise RuntimeError("Audio technical feature extraction produced no rows")
    save_df_parquet_safe(audio_df, str(paths.audio_technical_path))

    # ---- 5. transcription ---------------------------------------------
    reporter("transcribing", 4 / len(PIPELINE_STAGES))
    if skip_assemblyai:
        logger.warning("Skipping AssemblyAI transcription (debug flag set)")
        utterances_df = pd.DataFrame(columns=["text", "start", "end", "speaker", "words"])
    else:
        utterances_df = get_utterances_data(audio_path=audio_path)
    save_df_parquet_safe(utterances_df, str(paths.utterances_path))

    if skip_whisper:
        logger.warning("Skipping Whisper transcription (debug flag set)")
        whisper_df = pd.DataFrame(columns=["start", "end", "text", "words"])
    else:
        whisper_df = get_whisper_data(audio_path=audio_path)
    save_df_parquet_safe(whisper_df, str(paths.whisper_path))

    # ---- 6. merge ------------------------------------------------------
    reporter("merging", 5 / len(PIPELINE_STAGES))
    merged = merge_streams(
        face_df=face_df,
        audio_df=audio_df,
        utterances_df=utterances_df,
        whisper_df=whisper_df,
    )
    merged = compute_linguistic_features(merged, speaker=speaker_label)
    save_df_parquet_safe(merged, str(paths.merged_path))

    # ---- 7. feature engineering (raw) ---------------------------------
    reporter("feature_engineering", 6 / len(PIPELINE_STAGES))
    speaker_intervals = get_speaker_timings(
        merged[["Time", "speaker"]].copy(), speaker=speaker_label
    )
    median_pitch = None
    if speaker_intervals:
        try:
            median_pitch = compute_speaker_median_pitch(
                audio_path=str(audio_path), speaker_segments=speaker_intervals
            )
        except Exception:
            logger.exception("compute_speaker_median_pitch failed — falling back to None")

    raw_features = compute_raw_features(
        merged=merged,
        speaker_median_pitch=median_pitch,
        speaker=speaker_label,
    )
    save_df_parquet_safe(raw_features, str(paths.features_raw_path))

    # ---- 8. smoothing + rz --------------------------------------------
    reporter("smoothing", 7 / len(PIPELINE_STAGES))
    smoothed = apply_smoothing_rz(raw_features, speaker=speaker_label)
    save_df_parquet_safe(smoothed, str(paths.features_smoothed_path))

    # ---- 9. anomaly detection -----------------------------------------
    reporter("anomaly_detection", 8 / len(PIPELINE_STAGES))
    anomalies, c_anomalies = _detect_anomalies(smoothed)

    # ---- 10. building master df ---------------------------------------
    reporter("building_master_df", 9 / len(PIPELINE_STAGES))
    master = feature_engineering(
        merged=merged,
        smoothed_rz=smoothed,
        anomalies=anomalies,
        c_anomalies=c_anomalies,
        speaker=speaker_label,
    )
    save_df_parquet_safe(master, str(paths.master_path))

    reporter("done", 1.0)
    logger.info("=== Pipeline complete — master parquet at %s ===", paths.master_path)
    return paths.master_path


# ---------------------------------------------------------------------------
# Anomaly detection sweep
# ---------------------------------------------------------------------------


def _detect_anomalies(
    smoothed: pd.DataFrame,
) -> tuple[dict[str, list[float]], dict[str, list[list[float]]]]:
    """Run RRCF + MAD thresholding on every smoothed feature column.

    Returns two parallel dicts keyed by feature column:
    ``anomalies[feature] -> [anomalous timestamps]``
    ``c_anomalies[feature] -> [[t, t, ...], ...]`` continuous ranges.

    Filler / pause percentages are not run through RRCF; they get an
    empty-list entry, which means downstream code treats them as
    non-anomalous unless the categorical level was flagged earlier.
    """
    anomalies: dict[str, list[float]] = {}
    c_anomalies: dict[str, list[list[float]]] = {}

    for feature in _RRCF_FEATURES:
        series = smoothed[feature].copy()
        # speaker-restricted features have NaN for the other speaker; we
        # forward-fill so RRCF gets a continuous stream, then mask out
        # any rows whose original value was NaN from the anomaly outputs.
        valid_mask = series.notna()
        if not valid_mask.any():
            anomalies[feature] = []
            c_anomalies[feature] = []
            continue

        feature_arr = series.ffill().bfill().to_numpy(dtype=float)
        times = smoothed["Time"].to_numpy(dtype=float)
        if len(feature_arr) < 2:
            anomalies[feature] = []
            c_anomalies[feature] = []
            continue

        scores = np.array(run_rrcf(feature_arr.reshape(-1, 1)))
        n_sigma = adaptive_n_sigma(scores)
        threshold = get_threshold_mad(scores, n_sigma=n_sigma)

        flagged = (scores >= threshold) & valid_mask.to_numpy()
        anom_times = times[flagged].tolist()
        anomalies[feature] = [float(t) for t in anom_times]

        ranges_df = pd.DataFrame({"Time": anom_times}).sort_values("Time").reset_index(drop=True)
        c_anomalies[feature] = get_anomalous_time_ranges(ranges_df)

    # Linguistic categoricals — no RRCF; downstream marks "abnormally high"
    # via the FillerPercentageIncrease / PausePercentageIncrease enums.
    anomalies.setdefault("filler_percentage", [])
    c_anomalies.setdefault("filler_percentage", [])
    anomalies.setdefault("pause_percent_pr", [])
    c_anomalies.setdefault("pause_percent_pr", [])
    return anomalies, c_anomalies


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _configure_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.orchestrator",
        description="Run the MMR pipeline on a video file and write a master parquet.",
    )
    parser.add_argument("video", type=Path, help="Path to the input video file")
    parser.add_argument(
        "--speaker",
        default="B",
        help="AssemblyAI speaker label of the interviewee (default: B)",
    )
    parser.add_argument(
        "--face-landmarker",
        type=Path,
        default=None,
        help="Path to MediaPipe face_landmarker.task (defaults to models/face_landmarker.task)",
    )
    parser.add_argument("--fps", type=int, default=1, help="Frames-per-second to sample")
    parser.add_argument("--skip-assemblyai", action="store_true")
    parser.add_argument("--skip-whisper", action="store_true")
    parser.add_argument(
        "-v", "--verbose", action="count", default=1, help="Increase verbosity (repeatable)"
    )

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if not args.video.exists():
        print(f"Video not found: {args.video}", file=sys.stderr)
        return 2

    master = run_pipeline(
        video_path=args.video,
        speaker_label=args.speaker,
        face_landmarker_path=args.face_landmarker,
        skip_assemblyai=args.skip_assemblyai,
        skip_whisper=args.skip_whisper,
        stage_reporter=lambda s, p: logger.info("stage=%s progress=%.2f", s, p),
        nof_ps=args.fps,
    )
    print(master)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
