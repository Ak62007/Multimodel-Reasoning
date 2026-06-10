"""Per-row feature transforms and master-dataframe assembly.

Two pieces live here:

1. **Raw feature helpers** (``blink_data``, ``gaze_data``, ``jaw_data``,
   ``smile_data``, ``audio_metrics_from_raw``) convert each row's raw
   blendshape / acoustic values into intermediate dictionaries.

2. **Master-dataframe assembly** (``compute_raw_features``,
   ``feature_engineering``) wraps those helpers into the two passes the
   pipeline runs:

   - ``compute_raw_features`` (used to be ``mode="training"``) emits one
     numeric row per merged-master row containing the derived features
     that feed smoothing + anomaly detection.
   - ``feature_engineering`` (used to be ``mode="evaluation"``) consumes
     the smoothed + RZ'd dataframe plus the anomaly bookkeeping dicts
     and emits the per-row Pydantic-dict cells that downstream agents
     decode.

The split lets us type both passes precisely; the previous
``mode`` parameter was the source of every ``Any | dict`` widening that
mypy flagged in M1.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import librosa
import numpy as np
import pandas as pd

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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-row helpers
# ---------------------------------------------------------------------------


def blink_intensity_only(
    eye_blink_left: float,
    eye_blink_right: float,
    eye_squint_left: float,
    eye_squint_right: float,
    blink_weight: float = 0.8,
    squint_weight: float = 0.2,
) -> float:
    """Average eyelid closure (used as ``blink_intensity``)."""
    left = (eye_blink_left * blink_weight) + (eye_squint_left * squint_weight)
    right = (eye_blink_right * blink_weight) + (eye_squint_right * squint_weight)
    return (left + right) / 2.0


def blink_data(
    eye_blink_left: float,
    eye_blink_right: float,
    eye_squint_left: float,
    eye_squint_right: float,
    blink_weight: float = 0.8,
    squint_weight: float = 0.2,
) -> dict[str, float | bool]:
    """Full per-row blink dict (intensity, asymmetry, ``is_blinking``)."""
    left = (eye_blink_left * blink_weight) + (eye_squint_left * squint_weight)
    right = (eye_blink_right * blink_weight) + (eye_squint_right * squint_weight)
    intensity = (left + right) / 2.0
    return {
        "intensity": intensity,
        "asymmetry": abs(left - right),
        "is_blinking": intensity > 0.5,
    }


def gaze_magnitude_only(
    h_ratio: float,
    eye_look_up_left: float,
    eye_look_up_right: float,
    eye_look_down_left: float,
    eye_look_down_right: float,
    h_center: float = 0.5,
) -> float:
    """Composite gaze magnitude used by anomaly detection."""
    h_deviation = h_ratio - h_center
    look_up = (eye_look_up_left + eye_look_up_right) / 2.0
    look_down = (eye_look_down_left + eye_look_down_right) / 2.0
    intensity_left = max(0.0, min(1.0, -h_deviation / 0.2))
    intensity_right = max(0.0, min(1.0, h_deviation / 0.2))
    intensity_up = min(1.0, look_up / 0.6)
    intensity_down = min(1.0, look_down / 0.6)
    return intensity_left + intensity_right + intensity_up + intensity_down


def gaze_data(
    h_ratio: float,
    eye_look_up_left: float,
    eye_look_up_right: float,
    eye_look_down_left: float,
    eye_look_down_right: float,
    h_center: float = 0.5,
    h_dead_zone: float = 0.08,
    v_threshold: float = 0.15,
) -> dict[str, float | str]:
    """Per-row gaze dict (horizontal/vertical deviations + dominant direction)."""
    h_deviation = h_ratio - h_center
    look_up = (eye_look_up_left + eye_look_up_right) / 2.0
    look_down = (eye_look_down_left + eye_look_down_right) / 2.0
    if look_up > v_threshold:
        primary = "up"
    elif look_down > v_threshold:
        primary = "down"
    elif h_deviation < -h_dead_zone:
        primary = "left"
    elif h_deviation > h_dead_zone:
        primary = "right"
    else:
        primary = "center"
    return {
        "horizontal_deviation": h_deviation,
        "vertical_deviation": look_up - look_down,
        "primary_direction": primary,
    }


def jaw_magnitude_only(
    jaw_open: float,
    jaw_left: float,
    jaw_right: float,
    jaw_forward: float,
) -> float:
    """Composite jaw magnitude used by anomaly detection."""
    return jaw_open + abs(jaw_right - jaw_left) + jaw_forward


def jaw_data(
    jaw_open: float,
    jaw_left: float,
    jaw_right: float,
    jaw_forward: float,
) -> dict[str, float | bool]:
    """Per-row jaw dict (open/lateral/forward components + ``is_open``)."""
    return {
        "open": jaw_open,
        "lateral": jaw_right - jaw_left,
        "forward": jaw_forward,
        "is_open": jaw_open > 0.3,
    }


def smile_intensity_only(
    mouth_smile_left: float,
    mouth_smile_right: float,
    cheek_squint_left: float,
    cheek_squint_right: float,
    smile_weight: float = 0.7,
    squint_weight: float = 0.3,
) -> float:
    """Average smile intensity used by anomaly detection."""
    left = mouth_smile_left * smile_weight + cheek_squint_left * squint_weight
    right = mouth_smile_right * smile_weight + cheek_squint_right * squint_weight
    return (left + right) / 2.0


def smile_data(
    mouth_smile_left: float,
    mouth_smile_right: float,
    cheek_squint_left: float,
    cheek_squint_right: float,
    mouth_stretch_left: float,
    mouth_stretch_right: float,
    smile_weight: float = 0.7,
    squint_weight: float = 0.3,
) -> dict[str, float | bool]:
    """Per-row smile dict (intensity / asymmetry / left / right / stretch / ``is_smiling``)."""
    left = mouth_smile_left * smile_weight + cheek_squint_left * squint_weight
    right = mouth_smile_right * smile_weight + cheek_squint_right * squint_weight
    intensity = (left + right) / 2.0
    return {
        "intensity": intensity,
        "asymmetry": abs(left - right),
        "left_intensity": left,
        "right_intensity": right,
        # Matches the legacy formula in src/sync/Feature_Transformation.py — note
        # it intentionally uses mouth_smile_right (not mouth_stretch_right) for
        # the second term, which was the behaviour the existing master parquets
        # were produced with.
        "mouth_stretch": (mouth_stretch_left + mouth_smile_right) / 2.0,
        "is_smiling": intensity > 0.3,
    }


# ---------------------------------------------------------------------------
# Loudness / pitch categoricals (raw rz_score -> label).
# ---------------------------------------------------------------------------


def loudness_level(rz: float) -> str:
    if rz <= -4.0:
        return "very_quiet"
    if rz <= -2.5:
        return "quiet"
    if rz <= 1.0:
        return "normal"
    if rz <= 4.0:
        return "loud"
    return "very_loud"


def pitch_relative_level(rz: float) -> str:
    if rz <= -3.5:
        return "much_lower"
    if rz <= -1.5:
        return "lower"
    if rz <= 1.5:
        return "normal"
    if rz <= 3.5:
        return "higher"
    return "much_higher"


def pitch_expressiveness_level(rz: float) -> str:
    if rz <= -2.5:
        return "flat"
    if rz <= -0.8:
        return "slightly_expressive"
    if rz <= 2.5:
        return "expressive"
    return "highly_expressive"


def wps_level(rz: float) -> str:
    if rz <= -3.0:
        return "very_slow"
    if rz <= -1.5:
        return "slow"
    if rz <= 1.5:
        return "normal"
    if rz <= 3.0:
        return "fast"
    return "very_fast"


# ---------------------------------------------------------------------------
# Pitch baseline + per-row audio metrics
# ---------------------------------------------------------------------------


def compute_speaker_median_pitch(
    audio_path: str,
    speaker_segments: list[tuple[float, float]],
    sr: int = 16000,
    fmin: float = 50.0,
    fmax: float = 600.0,
) -> float | None:
    """Median voiced f0 over the speaker's segments. ``None`` if unvoiced."""
    y, sr_loaded = librosa.load(audio_path, sr=sr)
    sr_used = int(sr_loaded)
    f0, _voiced_flag, _ = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr_used)
    times = librosa.times_like(f0, sr=sr_used)
    pitches: list[float] = []
    for start, end in speaker_segments:
        mask = (times >= start) & (times <= end)
        voiced = f0[mask]
        voiced = voiced[~np.isnan(voiced)]
        pitches.extend(voiced.tolist())
    if not pitches:
        return None
    return round(float(np.median(pitches)), 2)


