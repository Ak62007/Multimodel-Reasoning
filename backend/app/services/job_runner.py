"""Glue between FastAPI's BackgroundTasks queue and the pipeline + agent chain.

Designed so the executor can be swapped to Celery/RQ/Arq later without
touching the routers. `run_job_blocking` is fully synchronous and only uses
`asyncio.run` for the agent chain step.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from agents.orchestrator import build_report
from agents.schemas import FinalReport, WindowAnalysis
from backend.app.config import Settings
from backend.app.db import session_scope
from backend.app.models import Job
from backend.app.services.storage import job_paths
from pipeline._logging import configure_logging
from pipeline.io.parquet import load_df_parquet_safe, save_df_parquet_safe
from pipeline.orchestrator import PipelineConfig, run_pipeline

_log = logging.getLogger(__name__)

# Backend-side stage list — pipeline (9) + agentic (2) per spec §7.
_ALL_STAGES = (
    "extracting_frames",
    "extracting_audio",
    "extracting_face_features",
    "extracting_audio_features",
    "transcribing",
    "merging",
    "feature_engineering",
    "anomaly_detection",
    "building_master_df",
    "running_agents",
    "generating_final_report",
)


def _set_stage(session: Session, job_id: str, stage: str, progress: float) -> None:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if job is None:
        return
    job.current_stage = stage
    job.progress = float(progress)
    job.updated_at = datetime.now(UTC)
    session.add(job)
    session.commit()


def _set_status(
    session: Session,
    job_id: str,
    *,
    status: str,
    error: str | None = None,
    finished: bool = False,
) -> None:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if job is None:
        return
    job.status = status
    if error is not None:
        job.error = error
    if status == "running" and job.started_at is None:
        job.started_at = datetime.now(UTC)
    if finished:
        job.finished_at = datetime.now(UTC)
        job.progress = 1.0
    job.updated_at = datetime.now(UTC)
    session.add(job)
    session.commit()


def _save_segments_and_report(
    reports: list[WindowAnalysis],
    final: FinalReport,
    *,
    segments_path: Path,
    report_path: Path,
) -> None:
    """Persist the per-window journal + final report as JSON next to the master parquet."""
    segments_path.parent.mkdir(parents=True, exist_ok=True)
    segments_path.write_text(json.dumps([r.model_dump() for r in reports], indent=2, default=str))
    report_path.write_text(json.dumps(final.model_dump(), indent=2, default=str))


def _fmt_ts(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _build_markdown(final: FinalReport) -> str:
    """Render the new report. The timestamped highlights are the centrepiece —
    they're the user's 'jump back to the video' list."""
    parts = [f"# {final.headline}\n", "## Overview\n", f"{final.overview}\n"]
    parts.append("## Behavioral Arc\n")
    parts.append(f"{final.behavioral_arc}\n")

    parts.append("## Highlights — moments worth re-watching\n")
    if final.highlights:
        for h in final.highlights:
            mods = ", ".join(h.modalities) if h.modalities else "—"
            parts.append(
                f"### {_fmt_ts(h.ts_start)}–{_fmt_ts(h.ts_end)} · {h.kind} · {h.significance}\n"
                f"**{h.title}**\n\n"
                f"{h.what_happened}\n\n"
                f"*Why it matters:* {h.why_it_matters}  \n"
                f"*Modalities:* {mods}\n"
            )
    else:
        parts.append("_No standout moments surfaced._\n")

    if final.threads:
        parts.append("## Recurring Threads\n")
        for t in final.threads:
            stamps = ", ".join(_fmt_ts(o) for o in t.occurrences) or "—"
            parts.append(
                f"### {t.title} ({t.relation})\n"
                f"{t.summary}\n\n"
                f"*Seen at:* {stamps}  \n"
                f"*Read:* {t.interpretation}\n"
            )

    if final.coaching_notes:
        parts.append("## Coaching Notes\n")
        parts.append(f"{final.coaching_notes}\n")

    return "\n".join(parts)


def _run_agents_sync(
    master_df: pd.DataFrame,
    speaker_label: str,
    transcript_df: pd.DataFrame | None,
) -> tuple[list[WindowAnalysis], FinalReport]:
    """Wrap the async build_report so BackgroundTasks can call it synchronously."""
    return asyncio.run(
        build_report(master_df, speaker_label=speaker_label, transcript_df=transcript_df)
    )


def run_job_blocking(job_id: str, settings: Settings) -> None:
    """Top-level worker entrypoint.

    Reads the job row, runs the pipeline + agent chain, updates status as it
    goes, persists artefacts. Catches all exceptions and marks the job failed.
    """
    paths = job_paths(settings.processed_dir, job_id)
    paths.ensure_dirs()

    # Re-configure logging so per-job logs land in paths.log_file.
    configure_logging(level=logging.INFO, log_file=paths.log_file, force=True)

    try:
        with session_scope(settings) as session:
            job = session.exec(select(Job).where(Job.id == job_id)).first()
            if job is None:
                _log.error("job_runner: job %s not found", job_id)
                return
            upload_path = Path(job.upload_path)
            speaker_label = job.speaker_label
            is_test_input = job.is_test_input
            _set_status(session, job_id, status="running")

        if is_test_input:
            # Test-mode path: skip stages 1-9, load the pre-computed master parquet.
            _log.info("Test-mode upload: skipping pipeline, loading %s", upload_path)
            master_df = load_df_parquet_safe(upload_path)
            save_df_parquet_safe(master_df, paths.master_parquet)
        else:
            # Real pipeline path: run stages 1-9 with progress callback.
            def _progress_cb(stage: str, frac: float) -> None:
                with session_scope(settings) as session:
                    # Reserve the last ~22% for the agent chain.
                    _set_stage(session, job_id, stage, frac * 0.78)

            pipeline_cfg = PipelineConfig(
                job_id=job_id,
                data_root=settings.processed_dir,
                speaker_label=speaker_label,
                face_model_path=settings.face_landmarker_path,
                assemblyai_api_key=settings.assemblyai_api_key,
                whisper_model_size=settings.whisper_model_size,
                whisper_device=settings.whisper_device,
            )
            run_pipeline(upload_path, pipeline_cfg, progress_cb=_progress_cb)
            master_df = load_df_parquet_safe(paths.master_parquet)

        # Load the transcript so the agents know *what was said* (utterances
        # preferred — it carries speaker labels; whisper is the fallback).
        transcript_df: pd.DataFrame | None = None
        if paths.utterances_parquet.exists():
            transcript_df = load_df_parquet_safe(paths.utterances_parquet)
        elif paths.whisper_parquet.exists():
            _log.warning("No utterances.parquet — falling back to whisper (no speaker labels).")
            transcript_df = load_df_parquet_safe(paths.whisper_parquet)
        else:
            _log.warning("No transcript parquet found — agents run without spoken context.")

        # Stage 10: agents
        with session_scope(settings) as session:
            _set_stage(session, job_id, "running_agents", 0.80)
        reports, final = _run_agents_sync(master_df, speaker_label, transcript_df)

        # Stage 11: final report persistence
        with session_scope(settings) as session:
            _set_stage(session, job_id, "generating_final_report", 0.95)

        segments_path = paths.job_dir / "segments.json"
        report_path = paths.job_dir / "report.json"
        markdown_path = paths.job_dir / "report.md"
        _save_segments_and_report(
            reports, final, segments_path=segments_path, report_path=report_path
        )
        markdown_path.write_text(_build_markdown(final))

        with session_scope(settings) as session:
            _set_status(session, job_id, status="succeeded", finished=True)
        _log.info("Job %s succeeded.", job_id)

    except Exception as e:
        _log.exception("Job %s failed", job_id)
        # Persist traceback to job log
        try:
            with paths.log_file.open("a", encoding="utf-8") as f:
                f.write("\n=== FAILURE TRACEBACK ===\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        with session_scope(settings) as session:
            _set_status(session, job_id, status="failed", error=str(e), finished=True)


__all__ = ["_ALL_STAGES", "run_job_blocking"]
