import pytest
from petrosense_edge.decision import (
    DecisionOutcome,
    DecisionPolicy,
    DecisionThresholds,
    UncertaintyEvaluator,
)


def test_uncertainty_is_symmetric_around_boundary():
    evaluator = UncertaintyEvaluator()
    assert evaluator.uncertainty(0.5) == pytest.approx(0.5)
    assert evaluator.uncertainty(0.9) == pytest.approx(0.1)
    assert evaluator.uncertainty(0.1) == pytest.approx(0.1)


def test_decision_policy_supports_normal_fault_and_abstention():
    policy = DecisionPolicy(DecisionThresholds(fault_threshold=0.65, normal_threshold=0.35))
    fault = policy.decide(0.9, model_label="Synthetic model v0.1.0")
    normal = policy.decide(0.1, model_label="Synthetic model v0.1.0")
    uncertain = policy.decide(0.5, model_label="Synthetic model v0.1.0")

    assert fault.decision == DecisionOutcome.FAULT
    assert normal.decision == DecisionOutcome.NORMAL
    assert uncertain.decision == DecisionOutcome.UNCERTAIN
    assert uncertain.uncertainty_score == pytest.approx(0.5)
    assert "review" in uncertain.explanation.lower()
    assert "not a verified pump diagnosis" in fault.explanation


def test_decision_thresholds_are_ordered():
    with pytest.raises(ValueError):
        DecisionThresholds(fault_threshold=0.4, normal_threshold=0.6)
    with pytest.raises(ValueError):
        DecisionPolicy().decide(1.2, model_label="x")
