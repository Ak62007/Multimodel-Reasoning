"""Extract an audio track from a video file as WAV.

If `output_path` is supplied, audio is written there directly; otherwise the
output filename derives from the video filename and lands in `output_dir`.
The orchestrator always passes an explicit path; the bare-name defaults exist
for ad-hoc CLI use only.
"""

from __future__ import annotations

import logging
from pathlib import Path

from moviepy import VideoFileClip

_log = logging.getLogger(__name__)


def extract_audio(
    video_path: str | Path,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    output_ext: str = "wav",
) -> Path | None:
    """Extract audio from `video_path` to a WAV file.

    Provide either `output_path` (preferred) or `output_dir` (filename is
    derived from `video_path`). Returns the resolved output path, or None if
    the source video has no audio track.
    """
    video_path = Path(video_path)

    if output_path is None:
        if output_dir is None:
            raise ValueError("Provide either output_path or output_dir.")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}.{output_ext.lstrip('.')}"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        _log.info("Audio already exists, reusing: %s", output_path)
        return output_path

    try:
        video_clip = VideoFileClip(str(video_path))
        if video_clip.audio is None:
            _log.error("Video has no audio track: %s", video_path)
            video_clip.close()
            return None
        video_clip.audio.write_audiofile(str(output_path), logger="bar")
        video_clip.close()
        _log.info("Extracted audio to %s", output_path)
        return output_path
    except Exception:
        _log.exception("Failed to extract audio from %s", video_path)
        raise
