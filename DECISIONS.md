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

---

## 2026-06-10 — M2: pipeline orchestrator + cleanup

### Column renames

- `audio_rms(volumn)` → `audio_rms`
- `audio_pitch_var(expressiveness)` → `audio_pitch_var`
- Consumers (`pipeline/features/transforms.py`, `pipeline/orchestrator.py`)
  migrated in the same commit. Parens-style column names appeared only in
  the audio technical extractor; no parquet artefacts are checked in, so
  there is no legacy data migration to perform.

### Mode split

- The original `feature_engineering(mode="training"|"evaluation")` was the
  single largest source of type-system ambiguity (and of bugs — passing
  the wrong mode produced wildly different return shapes). Split into
  `compute_raw_features` (numeric outputs feeding smoothing) and
  `feature_engineering` (Pydantic-decodable outputs for the final master
  parquet). The mypy override added in M1 is removed accordingly.

### Master dataframe resolution

- Existing notebooks merged at **1 Hz** (inner join on `Time`), silently
  dropping the half-second audio rows. M2 changes the master grid to the
  audio grid (**0.5 s**) using `merge_asof(... direction='backward')` to
  forward-fill face features. This preserves the per-row schema and
  every Pydantic field downstream agents depend on, while keeping the
  full acoustic signal. The decision is contained inside `pipeline/merge.py`
  and changes resolution only; the column names are unchanged.

### Smoothing + robust-z

- EWM spans preserved verbatim from `feature_engineering.ipynb`:
  visual {blink:3, gaze:6, jaw:4, smile:8}, audio/verbal
  {loudness:5, pitch_rel:8, pitch_expr:6, wps:6}. Robust-z formula:
  `(x - median) / (1.4826 * MAD)`, returning 0 when MAD == 0. Visual
  features are normalised over the whole series; audio/verbal features
  are normalised over the target-speaker rows only.

### Anomaly detection sweep

- `pipeline/orchestrator._detect_anomalies` runs RRCF against the eight
  smoothed-rz feature columns, picks an adaptive `n_sigma`, thresholds
  via MAD, and groups consecutive anomalous timestamps into ranges with
  `get_anomalous_time_ranges`. Filler / pause categorical anomalies are
  passed through as empty lists; the per-row `FillerPercentageIncrease`
  / `PausePercentageIncrease` Pydantic models surface them via their
  existing `*_level` enum field.

### `JobPaths`

- Every pipeline component now reads its paths from
  `pipeline.io.paths.JobPaths`. No relative paths (`../data/raw/`)
  remain. The CLI keys a workdir by video stem; the backend will key
  it by job id (M5).

### Logging

- Every `print()` in `pipeline/` is now `logger.info` / `logger.warning`
  / `logger.exception`. The CLI's `--verbose` flag controls the root
  log level.
