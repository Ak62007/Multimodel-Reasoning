# MMR — Multimodal interview Reports

MMR is a multimodal behavioural analysis system for interview videos.
It runs a recorded interview through a deterministic feature-extraction
pipeline (visual landmarks via MediaPipe, audio via librosa, speech via
whisper + AssemblyAI), detects anomalous behavioural moments with a
streaming RRCF model, and then routes those moments through a chain of
specialised LLM agents that surface cross-modal patterns and produce an
executive-style coaching report.

The codebase is split into three deployable units: a deterministic
Python `pipeline/` (videos → master parquet), an LLM `agents/` layer
that interprets the parquet, and a FastAPI `backend/` that ties them
together for a single-page React `frontend/`. Everything is
reproducible: `docker compose up` brings the stack online, `make dev`
runs the same stack hot-reloading on a developer's machine, and `pytest`
covers the pipeline, agents, and backend with deterministic fixtures.

---

## Quickstart — Docker

The fastest way to a running instance. Requires Docker Desktop / Docker
Engine ≥ 20.10 with the `compose` plugin.

```bash
git clone https://github.com/<owner>/mmr.git
cd mmr

# 1. Provide the MediaPipe face-landmarker weights (~6.7 MB, gitignored).
mkdir -p models
curl -fsSL -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

# 2. Configure environment.
cp .env.example .env
# Edit .env and set GROQ_API_KEY and ASSEMBLYAI_API_KEY.

# 3. Build and start the stack.
docker compose build      # ~10 min first time (backend image is ~14 GB)
docker compose up -d

# 4. Open http://localhost:8080
```

Backend logs: `docker compose logs -f backend`. Stop: `docker compose
down`. State persists in `./data/`.

