"""Tests for ``pipeline.io.paths`` — env-driven path resolution + JobPaths."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _reload_paths() -> object:
    """Re-import ``pipeline.io.paths`` so it picks up monkey-patched env vars."""
    import pipeline.io.paths as paths

    return importlib.reload(paths)


def test_for_video_uses_video_stem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    paths = _reload_paths()

    job = paths.for_video("/some/path/interview_42.mp4")  # type: ignore[attr-defined]
    assert "interview_42" in str(job.workdir)
    assert job.audio_path.name == "audio.wav"
    assert job.master_path.name == "master.parquet"


def test_for_job_keyed_by_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    paths = _reload_paths()

    job = paths.for_job("abcd-1234")  # type: ignore[attr-defined]
    assert job.workdir.name == "abcd-1234"
    assert job.frames_dir.parent == job.workdir
    assert job.face_features_path.parent == job.workdir / "parquet"


def test_ensure_dirs_creates_workdir_and_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    paths = _reload_paths()

    job = paths.for_job("job-1")  # type: ignore[attr-defined]
    job.ensure_dirs()
    assert job.workdir.is_dir()
    assert job.frames_dir.is_dir()
    assert (job.workdir / "parquet").is_dir()


def test_for_video_falls_back_to_default_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    paths = _reload_paths()

    # Empty stem path → falls back to "video"
    job = paths.for_video(Path(""))  # type: ignore[attr-defined]
    assert job.workdir.name == "video"


def test_face_landmarker_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom.task"
    custom.write_text("")
    monkeypatch.setenv("FACE_LANDMARKER_PATH", str(custom))
    paths = _reload_paths()
    assert paths.FACE_LANDMARKER_PATH == custom  # type: ignore[attr-defined]


def test_default_paths_resolve_inside_repo() -> None:
    # No env vars: defaults must live under REPO_ROOT.
    import pipeline.io.paths as paths

    importlib.reload(paths)
    assert paths.REPO_ROOT.exists()
    assert paths.DATA_DIR.name == "data"
    assert paths.MODELS_DIR.name == "models"
