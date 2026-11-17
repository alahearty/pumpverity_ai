from typing import Any

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

NORMAL_THRESHOLD = 0.35
FAULT_THRESHOLD = 0.65


def decisions_from_scores(scores: np.ndarray) -> np.ndarray:
    decisions = np.full(scores.shape, "UNCERTAIN", dtype=object)
    decisions[scores >= FAULT_THRESHOLD] = "FAULT"
    decisions[scores <= NORMAL_THRESHOLD] = "NORMAL"
    return decisions


def _safe_metric(metric, y_true, y_pred, **kwargs) -> float:
    if len(y_true) == 0:
        return 0.0
    return float(metric(y_true, y_pred, **kwargs))


def _risk_coverage(scores: np.ndarray, labels: np.ndarray) -> list[dict[str, float]]:
    predictions = (scores >= 0.5).astype(int)
    confidence = np.maximum(scores, 1 - scores)
    points = []
    for threshold in np.round(np.arange(0.5, 0.96, 0.05), 2):
        accepted = confidence >= threshold
        coverage = float(np.mean(accepted))
        risk = float(np.mean(predictions[accepted] != labels[accepted])) if accepted.any() else 0.0
        points.append({"threshold": float(threshold), "coverage": coverage, "risk": risk})
    return points


def _calibration(scores: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    bins = np.linspace(0, 1, 11)
    bin_ids = np.clip(np.digitize(scores, bins) - 1, 0, 9)
    ece = 0.0
    bins_out = []
    for bin_index in range(10):
        mask = bin_ids == bin_index
        count = int(mask.sum())
        if count == 0:
            bins_out.append({"bin": bin_index, "count": 0})
            continue
        avg_score = float(scores[mask].mean())
        fraction_positive = float(labels[mask].mean())
        ece += (count / len(scores)) * abs(fraction_positive - avg_score)
        bins_out.append(
            {
                "bin": bin_index,
                "count": count,
                "mean_score": round(avg_score, 4),
                "fraction_positive": round(fraction_positive, 4),
            }
        )
    return {
        "brier": float(brier_score_loss(labels, scores)),
        "ece": float(ece),
        "bins": bins_out,
    }


def evaluate_model(
    name: str,
    scores: np.ndarray,
    labels: np.ndarray,
    *,
    scenario: np.ndarray | None = None,
) -> dict[str, Any]:
    decisions = decisions_from_scores(scores)
    accepted = decisions != "UNCERTAIN"
    accepted_labels = labels[accepted]
    accepted_predictions = (scores[accepted] >= 0.5).astype(int)
    coverage = float(accepted.mean()) if len(labels) else 0.0
    risk = (
        float(np.mean(accepted_predictions != accepted_labels))
        if accepted.any()
        else 0.0
    )
    matrix = confusion_matrix(
        accepted_labels, accepted_predictions, labels=[0, 1]
    ).tolist() if accepted.any() else [[0, 0], [0, 0]]
    normal_count = int((accepted_labels == 0).sum())
    false_alerts = int(((accepted_labels == 0) & (accepted_predictions == 1)).sum())
    false_alert_rate = false_alerts / normal_count if normal_count else 0.0

    metrics = {
        "model": name,
        "sample_count": len(labels),
        "coverage": coverage,
        "risk": risk,
        "balanced_accuracy": _safe_metric(
            balanced_accuracy_score, accepted_labels, accepted_predictions
        ),
        "macro_f1": _safe_metric(
            f1_score,
            accepted_labels,
            accepted_predictions,
            average="macro",
            zero_division=0,
        ),
        "precision_fault": _safe_metric(
            precision_score,
            accepted_labels,
            accepted_predictions,
            pos_label=1,
            zero_division=0,
        ),
        "recall_fault": _safe_metric(
            recall_score,
            accepted_labels,
            accepted_predictions,
            pos_label=1,
            zero_division=0,
        ),
        "false_alert_rate": float(false_alert_rate),
        "accepted_count": int(accepted.sum()),
        "abstained_count": int((~accepted).sum()),
        "confusion_matrix": {
            "labels": ["NORMAL", "FAULT"],
            "matrix": matrix,
            "abstained": int((~accepted).sum()),
        },
        "risk_coverage": _risk_coverage(scores, labels),
        "calibration": _calibration(scores, labels),
    }
    if scenario is not None:
        metrics["incipient_stress"] = {
            "count": int((scenario == "incipient_fault").sum()),
            "abstained": int(
                ((scenario == "incipient_fault") & (~accepted)).sum()
            ),
        }
    return metrics


def comparison_report(
    metrics_by_model: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "dataset_provenance": "SIMULATED",
        "decision_thresholds": {
            "fault": FAULT_THRESHOLD,
            "normal": NORMAL_THRESHOLD,
        },
        "models": metrics_by_model,
        "warning": (
            "These metrics are generated from synthetic signals. They do not establish "
            "real-world pump-fault detection performance and must not be reported as such."
        ),
    }
