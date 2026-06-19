"""Sample frames from a video at `nof_ps` per second.

The filename convention `{n}_ts_{seconds}.jpg` is load-bearing — downstream
`face_features.face_analysis_data` parses the timestamp out of the stem.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2 as cv

_log = logging.getLogger(__name__)


def extract_frames(
    video_path: str | Path, output_path: str | Path, nof_ps: int = 1
) -> list[tuple[str, float]]:
    """Sample frames from `video_path` at `nof_ps` frames per second.

    Returns a list of `(frame_path, time_seconds)` pairs sorted by time.
    Raises `FileNotFoundError` if the video can't be opened.
    """
    video_path = str(video_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    result: list[tuple[str, float]] = []
    vid = cv.VideoCapture(video_path)
    if not vid.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = vid.get(cv.CAP_PROP_FPS)
    total_frame = vid.get(cv.CAP_PROP_FRAME_COUNT)
    vid_duration_ms = (total_frame / fps) * 1000

    current_time_ms: float = 0.0
    frame_cnt = 0

    while current_time_ms < vid_duration_ms:
        vid.set(cv.CAP_PROP_POS_MSEC, current_time_ms)
        ok, frame = vid.read()
        if not ok or frame is None:
            _log.debug("frame read failed at t=%.3fs", current_time_ms / 1000)
            current_time_ms += 1000 / nof_ps
            continue

        time_frame = current_time_ms / 1000
        path = str(output_path / f"{frame_cnt + 1}_ts_{time_frame}.jpg")
        cv.imwrite(path, frame)

        frame_cnt += 1
        current_time_ms += 1000 / nof_ps
        result.append((path, time_frame))

    vid.release()
    _log.info("Extracted %d frames from %s", len(result), video_path)
    return result
