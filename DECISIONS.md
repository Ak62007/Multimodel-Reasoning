# Decisions log

Recorded decisions made during the brownfield refactor when the build brief
left a detail genuinely ambiguous (not just unspecified). Spec wins ties.

## M1 — Refactor + scaffolding

- **`pipeline/utils.py` kept as a standalone module.** The target layout in
  spec §6 does not list a `utils.py`, but the original `src/utils/utils.py`
  contained a small `secs_mins` helper. Lifted as-is into `pipeline/utils.py`
  rather than deleting it (might be useful in M2 logging) or dropping it into
  another module where it doesn't belong.

- **`pipeline/anomaly/ranges.py` re-exports from `rrcf.py`.** The brief lists
  `ranges.py` separately, but the existing `get_anomalous_time_ranges`
  implementation has no rrcf dependency and lives in the same file. Re-export
  rather than duplicate, with a docstring explaining why.

- **Plotting helpers moved to `legacy_notebooks/_plotting/`.** The brief
  requires fixing the broken `from cv2 import cv` import in `plot_landmarks.py`
  but does not specify where the file should live in the new layout (none of
  `pipeline/`, `agents/`, or `backend/app/` is the right home — plotting is
  notebook-debug-only). Moved to `legacy_notebooks/_plotting/` and fixed the
  import there.

- **`AI/My First Board.jpg` preserved as `legacy_notebooks/board.jpg`.** It is
  reference material the author committed deliberately; not deleting it.

- **`pipeline/features/linguistic.py`, `pipeline/merge.py`,
  `pipeline/orchestrator.py`, and most files under `agents/` and
  `backend/app/` are stubs in M1.** They exist with docstrings explaining what
  goes where. Full implementations land in their target milestone (M2, M4, M5)
  per the execution order in spec §13.

- **Pydantic schemas for agent outputs not yet updated to the new
  `pattern_type`/`overall_window_tone` shape.** Spec §9.5 requires schema
  changes (rename `suspicion_level` → `significance`, add `pattern_type`,
  relax `overall_credibility` to `overall_window_tone`), but those touch
  agent code that doesn't exist yet. Schema work deferred to M4 alongside
  the agent implementations and prompts they're paired with — applying them
  in M1 would leave dead-code mismatches between the new schemas and the
  unchanged prompts.

- **Prompts not yet revised.** `agents/prompts.py` is moved verbatim from
  `AI/prompts.py`. Spec §9.6 requires revising them to match the
  Strength/Concern/Notable framing; that revision is bundled with M4 so the
  prompts and the matching schema changes ship together.

- **`from src.utils.datamodels import *` in `transforms.py` replaced with a
  precise list of names actually used downstream.** Wildcard imports trip
  ruff and hide what the module actually depends on.

- **Mypy `check_untyped_defs = false`** because the existing pipeline code is
  largely untyped and tightening this in M1 would require hundreds of
  annotations. Reassess in M3 once tests anchor behavior.

- **Ruff `extend-exclude = ["legacy_notebooks", ...]`** because the legacy
  files intentionally retain old style.

## M2 — Pipeline orchestrator + cleanup

- **Column renames touch only `pipeline/audio/technical.py` (producer) and
  `pipeline/features/transforms.py` (consumer).** `audio_rms(volumn)` →
  `audio_rms`, `audio_pitch_var(expressiveness)` → `audio_pitch_var`. The
  legacy notebooks under `legacy_notebooks/` still reference the old names —
  they're frozen reference material so we don't migrate them.

- **`extract_audio` signature widened.** Original took only `output_dir`; the
  orchestrator needs a precise output path. Added an `output_path` parameter
  that takes precedence over `output_dir`; the original `output_dir` form is
  preserved for ad-hoc CLI use. Removed the bare `../data/raw/` default since
  it is a relative path that depended on `cwd`.

- **`AssemblyAI` timestamps normalized ms→sec at the boundary
  (`transcribe_assemblyai.py`), not in consumers.** Earlier I tried defensive
  "max > 10_000" sniffing in `linguistic.py` and it failed on short
  utterances. The contract is now: utterances DataFrames always carry
  start/end in seconds. Documented in the docstring of `assign_speakers` /
  `get_speaker_segments`.

