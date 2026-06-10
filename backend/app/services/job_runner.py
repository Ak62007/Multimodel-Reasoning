"""Job runner: orchestrate the pipeline + agents for a single upload.

Runs inside FastAPI :class:`BackgroundTasks` per spec §4. The runner:

1. attaches a per-job log handler so every `logging` call from
   ``pipeline.*`` and ``agents.*`` ends up in the job's log file;
2. updates the SQLite job row at every stage transition;
3. catches any exception, records ``status=failed`` + an error message,
   and writes the full traceback to the job log;
4. persists per-window reports + the final report (markdown + JSON) to
   the job's working directory, where the report router reads them.

The split between ``run_job`` (sync, called by FastAPI) and ``_run_job``
(async) keeps the BackgroundTasks contract simple while still letting us
``await`` the agent orchestrator.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session

from agents import build_report
from agents.schemas import FinalReport, IntegratedBehavioralReport
from backend.app.config import Settings
from backend.app.db import get_engine
from backend.app.models import JobRecord
from pipeline.io.parquet import load_df_parquet_safe
from pipeline.io.paths import UPLOADS_DIR, for_job

logger = logging.getLogger(__name__)


# Public stage list reported through ``Job.current_stage`` (matches §7.3).
# The pipeline's internal ``smoothing`` stage is collapsed into
# ``feature_engineering`` from the API's point of view.
PUBLIC_STAGES: tuple[str, ...] = (
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

_PIPELINE_TO_PUBLIC = {
    "smoothing": "feature_engineering",
}


# ---------------------------------------------------------------------------
# Entrypoint exposed to FastAPI
# ---------------------------------------------------------------------------


def run_job(job_id: str, settings: Settings) -> None:
    """Top-level entrypoint that FastAPI's ``BackgroundTasks`` calls."""
    asyncio.run(_run_job(job_id=job_id, settings=settings))


async def _run_job(*, job_id: str, settings: Settings) -> None:
    job_paths = for_job(job_id)
    job_paths.ensure_dirs()

    file_handler = _attach_job_log_handler(job_paths.log_path)
    started_at = time.monotonic()
    try:
        _update_job(
            job_id,
            settings=settings,
            status="running",
            current_stage=PUBLIC_STAGES[0],
            progress=0.0,
        )
        upload_path = _find_upload_path(job_id)

        if settings.mmr_test_mode and upload_path.suffix.lower() == ".parquet":
            # Test path: skip the heavy pipeline, run only agents on the
            # provided master parquet.
            logger.info("[%s] MMR_TEST_MODE=1: skipping pipeline", job_id)
            _update_job(
                job_id,
                settings=settings,
                current_stage="running_agents",
                progress=0.85,
            )
            master = load_df_parquet_safe(str(job_paths.master_path))
        else:
            master = await _run_pipeline_async(
                job_id=job_id, settings=settings, upload_path=upload_path
            )

        reports, final = await _run_agents(job_id=job_id, settings=settings, master_df=master)
        _persist_agent_outputs(job_paths.workdir, reports, final)

        duration = time.monotonic() - started_at
        _update_job(
            job_id,
            settings=settings,
            status="succeeded",
            current_stage="done",
            progress=1.0,
            duration_sec=duration,
        )
        logger.info("[%s] job complete in %.1fs", job_id, duration)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("[%s] job failed: %s\n%s", job_id, exc, tb)
        current = _get_current_stage(job_id, settings)
        _update_job(
            job_id,
            settings=settings,
            status="failed",
            error=f"{current or 'unknown'}: {exc}",
        )
    finally:
        _detach_job_log_handler(file_handler)


# ---------------------------------------------------------------------------
# Pipeline + agent calls
# ---------------------------------------------------------------------------


