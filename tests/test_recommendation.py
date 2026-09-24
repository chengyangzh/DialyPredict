import math

from dialypredict.recommendation import (
    ContinuousPrescriptionRecommender,
    EmpiricalSupport,
)


def synthetic_predictor(features: dict[str, float]) -> tuple[float, float, float]:
    predicted = (
        0.35
        + 0.0016 * features["qb_prescribed"]
        + 0.0022 * features["actual_duration"]
        - 0.002 * (features["weight"] - 65.0)
    )
    probability = 1.0 / (1.0 + math.exp(-10.0 * (predicted - 1.08)))
    return predicted, probability, 0.08


def supported_region(qb: float, duration: float) -> int:
    return 80 if 180 <= qb <= 340 and 180 <= duration <= 300 else 0


def test_recommender_returns_candidates_for_review() -> None:
    recommender = ContinuousPrescriptionRecommender(
        predictor=synthetic_predictor,
        support_counter=supported_region,
        support=EmpiricalSupport(180, 340, 180, 300),
        target=1.2,
        minimum_probability=0.7,
        minimum_local_support=20,
    )
    result = recommender.recommend({"weight": 65.0}, current_qb=220, current_duration=220)
    assert result.status == "CANDIDATES_FOR_CLINICIAN_REVIEW"
    assert result.candidates
    assert all(candidate.predicted_spktv >= 1.2 for candidate in result.candidates)


def test_recommender_refuses_outside_empirical_support() -> None:
    recommender = ContinuousPrescriptionRecommender(
        predictor=synthetic_predictor,
        support_counter=supported_region,
        support=EmpiricalSupport(180, 340, 180, 300),
    )
    result = recommender.recommend({"weight": 65.0}, current_qb=500, current_duration=220)
    assert result.status == "REFUSE_OUT_OF_EMPIRICAL_SUPPORT"
    assert not result.candidates
