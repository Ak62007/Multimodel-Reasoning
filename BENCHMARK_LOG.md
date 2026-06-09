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

- Input: 7.4k tokens
- Output: 149.2k tokens
- Cache read: 30.1m tokens
- Cache write: 702.8k tokens
- Session subtotal: $22.37

### Run total (sum across ALL sessions in this run)

- Input: 7.4k tokens
- Output: 149.2k tokens
- Cache read: 30.1m tokens
- Cache write: 702.8k tokens
- Run total: $22.37

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

- Agent: Renamed `audio_rms(volumn)`→`audio_rms`, `audio_pitch_var(expressiveness)`→`audio_pitch_var` (producer + consumer migrated in same commit). Replaced 12 `print()` calls with `logging`+`rich`. Added `pipeline/_logging.py`, `pipeline/anomaly/smoothing.py`, `pipeline/features/linguistic.py` (wps/filler/pause), `pipeline/merge.py`. Wired `pipeline/orchestrator.py` with 9 stages matching spec §7, `progress_cb` callback for backend, CLI entrypoint `python -m pipeline.orchestrator`. AssemblyAI ms→sec normalization moved to producer boundary. 14 new structural tests in `test_orchestrator_pieces.py` cover merge / smoothing / RZ / RRCF wiring / categorical anomaly logic. Full video→parquet acceptance also ran successfully against `data/uploads/Interview_2.mp4` (632-row master parquet, 34 blink anomalies detected); two post-tag fixes for whisper-ffmpeg dependency and dotenv autoload landed in commit 271bb13.
- User: <fill if any retries / restarts / interventions occurred>

---

## M3 — Pipeline tests

- Completed: 2026-06-09T16:14:27Z
- Commit: 0571600f6e0504755c29418ecc37a3b861db7d4d
- Tag: m3-done
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

- Agent: Generated `tests/fixtures/tiny_master_df.parquet` (60 rows × 12 cols, two engineered anomalous windows) and `sample_anomaly_dicts.json` via committed one-shot script. Wrote `test_schemas.py` (13 tests across all 10 Pydantic per-frame models), `test_features.py` (27 tests across blink/gaze/jaw/smile/audio_metrics + level helpers), `test_anomaly.py` (15 tests for RRCF, MAD threshold, range grouping, smoothing+RZ), `test_parquet_io.py` (8 tests for round-trip + sidecar schema + fixture loading), `test_feature_engineering.py` (5 integration tests on synthetic input incl. monkeypatched librosa), `test_rrcf_internals.py`, `test_paths.py`. 106 tests passing. Coverage: `pipeline/features/` 98.75%, `pipeline/anomaly/` 93.86%, `pipeline/io/` 96.67% — all spec §10 targets exceeded.
- User: <fill if any retries / restarts / interventions occurred>

---
