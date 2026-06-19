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

from agents._retry import (
    DAILY_QUOTA_MESSAGE,
    RATE_LIMIT_MESSAGE,
    RateLimitedError,
    _is_daily_quota,
)
from agents._settings import AgentSettings, get_agent_settings
from agents._usage import UsageTotals, capture_usage
from agents.orchestrator import build_report
from agents.schemas import FinalReport, WindowAnalysis
from backend.app.config import Settings
from backend.app.db import session_scope
from backend.app.models import Job
from backend.app.services.storage import job_paths
from pipeline._logging import configure_logging
from pipeline.features.linguistic import detect_interviewee
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


def _friendly_error(exc: Exception) -> str:
    """Translate an internal exception into a short, user-facing message.

    Users never see the raw traceback (that still goes to the job log for ops);
    they get a clear sentence about what to fix.
    """
    if isinstance(exc, RateLimitedError):
        return str(exc)
    if _is_daily_quota(exc):
        return DAILY_QUOTA_MESSAGE
    low = str(exc).lower()
    if "gemini_api_key" in low or ("gemini" in low and "key" in low) or "api key not valid" in low:
        return "Your Gemini API key was rejected or isn't set. Check the key and try again."
    if "groq_api_key" in low or ("groq" in low and "key" in low):
        return "Your Groq API key was rejected or isn't set. Check the key and try again."
    if "assemblyai" in low and ("key" in low or "401" in low or "unauthor" in low):
        return "Your AssemblyAI API key was rejected or isn't set. Check the key and try again."
    if "no audio track" in low:
        return (
            "This video has no audio track, so it can't be analyzed. Upload a recording with sound."
        )
    if any(
        s in low for s in ("rate limit", "429", "quota", "resource_exhausted", "too many requests")
    ):
        return RATE_LIMIT_MESSAGE
    if "permission" in low or "403" in low:
        return "The API rejected the request (permission denied). Check that your key has access."
    return (
        "Something went wrong during analysis. Please try again — if it keeps failing, "
        "re-check your video and API keys."
    )


def _run_agents_sync(
    master_df: pd.DataFrame,
    speaker_label: str,
    transcript_df: pd.DataFrame | None,
    *,
    agent_settings: AgentSettings | None = None,
    tier: str = "paid",
) -> tuple[list[WindowAnalysis], FinalReport, UsageTotals]:
    """Wrap the async build_report so BackgroundTasks can call it synchronously.

    `agent_settings` carries any per-request overrides (e.g. a user-supplied
    Gemini key). `tier` picks the full vs lean analysis path. Token usage is
    captured for the whole chain and returned.
    """
    with capture_usage() as usage:
        reports, final = asyncio.run(
            build_report(
                master_df,
                speaker_label=speaker_label,
                transcript_df=transcript_df,
                settings=agent_settings,
                tier=tier,
            )
        )
    return reports, final, usage


def _build_agent_settings(user_gemini_key: str | None) -> AgentSettings:
    """Env-derived agent settings, with the user's Gemini key layered on top
    when supplied (BYOK). The key lives only in this in-memory object."""
    settings = get_agent_settings()
    if user_gemini_key:
        settings = settings.model_copy(update={"gemini_api_key": user_gemini_key})
    return settings


def run_job_blocking(
    job_id: str,
    settings: Settings,
    gemini_api_key: str | None = None,
    assemblyai_api_key: str | None = None,
) -> None:
    """Top-level worker entrypoint.

    Reads the job row, runs the pipeline + agent chain, updates status as it
    goes, persists artefacts. Catches all exceptions and marks the job failed.

    `gemini_api_key` / `assemblyai_api_key` are optional per-request keys (BYOK).
    They are used in-memory only — never written to the DB, the job log, or
    error messages — and fall back to the server's env values when absent.
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
            tier = job.tier or "paid"
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
                assemblyai_api_key=assemblyai_api_key or settings.assemblyai_api_key,
                whisper_model_size=settings.whisper_model_size,
                whisper_device=settings.whisper_device,
            )
            result = run_pipeline(upload_path, pipeline_cfg, progress_cb=_progress_cb)
            # The pipeline resolves "auto" → the detected interviewee label; keep
            # the agents (and the persisted record) in sync with that decision.
            speaker_label = result.speaker_label
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

        # The real pipeline already resolved "auto"; the test-input path skips it,
        # so detect here from the loaded transcript. Persist the resolved label so
        # the record reflects which speaker was actually analyzed.
        if speaker_label.strip().lower() == "auto":
            speaker_label = detect_interviewee(transcript_df) if transcript_df is not None else "B"
            _log.info("Resolved interviewee label (test-input path): %s", speaker_label)
        with session_scope(settings) as session:
            job = session.exec(select(Job).where(Job.id == job_id)).first()
            if job is not None:
                job.speaker_label = speaker_label
                session.add(job)
                session.commit()

        # Stage 10: agents
        with session_scope(settings) as session:
            _set_stage(session, job_id, "running_agents", 0.80)
        reports, final, usage = _run_agents_sync(
            master_df,
            speaker_label,
            transcript_df,
            agent_settings=_build_agent_settings(gemini_api_key),
            tier=tier,
        )

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
            job = session.exec(select(Job).where(Job.id == job_id)).first()
            if job is not None:
                job.input_tokens = usage.input_tokens
                job.output_tokens = usage.output_tokens
                job.total_tokens = usage.total_tokens
                session.add(job)
                session.commit()
            _set_status(session, job_id, status="succeeded", finished=True)
        _log.info(
            "Job %s succeeded (tokens in=%d out=%d total=%d).",
            job_id,
            usage.input_tokens,
            usage.output_tokens,
            usage.total_tokens,
        )

    except Exception as e:
        _log.exception("Job %s failed", job_id)
        # Full traceback goes to the job log (ops/debugging only — never shown to
        # the user). Belt-and-suspenders: redact the user's API keys in case any
        # library echoed them into an exception message.
        try:
            tb = traceback.format_exc()
            for secret in (gemini_api_key, assemblyai_api_key):
                if secret:
                    tb = tb.replace(secret, "***REDACTED***")
            with paths.log_file.open("a", encoding="utf-8") as f:
                f.write("\n=== FAILURE TRACEBACK ===\n")
                f.write(tb)
        except Exception:
            pass
        with session_scope(settings) as session:
            _set_status(session, job_id, status="failed", error=_friendly_error(e), finished=True)


__all__ = ["_ALL_STAGES", "run_job_blocking"]
