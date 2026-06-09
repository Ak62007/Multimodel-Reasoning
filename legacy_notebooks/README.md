# Legacy notebooks

The notebooks in this directory are kept as **reference material only**. They
were the original exploration of the multimodal pipeline and agentic chain
before the codebase was refactored into `pipeline/`, `agents/`, and
`backend/app/`.

- `notebooks/old_notebooks/` — original `notebooks/` directory: per-stage
  exploration (audio, video, feature engineering, anomaly detection, merge,
  master dataframe analysis, parallel processing).
- `AI_notebooks/notebooks/` — the original `AI/notebooks/` containing
  `archi_testing.ipynb`, the only place the agent chain was wired up before M4.
- `_plotting/` — old plotting helpers (`plot_landmarks.py`, `plot_graphs.py`).
  The invalid `from cv2 import cv` import in `plot_landmarks.py` was fixed
  during M1; both files are kept here because they are only used inside
  the legacy notebooks.
- `board.jpg` — design board image preserved from the original `AI/` folder.

Do **not** import from this directory in production code. If you want logic
from here, lift it into `pipeline/` or `agents/` proper with tests.
