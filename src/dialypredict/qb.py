"""Utilities for comparing prescribed and machine-recorded Qb."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QbSourceComparison:
    prescribed_mae: float
    actual_mae: float
    selected_source: str
    relative_change: float


def robust_actual_qb(
    readings: Iterable[float],
    minimum_readings: int = 3,
    plausible_low: float = 100.0,
    plausible_high: float = 500.0,
) -> float | None:
    """Summarize delivered Qb using the median of plausible machine readings."""

    values = np.asarray(tuple(readings), dtype=float)
    values = values[np.isfinite(values)]
    values = values[(values >= plausible_low) & (values <= plausible_high)]
    if values.size < minimum_readings:
        return None
    return float(np.median(values))


def compare_qb_sources(
    observed: Iterable[float],
    prescribed_predictions: Iterable[float],
    actual_predictions: Iterable[float],
    minimum_relative_improvement: float = 0.0,
) -> QbSourceComparison:
    """Select Qb source on the same held-out rows, preferring simplicity on ties."""

    y = np.asarray(tuple(observed), dtype=float)
    prescribed = np.asarray(tuple(prescribed_predictions), dtype=float)
    actual = np.asarray(tuple(actual_predictions), dtype=float)
    if y.shape != prescribed.shape or y.shape != actual.shape or y.size == 0:
        raise ValueError("all arrays must be non-empty and have identical shapes")
    prescribed_mae = float(np.mean(np.abs(y - prescribed)))
    actual_mae = float(np.mean(np.abs(y - actual)))
    required = prescribed_mae * (1.0 - minimum_relative_improvement)
    selected = "actual_qb" if actual_mae < required else "prescribed_qb"
    relative = (actual_mae - prescribed_mae) / max(prescribed_mae, np.finfo(float).eps)
    return QbSourceComparison(
        prescribed_mae=prescribed_mae,
        actual_mae=actual_mae,
        selected_source=selected,
        relative_change=float(relative),
    )