async def _run_pipeline_async(
    *,
    job_id: str,
    settings: Settings,
    upload_path: Path,
) -> pd.DataFrame:
    """Run the pipeline (which is sync) on the executor so the event loop is free."""
    from pipeline.io.paths import for_job as paths_for_job
    from pipeline.orchestrator import run_pipeline

    job_paths = paths_for_job(job_id)

    def _reporter(stage: str, fraction: float) -> None:
        public_stage = _PIPELINE_TO_PUBLIC.get(stage, stage)
        public_progress = 0.0 + (fraction * 0.85)  # leave 0.85-1.0 for agents
        _update_job(
            job_id,
            settings=settings,
            current_stage=public_stage,
            progress=public_progress,
        )

    def _runner() -> Path:
        out_workdir = run_pipeline(
            video_path=upload_path,
            speaker_label="B",
            stage_reporter=_reporter,
        )
        # Pipeline writes to its own workdir keyed by video stem; copy to
        # the job's master_path so downstream code is workdir-stable.
        if out_workdir != job_paths.master_path:
            job_paths.ensure_dirs()
            import shutil

            shutil.copy2(out_workdir, job_paths.master_path)
            sidecar = out_workdir.with_name(out_workdir.name + ".schema.json")
            if sidecar.exists():
                shutil.copy2(
                    sidecar,
                    job_paths.master_path.parent / (job_paths.master_path.name + ".schema.json"),
                )
        return job_paths.master_path

    master_path = await asyncio.to_thread(_runner)
    return load_df_parquet_safe(str(master_path))


async def _run_agents(
    *,
    job_id: str,
    settings: Settings,
    master_df: pd.DataFrame,
) -> tuple[list[IntegratedBehavioralReport], FinalReport]:
    _update_job(
        job_id,
        settings=settings,
        current_stage="running_agents",
        progress=0.85,
    )

    seen: list[IntegratedBehavioralReport] = []

    def on_window_done(report: IntegratedBehavioralReport) -> None:
        seen.append(report)
        # Linear progress between 0.85 and 0.95 across windows.
        fraction = min(1.0, len(seen) / max(1, len(seen) + 1))
        _update_job(
            job_id,
            settings=settings,
            progress=0.85 + 0.10 * fraction,
        )

    reports, final = await build_report(
        master_df=master_df,
        speaker_label="B",
        on_window_done=on_window_done,
        max_concurrency=settings.agent_max_concurrency,
    )

    _update_job(
        job_id,
        settings=settings,
        current_stage="generating_final_report",
        progress=0.95,
    )

    return reports, final


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _persist_agent_outputs(
    workdir: Path,
    reports: list[IntegratedBehavioralReport],
    final: FinalReport,
) -> None:
    segments_path = workdir / "segments.json"
    report_md_path = workdir / "report.md"
    report_json_path = workdir / "report.json"

    segments_path.write_text(json.dumps([r.model_dump(mode="json") for r in reports], indent=2))
    report_json_path.write_text(json.dumps(final.model_dump(mode="json"), indent=2))
    report_md_path.write_text(_render_markdown(final))


def _render_markdown(final: FinalReport) -> str:
    return (
        "# Executive Summary\n\n"
        f"{final.executive_summary.strip()}\n\n"
        "# Behavioral Strengths\n\n"
        f"{final.behavioral_strengths.strip()}\n\n"
        "# Major Problems & Triggers\n\n"
        f"{final.vulnerabilities_and_triggers.strip()}\n\n"
        "# How to Improve - Actionable Coaching\n\n"
        f"{final.areas_for_improvement.strip()}\n"
    )


# ---------------------------------------------------------------------------
# DB write helpers
# ---------------------------------------------------------------------------


def _update_job(
    job_id: str,
    *,
    settings: Settings,
    status: str | None = None,
    current_stage: str | None = None,
    progress: float | None = None,
    error: str | None = None,
    duration_sec: float | None = None,
) -> None:
    engine = get_engine(settings)
    with Session(engine) as session:
        job = session.get(JobRecord, job_id)
        if job is None:
            logger.warning("[%s] update_job: row missing", job_id)
            return
        if status is not None:
            job.status = status
        if current_stage is not None:
            job.current_stage = current_stage
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if error is not None:
            job.error = error
        if duration_sec is not None:
            job.duration_sec = duration_sec
        job.updated_at = datetime.now(tz=UTC)
        session.add(job)
        session.commit()


def _get_current_stage(job_id: str, settings: Settings) -> str | None:
    engine = get_engine(settings)
    with Session(engine) as session:
        job = session.get(JobRecord, job_id)
        return job.current_stage if job else None


def _find_upload_path(job_id: str) -> Path:
    for candidate in UPLOADS_DIR.glob(f"{job_id}.*"):
        return candidate
    raise FileNotFoundError(f"No upload file found for job {job_id}")


# ---------------------------------------------------------------------------
# Log handler attach / detach
# ---------------------------------------------------------------------------


def _attach_job_log_handler(log_path: Path) -> logging.Handler:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    return handler


def _detach_job_log_handler(handler: logging.Handler) -> None:
    logging.getLogger().removeHandler(handler)
    handler.close()
