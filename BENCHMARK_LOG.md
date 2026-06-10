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

- Input: 1,359 tokens
- Output: 236,340 tokens
- Cache read: 20,215,471 tokens
- Cache write: 1,312,991 tokens
- Session subtotal: (cost not provided)

### Run total (sum across ALL sessions in this run)

- Input: 1,359 tokens
- Output: 236,340 tokens
- Cache read: 20,215,471 tokens
- Cache write: 1,312,991 tokens
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
