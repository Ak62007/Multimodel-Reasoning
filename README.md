# MMR — Multimodal Interview Behavioral Analysis

> **Status:** Brownfield refactor in progress. Milestones M1–M8 tracked in
> `BENCHMARK_LOG.md`. See `tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md` for the
> full build brief.

MMR ingests an interview recording and produces a per-segment cross-modal
behavioral report plus a final executive coaching report. It combines:

- Visual features (face landmarks, blendshapes, gaze) — MediaPipe
- Vocal features (loudness, pitch, expressiveness) — librosa
- Verbal fluency features (speaking rate, fillers, pauses) — AssemblyAI +
  whisper-timestamped
- Anomaly detection per feature — RRCF with adaptive MAD thresholding
- Agentic interpretation — `pydantic-ai` + Groq

## Quickstart

```bash
# 1. Clone & install Python deps
uv sync

# 2. Configure secrets
cp .env.example .env
# fill in GROQ_API_KEY and ASSEMBLYAI_API_KEY

# 3. (M5+) Run the backend
uvicorn backend.app.main:app --reload

# 4. (M6+) Run the frontend
cd frontend && bun install && bun run dev
```

Full Docker quickstart and architecture diagram land in M8.

## Repository layout

```
pipeline/   — pure data pipeline (video, audio, features, anomaly, IO, schemas)
agents/     — agentic interpretation layer (observers + pattern detector + judge)
backend/    — FastAPI service that orchestrates jobs
frontend/   — React + Vite + TS app (three screens: upload, analyzing, report)
tests/      — pytest suite (unit, api, agents)
docker/     — Dockerfiles
.github/    — CI workflows
legacy_notebooks/ — original exploration notebooks (reference only)
```

## Tests

```bash
uv run pytest
uv run ruff check .
uv run mypy backend/app pipeline agents
```

## Documentation

- `DECISIONS.md` — log of decisions made during the build.
- `BENCHMARK_LOG.md` — token-usage telemetry per milestone.
- `tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md` — the full build brief.
- `DEPLOYMENT.md` — production deployment guide (lands in M8).
