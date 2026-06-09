"""End-to-end pipeline orchestrator.

Takes a video path, runs every stage (extract → transcribe → merge →
feature engineering → anomaly detection), and writes the final master parquet.

Wired in M2. The CLI entrypoint is `python -m pipeline.orchestrator <video_path>`.
"""

from __future__ import annotations

import sys

__all__: list[str] = []


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    raise NotImplementedError("pipeline.orchestrator is implemented in milestone M2")


if __name__ == "__main__":
    raise SystemExit(main())
