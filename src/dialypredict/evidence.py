"""Uncertainty and empirical-support utilities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EvidenceAssessment:
    level: str
    point_estimate: float
    lower: float
    upper: float
    local_support: int
    target: float


def empirical_error_band(
    observed: Iterable[float],
    predicted: Iterable[float],
    coverage: float = 0.90,
) -> float:
    """Return a symmetric held-out absolute-error radius.

    This is an empirical error band, not a formal confidence interval. Inputs
    must come from held-out predictions rather than model-training residuals.
    """

    if not 0 < coverage < 1:
        raise ValueError("coverage must lie strictly between 0 and 1")
    y = np.asarray(tuple(observed), dtype=float)
    yhat = np.asarray(tuple(predicted), dtype=float)
    if y.shape != yhat.shape or y.ndim != 1 or y.size == 0:
        raise ValueError("observed and predicted must be non-empty one-dimensional arrays")
    if not np.isfinite(y).all() or not np.isfinite(yhat).all():
        raise ValueError("observed and predicted must be finite")
    return float(np.quantile(np.abs(y - yhat), coverage))


def evidence_level(
    point_estimate: float,
    error_radius: float,
    local_support: int,
    target: float,
    minimum_local_support: int = 20,
) -> EvidenceAssessment:
    """Classify a scenario as refused, exploratory, or robust."""

    if error_radius < 0 or local_support < 0 or minimum_local_support < 1:
        raise ValueError("invalid evidence parameters")
    lower = max(0.0, point_estimate - error_radius)
    upper = point_estimate + error_radius
    if local_support < minimum_local_support:
        level = "REFUSE_LOW_SUPPORT"
    elif point_estimate < target:
        level = "BELOW_TARGET"
    elif lower < target:
        level = "EXPLORATORY_CANDIDATE"
    else:
        level = "ROBUST_CANDIDATE"
    return EvidenceAssessment(
        level=level,
        point_estimate=float(point_estimate),
        lower=float(lower),
        upper=float(upper),
        local_support=int(local_support),
        target=float(target),
    )
