"""Sample frames from a video at a fixed rate.

Each frame is written as a JPEG whose filename encodes its timestamp:
``<index>_ts_<seconds>.jpg``. The face-feature pipeline later parses that
filename to recover the time axis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2 as cv

logger = logging.getLogger(__name__)


class VideoOpenError(RuntimeError):
    """Raised when OpenCV cannot open the source video."""


def extract_frames(
    video_path: str | Path,
    output_path: str | Path,
    nof_ps: int = 1,
) -> list[tuple[str, float]]:
    """Sample frames from ``video_path`` into ``output_path``.

    Args:
        video_path: Path to the source video.
        output_path: Directory to write JPEGs into. Created if missing.
        nof_ps: Frames-per-second to sample. Default 1 fps.

    Returns:
        A list of ``(jpeg_path, time_seconds)`` tuples in order.

    Raises:
        VideoOpenError: If the video cannot be opened.
    """
    video_path = str(video_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    vid = cv.VideoCapture(video_path)
    if not vid.isOpened():
        raise VideoOpenError(f"Cannot open video: {video_path}")

    fps = vid.get(cv.CAP_PROP_FPS)
    total_frame = vid.get(cv.CAP_PROP_FRAME_COUNT)
    vid_duration_ms = (total_frame / fps) * 1000 if fps > 0 else 0.0

    result: list[tuple[str, float]] = []
    current_time_ms: float = 0.0
    frame_cnt = 0
    step_ms = 1000.0 / nof_ps

    try:
        while current_time_ms < vid_duration_ms:
            vid.set(cv.CAP_PROP_POS_MSEC, current_time_ms)
            ok, frame = vid.read()
            if not ok or frame is None:
                logger.warning("Could not read frame at %.3fs", current_time_ms / 1000.0)
                current_time_ms += step_ms
                continue

            time_frame = current_time_ms / 1000.0
            path = str(output_path / f"{frame_cnt + 1}_ts_{time_frame}.jpg")
            cv.imwrite(path, frame)
            result.append((path, time_frame))

            frame_cnt += 1
            current_time_ms += step_ms
    finally:
        vid.release()

    logger.info("Sampled %d frames from %s into %s", len(result), video_path, output_path)
    return result