- **Linguistic features (`wps`, `filler_percentage`, `pause_percent_pr`)
  implemented in `pipeline/features/linguistic.py`.** The legacy notebooks
  load these from a pre-computed parquet; the actual compute code lived in a
  separate processing stage not visible from the four input notebooks.
  Re-derived from whisper-timestamped word-level segments using a simple
  filler-token list + `[*]` disfluency markers. The bookkeeping shape
  (anomalies dict keys) matches what `feature_engineering` expects.

- **Categorical anomaly detection vs RRCF.** `filler_percentage` and
  `pause_percent_pr` are categorical-ish: the per-row indicator is binary
  (filler present / window silent). RRCF on a binary signal would be noise.
  Used a simple threshold rule (`filler > 0`, `pause >= 1.0`) that produces
  the same `{col: [times]}` and `{col: [[time, ...]]}` shape RRCF emits.

- **`anomaly/smoothing.py` is new.** Logically lives in `anomaly/` because
  the smoothed-then-z-scored columns are the input to RRCF; per the original
  layout in spec §6 nothing forbids extra files inside `anomaly/`.

- **End-to-end acceptance via structural tests, not a real video.** The spec
  acceptance says "produces a final master parquet without error" when run on
  a real video. I don't have one — the user does. M2 ships 14 structural
  tests (`tests/unit/test_orchestrator_pieces.py`) that exercise the merge,
  smoothing, RZ, RRCF wiring, and feature_engineering integration on
  synthetic data. The full video→parquet path is exercised manually by the
  user (and via fixture-based tests in M3+). The orchestrator CLI parses,
  imports cleanly, and every glue function has type-checked. Documented this
  limitation in the test module docstring.

- **`STAGES` constant explicitly enumerates the 9 stages from spec §7.**
  Spec §7 lists 11 stages but stages 10 ("running_agents") and 11
  ("generating_final_report") belong to the agentic layer (M4); the
  pipeline's job ends at "building_master_df". The backend (M5) will add
  agent stages onto this list. A test (`test_stages_match_spec`) locks the
  pipeline-side names so they don't drift.

- **`feature_engineering` is called twice** — once in training mode to
  produce raw transformed metrics (input to smoothing), once in evaluation
  mode to produce the final Pydantic-dict columns. This matches the legacy
  notebooks' two-pass design. Kept the existing `Optional` signature so
  evaluation-mode callers can still pass real anomaly dicts.

- **`pipeline/_logging.py` is leading-underscore-prefixed** to mark it as
  package-private. Public callers should use a regular `logging.getLogger`
  in their own modules; `configure_logging` is invoked once by the
  orchestrator CLI and once by the backend job runner.

### M2 post-tag fixes (after `m2-done` tag, before `m3-done`)

The `m2-done` tag remains at the original M2 work commit per the spec's
"do not rewrite tags" rule. These follow-up fixes were discovered during the
real end-to-end validation run against `data/uploads/Interview_2.mp4`:

- **`pipeline/audio/transcribe_whisper.py` bypasses `wp.load_audio`.** The
  original `whisper-timestamped` call shells out to `ffmpeg` on PATH, which
  isn't a moviepy or any other dependency we already require — the user can
  trivially miss it. Switched to `librosa.load(audio_path, sr=16000, mono=True)`
  + `astype(float32)` and pass the waveform directly to
  `transcribe_timestamped`. Same numerical contract whisper expects, no
  extra system dependency.

