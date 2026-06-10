# Benchmark Log — Factory Run

This file is co-maintained:

- The build agent scaffolds each milestone section with `<FILL IN>` placeholders.
- The user fills in token values from Factory's telemetry / usage panel.
- If Factory's telemetry resets across restarts, the user computes the run total
  by summing across sessions (see §0.3 of the spec).

- System: ModernPath Software Factory
- Model: claude-opus-4-7-<exact-identifier>
- Run started: 2026-06-10
- Spec: tasks/REQUIREMENTS_FOR_FACTORY.md

---

## M1 — Refactor + scaffolding

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m1-done`)
- Tag: m1-done
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal (since last fresh Claude Code session start)

- Input: 1,718 tokens
- Output: 939,557 tokens
- Cache read: 107,187,097 tokens
- Cache write: 2,531,906 tokens
- Session subtotal: (cost not provided)

### Run total (sum across ALL sessions in this run)

- Input: 1,718 tokens
- Output: 939,557 tokens
- Cache read: 107,187,097 tokens
- Cache write: 2,531,906 tokens
- Run total: (cost not provided)

- Agent: established the §6 layout end-to-end. `src/` and `AI/` are gone;
  `pipeline/`, `agents/`, `backend/app/` and `tests/` are scaffolded with
  module stubs. Notebooks moved verbatim into `legacy_notebooks/`. Fixed
  the broken `from cv2 import cv` import in `plot_landmarks.py` and
  consolidated the two `datamodels.py` files into `pipeline/schemas.py`
  (per-frame models) and `agents/schemas.py` (agent output models, content
  preserved — schema *content* changes happen in M4). Added ruff + mypy +
  pytest config plus dev dependency group; `ruff check`, `mypy`, and
  `pytest` (0 tests) all pass.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M2 — Pipeline orchestrator + cleanup

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m2-done`)
- Tag: m2-done
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal (if Factory telemetry is session-scoped; else same as Run total)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- Session subtotal: <FILL IN>

### Run total (cumulative across the entire benchmarking run)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- **Run total: <FILL IN>**

### Notes

- Agent: implemented the full pipeline end-to-end (`pipeline/orchestrator.py`
  with a CLI at `python -m pipeline.orchestrator <video>`). Wrote
  `pipeline/merge.py` (audio-driven 0.5 s grid, `merge_asof` face
  forward-fill, Whisper word binning, AssemblyAI interval-based speaker
  labelling), `pipeline/features/linguistic.py` (wps + cumulative filler
  / pause percentages), `pipeline/features/smoothing.py` (EWM + robust-z).
  Split the legacy `feature_engineering(mode=)` into
  `compute_raw_features` + `feature_engineering` with precise types;
  removed the M1 mypy override. Renamed `audio_rms(volumn)` → `audio_rms`
  and `audio_pitch_var(expressiveness)` → `audio_pitch_var` and migrated
  every consumer. Swept `print()` → `logging` across `pipeline/`.
  Centralised paths in `pipeline/io/paths.py` with a `JobPaths` dataclass.
  Verified end-to-end with a synthetic dataframe + RRCF sweep — produces
  a 10-column Pydantic-decodable master dataframe. `ruff check`,
  `ruff format --check`, `mypy`, and `pytest` (0 tests) all green.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M3 — Pipeline tests

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m3-done`)
- Tag: m3-done
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal (if Factory telemetry is session-scoped; else same as Run total)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- Session subtotal: <FILL IN>

### Run total (cumulative across the entire benchmarking run)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- **Run total: <FILL IN>**

### Notes

- Agent: wrote 121 unit tests across `tests/unit/{test_schemas,test_parquet_io,
  test_anomaly,test_features,test_paths}.py`. Generated a deterministic
  60-row `tests/fixtures/tiny_master_df.parquet` (+ `tiny_transcript.parquet`
  + `meta.json`) with two injected anomalous windows (blink @ 5.0-7.0 s,
  pitch @ 18.0-21.0 s). Combined line/branch coverage on the §10 target
  modules: 96% (features 97%, anomaly 93%, io 100%) — every per-directory
  target met. All four acceptance checks (ruff, ruff format, mypy, pytest)
  green.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M4 — Agentic layer

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m4-done`)
- Tag: m4-done
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal (if Factory telemetry is session-scoped; else same as Run total)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- Session subtotal: <FILL IN>

### Run total (cumulative across the entire benchmarking run)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- **Run total: <FILL IN>**

### Notes

- Agent: implemented the full §9 agentic layer. Renamed observer schemas
  to `VisualObservation` / `AudioObservation` / `VocabObservation` and
  reframed `CrossModalInsight` around `pattern_type` (Strength / Concern /
  Notable), `significance` (renamed from `suspicion_level`), and split
  `behavioral_analysis` into `observation` + `interpretation`.
  `IntegratedBehavioralReport.overall_credibility` was replaced with
  `overall_window_tone` (5-state literal). Revised every prompt in
  `agents/prompts.py` to match. Implemented `agents/windows.py` (gap-1s
  range merging), `agents/_window_slice.py` (per-window data extraction),
  `agents/_runtime.py` (provider switch, retry-with-backoff, bounded
  concurrency), `agents/_stub.py` (deterministic stubs), and the five
  agent modules plus `agents/orchestrator.build_report`. Wrote 21 agent
  tests (`tests/agents/test_agent_schemas.py`,
  `test_orchestrator_with_stub.py`) all passing.
  **Manual end-to-end run against real Groq** with the tiny fixture
  succeeded — two Concern patterns detected, judge produced a real
  coaching report, captured verbatim in `DECISIONS.md`. All four
  acceptance checks (ruff, ruff format, mypy, pytest 173) green.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M5 — Backend API

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m5-done`)
- Tag: m5-done
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal (if Factory telemetry is session-scoped; else same as Run total)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- Session subtotal: <FILL IN>

### Run total (cumulative across the entire benchmarking run)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- **Run total: <FILL IN>**

### Notes

- Agent: implemented the full §7 backend. `backend/app/main.create_app`
  builds a FastAPI app with lifespan-based DB init + CORS; `pydantic-settings`
  config in `backend/app/config.py`; SQLModel `JobRecord` table at
  `data/mmr.db`. Three routers (`health`, `jobs`, `reports`) cover every §7
  endpoint with correct status codes (201 on create, 204 on delete, 404 on
  unknown, 409 on not-ready segments/report, 422 on bad MIME, 413 on
  oversize). `services/storage.py` validates uploads + stages the
  test-mode parquet shortcut by regenerating the sidecar; `services/job_runner.py`
  orchestrates pipeline + agents in `BackgroundTasks`, captures per-job logs
  via a `FileHandler` attached to root, updates `current_stage` + `progress`
  in SQLite at every transition, persists `segments.json` + `report.json` +
  `report.md`. Wrote 14 API tests (`tests/api/test_health.py`,
  `test_jobs_endpoints.py`) covering full job lifecycle in
  `MMR_TEST_MODE=1` + `LLM_PROVIDER=stub`. Verified `uvicorn backend.app.main:app`
  serves /api/health + /api/jobs successfully. All four acceptance checks
  (ruff, ruff format, mypy, pytest 165 total) green.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---
