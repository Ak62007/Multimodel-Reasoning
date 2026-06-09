# MMR — Multimodal Interview Behavioral Analysis

> Ingest an interview video → produce a per-window cross-modal behavioral report
> + a final executive coaching report.

MMR is a multimodal pipeline that watches an interview recording on three
channels at once — **what the candidate looks like**, **how they sound**, and
**what they say** — and surfaces the moments where those three channels stop
agreeing. The output is two reports: a list of cross-modal pattern segments
(each a coachable moment with a timestamp, a quote, and a Strength / Concern /
Notable label) and a four-section markdown coaching report.

Under the hood it stacks:

- **Visual features** — face landmarks, blendshapes, and gaze (MediaPipe)
- **Vocal features** — loudness, pitch, expressiveness (librosa)
- **Verbal fluency** — speaking rate, fillers, pauses (AssemblyAI + whisper-timestamped)
- **Anomaly detection** — robust z-score + RRCF with adaptive MAD thresholding
- **Agent chain** — `pydantic-ai` with Groq's `llama-3.3-70b-versatile`
  driving five agents (three internal observers + Pattern Detector + Judge).
  A `stub` provider gives deterministic, free outputs for tests and offline dev.

The intended user is an interview coach, recruiter, or behavioral analyst.

---

## Quickstart (Docker — recommended)

```bash
# 1. Clone
git clone <repo-url> mmr && cd mmr

# 2. Configure secrets
cp .env.example .env
# Open .env and fill in:
#   GROQ_API_KEY=...           (from console.groq.com)
#   ASSEMBLYAI_API_KEY=...     (from assemblyai.com)
# Defaults are fine for everything else.

# 3. Download the MediaPipe face landmarker model (~3.6 MB).
#    Without this, the pipeline will fail at the face-features stage.
mkdir -p models
curl -L \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task \
  -o models/face_landmarker.task

# 4. Boot the whole stack
docker compose up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000/api/health
```

Upload an `.mp4` / `.mov` / `.avi` / `.webm` in the browser, watch the stage
checklist tick through, read the report.

> Apple Silicon: backend image is pinned to `linux/amd64` because MediaPipe
> doesn't ship Linux arm64 wheels. Builds via Rosetta (slower); runtime is
> fine. See `DECISIONS.md` for details.

## Quickstart (local dev — no Docker)

```bash
# Python
uv sync --group dev
cp .env.example .env       # then fill in keys
mkdir -p models             # then download face_landmarker.task as above

# Frontend
cd frontend && bun install && cd ..

# Run both concurrently (uvicorn --reload + vite dev)
make dev
```

The frontend talks to the backend on `localhost:8000` via Vite's `/api`
proxy. Open `http://localhost:5173/`.

---

## Architecture

```
┌────────────────────────┐
│  React + Vite SPA      │  three screens: Upload / Analyzing / Report
│  (frontend/)           │  TanStack Query polling, no data viz library
└─────────────┬──────────┘
              │ /api/* (nginx proxy in prod)
              ▼
┌────────────────────────┐
│  FastAPI + SQLModel    │  Job CRUD, BackgroundTasks queue, log capture
│  (backend/app/)        │  SQLite at data/mmr.db
└──┬──────────────────┬──┘
   │                  │
   │ pipeline/         │ agents/
   │  9 stages         │  build_report()
   ▼                  ▼
┌────────────┐  ┌────────────┐
│ pipeline/  │  │ agents/    │  visual / audio / vocab observers
│ frames →   │  │ orchestr.  │  → Pattern Detector → IntegratedBehavioralReport
│ master_df  │  │ async fan- │  → Judge → FinalReport
│ parquet    │  │ out 4×     │
└────────────┘  └────────────┘
   │                  ▲
   │ MediaPipe        │ pydantic-ai → Groq (or stub)
   │ librosa
   │ AssemblyAI
   │ whisper-timestamped (via librosa, no system ffmpeg required)
   ▼
master.parquet (per-window Pydantic-dict columns)
```

### What's in each directory

