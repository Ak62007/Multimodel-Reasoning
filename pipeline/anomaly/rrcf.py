"""Robust Random Cut Forest streaming anomaly detection.

This module provides the data-preparation and RRCF scoring functions used by the
pipeline. Threshold computation and continuous-range detection live in
``pipeline.anomaly.ranges``.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
from pysad.models import RobustRandomCutForest
from pysad.utils import ArrayStreamer

logger = logging.getLogger(__name__)

# Default gap tolerance (seconds) used by downstream continuity helpers.
MIN = 0.5
MAX = 2.0


def get_data_ready(
    data: pd.DataFrame,
    features: list[str],
    type: Literal["ui", "ud"],  # noqa: A002 — preserves original API
) -> tuple[pd.Index, np.ndarray]:
    """Prepare a feature matrix for streaming anomaly detection.

    Args:
        data: Source dataframe.
        features: Names of the columns to extract.
        type: ``"ui"`` for user-independent (use all rows) or ``"ud"`` for
            user-dependent (restrict to ``speaker == 'B'``).

    Returns:
        A tuple ``(index, matrix)`` where ``matrix`` has shape
        ``(num_rows, len(features))``.
    """
    if type == "ui":
        frame = data[features].ffill()
        return frame.index, frame.to_numpy()

    frame = data.loc[data["speaker"] == "B", features]
    if not frame.notna().all().all():
        frame = frame.ffill()
    return frame.index, frame.to_numpy()


def run_rrcf(
    features: np.ndarray,
    num_trees: int = 40,
    tree_size: int = 256,
    shingle: int = 1,
) -> list[float]:
    """Stream ``features`` through an RRCF model and return per-sample scores.

    Args:
        features: Array of shape ``(num_samples, num_features)``.
        num_trees: Number of trees in the forest.
        tree_size: Maximum tree size.
        shingle: Shingle window length (1 for non-shingled streaming).

    Returns:
        A list of anomaly scores aligned with the input rows.
    """
    model = RobustRandomCutForest(
        num_trees=num_trees,
        tree_size=tree_size,
        shingle_size=shingle,
    )
    streamer = ArrayStreamer(shuffle=False)

    anomaly_scores: list[float] = []
    for x in streamer.iter(features):
        score = model.fit_score_partial(x)
        anomaly_scores.append(float(score))

    logger.info("Processed %d points", len(anomaly_scores))
    return anomaly_scores
