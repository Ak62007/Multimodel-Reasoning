"""Tests for `pipeline.io.paths.PipelinePaths`."""

from __future__ import annotations

from pathlib import Path

from pipeline.io.paths import PipelinePaths


def test_paths_derive_from_root_and_job_id(tmp_path: Path) -> None:
    paths = PipelinePaths(root=tmp_path, job_id="abc123")
    assert paths.job_dir == tmp_path / "abc123"
    assert paths.frames_dir == tmp_path / "abc123" / "frames"
    assert paths.audio_wav == tmp_path / "abc123" / "audio.wav"
    assert paths.face_features_parquet == tmp_path / "abc123" / "face_features.parquet"
    assert paths.audio_features_parquet == tmp_path / "abc123" / "audio_features.parquet"
    assert paths.utterances_parquet == tmp_path / "abc123" / "utterances.parquet"
    assert paths.whisper_parquet == tmp_path / "abc123" / "whisper.parquet"
    assert paths.merged_parquet == tmp_path / "abc123" / "merged.parquet"
    assert paths.master_parquet == tmp_path / "abc123" / "master.parquet"
    assert paths.log_file == tmp_path / "abc123" / "job.log"


def test_ensure_dirs_creates_job_and_frames(tmp_path: Path) -> None:
    paths = PipelinePaths(root=tmp_path, job_id="ensure")
    paths.ensure_dirs()
    assert paths.job_dir.is_dir()
    assert paths.frames_dir.is_dir()


def test_paths_are_frozen() -> None:
    import dataclasses

    paths = PipelinePaths(root=Path("/tmp"), job_id="x")
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        paths.job_id = "y"  # type: ignore[misc]
