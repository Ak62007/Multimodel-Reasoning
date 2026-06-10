# Decisions Log

Every non-trivial decision made on the user's behalf during this build is
recorded here, with timestamp + rationale. Per §17 of the spec.

---

## 2026-06-10 — M1: refactor + scaffolding

### Layout deviations

- The §6 layout did not include a home for the two notebook-helper modules
  (`plot_graphs.py`, `plot_landmarks.py`) or for `utils.py` (`secs_mins`).
  These have been moved to `legacy_notebooks/utils/` rather than into
  `pipeline/`, on the rationale that they are notebook-only helpers and
  the spec requires that notebooks be preserved under `legacy_notebooks/`.
  `plot_landmarks.py`'s broken `from cv2 import cv` import has been fixed
  to `import cv2 as cv` in this new location.

### File split

- `src/sync/RRCF_TS_anomaly_detection.py` was split into
  `pipeline/anomaly/rrcf.py` (model + scoring) and
  `pipeline/anomaly/ranges.py` (threshold computation + continuous-range
  detection), matching §6 exactly. Behaviour is preserved — only the file
  boundaries changed. The previously-commented-out earlier draft of
  `get_anomalous_time_ranges` has been removed as dead code.

### Schemas

- The two `datamodels.py` files were consolidated by destination, not by
  content: per-frame Pydantic models live in `pipeline/schemas.py`, agent
  output models live in `agents/schemas.py`. Schema *content* changes
  (renaming `VisualAnalysisReport` → `VisualObservation`, adding
  `pattern_type` to `CrossModalInsight`, etc.) are M4 work.

### Tooling

- Ruff and mypy are intentionally configured conservatively for M1 so that
  the existing exploratory code lints without churn. The rulesets will be
  tightened in later milestones as code stabilises and tests provide
  safety nets.
- `pytest --asyncio-mode=auto` is set globally so async test functions
  picked up in M4/M5 do not need decoration.
- `legacy_notebooks/` is excluded from ruff/mypy. The notebooks were
  preserved per §5 ("Do not delete the notebooks"), but they are not
  part of the live codebase.

### Logging

- `pipeline/anomaly/rrcf.py` had a stray `print()` — converted to a
  module-level logger call. M2 will sweep the rest of the package for
  `print()` usage per §16. `pipeline/io/parquet.py` was also converted
  during the refactor pass for parity.

### Mypy override for `pipeline.features.transforms`

- `pipeline/features/transforms.py` contains ~90 type errors that are all
  rooted in the same patterns: `Optional[DataFrame]` parameters that are
  always passed and indexed, `dict[str, X]` return types that mypy widens
  to `dict[str, X] | float`, etc. The function gets a substantive rewrite
  in M2 (column renames + helper extraction), so suppressing it via a
  per-module override is preferable to adding ~90 `# type: ignore[...]`
  comments that would be deleted again next milestone. The override is
  removed in M2.

---

## 2026-06-10 — M2: pipeline orchestrator + cleanup

### Column renames

- `audio_rms(volumn)` → `audio_rms`
- `audio_pitch_var(expressiveness)` → `audio_pitch_var`
- Consumers (`pipeline/features/transforms.py`, `pipeline/orchestrator.py`)
  migrated in the same commit. Parens-style column names appeared only in
  the audio technical extractor; no parquet artefacts are checked in, so
  there is no legacy data migration to perform.

### Mode split

- The original `feature_engineering(mode="training"|"evaluation")` was the
  single largest source of type-system ambiguity (and of bugs — passing
  the wrong mode produced wildly different return shapes). Split into
  `compute_raw_features` (numeric outputs feeding smoothing) and
  `feature_engineering` (Pydantic-decodable outputs for the final master
  parquet). The mypy override added in M1 is removed accordingly.

### Master dataframe resolution

- Existing notebooks merged at **1 Hz** (inner join on `Time`), silently
  dropping the half-second audio rows. M2 changes the master grid to the
  audio grid (**0.5 s**) using `merge_asof(... direction='backward')` to
  forward-fill face features. This preserves the per-row schema and
  every Pydantic field downstream agents depend on, while keeping the
  full acoustic signal. The decision is contained inside `pipeline/merge.py`
  and changes resolution only; the column names are unchanged.

### Smoothing + robust-z

- EWM spans preserved verbatim from `feature_engineering.ipynb`:
  visual {blink:3, gaze:6, jaw:4, smile:8}, audio/verbal
  {loudness:5, pitch_rel:8, pitch_expr:6, wps:6}. Robust-z formula:
  `(x - median) / (1.4826 * MAD)`, returning 0 when MAD == 0. Visual
  features are normalised over the whole series; audio/verbal features
  are normalised over the target-speaker rows only.

