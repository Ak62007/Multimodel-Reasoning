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