def get_speaker_timings(
    speaker_times: pd.DataFrame,
    speaker: str,
) -> list[tuple[float, float]]:
    """Collapse a per-row speaker column into contiguous ``(start, end)`` intervals."""
    not_null = speaker_times[~speaker_times["speaker"].isnull()]
    if not_null.empty:
        return []

    timings: list[dict[str, tuple[float, float]]] = []
    first = not_null.iloc[0]
    start_time = float(first.iloc[0])
    current_speaker = str(first.iloc[1])

    last_time = start_time
    for _, row in speaker_times.iterrows():
        t = float(row.iloc[0])
        sp = row.iloc[1]
        if sp is None:
            continue
        if sp != current_speaker:
            timings.append({current_speaker: (start_time, t)})
            start_time = t
            current_speaker = str(sp)
        last_time = t

    timings.append({current_speaker: (start_time, last_time)})
    return [v for d in timings for k, v in d.items() if k == speaker]


def audio_metrics_from_raw(
    audio_rms: float,
    pitch_avg_hz: float,
    pitch_var_hz2: float,
    speaker_median_pitch_hz: float | None = None,
    eps: float = 1e-9,
) -> dict[str, float | bool]:
    """Convert (rms, pitch_avg_hz, pitch_var_hz2) into (loudness_db, pitch_relative_st, pitch_expressiveness_st)."""
    is_voiced = pitch_avg_hz > 0.0

    loudness_db = 20.0 * math.log10(audio_rms + eps)

    if is_voiced and speaker_median_pitch_hz and speaker_median_pitch_hz > 0:
        pitch_relative_st = 12.0 * math.log2(pitch_avg_hz / speaker_median_pitch_hz)
    else:
        pitch_relative_st = 0.0

    pitch_expressiveness_st = math.sqrt(pitch_var_hz2) if is_voiced else 0.0

    return {
        "is_voiced": is_voiced,
        "loudness_db": round(loudness_db, 2),
        "pitch_relative_st": round(pitch_relative_st, 2),
        "pitch_expressiveness_st": round(pitch_expressiveness_st, 2),
    }


