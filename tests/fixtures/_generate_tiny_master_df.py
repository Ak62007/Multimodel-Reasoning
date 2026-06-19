"""One-shot generator for `tests/fixtures/tiny_master_df.parquet`.

Produces a synthetic ~30s master dataframe with two engineered anomalous
windows so anomaly-detection and agent tests have something to chew on.

Run once and commit the output:
    uv run python tests/fixtures/_generate_tiny_master_df.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.io.parquet import save_df_parquet_safe
from pipeline.schemas import (
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

OUT_PARQUET = Path(__file__).parent / "tiny_master_df.parquet"
OUT_JSON = Path(__file__).parent / "sample_anomaly_dicts.json"

# 60 rows × 0.5s = 30s of synthetic interview data
N_ROWS = 60
WINDOW = 0.5
SPEAKER_LABEL = "B"

# Two engineered anomalous ranges (inclusive, in seconds).
ANOM_RANGE_BLINK = [5.0, 5.5, 6.0]  # 5–6s blink cluster
ANOM_RANGE_AUDIO = [22.0, 22.5, 23.0, 23.5]  # 22–23.5s audio anomaly


def _is_anom(t: float, anom_range: list[float]) -> tuple[bool, bool, list[float] | None]:
    """Return (is_anomalous, continuous_anomaly, part_of_range_or_None)."""
    in_range = t in anom_range
    return in_range, in_range, anom_range if in_range else None


def main() -> None:
    rng = np.random.default_rng(0)
    rows = []

    for i in range(N_ROWS):
        t = round(i * WINDOW, 2)
        # 80% B (interviewee), 20% A (interviewer)
        speaker = "B" if i % 5 != 0 else "A"

        b_anom, b_cont, b_range = _is_anom(t, ANOM_RANGE_BLINK)
        blink = Blink(
            intensity=float(rng.uniform(0, 0.3) if not b_anom else rng.uniform(0.7, 1.0)),
            asymmetry=float(rng.uniform(0, 0.1)),
            is_blinking=b_anom,
            rz_score=float(rng.normal(0, 0.5) if not b_anom else rng.uniform(2.5, 4.0)),
            is_anomalous=b_anom,
            continuous_anomaly=b_cont,
            part_of_anomalous_range=b_range,
        )

        gaze = Gaze(
            horizontal_deviation=float(rng.uniform(-0.1, 0.1)),
            vertical_deviation=float(rng.uniform(-0.1, 0.1)),
            primary_direction="center",
            rz_score=float(rng.normal(0, 0.5)),
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )

        jaw = Jaw(
            open=float(rng.uniform(0, 0.4)),
            lateral=float(rng.uniform(-0.05, 0.05)),
            forward=float(rng.uniform(0, 0.1)),
            is_open=False,
            rz_score=float(rng.normal(0, 0.5)),
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )

        smile = Smile(
            intensity=float(rng.uniform(0, 0.3)),
            asymmetry=float(rng.uniform(0, 0.1)),
            left_intensity=float(rng.uniform(0, 0.3)),
            right_intensity=float(rng.uniform(0, 0.3)),
            mouth_stretch=float(rng.uniform(0, 0.2)),
            is_smiling=False,
            rz_score=float(rng.normal(0, 0.5)),
            is_anomalous=False,
            continuous_anomaly=False,
            part_of_anomalous_range=None,
        )

        row = {
            "Time": t,
            "speaker": speaker,
            "blinking_data": blink.model_dump(),
            "gaze_data": gaze.model_dump(),
            "jaw_movement_data": jaw.model_dump(),
            "smile_data": smile.model_dump(),
        }

        if speaker == SPEAKER_LABEL:
            a_anom, a_cont, a_range = _is_anom(t, ANOM_RANGE_AUDIO)
            loudness = LoudnessState(
                level="loud" if a_anom else "normal",
                rz_score=float(rng.uniform(2.5, 4.0) if a_anom else rng.normal(0, 0.5)),
                is_anomalous=a_anom,
                continuous_anomaly=a_cont,
                part_of_anomalous_range=a_range,
            )
            pitch = PitchState(
                relative_level="higher" if a_anom else "normal",
                rz_score=float(rng.uniform(2.0, 3.0) if a_anom else rng.normal(0, 0.5)),
                is_anomalous=a_anom,
                continuous_anomaly=a_cont,
                part_of_anomalous_range=a_range,
            )
            pitchstd = PitchStd(
                expressiveness="expressive",
                rz_score=float(rng.normal(0, 0.5)),
                is_anomalous=False,
                continuous_anomaly=False,
                part_of_anomalous_range=None,
            )
            wps = WPS(
                speaking_rate="normal",
                rz_score=float(rng.normal(0, 0.5)),
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
            row["loudness_data"] = loudness.model_dump()
            row["average_pitch_data"] = pitch.model_dump()
            row["pitch_standard_deviation"] = pitchstd.model_dump()
            row["words_per_sec"] = wps.model_dump()
            row["filler_words_usage"] = filler.model_dump()
            row["pauses_taken"] = pause.model_dump()
        else:
            row["loudness_data"] = None
            row["average_pitch_data"] = None
            row["pitch_standard_deviation"] = None
            row["words_per_sec"] = None
            row["filler_words_usage"] = None
            row["pauses_taken"] = None

        rows.append(row)

    df = pd.DataFrame(rows)
    save_df_parquet_safe(df, OUT_PARQUET)

    # Companion sample_anomaly_dicts.json for tests that need raw c_anomalies/anomalies
    sample = {
        "anomalies": {
            "blink_intensity_smooth_rz": ANOM_RANGE_BLINK,
            "gaze_magnitude_smooth_rz": [],
            "jaw_magnitude_smooth_rz": [],
            "smile_intensity_smooth_rz": [],
            "loudness_db_smooth_rz": ANOM_RANGE_AUDIO,
            "pitch_relative_st_smooth_rz": ANOM_RANGE_AUDIO,
            "pitch_expressiveness_st_smooth_rz": [],
            "wps_smooth_rz": [],
            "filler_percentage": [],
            "pause_percent_pr": [],
        },
        "c_anomalies": {
            "blink_intensity_smooth_rz": [ANOM_RANGE_BLINK],
            "gaze_magnitude_smooth_rz": [],
            "jaw_magnitude_smooth_rz": [],
            "smile_intensity_smooth_rz": [],
            "loudness_db_smooth_rz": [ANOM_RANGE_AUDIO],
            "pitch_relative_st_smooth_rz": [ANOM_RANGE_AUDIO],
            "pitch_expressiveness_st_smooth_rz": [],
            "wps_smooth_rz": [],
            "filler_percentage": [],
            "pause_percent_pr": [],
        },
    }
    OUT_JSON.write_text(json.dumps(sample, indent=2))

    print(f"Wrote {OUT_PARQUET} ({len(df)} rows × {df.shape[1]} cols)")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