- **`pipeline/orchestrator.main()` auto-loads `.env`.** Originally the CLI
  read raw `os.environ`, so `python -m pipeline.orchestrator …` wouldn't see
  `ASSEMBLYAI_API_KEY` unless the user had pre-exported it. Added a
  best-effort `dotenv.load_dotenv()` at the top of `main()` (no-op if
  python-dotenv isn't installed). The backend will use pydantic-settings
  instead, which has its own `.env` loading, so this is CLI-only convenience.

- **Validation result.** Ran on a real 10:31 interview at 1700×956. Pipeline
  produced `data/processed/m2-validate-v2/master.parquet` (632 rows, 12 cols)
  with all Pydantic-dict columns populated and schema-correct. 34 blink
  anomalies detected, speaker labels match utterance distribution
  (533 B / 87 A / 12 None), filler detection fired on rows that genuinely
  contain `[*]` disfluencies. Saved log: `data/processed/m2-validate-v2-run.log`.

## M3 — Pipeline tests

- **Committed fixture: `tests/fixtures/tiny_master_df.parquet`** (60 rows ×
  12 cols, ~30 s of synthetic data with two engineered anomalous windows
  at `[5.0, 5.5, 6.0]` for blink and `[22.0, 22.5, 23.0, 23.5]` for
  audio). Companion `sample_anomaly_dicts.json` carries the matching
  `anomalies` / `c_anomalies` shapes. Both regenerable with
  `PYTHONPATH=. uv run python tests/fixtures/_generate_tiny_master_df.py`.

- **Coverage scope.** The spec requires coverage in `pipeline/features/`,
  `pipeline/anomaly/`, `pipeline/io/`. `pipeline/orchestrator.py`,
  `pipeline/_logging.py`, `pipeline/utils.py`, `pipeline/merge.py`,
  `pipeline/audio/*`, and `pipeline/video/*` are intentionally only
  partially covered — they wrap external services (mediapipe, librosa,
  AssemblyAI, whisper) and are exercised via the M2 real-video validation
  run + the M2 structural tests (orchestrator pieces, merge contract).
  Treating them with the same target would force broad mocking that adds
  fragility without proving anything new.

- **`feature_engineering` covered via integration test, not micro-tests.**
  Its branches are tightly coupled (250+ lines, two modes, 10+ feature
  columns, both Pydantic instantiation and dict-shaped fallback). Cleaner
  to drive the whole function with a synthetic raw dataframe + sample
  anomaly dicts and assert on the output shape than to wrap each of its
  ~30 conditional branches.

- **`compute_speaker_median_pitch` covered via monkeypatched librosa.**
  Real audio fixtures cost megabytes; the function's logic (mask voiced
  pitch across multiple speaker segments, take overall median, round to
  2 dp) is fully exercised by faking `librosa.load` / `librosa.pyin` /
  `librosa.times_like`.

- **`pipeline/features/transforms.py` is still in the mypy override
  exclusion** even though tests now cover ~99 % of it. The remaining
  type problems are about the legacy `Optional`+`dict` plumbing, not
  about the test surface; the right fix is the refactor planned during
  the agentic-layer work (M4) where the function's contract gets pinned
  down by the agent input adapter.

- **Coverage totals (committed):** `pipeline/features/` = 98.75 %,
  `pipeline/anomaly/` = 93.86 %, `pipeline/io/` = 96.67 % — all targets
  exceeded with margin. Reported via
  `uv run pytest --cov=pipeline --cov-report=term`.

- **Per-file ignore for `RUF003` in tests.** Test/fixture file comments
  use the en-dash (`–`) and multiplication sign (`×`) for readability
  (e.g. "60 rows × 12 cols"). These are runtime-irrelevant.

## M4 — Agentic layer

- **Schema rename + extension (spec §9.5).** `*AnalysisReport` →
  `*Observation` to mark them as internal scaffolding. `CrossModalInsight`
  gained `pattern_type` (Strength / Concern / Notable),
  `modalities_involved`, and split `behavioral_analysis` into
  `observation` + `interpretation`. `IntegratedBehavioralReport` has
  `overall_window_tone` instead of `overall_credibility` — five-value enum
  covering positive cases. Tests in `test_agent_schemas.py` lock the new
  contract (incl. rejection of legacy literal values).

- **Prompts rewritten (spec §9.6).** Observers explicitly marked "internal
  observer"; Pattern Detector switched to Strength/Concern/Notable framing
  with selectivity rules; Judge updated to consume the cross-modal pattern
  list and produce the four-section markdown report. Old prompts in the
  legacy notebooks weren't migrated — `agents/prompts.py` is now the
  source of truth.

- **Stub provider as the determinism backbone.** `LLM_PROVIDER=stub`
  short-circuits each agent runner with `_stub.py`'s canned outputs.
  Outputs are derived from the structured input (number of anomalous
  events, transcript snippet) so they're schema-correct AND informative
  enough that integration tests can assert real properties (pattern
  detector emits insights only when ≥2 modalities active, judge counts
  Strengths vs Concerns). Real LLM is never called by the CI suite.

- **Bounded concurrency via `asyncio.Semaphore`.** `AGENT_MAX_CONCURRENCY`
  (default 4) caps how many windows are processed in parallel. The three
  observers per window then run via `asyncio.gather` since they're
  independent. With Groq's rate limits this is the safe parallelism level
  for the production model.

- **Retries (spec §9.4).** `agents/_retry.py` provides
  `with_retries(fn, max_attempts=3, base_delay=1.0)` — exponential
  backoff. Each agent runner wraps its `_call` in it. On final failure for
  a single window, `_process_window` catches and returns `None`; the
  orchestrator skips that window from the public output. The job as a
  whole continues.

