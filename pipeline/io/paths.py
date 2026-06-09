"""Path conventions for pipeline artefacts.

Single source of truth for where intermediate and final files land.
The orchestrator (M2) builds a `PipelinePaths` for each job and reads/writes
through it instead of hard-coding paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelinePaths:
    """Layout for one analysis job's intermediate and final artefacts."""

    root: Path
    job_id: str

    @property
    def job_dir(self) -> Path:
        return self.root / self.job_id

    @property
    def frames_dir(self) -> Path:
        return self.job_dir / "frames"

    @property
    def audio_wav(self) -> Path:
        return self.job_dir / "audio.wav"

    @property
    def face_features_parquet(self) -> Path:
        return self.job_dir / "face_features.parquet"

    @property
    def audio_features_parquet(self) -> Path:
        return self.job_dir / "audio_features.parquet"

    @property
    def utterances_parquet(self) -> Path:
        return self.job_dir / "utterances.parquet"

    @property
    def whisper_parquet(self) -> Path:
        return self.job_dir / "whisper.parquet"

    @property
    def merged_parquet(self) -> Path:
        return self.job_dir / "merged.parquet"

    @property
    def master_parquet(self) -> Path:
        return self.job_dir / "master.parquet"

    @property
    def log_file(self) -> Path:
        return self.job_dir / "job.log"

    def ensure_dirs(self) -> None:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
