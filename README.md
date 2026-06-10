# MMR — Multimodal interview Reports

MMR is a multimodal behavioural analysis system for interview videos. It
extracts visual, audio, and verbal features from a recorded interview,
detects behavioural anomalies, and uses a chain of specialised LLM agents
to surface cross-modal patterns and produce an executive coaching report.

> **Status:** under active refactor towards a deployable web application.
> The spec driving this work is at `tasks/REQUIREMENTS_FOR_FACTORY.md`;
> per-milestone progress is recorded in `BENCHMARK_LOG.md` and milestones
> are tagged `m1-done` … `m8-done`. README is filled in during M8.

## Repository layout

```
backend/   FastAPI service (M5)
pipeline/  Deterministic video → master parquet pipeline
agents/    LLM-driven cross-modal interpretation (M4)
frontend/  React + Vite single-page UI (M6)
tests/     pytest suites (M3 onward)
data/      Runtime artefacts (gitignored)
models/    MediaPipe weights (gitignored)
legacy_notebooks/  Historical research notebooks (preserved, not run)
```

## Quickstart

(Filled in during M8.)