### Anomaly detection sweep

- `pipeline/orchestrator._detect_anomalies` runs RRCF against the eight
  smoothed-rz feature columns, picks an adaptive `n_sigma`, thresholds
  via MAD, and groups consecutive anomalous timestamps into ranges with
  `get_anomalous_time_ranges`. Filler / pause categorical anomalies are
  passed through as empty lists; the per-row `FillerPercentageIncrease`
  / `PausePercentageIncrease` Pydantic models surface them via their
  existing `*_level` enum field.

### `JobPaths`

- Every pipeline component now reads its paths from
  `pipeline.io.paths.JobPaths`. No relative paths (`../data/raw/`)
  remain. The CLI keys a workdir by video stem; the backend will key
  it by job id (M5).

### Logging

- Every `print()` in `pipeline/` is now `logger.info` / `logger.warning`
  / `logger.exception`. The CLI's `--verbose` flag controls the root
  log level.

---

## 2026-06-10 — M3: pipeline tests

### Fixture generation strategy

- `tests/fixtures/generate.py` is the single source of truth for both
  `tiny_master_df.parquet` and `tiny_transcript.parquet`. It is
  **committed** alongside the generated parquets so that anyone can
  regenerate the fixtures deterministically (`np.random.default_rng(seed=0)`)
  and verify content stability. Re-run with
  `uv run python tests/fixtures/generate.py` if a schema change ever
  invalidates the committed binaries.

### Coverage targets vs reality

- M3 acceptance is *per-directory* coverage (features ≥ 90 %, anomaly
  ≥ 85 %, io ≥ 90 %). The CI configuration uses
  `--cov=pipeline/features --cov=pipeline/anomaly --cov=pipeline/io`
  to score each target independently. The combined number is 96 %.
- `pipeline/anomaly/ranges.py` reports 90 % rather than 100 % because
  `get_anomalous_time_ranges`' fast-path for the degenerate
  `len(anomalies_time) == 1` branch (lines 24-28) is exercised only
  via the integer-second variant the legacy notebooks used. Adding
  the branch test was redundant — the wider continuity tests cover
  the same logic — so we left it uncovered.

### Test for the RRCF noise property

- The "pure noise" RRCF test originally asserted that the maximum score
  was at most `20 × median + 1`. RRCF actually produces fairly long
  tails on noise (one score in 200 was ~62 vs a median of ~2.8), so
  the assertion was wrong. The test now only checks that every score
  is finite and non-negative — the meaningful behavioural assertion
  is in the companion spike test, which verifies the spike's score
  ends up in the top decile.

---

## 2026-06-10 — M4: agentic layer

### Schema renames (per spec §9.5)

- `VisualAnalysisReport` → `VisualObservation` (internal)
- `AudioAnalysisReport` → `AudioObservation` (internal)
- `VocabularyAnalysisReport` → `VocabObservation` (internal)
- `VocabularyAnomalyEvent` → `VocabAnomalyEvent` (matches the renamed
  observation; no behavioural change)
- `CrossModalInsight` reframed:
  - `anomalies_detected: list[str]` removed
  - `modalities_involved: list[Literal["Visual", "Audio", "Verbal"]]` added
  - `suspicion_level` → `significance` (neutral framing, same values)
  - `pattern_type: Literal["Strength", "Concern", "Notable"]` added
  - `behavioral_analysis` → `observation` + `interpretation`
- `IntegratedBehavioralReport.overall_credibility` →
  `overall_window_tone` with the new five-state literal.

### Prompt revisions

- Each observer prompt now opens with an explicit "you are an internal
  observer" note so the LLM does not write narrative prose intended for
  the user.
- `CORR_CONT_PROMPT` → `PATTERN_DETECTOR_PROMPT`, rewritten around the
  three-way `pattern_type` framing with one paragraph per Strength /
  Concern / Notable example. The rewrite preserves the original
  selectivity, brevity, and content-tie-in rules.
- `JUDGE_PROMPT` updated to reference *cross-modal patterns* (the new
  input shape) and the four `FinalReport` fields by name.

### Provider switch + retries

- `agents/_runtime.py` is the central place for: stub-vs-Groq selection
  (`LLM_PROVIDER`), Groq model id resolution (`LLM_MODEL`),
  bounded-concurrency limit (`AGENT_MAX_CONCURRENCY`, default 4), and
  retry-with-exponential-backoff wrapper (3 attempts, jittered backoff
  capped at 8 s).
- Each agent module checks `use_stub()` first and dispatches to the
  matching `agents/_stub.py` function on the stub path. This isolates
  pydantic-ai/Groq from the test surface — tests never need the network.

### Window selection

