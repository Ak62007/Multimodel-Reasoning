"""Manual smoke test: run the agent chain against a real master parquet using Groq.

Used for M4 acceptance ("manually, not in CI"). Requires GROQ_API_KEY in `.env`.

Usage:
    PYTHONPATH=. uv run python scripts/smoke_test_groq.py [path/to/master.parquet]

Defaults to the tiny committed fixture (no API cost — only a handful of windows).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Best-effort dotenv load so GROQ_API_KEY is picked up from .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agents.orchestrator import build_report
from pipeline._logging import configure_logging
from pipeline.io.parquet import load_df_parquet_safe

DEFAULT_PARQUET = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "tiny_master_df.parquet"
)


async def _main(parquet_path: Path) -> int:
    configure_logging(level=logging.INFO)
    master_df = load_df_parquet_safe(parquet_path)
    print(f"Loaded {len(master_df)} rows from {parquet_path}")

    public_reports, final = await build_report(master_df, speaker_label="B")

    print(f"\n=== {len(public_reports)} cross-modal windows ===")
    for i, r in enumerate(public_reports, 1):
        print(
            f"  [{i}] {r.time_range_start:.2f}-{r.time_range_end:.2f}s  tone={r.overall_window_tone}"
        )
        for ins in r.key_insights:
            print(
                f"      [{ins.pattern_type}/{ins.significance}] "
                f"({', '.join(ins.modalities_involved)})  {ins.observation}"
            )

    print("\n=== FinalReport ===")
    print("## Executive Summary")
    print(final.executive_summary)
    print("\n## Behavioral Strengths")
    print(final.behavioral_strengths)
    print("\n## Major Problems & Triggers")
    print(final.vulnerabilities_and_triggers)
    print("\n## Areas for Improvement")
    print(final.areas_for_improvement)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet_path", nargs="?", type=Path, default=DEFAULT_PARQUET)
    args = parser.parse_args()
    return asyncio.run(_main(args.parquet_path))


if __name__ == "__main__":
    sys.exit(main())
