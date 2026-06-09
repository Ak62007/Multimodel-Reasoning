# Decisions log

Recorded decisions made during the brownfield refactor when the build brief
left a detail genuinely ambiguous (not just unspecified). Spec wins ties.

## M1 — Refactor + scaffolding

- **`pipeline/utils.py` kept as a standalone module.** The target layout in
  spec §6 does not list a `utils.py`, but the original `src/utils/utils.py`
  contained a small `secs_mins` helper. Lifted as-is into `pipeline/utils.py`
  rather than deleting it (might be useful in M2 logging) or dropping it into
  another module where it doesn't belong.

- **`pipeline/anomaly/ranges.py` re-exports from `rrcf.py`.** The brief lists
  `ranges.py` separately, but the existing `get_anomalous_time_ranges`
  implementation has no rrcf dependency and lives in the same file. Re-export
  rather than duplicate, with a docstring explaining why.

- **Plotting helpers moved to `legacy_notebooks/_plotting/`.** The brief
  requires fixing the broken `from cv2 import cv` import in `plot_landmarks.py`
  but does not specify where the file should live in the new layout (none of
  `pipeline/`, `agents/`, or `backend/app/` is the right home — plotting is
  notebook-debug-only). Moved to `legacy_notebooks/_plotting/` and fixed the
  import there.

- **`AI/My First Board.jpg` preserved as `legacy_notebooks/board.jpg`.** It is
  reference material the author committed deliberately; not deleting it.

- **`pipeline/features/linguistic.py`, `pipeline/merge.py`,
  `pipeline/orchestrator.py`, and most files under `agents/` and
  `backend/app/` are stubs in M1.** They exist with docstrings explaining what
  goes where. Full implementations land in their target milestone (M2, M4, M5)
  per the execution order in spec §13.

- **Pydantic schemas for agent outputs not yet updated to the new
  `pattern_type`/`overall_window_tone` shape.** Spec §9.5 requires schema
  changes (rename `suspicion_level` → `significance`, add `pattern_type`,
  relax `overall_credibility` to `overall_window_tone`), but those touch
  agent code that doesn't exist yet. Schema work deferred to M4 alongside
  the agent implementations and prompts they're paired with — applying them
  in M1 would leave dead-code mismatches between the new schemas and the
  unchanged prompts.

- **Prompts not yet revised.** `agents/prompts.py` is moved verbatim from
  `AI/prompts.py`. Spec §9.6 requires revising them to match the
  Strength/Concern/Notable framing; that revision is bundled with M4 so the
  prompts and the matching schema changes ship together.

- **`from src.utils.datamodels import *` in `transforms.py` replaced with a
  precise list of names actually used downstream.** Wildcard imports trip
  ruff and hide what the module actually depends on.

- **Mypy `check_untyped_defs = false`** because the existing pipeline code is
  largely untyped and tightening this in M1 would require hundreds of
  annotations. Reassess in M3 once tests anchor behavior.

- **Ruff `extend-exclude = ["legacy_notebooks", ...]`** because the legacy
  files intentionally retain old style.

## M2 — Pipeline orchestrator + cleanup

- **Column renames touch only `pipeline/audio/technical.py` (producer) and
  `pipeline/features/transforms.py` (consumer).** `audio_rms(volumn)` →
  `audio_rms`, `audio_pitch_var(expressiveness)` → `audio_pitch_var`. The
  legacy notebooks under `legacy_notebooks/` still reference the old names —
  they're frozen reference material so we don't migrate them.

- **`extract_audio` signature widened.** Original took only `output_dir`; the
  orchestrator needs a precise output path. Added an `output_path` parameter
  that takes precedence over `output_dir`; the original `output_dir` form is
  preserved for ad-hoc CLI use. Removed the bare `../data/raw/` default since
  it is a relative path that depended on `cwd`.

- **`AssemblyAI` timestamps normalized ms→sec at the boundary
  (`transcribe_assemblyai.py`), not in consumers.** Earlier I tried defensive
  "max > 10_000" sniffing in `linguistic.py` and it failed on short
  utterances. The contract is now: utterances DataFrames always carry
  start/end in seconds. Documented in the docstring of `assign_speakers` /
  `get_speaker_segments`.

- **Linguistic features (`wps`, `filler_percentage`, `pause_percent_pr`)
  implemented in `pipeline/features/linguistic.py`.** The legacy notebooks
  load these from a pre-computed parquet; the actual compute code lived in a
  separate processing stage not visible from the four input notebooks.
  Re-derived from whisper-timestamped word-level segments using a simple
  filler-token list + `[*]` disfluency markers. The bookkeeping shape
  (anomalies dict keys) matches what `feature_engineering` expects.

- **Categorical anomaly detection vs RRCF.** `filler_percentage` and
  `pause_percent_pr` are categorical-ish: the per-row indicator is binary
  (filler present / window silent). RRCF on a binary signal would be noise.
  Used a simple threshold rule (`filler > 0`, `pause >= 1.0`) that produces
  the same `{col: [times]}` and `{col: [[time, ...]]}` shape RRCF emits.

- **`anomaly/smoothing.py` is new.** Logically lives in `anomaly/` because
  the smoothed-then-z-scored columns are the input to RRCF; per the original
  layout in spec §6 nothing forbids extra files inside `anomaly/`.

- **End-to-end acceptance via structural tests, not a real video.** The spec
  acceptance says "produces a final master parquet without error" when run on
  a real video. I don't have one — the user does. M2 ships 14 structural
  tests (`tests/unit/test_orchestrator_pieces.py`) that exercise the merge,
  smoothing, RZ, RRCF wiring, and feature_engineering integration on
  synthetic data. The full video→parquet path is exercised manually by the
  user (and via fixture-based tests in M3+). The orchestrator CLI parses,
  imports cleanly, and every glue function has type-checked. Documented this
  limitation in the test module docstring.

