from dataclasses import dataclass
from enum import StrEnum


class DecisionOutcome(StrEnum):
    NORMAL = "NORMAL"
    FAULT = "FAULT"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class DecisionThresholds:
    fault_threshold: float = 0.65
    normal_threshold: float = 0.35

    def __post_init__(self) -> None:
        if not 0 <= self.normal_threshold < self.fault_threshold <= 1:
            raise ValueError(
                "Decision thresholds must satisfy 0 <= normal < fault <= 1"
            )


@dataclass(frozen=True)
class DecisionResult:
    decision: DecisionOutcome
    decision_score: float
    uncertainty_score: float
    explanation: str


class UncertaintyEvaluator:
    """Selective-classification uncertainty from the model confidence.

    The score is 0.5 at the decision boundary and decreases towards the extremes. It is a
    decision uncertainty score, not a probability of mechanical failure.
    """

    def uncertainty(self, fault_score: float) -> float:
        return 1.0 - max(fault_score, 1.0 - fault_score)


class DecisionPolicy:
    def __init__(
        self,
        thresholds: DecisionThresholds | None = None,
        uncertainty: UncertaintyEvaluator | None = None,
    ) -> None:
        self.thresholds = thresholds or DecisionThresholds()
        self.uncertainty_evaluator = uncertainty or UncertaintyEvaluator()

    def decide(
        self,
        fault_score: float,
        *,
        model_label: str,
        score_name: str = "decision score",
    ) -> DecisionResult:
        if not 0 <= fault_score <= 1:
            raise ValueError("Model score must be in [0, 1]")
        uncertainty = self.uncertainty_evaluator.uncertainty(fault_score)
        if fault_score >= self.thresholds.fault_threshold:
            decision = DecisionOutcome.FAULT
            explanation = (
                f"{model_label} accepted a FAULT decision: {score_name} "
                f"{fault_score:.4f} is at or above the fault threshold "
                f"{self.thresholds.fault_threshold:.2f}. This synthetic research output "
                "requires engineering review and is not a verified pump diagnosis."
            )
        elif fault_score <= self.thresholds.normal_threshold:
            decision = DecisionOutcome.NORMAL
            explanation = (
                f"{model_label} accepted a NORMAL decision: {score_name} "
                f"{fault_score:.4f} is at or below the normal threshold "
                f"{self.thresholds.normal_threshold:.2f}. This is a model decision, not "
                "a certified statement of pump health."
            )
        else:
            decision = DecisionOutcome.UNCERTAIN
            explanation = (
                f"{model_label} abstained: {score_name} {fault_score:.4f} lies inside "
                f"the uncertainty band ({self.thresholds.normal_threshold:.2f}, "
                f"{self.thresholds.fault_threshold:.2f}). Engineering review is required."
            )
        return DecisionResult(
            decision=decision,
            decision_score=fault_score,
            uncertainty_score=uncertainty,
            explanation=explanation,
        )