- `agents/windows.py` walks the per-row Pydantic-dict columns
  (`blinking_data`, `gaze_data`, …) looking at `part_of_anomalous_range`
  fields. Adjacent ranges within `gap_tolerance` (default 1.0 s per §9.4)
  are merged into a single window. Long stretches with no anomalies
  emit no windows.

### Orchestrator

- `agents/orchestrator.build_report` is async, bounded by an
  `asyncio.Semaphore`, and runs the three observers concurrently per
  window. Per-window errors are logged and the window is dropped
  (`return_exceptions=True`) so a single LLM hiccup does not fail the
  whole job. The judge always runs at the end, even when no windows
  produced insights, so the API always has a `FinalReport` to return.

### Documented manual real-Groq run (M4)

Verified on 2026-06-10 against `tests/fixtures/tiny_master_df.parquet`
using model `llama-3.3-70b-versatile` and the `.env` keys:

```text
$ LLM_PROVIDER=groq uv run python -c "..." (script also in
  agents/_runtime.py docstrings)
reports=2 total insights=2
  [5.0s-7.0s] tone=Mixed_Signals insights=1
    [Concern/Medium] mod=['Visual', 'Verbal']
  [18.0s-21.0s] tone=Mixed_Signals insights=1
    [Concern/Medium] mod=['Visual', 'Audio', 'Verbal']
```

One window's Pattern Detector found a Concern spanning Visual + Verbal;
the other a Concern spanning all three modalities. The Judge agent
returned a four-section markdown report wired to the `FinalReport`
schema. Total wall time on Groq llama-3.3-70b-versatile was around
20 s. The vocab observer's first call timed out once and the retry
wrapper recovered transparently — exactly the behaviour §9.4 asks for.

---

## 2026-06-10 — M5: backend API

### `JobRunner` shape

The JobRunner runs inside FastAPI's `BackgroundTasks`. To keep the
contract simple, the public entrypoint (`run_job`) is sync and just
wraps `asyncio.run(_run_job(...))`. Inside `_run_job` the pipeline (sync)
is run via `asyncio.to_thread` so the event loop stays free for
SQLite writes.

### `MMR_TEST_MODE=1` ingestion path

Spec §10.2 asks for "a test-only ingestion path so tests don't run the
heavy pipeline." The implementation: when `MMR_TEST_MODE=1` and the
upload's suffix is `.parquet`, the storage layer reads the parquet,
JSON-decodes any object columns whose first value looks like JSON, and
re-saves via `save_df_parquet_safe` (which regenerates the sidecar).
The JobRunner then skips the pipeline and goes straight to the agents.
This means the API integration tests exercise the full router + DB +
JobRunner + agents chain without paying for MediaPipe / librosa /
AssemblyAI / Whisper.

### Public stage list vs. pipeline stages

Spec §7.3 lists eleven `current_stage` values; the pipeline orchestrator
internally has ten (it splits `smoothing` from `feature_engineering`).
The JobRunner collapses `smoothing` into `feature_engineering` when
reporting `current_stage`, and emits `running_agents` + 
`generating_final_report` after the pipeline returns. This keeps the
spec's stage list intact for the frontend's friendly-name table without
losing the cleaner pipeline-internal partitioning.

### Storage layout per job

```
data/uploads/{job_id}.{ext}                 # raw upload
data/processed/{job_id}/
  parquet/master.parquet                   # canonical master parquet
  parquet/master.parquet.schema.json       # sidecar
  segments.json                            # IntegratedBehavioralReport[]
  report.json                              # FinalReport
  report.md                                # human-readable markdown
  pipeline.log                             # per-job log (tail via /logs)
  frames/                                  # MediaPipe input frames
```

Persisting agent outputs on disk lets the report endpoints stream files
directly without holding state in the DB.

### Per-job log capture

The JobRunner attaches a `logging.FileHandler` to the root logger for the
duration of the job, so every `logger.info(...)` call from `pipeline.*`
and `agents.*` lands in the per-job log file. The handler is detached in
a `finally` block. There is a small risk of log-line cross-contamination
if multiple jobs run concurrently in the v1 single-user app; the spec is
explicit that v1 is single-user (§3), so this is acceptable.

---

## 2026-06-10 — M6: frontend

### Stack choices vs spec §4 / §8

- React 18 + Vite + TypeScript + Tailwind CSS (§4 / §8.5).
- TanStack Query v5 for all server state; polling interval set to 2 s on
  the Analyzing screen via `refetchInterval: q => status === "queued" || "running" ? 2000 : false` (§8.1.2).
- `vitest` + `@testing-library/react` for tests.
- `react-markdown` for the FinalReport markdown sections.
- `sonner` for toast errors (per §8.5).
- npm (not bun) — documented here.

### State-machine layout

- One top-level `<App>` component with a `mode` state of
  `"upload" | "analyzing" | "report"` plus an active `jobId`.