- **pydantic-ai Agent caching via `lru_cache`.** Re-building a
  `pydantic_ai.Agent` for every window would re-create the Groq client
  and re-validate the output schema; we cache by
  `(provider, model, api_key, prompt, output_type)` so all eight stages
  of one job share the right instance. `pydantic-ai`'s typed `Agent[T]`
  is generic; cast `result.output` and add `# type: ignore[return-value]`
  because the runtime is correct but mypy's generic inference loses the
  binding through the cache.

- **Empty-window drop is silent.** Per spec §9.4: if Pattern Detector
  returns empty `key_insights`, the window is removed from
  `public_reports` before the Judge sees them. The orchestrator logs at
  DEBUG; the user never sees baseline windows in the UI. The Judge still
  runs even when `public_reports == []` — the API contract is that
  `/api/jobs/{id}/report` always returns a FinalReport.

- **Real Groq end-to-end smoke test passed.** `scripts/smoke_test_groq.py`
  ran on `tests/fixtures/tiny_master_df.parquet` (60 rows, 2 engineered
  anomalous windows). The chain produced 9 Groq calls (3 observers × 2
  windows + 2 pattern detectors + 1 judge), surfaced both windows with
  `tone=Concerning` and `pattern_type=Concern`, and emitted a coherent
  four-section FinalReport. Logged in DECISIONS for traceability; not
  committed to CI because it costs tokens.

- **`_extract.py` is a separate module** (not inlined in each agent file)
  so the extraction logic is unit-testable without touching pydantic-ai
  and so the four agents share consistent input formatting.

- **PEP 695 generic syntax (`def f[T](...)`)** used in `_provider.py` and
  `_retry.py` per ruff's `UP047` — these are 3.12+ projects and the new
  syntax is clearer than `TypeVar`.

- **`agents/_settings.py` is separate from `backend/app/config.py`.**
  The backend has its own `Settings`; the agents read theirs directly
  via `pydantic-settings`. Two reasons: (1) `agents/` must be usable
  without importing the FastAPI app (tests, scripts/, the orchestrator
  CLI all consume `agents/` directly); (2) keeping them separate lets
  M5 wire the backend's `Settings` to feed the agents' env without
  introducing an import-time circular dependency.

## M5 — Backend API

- **SQLite engine is process-cached by `db_path`.** Tests swap `db_path` via
  `monkeypatch.setenv("DB_PATH", ...)` then `reset_engine_cache()`. The
  `check_same_thread=False` flag is required because FastAPI's
  BackgroundTasks runs on a different thread than the request handler.

- **Test-mode upload (`MMR_TEST_MODE=1`) accepts a pre-computed `.parquet`**
  in addition to videos. The JobRunner detects this via `Job.is_test_input`
  and skips the entire pipeline (stages 1–9), going straight to the
  agentic layer. This is what makes the API test suite deterministic and
  fast (sub-second per lifecycle). Without it, every API test would
  require a real video + mediapipe model + AssemblyAI key.

- **`load_df_parquet_safe` gained a sidecar-less fallback.** The
  authoritative `.schema.json` sidecar lists which columns are
  JSON-encoded; when it's missing (e.g. a test upload of just the
  `.parquet` bytes), every object/string column is run through a JSON
  auto-decoder. Decode errors keep the original value, so non-JSON
  columns are unaffected. Updated `test_parquet_io.py` to assert the new
  contract.

- **`/api/jobs/{id}/master_df` uses `response_model=None`** because the
  endpoint returns either `JSONResponse` (json format) or `FileResponse`
  (parquet format). FastAPI's Pydantic introspection can't reason about
  that union; explicit None disables response-model generation.

- **Progress budget: pipeline 0–78%, agents 78–95%, finalising → 100%.**
  Hardcoded factor `frac * 0.78` in the pipeline progress callback so the
  frontend's progress bar advances smoothly through all 11 stages. The
  exact split is a judgment call — pipeline dominates wall-clock time on
  real videos, but the agent chain is the visible "almost done" phase.

- **`BackgroundTasks` instead of Celery/RQ/Arq for v1.** Spec §4 mandates
  it. The `run_job_blocking` function is process-local, but `_set_stage`
  / `_set_status` use their own session scopes so the FastAPI worker
  thread can crash without leaving rows in inconsistent states. Each
  status update is a self-contained commit. When swap to Celery happens
  (M-future), `run_job_blocking` is the only function to wrap as a task.

