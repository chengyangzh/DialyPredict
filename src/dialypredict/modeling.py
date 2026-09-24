"""Model definitions that contain no fitted parameters or clinical records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskDefinition:
    """Declare an endpoint and its ordered feature contract."""

    name: str
    target: str
    features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    monotone_increasing: tuple[str, ...]

    def monotone_vector(self) -> tuple[int, ...]:
        return tuple(1 if feature in self.monotone_increasing else 0 for feature in self.features)


SPKTV_TASK = TaskDefinition(
    name="measured_spktv",
    target="measured_spktv",
    features=(
        "age",
        "sex",
        "height",
        "post_weight",
        "vascular_access",
        "qb_prescribed",
        "actual_duration",
        "ultrafiltration_volume",
        "anticoagulation_context",
    ),
    categorical_features=("sex", "vascular_access", "anticoagulation_context"),
    monotone_increasing=("qb_prescribed", "actual_duration"),
)

HDF_TASK = TaskDefinition(
    name="total_convective_volume",
    target="total_convective_volume",
    features=(
        "age",
        "sex",
        "height",
        "post_weight",
        "vascular_access",
        "qb_prescribed",
        "actual_duration",
        "anticoagulation_context",
    ),
    categorical_features=("sex", "vascular_access", "anticoagulation_context"),
    monotone_increasing=("qb_prescribed", "actual_duration"),
)


def build_xgboost_regressor(
    task: TaskDefinition,
    random_seed: int = 20260824,
    **overrides: Any,
) -> Any:
    """Construct an unfitted XGBoost baseline with declared monotonicity."""

    try:
        from xgboost import XGBRegressor
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise ImportError("Install DialyPredict with the 'ml' extra to use XGBoost") from exc
    parameters = {
        "objective": "reg:squarederror",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "tree_method": "hist",
        "monotone_constraints": task.monotone_vector(),
        "random_state": random_seed,
    }
    parameters.update(overrides)
    return XGBRegressor(**parameters)


def build_catboost_regressor(
    task: TaskDefinition,
    random_seed: int = 20260824,
    **overrides: Any,
) -> Any:
    """Construct an unfitted CatBoost baseline with declared monotonicity."""

    try:
        from catboost import CatBoostRegressor
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise ImportError("Install DialyPredict with the 'ml' extra to use CatBoost") from exc
    parameters = {
        "loss_function": "RMSE",
        "iterations": 600,
        "depth": 6,
        "learning_rate": 0.03,
        "random_seed": random_seed,
        "verbose": False,
        "monotone_constraints": {feature: 1 for feature in task.monotone_increasing},
    }
    parameters.update(overrides)
    return CatBoostRegressor(**parameters)