- **`STAGES` constant explicitly enumerates the 9 stages from spec §7.**
  Spec §7 lists 11 stages but stages 10 ("running_agents") and 11
  ("generating_final_report") belong to the agentic layer (M4); the
  pipeline's job ends at "building_master_df". The backend (M5) will add
  agent stages onto this list. A test (`test_stages_match_spec`) locks the
  pipeline-side names so they don't drift.

- **`feature_engineering` is called twice** — once in training mode to
  produce raw transformed metrics (input to smoothing), once in evaluation
  mode to produce the final Pydantic-dict columns. This matches the legacy
  notebooks' two-pass design. Kept the existing `Optional` signature so
  evaluation-mode callers can still pass real anomaly dicts.

- **`pipeline/_logging.py` is leading-underscore-prefixed** to mark it as
  package-private. Public callers should use a regular `logging.getLogger`
  in their own modules; `configure_logging` is invoked once by the
  orchestrator CLI and once by the backend job runner.

### M2 post-tag fixes (after `m2-done` tag, before `m3-done`)

The `m2-done` tag remains at the original M2 work commit per the spec's
"do not rewrite tags" rule. These follow-up fixes were discovered during the
real end-to-end validation run against `data/uploads/Interview_2.mp4`:

- **`pipeline/audio/transcribe_whisper.py` bypasses `wp.load_audio`.** The
  original `whisper-timestamped` call shells out to `ffmpeg` on PATH, which
  isn't a moviepy or any other dependency we already require — the user can
  trivially miss it. Switched to `librosa.load(audio_path, sr=16000, mono=True)`
  + `astype(float32)` and pass the waveform directly to
  `transcribe_timestamped`. Same numerical contract whisper expects, no
  extra system dependency.

- **`pipeline/orchestrator.main()` auto-loads `.env`.** Originally the CLI
  read raw `os.environ`, so `python -m pipeline.orchestrator …` wouldn't see
  `ASSEMBLYAI_API_KEY` unless the user had pre-exported it. Added a
  best-effort `dotenv.load_dotenv()` at the top of `main()` (no-op if
  python-dotenv isn't installed). The backend will use pydantic-settings
  instead, which has its own `.env` loading, so this is CLI-only convenience.

- **Validation result.** Ran on a real 10:31 interview at 1700×956. Pipeline
  produced `data/processed/m2-validate-v2/master.parquet` (632 rows, 12 cols)
  with all Pydantic-dict columns populated and schema-correct. 34 blink
  anomalies detected, speaker labels match utterance distribution
  (533 B / 87 A / 12 None), filler detection fired on rows that genuinely
  contain `[*]` disfluencies. Saved log: `data/processed/m2-validate-v2-run.log`.

## M3 — Pipeline tests

- **Committed fixture: `tests/fixtures/tiny_master_df.parquet`** (60 rows ×
  12 cols, ~30 s of synthetic data with two engineered anomalous windows
  at `[5.0, 5.5, 6.0]` for blink and `[22.0, 22.5, 23.0, 23.5]` for
  audio). Companion `sample_anomaly_dicts.json` carries the matching
  `anomalies` / `c_anomalies` shapes. Both regenerable with
  `PYTHONPATH=. uv run python tests/fixtures/_generate_tiny_master_df.py`.

- **Coverage scope.** The spec requires coverage in `pipeline/features/`,
  `pipeline/anomaly/`, `pipeline/io/`. `pipeline/orchestrator.py`,
  `pipeline/_logging.py`, `pipeline/utils.py`, `pipeline/merge.py`,
  `pipeline/audio/*`, and `pipeline/video/*` are intentionally only
  partially covered — they wrap external services (mediapipe, librosa,
  AssemblyAI, whisper) and are exercised via the M2 real-video validation
  run + the M2 structural tests (orchestrator pieces, merge contract).
  Treating them with the same target would force broad mocking that adds
  fragility without proving anything new.

- **`feature_engineering` covered via integration test, not micro-tests.**
  Its branches are tightly coupled (250+ lines, two modes, 10+ feature
  columns, both Pydantic instantiation and dict-shaped fallback). Cleaner
  to drive the whole function with a synthetic raw dataframe + sample
  anomaly dicts and assert on the output shape than to wrap each of its
  ~30 conditional branches.

- **`compute_speaker_median_pitch` covered via monkeypatched librosa.**
  Real audio fixtures cost megabytes; the function's logic (mask voiced
  pitch across multiple speaker segments, take overall median, round to
  2 dp) is fully exercised by faking `librosa.load` / `librosa.pyin` /
  `librosa.times_like`.

- **`pipeline/features/transforms.py` is still in the mypy override
  exclusion** even though tests now cover ~99 % of it. The remaining
  type problems are about the legacy `Optional`+`dict` plumbing, not
  about the test surface; the right fix is the refactor planned during
  the agentic-layer work (M4) where the function's contract gets pinned
  down by the agent input adapter.

- **Coverage totals (committed):** `pipeline/features/` = 98.75 %,
  `pipeline/anomaly/` = 93.86 %, `pipeline/io/` = 96.67 % — all targets
  exceeded with margin. Reported via
  `uv run pytest --cov=pipeline --cov-report=term`.

- **Per-file ignore for `RUF003` in tests.** Test/fixture file comments
  use the en-dash (`–`) and multiplication sign (`×`) for readability
  (e.g. "60 rows × 12 cols"). These are runtime-irrelevant.