# ---------------------------------------------------------------------------
# Master-dataframe assembly
# ---------------------------------------------------------------------------


def compute_raw_features(
    merged: pd.DataFrame,
    speaker_median_pitch: float | None,
    speaker: str,
) -> pd.DataFrame:
    """Take the merged stream + linguistic features and emit raw derived features.

    Output columns
    --------------
    - ``Time`` and identifying columns are propagated through.
    - ``blink_intensity``, ``gaze_magnitude``, ``jaw_magnitude``,
      ``smile_intensity``: per-row visual features.
    - ``loudness_db``, ``pitch_relative_st``, ``pitch_expressiveness_st``:
      audio features (NaN for non-target-speaker rows).
    """
    rows: list[dict[str, Any]] = []

    for _, r in merged.iterrows():
        blink = blink_intensity_only(
            eye_blink_left=float(r.get("eyeBlinkLeft", 0.0)),
            eye_blink_right=float(r.get("eyeBlinkRight", 0.0)),
            eye_squint_left=float(r.get("eyeSquintLeft", 0.0)),
            eye_squint_right=float(r.get("eyeSquintRight", 0.0)),
        )
        gaze = gaze_magnitude_only(
            h_ratio=float(r.get("h_ratio", 0.5)),
            eye_look_up_left=float(r.get("eyeLookUpLeft", 0.0)),
            eye_look_up_right=float(r.get("eyeLookUpRight", 0.0)),
            eye_look_down_left=float(r.get("eyeLookDownLeft", 0.0)),
            eye_look_down_right=float(r.get("eyeLookDownRight", 0.0)),
        )
        jaw = jaw_magnitude_only(
            jaw_open=float(r.get("jawOpen", 0.0)),
            jaw_left=float(r.get("jawLeft", 0.0)),
            jaw_right=float(r.get("jawRight", 0.0)),
            jaw_forward=float(r.get("jawForward", 0.0)),
        )
        smile = smile_intensity_only(
            mouth_smile_left=float(r.get("mouthSmileLeft", 0.0)),
            mouth_smile_right=float(r.get("mouthSmileRight", 0.0)),
            cheek_squint_left=float(r.get("cheekSquintLeft", 0.0)),
            cheek_squint_right=float(r.get("cheekSquintRight", 0.0)),
        )

        if r.get("speaker") == speaker:
            audio = audio_metrics_from_raw(
                audio_rms=float(r.get("audio_rms", 0.0)),
                pitch_avg_hz=float(r.get("audio_pitch_avg", 0.0)),
                pitch_var_hz2=float(r.get("audio_pitch_var", 0.0)),
                speaker_median_pitch_hz=speaker_median_pitch,
            )
            loudness_db = float(audio["loudness_db"])
            pitch_relative_st = float(audio["pitch_relative_st"])
            pitch_expressiveness_st = float(audio["pitch_expressiveness_st"])
        else:
            loudness_db = float("nan")
            pitch_relative_st = float("nan")
            pitch_expressiveness_st = float("nan")

        rows.append(
            {
                "Time": float(r["Time"]),
                "blink_intensity": blink,
                "gaze_magnitude": gaze,
                "jaw_magnitude": jaw,
                "smile_intensity": smile,
                "loudness_db": loudness_db,
                "pitch_relative_st": pitch_relative_st,
                "pitch_expressiveness_st": pitch_expressiveness_st,
                "words": r.get("words"),
                "text_concat": r.get("text_concat"),
                "speaker": r.get("speaker"),
                "filler_percentage": r.get("filler_percentage"),
                "pause_percent_pr": r.get("pause_percent_pr"),
                "wps": r.get("wps"),
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Computed %d rows of raw derived features", len(df))
    return df


# Map of feature column → master-row column for Pydantic dict assembly.
_FEATURE_TO_OBJECT_COL: dict[str, str] = {
    "blink_intensity_smooth_rz": "blinking_data",
    "gaze_magnitude_smooth_rz": "gaze_data",
    "jaw_magnitude_smooth_rz": "jaw_movement_data",
    "smile_intensity_smooth_rz": "smile_data",
    "loudness_db_smooth_rz": "loudness_data",
    "pitch_relative_st_smooth_rz": "average_pitch_data",
    "pitch_expressiveness_st_smooth_rz": "pitch_standard_deviation",
    "wps_smooth_rz": "words_per_sec",
    "filler_percentage": "filler_words_usage",
    "pause_percent_pr": "pauses_taken",
}


def _anomaly_flags(
    current_time: float,
    feature: str,
    anomalies: dict[str, list[float]],
    c_anomalies: dict[str, list[list[float]]],
) -> tuple[bool, bool, list[float] | None]:
    """Look up per-row anomaly flags for a feature at ``current_time``."""
    anom_times = anomalies.get(feature, [])
    is_anomalous = current_time in anom_times

    c_ranges = c_anomalies.get(feature, [])
    continuous_anomaly = any(current_time in r for r in c_ranges)
    part_of = next((r for r in c_ranges if current_time in r), None)
    return is_anomalous, continuous_anomaly, part_of


def feature_engineering(
    merged: pd.DataFrame,
    smoothed_rz: pd.DataFrame,
    anomalies: dict[str, list[float]],
    c_anomalies: dict[str, list[list[float]]],
    speaker: str,
) -> pd.DataFrame:
    """Assemble the final master dataframe of per-row Pydantic-decodable cells.

    Args:
        merged: The merged + linguistic-feature dataframe (raw inputs).
        smoothed_rz: ``merged`` with smoothed / robust-z columns added.
        anomalies: ``{feature_column: [anomalous timestamps]}``.
        c_anomalies: ``{feature_column: [[time, time, …], …]}`` of
            continuous anomaly ranges.
        speaker: Speaker label whose rows carry audio + verbal data.

    Returns:
        A dataframe with object columns whose JSON-decodable values map to
        the Pydantic schemas in :mod:`pipeline.schemas`.
    """
    rows: list[dict[str, Any]] = []

    for i in range(len(smoothed_rz)):
        current_time = float(smoothed_rz.iloc[i]["Time"])

        # ---- per-row helpers (full dicts, not just intensities) -------
        blink_dict = blink_data(
            eye_blink_left=float(merged.iloc[i].get("eyeBlinkLeft", 0.0)),
            eye_blink_right=float(merged.iloc[i].get("eyeBlinkRight", 0.0)),
            eye_squint_left=float(merged.iloc[i].get("eyeSquintLeft", 0.0)),
            eye_squint_right=float(merged.iloc[i].get("eyeSquintRight", 0.0)),
        )
        gaze_dict = gaze_data(
            h_ratio=float(merged.iloc[i].get("h_ratio", 0.5)),
            eye_look_up_left=float(merged.iloc[i].get("eyeLookUpLeft", 0.0)),
            eye_look_up_right=float(merged.iloc[i].get("eyeLookUpRight", 0.0)),
            eye_look_down_left=float(merged.iloc[i].get("eyeLookDownLeft", 0.0)),
            eye_look_down_right=float(merged.iloc[i].get("eyeLookDownRight", 0.0)),
        )
        jaw_dict = jaw_data(
            jaw_open=float(merged.iloc[i].get("jawOpen", 0.0)),
            jaw_left=float(merged.iloc[i].get("jawLeft", 0.0)),
            jaw_right=float(merged.iloc[i].get("jawRight", 0.0)),
            jaw_forward=float(merged.iloc[i].get("jawForward", 0.0)),
        )
        smile_dict = smile_data(
            mouth_smile_left=float(merged.iloc[i].get("mouthSmileLeft", 0.0)),
            mouth_smile_right=float(merged.iloc[i].get("mouthSmileRight", 0.0)),
            cheek_squint_left=float(merged.iloc[i].get("cheekSquintLeft", 0.0)),
            cheek_squint_right=float(merged.iloc[i].get("cheekSquintRight", 0.0)),
            mouth_stretch_left=float(merged.iloc[i].get("mouthStretchLeft", 0.0)),
            mouth_stretch_right=float(merged.iloc[i].get("mouthStretchRight", 0.0)),
        )

        # ---- visual Pydantic models ----------------------------------
        blink_is_anom, blink_cont, blink_range = _anomaly_flags(
            current_time, "blink_intensity_smooth_rz", anomalies, c_anomalies
        )
        blink = Blink(
            intensity=float(blink_dict["intensity"]),
            asymmetry=float(blink_dict["asymmetry"]),
            is_blinking=bool(blink_dict["is_blinking"]),
            rz_score=float(smoothed_rz.iloc[i].get("blink_intensity_smooth_rz", 0.0) or 0.0),
            is_anomalous=blink_is_anom,
            continuous_anomaly=blink_cont,
            part_of_anomalous_range=blink_range,
        )

        gaze_is_anom, gaze_cont, gaze_range = _anomaly_flags(
            current_time, "gaze_magnitude_smooth_rz", anomalies, c_anomalies
        )
        gaze = Gaze(
            horizontal_deviation=float(gaze_dict["horizontal_deviation"]),
            vertical_deviation=float(gaze_dict["vertical_deviation"]),
            primary_direction=str(gaze_dict["primary_direction"]),  # type: ignore[arg-type]
            rz_score=float(smoothed_rz.iloc[i].get("gaze_magnitude_smooth_rz", 0.0) or 0.0),
            is_anomalous=gaze_is_anom,
            continuous_anomaly=gaze_cont,
            part_of_anomalous_range=gaze_range,
        )

        jaw_is_anom, jaw_cont, jaw_range = _anomaly_flags(
            current_time, "jaw_magnitude_smooth_rz", anomalies, c_anomalies
        )
        jaw = Jaw(
            open=float(jaw_dict["open"]),
            lateral=float(jaw_dict["lateral"]),
            forward=float(jaw_dict["forward"]),
            is_open=bool(jaw_dict["is_open"]),
            rz_score=float(smoothed_rz.iloc[i].get("jaw_magnitude_smooth_rz", 0.0) or 0.0),
            is_anomalous=jaw_is_anom,
            continuous_anomaly=jaw_cont,
            part_of_anomalous_range=jaw_range,
        )

        smile_is_anom, smile_cont, smile_range = _anomaly_flags(
            current_time, "smile_intensity_smooth_rz", anomalies, c_anomalies
        )
        smile = Smile(
            intensity=float(smile_dict["intensity"]),
            asymmetry=float(smile_dict["asymmetry"]),
            left_intensity=float(smile_dict["left_intensity"]),
            right_intensity=float(smile_dict["right_intensity"]),
            mouth_stretch=float(smile_dict["mouth_stretch"]),
            is_smiling=bool(smile_dict["is_smiling"]),
            rz_score=float(smoothed_rz.iloc[i].get("smile_intensity_smooth_rz", 0.0) or 0.0),
            is_anomalous=smile_is_anom,
            continuous_anomaly=smile_cont,
            part_of_anomalous_range=smile_range,
        )

        row: dict[str, Any] = {
            "Time": current_time,
            "blinking_data": blink.model_dump(),
            "gaze_data": gaze.model_dump(),
            "jaw_movement_data": jaw.model_dump(),
            "smile_data": smile.model_dump(),
        }

        # ---- audio + verbal Pydantic models (target speaker only) ----
        if smoothed_rz.iloc[i].get("speaker") == speaker:
            loud_is_anom, loud_cont, loud_range = _anomaly_flags(
                current_time, "loudness_db_smooth_rz", anomalies, c_anomalies
            )
            pa_is_anom, pa_cont, pa_range = _anomaly_flags(
                current_time, "pitch_relative_st_smooth_rz", anomalies, c_anomalies
            )
            ps_is_anom, ps_cont, ps_range = _anomaly_flags(
                current_time, "pitch_expressiveness_st_smooth_rz", anomalies, c_anomalies
            )
            w_is_anom, w_cont, w_range = _anomaly_flags(
                current_time, "wps_smooth_rz", anomalies, c_anomalies
            )
            f_is_anom, f_cont, f_range = _anomaly_flags(
                current_time, "filler_percentage", anomalies, c_anomalies
            )
            p_is_anom, p_cont, p_range = _anomaly_flags(
                current_time, "pause_percent_pr", anomalies, c_anomalies
            )

            loudness = LoudnessState(
                level=loudness_level(  # type: ignore[arg-type]
                    rz=float(smoothed_rz.iloc[i].get("loudness_db_smooth_rz", 0.0) or 0.0)
                ),
                rz_score=float(smoothed_rz.iloc[i].get("loudness_db_smooth_rz", 0.0) or 0.0),
                is_anomalous=loud_is_anom,
                continuous_anomaly=loud_cont,
                part_of_anomalous_range=loud_range,
            )
            pitch_state = PitchState(
                relative_level=pitch_relative_level(  # type: ignore[arg-type]
                    rz=float(smoothed_rz.iloc[i].get("pitch_relative_st_smooth_rz", 0.0) or 0.0)
                ),
                rz_score=float(smoothed_rz.iloc[i].get("pitch_relative_st_smooth_rz", 0.0) or 0.0),
                is_anomalous=pa_is_anom,
                continuous_anomaly=pa_cont,
                part_of_anomalous_range=pa_range,
            )
            pitch_std = PitchStd(
                expressiveness=pitch_expressiveness_level(  # type: ignore[arg-type]
                    rz=float(
                        smoothed_rz.iloc[i].get("pitch_expressiveness_st_smooth_rz", 0.0) or 0.0
                    )
                ),
                rz_score=float(
                    smoothed_rz.iloc[i].get("pitch_expressiveness_st_smooth_rz", 0.0) or 0.0
                ),
                is_anomalous=ps_is_anom,
                continuous_anomaly=ps_cont,
                part_of_anomalous_range=ps_range,
            )
            wps_model = WPS(
                speaking_rate=wps_level(  # type: ignore[arg-type]
                    rz=float(smoothed_rz.iloc[i].get("wps_smooth_rz", 0.0) or 0.0)
                ),
                rz_score=float(smoothed_rz.iloc[i].get("wps_smooth_rz", 0.0) or 0.0),
                is_anomalous=w_is_anom,
                continuous_anomaly=w_cont,
                part_of_anomalous_range=w_range,
            )
            filler = FillerPercentageIncrease(
                filler_percentage_level="abnormally high" if f_is_anom else "normal",
                is_anomalous=f_is_anom,
                continuous_anomaly=f_cont,
                part_of_anomalous_range=f_range,
            )
            pause = PausePercentageIncrease(
                pause_percentage_level="abnormally high" if p_is_anom else "normal",
                is_anomalous=p_is_anom,
                continuous_anomaly=p_cont,
                part_of_anomalous_range=p_range,
            )

            row.update(
                {
                    "loudness_data": loudness.model_dump(),
                    "average_pitch_data": pitch_state.model_dump(),
                    "pitch_standard_deviation": pitch_std.model_dump(),
                    "words_per_sec": wps_model.model_dump(),
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

        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info("Built master dataframe: %d rows x %d cols", *df.shape)
    return df