| Path                            | Role |
| ------------------------------- | ---- |
| `pipeline/`                     | Pure data pipeline. Eleven stages: extract → merge → smooth + RZ → RRCF → build master parquet. |
| `pipeline/orchestrator.py`      | `run_pipeline(video_path, config, progress_cb)`. CLI entrypoint `python -m pipeline.orchestrator`. |
| `pipeline/{video,audio}/`       | Frame extraction, audio extraction, librosa features, AssemblyAI + whisper-timestamped transcription. |
| `pipeline/features/transforms.py` | Visual blendshape → intensity / magnitude transforms; `feature_engineering(...)` produces the Pydantic-dict per-row columns. |
| `pipeline/anomaly/`             | RRCF + MAD threshold + continuous-range grouping + EWM smoothing + robust z-score. |
| `pipeline/merge.py`             | Aligns the four streams (face, audio-tech, whisper words, utterances) on the 0.5 s grid. |
| `pipeline/schemas.py`           | Pydantic per-frame containers (Blink, Gaze, ..., WPS). |
| `pipeline/io/parquet.py`        | `save_df_parquet_safe` + `load_df_parquet_safe` (preserves object cols + sidecar-less fallback). |
| `agents/`                       | Agent chain layer.  |
| `agents/orchestrator.py`        | `build_report(master_df, …)`. Async, semaphore-bounded. |
| `agents/windows.py`             | Group anomalous ranges into analysis windows (1 s gap merging). |
| `agents/prompts.py`             | The five system prompts (rewritten in M4 for Strength/Concern/Notable framing). |
| `agents/_stub.py`               | Deterministic stub provider used when `LLM_PROVIDER=stub`. |
| `agents/_provider.py`           | pydantic-ai `Agent` factory bound to Groq. |
| `backend/app/main.py`           | FastAPI app factory + CORS. |
| `backend/app/routers/`          | `/api/health`, `/api/jobs`, `/api/jobs/{id}/…`. |
| `backend/app/services/job_runner.py` | Pipeline + agent chain glue; sets `current_stage` and `progress` on the Job row as it goes. |
| `backend/app/models.py`         | SQLModel `Job` table. |
| `frontend/src/screens/`         | `UploadScreen`, `AnalyzingScreen`, `ReportScreen`. |
| `frontend/src/components/`      | `StageChecklist`, `CrossModalSegment`, `PatternRow`, `ToneBadge`, etc. |
| `frontend/src/types/api.ts`     | Hand-written TS types matching the backend Pydantic models. |
| `tests/{unit,api,agents}/`      | pytest suite. |
| `tests/fixtures/tiny_master_df.parquet` | 60-row synthetic master frame with two engineered anomalous windows; powers backend + agent integration tests. |
| `frontend/tests/`               | Vitest screen tests with mocked `fetch`. |
| `docker/`                       | `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf`. |
| `legacy_notebooks/`             | Original exploration; reference only. |
| `tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md` | The original build brief. |
| `DECISIONS.md`                  | Per-milestone log of decisions taken. |
| `BENCHMARK_LOG.md`              | Per-milestone token-usage telemetry. |

---

## Tests

```bash
# Python — all 138 tests, takes ~3 s
uv run pytest -q

# Coverage report
uv run pytest --cov=pipeline --cov=agents --cov=backend/app --cov-report=term

# Lint + type
uv run ruff check .
uv run ruff format --check .
uv run mypy backend/app pipeline agents

# Frontend
cd frontend && bun run test --run && bun run typecheck && bun run build
```

All three CI jobs run on every push (`.github/workflows/ci.yml`). Docker
images build on pushes to `main` (`.github/workflows/docker.yml`).

### Manual smoke tests

| Script | What it does |
| --- | --- |
| `make smoke-groq` | Runs the agent chain against real Groq on the tiny committed fixture (~9 LLM calls; costs ~$0.01). |
| `python -m pipeline.orchestrator <video.mp4>` | Runs the full pipeline on a real video and writes `data/processed/{job-id}/master.parquet`. |

---

## Configuration

All settings load from `.env` via `pydantic-settings`. See `.env.example`
for the full list; the most important:

