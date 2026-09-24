import pytest

from dialypredict.evidence import empirical_error_band, evidence_level


def test_empirical_error_band_uses_held_out_absolute_errors() -> None:
    radius = empirical_error_band([1.0, 1.2, 1.4], [1.0, 1.1, 1.2], coverage=0.5)
    assert radius == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("point", "radius", "support", "expected"),
    [
        (1.4, 0.1, 8, "REFUSE_LOW_SUPPORT"),
        (1.1, 0.1, 40, "BELOW_TARGET"),
        (1.25, 0.1, 40, "EXPLORATORY_CANDIDATE"),
        (1.35, 0.1, 40, "ROBUST_CANDIDATE"),
    ],
)
def test_evidence_levels(point: float, radius: float, support: int, expected: str) -> None:
    result = evidence_level(point, radius, support, target=1.2)
    assert result.level == expected