For a real deployment (TLS, backups, sizing) see
[`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Quickstart — local development

Use this when you want to edit the code with hot-reload.

```bash
# Prerequisites: Python 3.12 (pinned in .python-version), Node 20+,
# uv (https://docs.astral.sh/uv/), and ffmpeg in $PATH.

# 1. Install Python deps into a project-local venv.
uv sync --group dev

# 2. Install frontend deps.
cd frontend && npm install && cd ..

# 3. Drop in the MediaPipe model + .env (same as the Docker path above).
mkdir -p models
curl -fsSL -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
cp .env.example .env  # edit GROQ_API_KEY + ASSEMBLYAI_API_KEY

# 4. Run backend + frontend hot-reloading in one terminal.
make dev
# backend at  http://localhost:8000
# frontend at http://localhost:5173 (Vite dev server, proxies /api → :8000)
```

Other Make targets: `make backend`, `make frontend`, `make test`,
`make lint`, `make fmt`, `make mypy`, `make build`, `make clean`,
`make help`.

---

## Architecture

```
                                            ┌──────────────────────┐
   user browser ── HTTPS ──▶ Caddy (TLS) ──▶│  frontend  (nginx)   │
                                            │  React SPA + /api    │
                                            │  reverse proxy       │
                                            └──────────┬───────────┘
                                                       │ /api/*
                                                       ▼
                                            ┌──────────────────────┐
                                            │  backend (FastAPI)   │
                                            │   uvicorn :8000      │
                                            │  ┌────────────────┐  │
                                            │  │ JobRunner      │  │
                                            │  │  (BackgroundT) │  │
                                            │  └───┬────────────┘  │
                                            └──────┼───────────────┘
                                                   │
                                  ┌────────────────┼──────────────────┐
                                  ▼                                   ▼
                       ┌────────────────────┐              ┌────────────────────┐
                       │   pipeline/        │              │   agents/          │
                       │ video ─▶ frames    │              │ window slicing     │
                       │ audio ─▶ features  │ ── parquet ─▶│ visual / audio /   │
                       │ STT ─▶ utterances  │              │ vocab agents (∥)   │
                       │ RRCF ─▶ anomalies  │              │  ──▶ judge agent   │
                       │ merge ─▶ master.pq │              │  ──▶ profiler      │
                       └────────────────────┘              └────────────────────┘
                                  │                                   │
                                  ▼                                   ▼
                         ./data/processed/<job_id>/master.parquet   /agents/*.json
                                                       │
                                                       ▼
                              ./data/mmr.db (SQLite job metadata)
```

The deterministic pipeline produces a single `master.parquet` per job
on a 0.5 s grid; agents read sliced windows from it and emit
schema-validated JSON observations; the judge agent reconciles them
and the profiler agent produces the final report. All three layers
are independently testable and the agents can be swapped for a
deterministic `stub` provider via `LLM_PROVIDER=stub`.

---

## Repository layout

```
backend/         FastAPI service
  app/
    config.py        Settings (env-var-backed, pydantic-settings)
    db.py            SQLModel engine + session factory
    deps.py          FastAPI dependency wiring
    main.py          App factory + router registration + CORS
    models.py        SQLModel ORM rows (JobRecord)
    schemas.py       API request/response Pydantic models
    routers/
      health.py        GET /api/health
      jobs.py          POST/GET/DELETE /api/jobs
      reports.py       GET /api/jobs/{id}/report and friends
    services/
      job_runner.py    Background pipeline + agent orchestration
      storage.py       Upload validation + on-disk layout helpers
pipeline/        Deterministic video → master parquet
  orchestrator.py  CLI: python -m pipeline.orchestrator <video>
  video/, audio/, features/, anomaly/, merge.py, schemas.py, io/
agents/          LLM-driven cross-modal interpretation
  visual_agent.py, audio_agent.py, vocab_agent.py
  judge_agent.py, profiler_agent.py
  orchestrator.py  Fan-out per window + judge → profiler
  _runtime.py      Provider abstraction (groq + stub)
  prompts.py, schemas.py, windows.py
frontend/        React + Vite single-page UI
  src/
    api/             Typed REST client wrapping fetch()
    components/      Presentation-only React components
    screens/         Upload / Analyzing / Report screens
    lib/, types/
docker/          Dockerfiles + nginx.conf (frontend proxy)
.github/workflows/   CI (ruff/mypy/pytest/vitest) + Docker image build
tests/           pytest suites (M3+)
data/            Runtime artefacts (gitignored)
models/          MediaPipe weights (gitignored)
legacy_notebooks/  Historical research notebooks (preserved, not run)
```

---

## Configuration

All runtime config is read from environment variables. The defaults
live in `backend/app/config.py`; a starter file is in `.env.example`.

| Variable                | Default                            | Purpose                                                                                          |
|-------------------------|------------------------------------|--------------------------------------------------------------------------------------------------|
| `LLM_PROVIDER`          | `groq`                             | `groq` for production; `stub` for tests/CI (deterministic, no API calls).                        |
| `LLM_MODEL`             | `llama-3.3-70b-versatile`          | Groq model identifier.                                                                           |
| `GROQ_API_KEY`          | —                                  | Required when `LLM_PROVIDER=groq`.                                                               |
| `ASSEMBLYAI_API_KEY`    | —                                  | Required for diarised utterance transcription.                                                   |
| `AGENT_MAX_CONCURRENCY` | `4`                                | Bounded parallelism across agents within one window.                                             |
| `MAX_UPLOAD_MB`         | `500`                              | Cap on upload size; larger requests return 413.                                                  |
| `MMR_DB_URL`            | `sqlite:///./data/mmr.db`          | SQLAlchemy URL for the job-metadata DB.                                                          |
| `DATA_ROOT`             | `./data`                           | Root for runtime artefacts.                                                                      |
| `UPLOAD_DIR`            | `${DATA_ROOT}/uploads`             | Per-job raw uploads.                                                                             |
| `PROCESSED_DIR`         | `${DATA_ROOT}/processed`           | Per-job master parquet + agent outputs.                                                          |
| `MMR_TEST_MODE`         | `0`                                | `1` accepts a precomputed master parquet on POST /api/jobs and skips the pipeline. CI-only.      |
| `VITE_API_BASE_URL`     | `""` (same origin via nginx proxy) | Build-time. Set to `http://localhost:8000` for `make dev`; leave empty under bundled compose.    |

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for an operator-oriented version
of this table with "required / optional / never set in prod" labels.

---

## Tests

```bash
# Backend + pipeline + agents.
uv run pytest -q                            # 165 tests
uv run pytest -q --cov=pipeline --cov=agents --cov=backend/app

# Frontend.
cd frontend && npx vitest run               # 14 tests
```

Lint + types:

```bash
make lint
# ↳ uv run ruff check .
# ↳ uv run ruff format --check .
# ↳ uv run mypy
# ↳ cd frontend && npm run lint && npm run typecheck
```

CI runs all of the above on every push and pull request; see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml). A separate
[`.github/workflows/docker.yml`](.github/workflows/docker.yml) builds
both images on pushes to `main`.

---

## Known limitations

- **No auth.** The default deployment assumes single-tenant use (a
  team behind a VPN / private network). See `DEPLOYMENT.md` §6 for
  add-it-later notes.
- **CPU-only.** Whisper, MediaPipe, and the anomaly detector all run
  on CPU. No CUDA path is wired up; adding one means rebuilding the
  backend image from a CUDA base.
- **`linux/amd64` only.** MediaPipe wheels are published only for
  `manylinux_2_28_x86_64`. The Docker image pins this platform; arm64
  hosts build via emulation and run slower.
- **SQLite job DB.** Fine for a single-instance deployment; for
  horizontal scale, point `MMR_DB_URL` at Postgres.
- **No realtime progress stream.** The frontend polls `GET /api/jobs/
  {id}` rather than holding a websocket open. Adequate for jobs that
  take minutes, not seconds.

---

## Troubleshooting

- **`docker compose up` says `face_landmarker.task` is missing.** You
  didn't run the `curl` from the Quickstart that drops the model into
  `./models/`.
- **`uv sync` errors on `mediapipe`.** You're on a Python version
  other than 3.12 or on an arm64 host without emulation. Use the
  pinned Python (`uv python install 3.12`) and an amd64 environment.
- **`pytest` complains about `whisper` / `ffmpeg` not found.**
  Install ffmpeg system-wide (`brew install ffmpeg` on macOS,
  `apt-get install ffmpeg` on Linux). The whisper-timestamped wheel
  shells out to it.
- **Apple Silicon: backend Docker build is very slow.** Expected —
  the image is built under qemu emulation because of the MediaPipe
  wheel constraint. Cache hits make subsequent builds fast; for a
  one-off run, `docker compose up` runs fine under Rosetta.
- **`uv sync --frozen` fails after editing `pyproject.toml`.** Run
  `uv lock` to regenerate `uv.lock`, then re-`sync`.
- **Frontend dev server shows CORS errors against the backend.**
  Make sure `VITE_API_BASE_URL=http://localhost:8000` in your dev
  shell (or in `frontend/.env.local`). The backend's CORS allow-list
  already covers `localhost:5173`.
- **Upload through port 8080 fails with a 413 well below 500 MB.**
  You're on an old build of the frontend image. Rebuild it
  (`docker compose build frontend && docker compose up -d frontend`)
  — the bundled `docker/nginx.conf` sets `client_max_body_size 600M`
  to match the backend `MAX_UPLOAD_MB=500` default. If you raised
  `MAX_UPLOAD_MB` above 600, raise `client_max_body_size` in
  `docker/nginx.conf` to match and rebuild the frontend image.

---

## Further docs

- [`DEPLOYMENT.md`](DEPLOYMENT.md) — full deployment walkthrough (VPS
  + Caddy + Fly.io notes).
- [`DECISIONS.md`](DECISIONS.md) — every non-trivial decision taken
  during the build, with rationale, per-milestone.
- [`BENCHMARK_LOG.md`](BENCHMARK_LOG.md) — token usage + outcomes for
  each milestone of the build run.

## License

See [`LICENSE`](LICENSE).
