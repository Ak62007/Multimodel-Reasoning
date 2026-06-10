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

- Input: 1,463 tokens
- Output: 380,309 tokens
- Cache read: 39,105,093 tokens
- Cache write: 1,506,015 tokens
- Session subtotal: (cost not provided)

### Run total (sum across ALL sessions in this run)

- Input: 1,463 tokens
- Output: 380,309 tokens
- Cache read: 39,105,093 tokens
- Cache write: 1,506,015 tokens
- Run total: (cost not provided)

### Notes

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
