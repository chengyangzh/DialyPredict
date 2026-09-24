"""Constrained Qb and duration candidate generation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import differential_evolution

PredictionFunction = Callable[[Mapping[str, float]], tuple[float, float, float]]
SupportFunction = Callable[[float, float], int]


@dataclass(frozen=True)
class EmpiricalSupport:
    """Training-data support region; this is not a clinical safety boundary."""

    qb_low: float
    qb_high: float
    duration_low: float
    duration_high: float


@dataclass(frozen=True)
class Candidate:
    qb: float
    duration: float
    predicted_spktv: float
    probability_adequate: float
    uncertainty: float
    local_support: int
    objective: float
    evidence_level: str
    requires_clinician_confirmation: bool = True


@dataclass(frozen=True)
class RecommendationResult:
    status: str
    candidates: tuple[Candidate, ...]
    warnings: tuple[str, ...]


class ContinuousPrescriptionRecommender:
    """Generate research candidates without prescribing treatment.

    The supplied predictor returns
    ``(predicted spKt/V, P(spKt/V >= target), uncertainty radius)``.
    """

    def __init__(
        self,
        predictor: PredictionFunction,
        support_counter: SupportFunction,
        support: EmpiricalSupport,
        target: float = 1.2,
        minimum_probability: float = 0.8,
        maximum_uncertainty: float = 0.30,
        minimum_local_support: int = 20,
        random_seed: int = 20260824,
    ) -> None:
        self.predictor = predictor
        self.support_counter = support_counter
        self.support = support
        self.target = target
        self.minimum_probability = minimum_probability
        self.maximum_uncertainty = maximum_uncertainty
        self.minimum_local_support = minimum_local_support
        self.random_seed = random_seed

    def recommend(
        self,
        patient_context: Mapping[str, float],
        current_qb: float,
        current_duration: float,
    ) -> RecommendationResult:
        if not (
            self.support.qb_low <= current_qb <= self.support.qb_high
            and self.support.duration_low <= current_duration <= self.support.duration_high
        ):
            return RecommendationResult(
                status="REFUSE_OUT_OF_EMPIRICAL_SUPPORT",
                candidates=(),
                warnings=("Current prescription is outside empirical support.",),
            )

        qb_scale = max(self.support.qb_high - self.support.qb_low, 1.0)
        time_scale = max(self.support.duration_high - self.support.duration_low, 1.0)
        weight_pairs = ((1.0, 0.35), (0.35, 1.0), (0.7, 0.7))
        candidates: list[Candidate] = []

        for qb_weight, time_weight in weight_pairs:

            def objective(
                action: np.ndarray,
                qb_weight: float = qb_weight,
                time_weight: float = time_weight,
            ) -> float:
                qb, duration = map(float, action)
                features = dict(patient_context)
                features["qb_prescribed"] = qb
                features["actual_duration"] = duration
                predicted, probability, uncertainty = self.predictor(features)
                local_n = self.support_counter(qb, duration)
                change_cost = (
                    qb_weight * abs(qb - current_qb) / qb_scale
                    + time_weight * abs(duration - current_duration) / time_scale
                )
                return (
                    change_cost
                    + 100.0 * max(0.0, self.target - predicted)
                    + 50.0 * max(0.0, self.minimum_probability - probability)
                    + 20.0 * max(0.0, uncertainty - self.maximum_uncertainty)
                    + 10.0 * max(0.0, self.minimum_local_support - local_n) ** 2
                )

            result = differential_evolution(
                objective,
                bounds=(
                    (self.support.qb_low, self.support.qb_high),
                    (self.support.duration_low, self.support.duration_high),
                ),
                seed=self.random_seed,
                polish=True,
                workers=1,
            )
            qb, duration = map(float, result.x)
            features = dict(patient_context)
            features["qb_prescribed"] = qb
            features["actual_duration"] = duration
            predicted, probability, uncertainty = self.predictor(features)
            local_n = int(self.support_counter(qb, duration))
            if predicted < self.target or probability < self.minimum_probability:
                continue
            if uncertainty > self.maximum_uncertainty or local_n < self.minimum_local_support:
                continue
            evidence = (
                "ROBUST_CANDIDATE"
                if predicted - uncertainty >= self.target
                else "EXPLORATORY_CANDIDATE"
            )
            candidate = Candidate(
                qb=qb,
                duration=duration,
                predicted_spktv=float(predicted),
                probability_adequate=float(probability),
                uncertainty=float(uncertainty),
                local_support=local_n,
                objective=float(result.fun),
                evidence_level=evidence,
            )
            if not any(
                abs(candidate.qb - prior.qb) < 1e-3
                and abs(candidate.duration - prior.duration) < 1e-3
                for prior in candidates
            ):
                candidates.append(candidate)

        if not candidates:
            return RecommendationResult(
                status="REFUSE_NO_RELIABLE_CANDIDATE",
                candidates=(),
                warnings=("No candidate passed all prediction and evidence gates.",),
            )

        candidates.sort(
            key=lambda item: (item.evidence_level != "ROBUST_CANDIDATE", item.objective)
        )
        return RecommendationResult(
            status="CANDIDATES_FOR_CLINICIAN_REVIEW",
            candidates=tuple(candidates),
            warnings=(
                "Empirical support is not a clinical safety boundary.",
                "Anticoagulation is warning-only and dialyzer changes are not recommended.",
            ),
        )