- **CORS origins default to Vite dev (`http://localhost:5173`,
  `:5174`, `127.0.0.1:5173`).** Production deploy will need to override
  via `CORS_ORIGINS`.

- **Job log capture via `configure_logging(log_file=paths.log_file,
  force=True)`** at the top of `run_job_blocking`. The root logger gets a
  file handler pointed at the job's log path. The frontend's error mode
  uses this through `/api/jobs/{id}/logs?tail=N`.

## M6 — Frontend

- **Single-route app, three screens via React Router.** Routes: `/`,
  `/analyzing/:id`, `/report/:id`. The state machine the spec describes
  ("UI is a single state machine over the active job") maps cleanly to
  three URLs; localStorage tracks the active job id so a refresh resumes
  the same flow.

- **TanStack Query polling on AnalyzingScreen.** `refetchInterval` reads
  the cached job's status and returns `false` once it's terminal — this
  is cleaner than a setInterval+useEffect tangle. 2 second cadence per
  spec §8.1.

- **Stage labels + canonical order live in `types/api.ts`.** Keeping the
  friendly-label map and `ALL_STAGES` ordering in one place means a new
  pipeline stage only needs one edit; the checklist uses index
  comparison to decide pending/active/done.

- **`max-w-report` Tailwind extension (`768px`)** matches spec §8.4's
  "executive briefing memo" max width.

- **Inter font loaded from rsms.me** so typography matches across systems
  without bundling a font file. Falls back to system fonts.

- **No data viz library.** Spec §8.4 forbids Recharts/D3/Chart.js;
  patterns render as inline rows with pill tags. Optional timeline bar
  not implemented (spec allows omission).

- **Recent analyses dropdown is localStorage-backed only.** No API call —
  keeps Screen 1 fast and matches the "no dashboard" spirit. Hidden
  when empty.

- **Hand-written `types/api.ts` instead of openapi-generated.** Marginal
  value at this size; hand-writing forces UI authors to think about the
  exact shape the frontend consumes. Mismatches surface as build errors.

- **`vite.config.ts` proxies `/api` to localhost:8000** so dev and prod
  use the same path. `VITE_API_BASE_URL` overrides the proxy target for
  staging deploys (M8).

- **Tests use mocked `fetch`, not MSW.** MSW would be the production
  choice for a larger app; nine screen tests with hand-rolled fetch
  mocks in `tests/test-utils.tsx` give the same guarantees here with
  less setup. Each test installs its own restore() cleanup.

- **`URL.createObjectURL` / `revokeObjectURL` stubbed in `tests/setup.ts`**
  because jsdom doesn't implement them — required for the "Download as
  Markdown" test on ReportScreen.

- **React Router v7 future-flag warnings are not addressed.** Advisory,
  don't affect behavior on v6; staying on v6 stable for now.

## M7 — Docker + CI

- **Backend image is pinned to `linux/amd64`** via
  `FROM --platform=linux/amd64 …`. `mediapipe==0.10.31` (locked in
  `uv.lock`) does not publish Linux arm64 wheels; without the pin uv
  fails to resolve the dep on Apple Silicon builders. CI runners are
  amd64 natively. Apple Silicon devs pay a Rosetta-emulation cost
  (~3× slower build; runtime stays usable for `/api/health` and the
  test-mode upload path).

- **Backend uses multistage uv.** The `builder` stage runs
  `uv sync --frozen --no-dev` into `/app/.venv`; the `runtime` stage
  copies that venv on top of `python:3.12-slim` + the C libs that
  librosa (`libsndfile1`), MediaPipe / OpenCV (`libgl1`,
  `libglib2.0-0`), and numpy / scikit-learn (`libgomp1`) need. The
  `--no-dev` flag keeps test deps out of the runtime layer.

- **Frontend uses `oven/bun:1.3-debian` then `nginx:alpine`.** The
  `1.1` tag I tried first rejected our generated `bun.lock` with
  "Unknown lockfile version" — bun's lockfile format changed between
  those minor versions; the Dockerfile + CI both pin `1.3`. Final
  frontend image is ~92 MB.

- **Backend image is large.** `whisper-timestamped` pulls in `torch`
  (CPU build) + `numpy` + `mediapipe` + `opencv-python`. Slim isn't an
  option without dropping deps. Mitigations possible but deferred to
  M8 or later: (1) GPU-less torch wheel via constraint, (2) drop
  whisper-timestamped in favour of AssemblyAI-only when the user
  doesn't need word-level disfluency markers.

