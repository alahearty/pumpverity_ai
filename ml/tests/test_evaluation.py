import numpy as np
from petrosense_ml.evaluation import decisions_from_scores, evaluate_model


def test_decisions_respect_abstention_band():
    scores = np.array([0.1, 0.35, 0.5, 0.65, 0.9])
    decisions = decisions_from_scores(scores)
    assert list(decisions) == ["NORMAL", "NORMAL", "UNCERTAIN", "FAULT", "FAULT"]


def test_evaluation_reports_coverage_risk_and_abstention():
    scores = np.array([0.9, 0.1, 0.5, 0.8, 0.2])
    labels = np.array([1, 0, 1, 1, 0])
    metrics = evaluate_model("test", scores, labels)
    assert metrics["coverage"] == 0.8
    assert metrics["abstained_count"] == 1
    assert metrics["risk"] == 0.0
    assert metrics["balanced_accuracy"] == 1.0
    assert len(metrics["risk_coverage"]) == 10
    assert "brier" in metrics["calibration"]


def test_evaluation_detects_false_alerts():
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    labels = np.array([0, 0, 0, 1])
    metrics = evaluate_model("test", scores, labels)
    assert metrics["false_alert_rate"] == 2 / 3
    assert metrics["risk"] == 0.75
