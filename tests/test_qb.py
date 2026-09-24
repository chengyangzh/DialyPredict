import pytest

from dialypredict.qb import compare_qb_sources, robust_actual_qb


def test_robust_actual_qb_filters_implausible_readings() -> None:
    result = robust_actual_qb([20, 238, 240, 242, 900])
    assert result == pytest.approx(240)


def test_robust_actual_qb_requires_repeated_measurement() -> None:
    assert robust_actual_qb([240, 242], minimum_readings=3) is None


def test_actual_qb_selected_only_when_it_improves_same_rows() -> None:
    comparison = compare_qb_sources(
        observed=[1.0, 1.2, 1.4],
        prescribed_predictions=[0.8, 1.0, 1.2],
        actual_predictions=[0.95, 1.15, 1.35],
        minimum_relative_improvement=0.1,
    )
    assert comparison.selected_source == "actual_qb"
    assert comparison.actual_mae < comparison.prescribed_mae
