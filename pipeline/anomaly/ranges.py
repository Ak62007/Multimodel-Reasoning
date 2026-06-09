"""Continuous anomalous-range grouping.

Re-exports the canonical implementation that lives in `pipeline.anomaly.rrcf`.
Kept as its own module because (1) the layout in the build brief separates rrcf
from range-grouping, and (2) range-grouping has no rrcf dependency, so future
work could swap detectors without touching range logic.
"""

from pipeline.anomaly.rrcf import get_anomalous_time_ranges

__all__ = ["get_anomalous_time_ranges"]
