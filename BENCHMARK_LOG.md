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

- Input: 1,814 tokens
- Output: 1,259,960 tokens
- Cache read: 146,770,326 tokens
- Cache write: 8,494,013 tokens
- Session subtotal: (cost not provided)

### Run total (sum across ALL sessions in this run)

- Input: 1,814 tokens
- Output: 1,259,960 tokens
- Cache read: 146,770,326 tokens
- Cache write: 8,494,013 tokens
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

### This-session subtotal (since last fresh Claude Code session start)

- Input: 2,297 tokens
- Output: 1,482,006 tokens
- Cache read: 186,584,419 tokens
- Cache write: 49,564,781 tokens
- Session subtotal: (cost not provided)

### Run total (sum across ALL sessions in this run)

- Input: 2,297 tokens
- Output: 1,482,006 tokens
- Cache read: 186,584,419 tokens
- Cache write: 49,564,781 tokens
- Run total: (cost not provided)

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

## M6 — Frontend

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m6-done`)
- Tag: m6-done
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

- Agent: implemented the full §8 React + Vite + TypeScript + Tailwind
  frontend. Three screens (`UploadScreen`, `AnalyzingScreen`,
  `ReportScreen`) flow as a state machine over a single in-flight job id,
  persisted to `localStorage` per §8.1. TanStack Query handles all server
  state; the Analyzing screen polls `/api/jobs/{id}` every 2 s. Stage
  friendly-text table (`src/lib/stages.ts`) mirrors §8.1.2 verbatim;
  `StageChecklist` renders done / in-progress / pending icons.
  `ReportScreen` shows the three §8.2 sections (Executive Summary +
  Cross-Modal Patterns + Final Conclusion), with semantic tone badges
  (green / gray / amber / red) and pattern-type badges (green / red /
  amber). Markdown download wired via Blob + revoked URL.
  Failed-job state renders an error card + collapsible log tail per §8.3.
  14 vitest tests cover: Upload disabled state, file selection, submit →
  uploadJob → onJobCreated; Analyzing stage label + progress bar +
  per-stage checklist transitions + onSucceeded / onFailed callbacks;
  Report happy path (three sections), empty-segments fallback, all three
  pattern_type badge colors, markdown download, and failed-job error
  card with log tail. `npm run build` succeeds (354 KB JS / 109 KB gz);
  `vite dev` serves cleanly on 127.0.0.1:5177 (smoke-verified by curl).
  Backend test suite (165) still green.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M7 — Docker + CI

- Completed: 2026-06-10
- Commit: (see `git rev-list -n 1 m7-done`)
- Tag: m7-done
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

- Agent: wrote `docker/Dockerfile.backend` (multistage uv build +
  ffmpeg / libsndfile / libgl runtime deps + curl healthcheck) and
  `docker/Dockerfile.frontend` (Node 20 builder → nginx:alpine serve,
  proxying /api to the backend service via `docker/nginx.conf`).
  `docker-compose.yml` exposes backend on :8000 and frontend on :8080,
  mounts `./data:/app/data` for persistence and `./models:/app/models:ro`
  for the MediaPipe weights, and passes `.env` to the backend.
  `.dockerignore` trims the build context (no `.venv`, `data/`,
  `legacy_notebooks/`, `frontend/node_modules`, etc.).
  GitHub Actions: `.github/workflows/ci.yml` runs the three §11 jobs
  (python-lint-and-type, python-tests with coverage, frontend lint +
  typecheck + vitest + build); `.github/workflows/docker.yml` builds
  both images on push-to-main with GHA cache.
  Added ESLint v9 flat config + a minimal `Makefile` with the §12.2
  targets (`dev` / `test` / `lint` / `fmt` / `mypy` / `build` / `clean`).
  Fixed three `ReportScreen` `react-hooks/exhaustive-deps` warnings by
  wrapping `segments` in its own `useMemo`. All four backend acceptance
  checks (ruff, ruff format, mypy, pytest 165) + all four frontend
  acceptance checks (eslint, tsc, vitest 14, vite build) green;
  `docker compose config` validates the full stack. The Docker daemon
  wasn't running on the local machine so the image builds will be
  exercised by the docker.yml CI job on first push to main — captured
  in DECISIONS.md. (Superseded — see the M7 follow-up below.)
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M7 follow-up — Docker image builds verified locally

- Completed: 2026-06-11
- Commit: 9a5f107 ("M7 fix: make Docker images actually buildable
  locally")
- Tag: (none — folded into the M7 milestone)
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal

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

- Agent: re-ran the M7 acceptance with the Docker daemon up. Surfaced
  three real bugs the original M7 commit missed: `.dockerignore`
  excluded `docker/` (so `Dockerfile.frontend`'s `COPY docker/nginx.conf`
  failed), `.dockerignore` excluded `README.md` (which
  `pyproject.toml`'s `readme = "README.md"` requires for `uv sync`),
  and the backend stages needed `--platform=linux/amd64` for
  MediaPipe's `manylinux_2_28_x86_64` wheel. Bumped
  `UV_HTTP_TIMEOUT=600` so the ~800 MB torch download wouldn't time
  out on slow networks. After the fix: `docker build` succeeded for
  both images locally, `docker compose up -d` brought the stack up,
  `/api/health` returned `ok` directly and through the nginx `/api`
  proxy, `/api/jobs` round-tripped through the proxy too, and the SPA
  rendered cleanly in a headless browser with no JS errors. Full
  rationale is captured in the new DECISIONS.md "M7 follow-up" entry.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---

## M8 — Docs + polish

- Completed: 2026-06-11
- Commit: (see `git rev-list -n 1 m8-done` once tagged, or `git log
  --grep='M8: Docs + Polish' -1`)
- Tag: m8-done (the `m8-done` tag already exists on the parallel
  `cc-run` lineage; not retagging — see DECISIONS.md M8 §"What was
  *not* changed")
- Telemetry source used (logfire / Factory UI / other): <FILL IN>

### This-session subtotal

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

- Agent: replaced the M1-scaffold `README.md` and `DEPLOYMENT.md` with
  full documents per spec §12 + §14. README covers a two-paragraph
  product overview, Docker and local-dev quickstarts, an ASCII
  architecture diagram, the full directory layout, a config table
  generated from `backend/app/config.py` + `.env.example`, test
  commands, known limitations, troubleshooting, and links to deeper
  docs. DEPLOYMENT walks through a generic-VPS install with
  `docker compose` + Caddy for TLS, gives an env-var checklist with
  required/optional labels, covers sizing (20 GB volume = ~30
  analyses, 4 vCPU / 8 GB RAM minimum, amd64-only because of
  MediaPipe), backup + reaper + secrets-rotation operational notes,
  three escalating options for adding auth later, and a short Fly.io
  alternative path. DECISIONS.md gains an M8 entry recording why VPS
  beat Fly.io / Railway for the primary doc, why Caddy beat nginx for
  TLS, how the 20 GB volume recommendation was derived, and what was
  deliberately *not* done (no tag move, no spec-compliance audit
  commit beyond this entry). No code changed in M8.
- User: <FILL IN — any retries / restarts / interventions worth noting>

---
