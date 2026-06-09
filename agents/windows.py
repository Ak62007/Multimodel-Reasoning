"""Group anomalous time ranges into analysis windows for the agent chain.

Implemented in M4. Default strategy: each per-feature `part_of_anomalous_range`
defines a candidate window; merge overlapping or adjacent (<1s gap) ranges.
Windows with no anomalies are skipped (don't waste tokens on baseline).
"""

from __future__ import annotations

__all__: list[str] = []
