"""Extract the audio track from a video file to a WAV.

Thin wrapper around MoviePy. The caller is expected to pass an explicit
``output_path`` (see :mod:`pipeline.io.paths`) so there are no hidden
relative paths.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from moviepy import VideoFileClip

logger = logging.getLogger(__name__)


def extract_audio(
    video_path: str | Path,
    output_path: str | Path,
) -> Path | None:
    """Extract the audio track from ``video_path`` to ``output_path``.

    Args:
        video_path: Path to the source video.
        output_path: Path where the WAV file should be written.

    Returns:
        The resolved output path, or ``None`` if the video has no audio /
        extraction failed.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info("Audio already exists at %s — reusing", output_path)
        return output_path

    try:
        with VideoFileClip(str(video_path)) as clip:
            if clip.audio is None:
                logger.error("Video has no audio: %s", video_path)
                return None
            clip.audio.write_audiofile(str(output_path), logger=None)
    except Exception:
        logger.exception("Failed to extract audio from %s", video_path)
        return None

    logger.info("Wrote audio to %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path
