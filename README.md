# MMR — Multimodal Interview Analysis

Upload an interview video. MMR reads the candidate's **face, voice, and words at
once** and produces a timestamped report of the moments worth re-watching — where
those three channels line up, or quietly contradict each other.

## What it does

MMR watches a recording on three channels:

- **Face** — gaze, blinks, jaw, micro-expressions (MediaPipe)
- **Voice** — loudness, pitch, expressiveness (librosa)
- **Words** — speaking rate, fillers, pauses (AssemblyAI, with a local Whisper fallback)

It detects where those channels deviate from the candidate's baseline, then an
agent chain turns that into a report:

- a one-line headline, an overview, and a behavioral arc
- **highlights** — timestamped moments to jump back to (what happened, when, why it matters)
- **recurring threads** — patterns that show up across the interview
- coaching notes, plus a window-by-window journal

The interviewee speaker is detected automatically.

## Bring your own key (BYOK)

MMR runs on the user's own API keys, entered in the browser for each analysis:

- **Gemini** (the analysis) and **AssemblyAI** (transcription).
- Keys are validated up front, used only for that one run, and **never stored or
  logged**. See [`SECURITY.md`](SECURITY.md).
- Two modes, chosen on upload:
  - **Free key** — one combined call per moment, paced to fit free-tier rate limits.
  - **Paid key** — the full multi-agent depth (a specialist per channel + analyst).

For self-hosting, keys can instead live in `.env` and be used for every run.

## Quickstart (Docker)

```bash
git clone <repo-url> mmr && cd mmr
cp .env.example .env          # fill in keys, or leave blank for BYOK in the UI

# Download the MediaPipe face model (~3.6 MB) — required for the face stage.
mkdir -p models
curl -L \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task \
  -o models/face_landmarker.task

docker compose up --build
# Frontend: http://localhost:5173   Backend: http://localhost:8000/api/health
```

## Quickstart (local dev)

```bash
uv sync --group dev
cp .env.example .env
mkdir -p models               # download face_landmarker.task as above
cd frontend && bun install && cd ..

make dev                      # uvicorn --reload + vite, both at once
```

Open `http://localhost:5173`. The frontend reaches the backend via Vite's `/api` proxy.

## How it works

```
video ──▶ pipeline (frames, audio, transcript, features, anomaly detection)
            └─▶ master.parquet  (per-window signals at 0.5s cadence)
                  └─▶ agent chain ──▶ report (highlights, threads, journal)
```

The agent chain (paid tier) per window: **visual / audio / vocab observers →
Window Analyst**, then across the whole interview: **Pattern Weaver → Narrative
Editor**. The free tier collapses the three observers into a single Window Analyst
call to cut the request count ~4x.

LLMs run through `pydantic-ai`; the provider is derived from `LLM_MODEL`
(`google-gla:gemini-2.5-flash` for Gemini, `groq:…` for Groq, or `stub` for
deterministic, free test runs).

### Layout

| Path | Role |
| --- | --- |
| `pipeline/` | Video/audio/transcript extraction → features → anomaly detection → `master.parquet`. |
| `agents/` | The agent chain: observers, Window Analyst, Pattern Weaver, Narrative Editor (`orchestrator.py`). |
| `backend/app/` | FastAPI + SQLModel: job CRUD, BackgroundTasks runner, BYOK key validation. |
| `frontend/src/` | React + Vite SPA: Intro / Upload / Analyzing / Report screens. |
| `tests/` | pytest (unit, api, agents) + Vitest screen tests. |
| `docker/` | Backend + frontend Dockerfiles and nginx config. |

## Configuration

Settings load from `.env` (`pydantic-settings`); see `.env.example`. Most relevant:

| Var | Default | Purpose |
| --- | --- | --- |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Set to `google-gla:gemini-2.5-flash` for Gemini. Provider is inferred from the prefix. |
| `LLM_PROVIDER` | `groq` | Use `stub` to skip all LLM calls (tests, offline dev). |
| `GEMINI_API_KEY` | (unset) | Server-wide Gemini key. Leave blank for BYOK (users supply their own). |
| `ASSEMBLYAI_API_KEY` | (unset) | Transcription key. Leave blank for BYOK. |
| `LOGFIRE_TOKEN` | (unset) | Optional — sends pydantic-ai traces + token usage to Logfire. No-op when unset. |
| `AGENT_MAX_CONCURRENCY` | `4` | Windows analyzed concurrently (paid tier). |
| `MMR_TEST_MODE` | `0` | `1` allows uploading pre-computed master parquets (used by API tests). |
| `CORS_ORIGINS` | localhost | Add your production origin before deploying. |

## Tests

```bash
LLM_PROVIDER=stub MMR_TEST_MODE=1 uv run pytest -q   # ~160 tests, a few seconds
uv run ruff check . && uv run ruff format --check . && uv run mypy backend/app pipeline agents
cd frontend && bun run typecheck && bun run lint && bunx vitest run && bun run build
```

CI runs all of the above on every push (`.github/workflows/ci.yml`).

## Notes

- **HTTPS is required in production** — API keys travel in the request body. See
  [`SECURITY.md`](SECURITY.md) and [`DEPLOYMENT.md`](DEPLOYMENT.md).
- **Free-tier keys have a daily request cap.** A full interview uses many calls;
  the free mode helps, but a long video can still exhaust a free key for the day.
  MMR fails fast with a clear message when that happens.
- **Apple Silicon:** the backend image is pinned to `linux/amd64` (MediaPipe has no
  Linux arm64 wheels), so `docker build` runs via Rosetta. Runtime is fine.
- **No built-in auth.** Put an access layer in front for a shared deployment.

## Documentation

- [`SECURITY.md`](SECURITY.md) — how API keys are handled (BYOK).
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — VPS / Fly.io deployment.
- [`DECISIONS.md`](DECISIONS.md) — design decisions taken during the build.

## License

See [`LICENSE`](LICENSE).