| Var | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `groq` | Set to `stub` to skip all LLM calls (tests, offline dev). |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Any Groq-served model. |
| `GROQ_API_KEY` | (unset) | Required when `LLM_PROVIDER=groq`. |
| `ASSEMBLYAI_API_KEY` | (unset) | Required for transcription. |
| `AGENT_MAX_CONCURRENCY` | `4` | How many analysis windows process concurrently. |
| `FACE_LANDMARKER_PATH` | `models/face_landmarker.task` | MediaPipe model weights. |
| `WHISPER_MODEL_SIZE` | `small` | Trades speed for accuracy. `tiny`, `small`, `medium`, `large`. |
| `WHISPER_DEVICE` | `cpu` | Use `cuda` if you have a GPU and a CUDA-built torch. |
| `MMR_TEST_MODE` | `0` | Set to `1` to allow uploading pre-computed master parquets (used by API tests). |
| `MAX_UPLOAD_MB` | `500` | Upload size cap. |
| `CORS_ORIGINS` | `["http://localhost:5173", …]` | Add your production origin here. |

---

## Known limitations

- **Backend image is large (~3-5 GB squashed).** Driven mostly by `torch`
  (CPU build) inside `whisper-timestamped`, plus MediaPipe. Mitigations
  (CPU-only torch constraint, drop whisper) are documented in
  `DECISIONS.md` under M7 and deferred.
- **Apple Silicon dev needs Rosetta for `docker compose build`.**
  MediaPipe 0.10.31 doesn't ship Linux arm64 wheels. Backend Dockerfile
  pins `--platform=linux/amd64`.
- **Whisper "small" on CPU is the slowest pipeline stage** (~30-50% of
  total wall time on a 10-minute interview). Use `WHISPER_MODEL_SIZE=tiny`
  for faster iteration or move to GPU.
- **Single-process BackgroundTasks executor.** Spec §4 allows this for v1;
  swap to Celery / RQ / Arq via the same `run_job_blocking(job_id, settings)`
  entrypoint when you need horizontal scaling.
- **No authentication.** This is a single-user behavioral analysis tool;
  multi-user deployments should add an auth layer in front (oauth-proxy,
  Cloudflare Access, …).
- **The pipeline emits a "baseline" FinalReport even when no patterns are
  found.** The API contract guarantees the report endpoint always returns
  something; the frontend renders a "no notable patterns detected"
  placeholder for the Cross-Modal Patterns section.

---

## Troubleshooting

**`uv sync` fails on `mediapipe`** — MediaPipe pins Python and platform
narrowly. If you're on Linux arm64 (Raspberry Pi, …) it has no wheel; the
docker image is the recommended path. On macOS arm64 / Linux amd64 / macOS
x86 it works.

**`whisper.load_audio` complains about `ffmpeg`** — fixed in M2; we load
via librosa now. If you still see it, you're on a stale checkout — rebase
on `m2-done` or later.

**Backend container takes minutes to boot on Apple Silicon** — Rosetta
emulation for the amd64 image. The runtime itself is fine; subsequent
restarts are fast because Docker caches the unpacked image.

**`/api/jobs` returns 422 on parquet uploads** — production mode doesn't
accept `.parquet`; only enabled when `MMR_TEST_MODE=1`. Upload an actual
video file.

**No face detected in any frame** — `pipeline/video/face_features.py` logs
per-frame at DEBUG level. Make sure the candidate's face is visible at 1
frame per second (default `FPS=1` sample rate) and that
`FACE_LANDMARKER_PATH` points at the real `face_landmarker.task` file (not
a zero-byte placeholder).

**GitHub Actions "frozen lockfile" error on `uv sync`** — regenerate
`uv.lock` locally with `uv lock` and commit the result.

---

## Documentation

- [`DECISIONS.md`](DECISIONS.md) — per-milestone log of decisions taken
  during the build. Read this before changing something non-obvious.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Fly.io / Railway / generic VPS
  deployment guide.
- [`BENCHMARK_LOG.md`](BENCHMARK_LOG.md) — token-usage telemetry per
  milestone. Co-maintained by the build agent + the user.
- [`tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md`](tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md) — the original
  build brief.

## License

See `LICENSE`.
