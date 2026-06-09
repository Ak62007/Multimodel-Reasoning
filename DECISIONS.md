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