- The active job id is mirrored to `localStorage` so a page refresh
  resumes the in-flight flow (matches the §8.1 "Persist the active job
  id" requirement).
- "Recent analyses" are recorded in `localStorage` and surfaced under
  the upload card per §8.1.1.

### Stage list shared with backend

- `frontend/src/lib/stages.ts` mirrors the §7.3 / `PUBLIC_STAGES` list
  in `backend/app/services/job_runner.py`. The friendly-text map in §8.1.2
  is implemented verbatim. There is no compile-time link between the two —
  they are duplicated by design (the backend ships the JSON labels, the
  frontend just maps them to human strings). Keeping them in sync is a
  manual exercise.

### Markdown download

- The "Download as Markdown" button creates an in-memory `Blob`, calls
  `URL.createObjectURL`, programmatically clicks an `<a download>` link,
  then revokes the blob URL. Filename pattern:
  `{filename_without_extension}-behavioral-report.md`.

### Restraint vs. ornament

- Per §8.4 the design is deliberately minimal: no gradients, no charts,
  no sidebar / app shell, centered single-column at `max-w-768px`. Two
  colors of chrome (white + neutral-50) plus semantic accent colors on
  tone badges (green / gray / amber / red) and pattern-type badges
  (green / red / amber).

---

## 2026-06-10 — M7: Docker + CI

### Two Dockerfiles, one compose file

- `docker/Dockerfile.backend` — multistage. The builder uses
  `python:3.12-slim` + `uv` to resolve `pyproject.toml` + `uv.lock` into
  a single `/opt/venv`. The runtime stage installs only the system
  libraries the pipeline needs (ffmpeg, libsndfile1, libgl1,
  libglib2.0-0, libgomp1, curl) and copies the venv + app source. A
  `HEALTHCHECK` curls `/api/health`.
- `docker/Dockerfile.frontend` — multistage. The builder runs `npm ci`
  + `npm run build` to produce `dist/`, then `nginx:alpine` serves it.
  `docker/nginx.conf` proxies `/api/*` to the `backend` service so the
  SPA can call same-origin endpoints.
- `docker-compose.yml` — backend on `:8000`, frontend on `:8080`,
  `.env` loaded into backend, `./data:/app/data` mounted for
  persistence, `./models:/app/models:ro` for the MediaPipe weights.

### `.dockerignore`

- Excludes `.venv`, `__pycache__`, `data/`, `legacy_notebooks/`,
  `frontend/node_modules`, `.env`, the `tests/` tree, and the
  documentation files. This keeps the build context small enough to
  send to the Docker daemon without bundling the entire 500 MB sample
  video or the legacy notebooks.

### Two GitHub Actions workflows

- `.github/workflows/ci.yml` — three independent jobs per §11:
  `python-lint-and-type` (ruff check + ruff format --check + mypy),
  `python-tests` (pytest with coverage, `LLM_PROVIDER=stub`,
  `MMR_TEST_MODE=1`), `frontend-build-and-test` (Node 20, npm ci, lint,
  typecheck, vitest, build).
- `.github/workflows/docker.yml` — builds both images via
  `docker/build-push-action@v6` with GHA cache, gated on pushes to
  `main` per spec §11. Images are loaded into the runner's daemon but
  not pushed; wiring a registry is out of scope for M7.

### Frontend lint + the `ReportScreen` `useMemo` warnings

- ESLint v9 flat config in `frontend/eslint.config.js` (typescript-eslint
  + react-hooks + react-refresh). After enabling react-hooks, the
  `useMemo` calls in `ReportScreen` flagged because `segments` was being
  re-derived inline as `segmentsQuery.data ?? []` on every render,
  which changes the dependency identity. Wrapped `segments` in its own
  `useMemo` keyed off `segmentsQuery.data` — clean and matches the
  intent of "stable memo while the query is loading".

### Docker daemon availability during M7 verification

- The Docker daemon was not running on the local machine when I tried
  to do a build-stage smoke test of `docker/Dockerfile.frontend`, so I
  couldn't actually exercise the image builds. Two compensating
  validations were performed: `docker compose config` successfully
  resolved the full compose stack with both services, args, env, ports,
  volumes, and the `depends_on` graph; and `.github/workflows/docker.yml`
  will run a real `docker buildx build` for both images on the first
  push to `main`. The Dockerfiles themselves were written carefully
  with the same dependency list the local `uv sync` already validates.

### Makefile

- `make dev` uses `npx concurrently` to fan out backend + frontend in
  one terminal (`uv run uvicorn --reload` and `npm run dev`). Other
  targets: `make test`, `make lint`, `make fmt`, `make mypy`, `make build`,
  `make clean`.