- **nginx in the frontend image proxies `/api/*` to the backend
  container.** This is what makes the SPA "single-origin" — same
  domain handles both. The build context for the frontend Dockerfile
  is the repo root (not `./frontend`) so it can copy both `frontend/`
  and `docker/nginx.conf` in one image.

- **`docker-compose.yml` uses a bind-mounted `./data` and read-only
  `./models`.** Persistent data lives on the host; the SQLite DB,
  uploads, and processed parquets all survive container restarts.
  The `models/face_landmarker.task` file is bind-mounted read-only so
  the container can't accidentally write to it.

- **Single CI workflow with three jobs** in `.github/workflows/ci.yml`
  (python lint+type, python tests, frontend build+test). Docker
  images build in a separate `.github/workflows/docker.yml` triggered
  only on `main` so PRs don't slow themselves with image builds.
  `concurrency: cancel-in-progress: true` avoids piling up redundant
  jobs on rapid pushes.

- **CI uses `astral-sh/setup-uv@v3`** with `enable-cache: true` so the
  uv resolver cache survives across runs. `uv sync --frozen --group
  dev` is what locks the test deps in.

- **`.dockerignore` excludes `legacy_notebooks/`** (~5 MB of `.ipynb`)
  and `data/` (potentially hundreds of MB of uploads + parquets).
  Without this, the build context balloons and every layer
  invalidates on any host-side file change.

- **`Makefile` provides `dev`, `test`, `lint`, `build`, `up`, `down`,
  `clean`, `fixture`, `smoke-groq`.** `make dev` runs uvicorn and
  vite concurrently via `&` + `trap 'kill 0' INT TERM EXIT`. Simpler
  than `concurrently` or `npm-run-all` for this size.

- **`docker compose up` verified locally end-to-end.** Backend serves
  `/api/health` directly on `:8000` AND through the nginx proxy at
  `:5173/api/health` (the single-origin production path). Confirmed
  with curl during M7 acceptance.

## M8 — Docs + Polish

- **`README.md` is fully populated.** Two-paragraph product overview,
  Docker quickstart (with MediaPipe model download step), local-dev
  quickstart via `make dev`, ASCII architecture diagram, per-directory
  module map, test commands, configuration table, known limitations,
  troubleshooting section, doc links. Replaces the placeholder
  scaffold from M1.

- **`DEPLOYMENT.md` covers two paths: VPS via `docker compose` and
  Fly.io.** Per spec §12 ("pick one of: Fly.io, Railway, generic
  VPS") I covered the VPS path as the recommended one and Fly.io as
  the secondary because Fly's free-tier shape works well for this
  app's two-container topology. Skipped Railway because its Docker
  story is identical to the VPS path with a different control plane,
  which would have padded the doc without adding value.

- **Env-var checklist in `DEPLOYMENT.md`** annotates each var with
  Required / Warning (will work but probably wrong default) / Optional.
  `CORS_ORIGINS` and `MMR_TEST_MODE` are the easiest production
  mis-configurations to make; they get Warning status.

- **Persistent volume sizing recommendation: 20 GB initially.** Based
  on ~500 MB per 10-min 1080p interview after compression + room for
  history. Documented in DEPLOYMENT.md alongside a reaper script
  example for jobs older than 30 days.

- **Definition of Done audit (spec §14) passes every item.**
  Repo layout ✓, all 9 API endpoints ✓ (verified by grep on routers),
  agentic layer callable without a notebook ✓ (`build_report` in
  `agents/orchestrator.py`), coverage targets ✓ (pipeline/features
  98.75%, pipeline/anomaly 93.86%, pipeline/io 92%, backend/app 93%),
  CI green (locally — full push validation lands when this branch
  hits CI), `docker compose up` ✓ (M7), README ✓, DEPLOYMENT.md ✓,
  DECISIONS.md ✓, notebooks preserved in `legacy_notebooks/` (10
  ipynb files), `.env.example` lists all 18 env vars, real-Groq
  smoke test passed in M4.

- **No M8 code changes.** Final `ruff check` / `ruff format --check`
  / `mypy` / `pytest` / frontend `typecheck` + `lint` + `vitest` +
  `vite build` all pass without modification — the milestones built
  cleanly on each other. The only M8 deliverables are documentation
  files.
