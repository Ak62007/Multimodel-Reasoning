"""Build the deterministic test fixtures used by ``tests/unit`` and ``tests/agents``.

Two parquet files are produced:

* ``tiny_master_df.parquet`` — a 60-row master dataframe at 0.5 s resolution
  (= 30 seconds total) containing the full per-row Pydantic-decodable cells
  the pipeline produces. Anomalous windows are injected at 5.0-7.0 s
  (blink_intensity) and 18.0-21.0 s (pitch_relative).
* ``tiny_transcript.parquet`` — a matching transcript slice keyed by
  ``Time`` containing ``words``, ``text_concat`` and ``speaker``.

Generation is **deterministic** (``random.seed(0)``) so the fixture is
content-stable across regenerations. Re-run with::

    uv run python tests/fixtures/generate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.io.parquet import save_df_parquet_safe  # noqa: E402
from pipeline.schemas import (  # noqa: E402
    WPS,
    Blink,
    FillerPercentageIncrease,
    Gaze,
    Jaw,
    LoudnessState,
    PausePercentageIncrease,
    PitchState,
    PitchStd,
    Smile,
)

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
MASTER_PATH = FIXTURE_DIR / "tiny_master_df.parquet"
TRANSCRIPT_PATH = FIXTURE_DIR / "tiny_transcript.parquet"
SPEAKER_MEDIAN_PITCH = 160.0
SPEAKER = "B"

# Two anomalous windows on different features so tests can exercise both
# the per-feature and cross-feature behaviours of the agent layer.
BLINK_ANOMALY_RANGE = [5.0, 5.5, 6.0, 6.5, 7.0]
PITCH_ANOMALY_RANGE = [18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0]


def _build_master_df() -> pd.DataFrame:
    """Construct the tiny master dataframe deterministically."""
    rng = np.random.default_rng(seed=0)
    times = np.arange(0.0, 30.0, 0.5)

    rows: list[dict[str, object]] = []
    for i, t in enumerate(times):
        # Speaker A talks 0-4.5 s; speaker B (the candidate) talks 4.5-30 s.
        speaker: str | None = "A" if t < 4.5 else SPEAKER
        is_blink_anom = t in BLINK_ANOMALY_RANGE
        is_pitch_anom = t in PITCH_ANOMALY_RANGE
        rz_baseline = float(rng.normal(0.0, 0.4))

        blink = Blink(
            intensity=float(rng.uniform(0.0, 0.3)),
            asymmetry=float(rng.uniform(0.0, 0.1)),
            is_blinking=is_blink_anom,
            rz_score=4.0 if is_blink_anom else rz_baseline,
            is_anomalous=is_blink_anom,
            continuous_anomaly=is_blink_anom,
            part_of_anomalous_range=BLINK_ANOMALY_RANGE if is_blink_anom else None,
        )
        gaze = Gaze(
            horizontal_deviation=float(rng.uniform(-0.1, 0.1)),
            vertical_deviation=float(rng.uniform(-0.1, 0.1)),
            primary_direction="center",
            rz_score=rz_baseline,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        jaw = Jaw(
            open=float(rng.uniform(0.0, 0.3)),
            lateral=float(rng.uniform(-0.05, 0.05)),
            forward=float(rng.uniform(0.0, 0.05)),
            is_open=False,
            rz_score=rz_baseline,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )
        smile = Smile(
            intensity=float(rng.uniform(0.0, 0.3)),
            asymmetry=float(rng.uniform(0.0, 0.05)),
            left_intensity=float(rng.uniform(0.0, 0.3)),
            right_intensity=float(rng.uniform(0.0, 0.3)),
            mouth_stretch=float(rng.uniform(0.0, 0.2)),
            is_smiling=False,
            rz_score=rz_baseline,
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )

        row: dict[str, object] = {
            "Time": float(t),
            "blinking_data": blink.model_dump(),
            "gaze_data": gaze.model_dump(),
            "jaw_movement_data": jaw.model_dump(),
            "smile_data": smile.model_dump(),
        }

        if speaker == SPEAKER:
            loudness = LoudnessState(
                level="normal",
                rz_score=rz_baseline,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            pitch_state = PitchState(
                relative_level="higher" if is_pitch_anom else "normal",
                rz_score=2.8 if is_pitch_anom else rz_baseline,
                is_anomalous=is_pitch_anom,
                continuous_anomaly=is_pitch_anom,
                part_of_anomalous_range=PITCH_ANOMALY_RANGE if is_pitch_anom else None,
            )
            pitch_std = PitchStd(
                expressiveness="expressive",
                rz_score=rz_baseline,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            wps = WPS(
                speaking_rate="normal",
                rz_score=rz_baseline,
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            filler = FillerPercentageIncrease(
                filler_percentage_level="normal",
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            pause = PausePercentageIncrease(
                pause_percentage_level="normal",
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            row.update(
                {
                    "loudness_data": loudness.model_dump(),
                    "average_pitch_data": pitch_state.model_dump(),
                    "pitch_standard_deviation": pitch_std.model_dump(),
                    "words_per_sec": wps.model_dump(),
                    "filler_words_usage": filler.model_dump(),
                    "pauses_taken": pause.model_dump(),
                }
            )
        else:
            row.update(
                {
                    "loudness_data": np.nan,
                    "average_pitch_data": np.nan,
                    "pitch_standard_deviation": np.nan,
                    "words_per_sec": np.nan,
                    "filler_words_usage": np.nan,
                    "pauses_taken": np.nan,
                }
            )

        # Carry the speaker label as a plain column to make tests trivial.
        row["speaker"] = speaker
        _ = i  # keep the loop index in scope for future extensions
        rows.append(row)

    return pd.DataFrame(rows)


def _build_transcript_df() -> pd.DataFrame:
    """Build a tiny transcript dataframe aligned with the master Time grid."""
    times = np.arange(0.0, 30.0, 0.5)
    scripted_words = [
        "thanks",
        "for",
        "having",
        "me",
        "today",
        "i",
        "really",
        "appreciate",
        "the",
        "opportunity",
        "to",
        "speak",
        "with",
        "you",
        "about",
        "this",
        "role",
        "and",
        "my",
        "experience",
        "in",
        "machine",
        "learning",
    ]
    rows: list[dict[str, object]] = []
    word_idx = 0
    for t in times:
        speaker = "A" if t < 4.5 else "B"
        if speaker == "B" and word_idx < len(scripted_words):
            words_list = [scripted_words[word_idx]]
            word_idx += 1
        else:
            words_list = []
        rows.append(
            {
                "Time": float(t),
                "speaker": speaker,
                "words": words_list,
                "text_concat": " ".join(words_list),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    master = _build_master_df()
    save_df_parquet_safe(master, str(MASTER_PATH))

    transcript = _build_transcript_df()
    save_df_parquet_safe(transcript, str(TRANSCRIPT_PATH))

    # Record the fixture metadata for tests that need it.
    meta_path = FIXTURE_DIR / "meta.json"
    meta_path.write_text(
        "{\n"
        f'  "rows": {len(master)},\n'
        f'  "duration_sec": {float(master["Time"].iloc[-1]) + 0.5},\n'
        f'  "speaker_median_pitch_hz": {SPEAKER_MEDIAN_PITCH},\n'
        f'  "speaker_label": "{SPEAKER}",\n'
        f'  "blink_anomaly_range": {BLINK_ANOMALY_RANGE},\n'
        f'  "pitch_anomaly_range": {PITCH_ANOMALY_RANGE}\n'
        "}\n"
    )


if __name__ == "__main__":
    main()
