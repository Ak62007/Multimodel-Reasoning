# Benchmark Log — Claude Code Run

This file is co-maintained:

- The build agent scaffolds each milestone section with `<FILL IN>` placeholders.
- The user fills in token values from `/cost` (or `ccusage session`).
- Per-milestone, sum across sessions if Claude Code was restarted (see §0.3 of the spec).

- System: Claude Code
- Model: claude-opus-4-7[1m]
- Run started: 2026-06-09T13:49:45Z
- Spec: tasks/REQUIREMENTS_FOR_CLAUDE_CODE.md

---

## M1 — Refactor + scaffolding

- Completed: 2026-06-09T13:49:45Z
- Commit: f88a1879c512a4646f54366d899399dd8687ae79
- Tag: m1-done
- Session ID (if known, else "unknown"): unknown

### This-session subtotal (since last fresh Claude Code session start)

- Input: 2.3k tokens
- Output: 41.1k tokens
- Cache read: 7.0m tokens
- Cache write: 350.9k tokens
- Session subtotal: $6.75

### Run total (sum across ALL sessions in this run)

- Input: 2.3k tokens
- Output: 41.1k tokens
- Cache read: 7.0m tokens
- Cache write: 350.9k tokens
- Run total: $6.75

### Notes

- Agent: Moved `src/` → `pipeline/`, `AI/` → `agents/`. Added stub backend, frontend dir, tests scaffold. Fixed `plot_landmarks.py` invalid `from cv2 import cv` import. Consolidated `src/utils/datamodels.py` and `AI/datamodels.py` into `pipeline/schemas.py` (per-frame) and `agents/schemas.py` (agent outputs). Added ruff + mypy + pytest config. Notebooks moved to `legacy_notebooks/`. Ruff, mypy, and pytest all green.
- User: <fill if any retries / restarts / interventions occurred>

---

## M2 — Pipeline orchestrator + cleanup

- Completed: 2026-06-09T15:18:51Z
- Commit: 310b814b6ae6cc144592da6a2bbf970a225d32f7
- Tag: m2-done
- Session ID (if known, else "unknown"): unknown

### This-session subtotal (since last fresh Claude Code session start)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- Session subtotal: <FILL IN>

### Run total (sum across ALL sessions in this run)

- Input: <FILL IN>
- Output: <FILL IN>
- Cache read: <FILL IN>
- Cache write: <FILL IN>
- **Run total: <FILL IN>**

### Notes

- Agent: Renamed `audio_rms(volumn)`→`audio_rms`, `audio_pitch_var(expressiveness)`→`audio_pitch_var` (producer + consumer migrated in same commit). Replaced 12 `print()` calls with `logging`+`rich`. Added `pipeline/_logging.py`, `pipeline/anomaly/smoothing.py`, `pipeline/features/linguistic.py` (wps/filler/pause), `pipeline/merge.py`. Wired `pipeline/orchestrator.py` with 9 stages matching spec §7, `progress_cb` callback for backend, CLI entrypoint `python -m pipeline.orchestrator`. AssemblyAI ms→sec normalization moved to producer boundary. 14 new structural tests in `test_orchestrator_pieces.py` cover merge / smoothing / RZ / RRCF wiring / categorical anomaly logic. Full video→parquet acceptance run deferred — needs real interview video + API keys; documented in DECISIONS.md.
- User: <fill if any retries / restarts / interventions occurred>

---
