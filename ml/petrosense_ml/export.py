import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from petrosense_edge.features import FEATURE_CONTRACT

from petrosense_ml.dataset import DATASET_VERSION
from petrosense_ml.train import FEATURE_NAMES, TrainedModels

LINEAR_CODE = "petrosense-linear"
LINEAR_NAME = "PUMPVERITY lightweight linear"
THRESHOLD_CODE = "petrosense-threshold"
THRESHOLD_NAME = "PUMPVERITY engineering threshold baseline"
MODEL_VERSION = "0.1.0"
EVALUATION_DATASET = "synthetic-grouped-holdout-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base_artifact() -> dict[str, Any]:
    return {
        "format_version": 1,
        "model_version_semantics": "research-artifact",
        "provenance": "SIMULATED",
        "training_dataset_version": DATASET_VERSION,
        "evaluation_dataset": EVALUATION_DATASET,
        "created_at": datetime.now(UTC).isoformat(),
        "limitations": (
            "Trained and evaluated on synthetic signals only. This artefact must not be "
            "presented as evidence of real-pump fault-detection performance."
        ),
    }


def export_artifacts(
    trained: TrainedModels,
    metrics_by_model: dict[str, dict[str, Any]],
    artifact_dir: Path,
) -> dict[str, dict[str, Any]]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    logistic = trained.logistic.named_steps["classifier"]
    scaler = trained.logistic.named_steps["scaler"]

    linear = {
        **_base_artifact(),
        "type": "linear",
        "model_code": LINEAR_CODE,
        "name": LINEAR_NAME,
        "version": MODEL_VERSION,
        "algorithm": "logistic-regression",
        "runtime": "LINEAR_JSON",
        "feature_contract": FEATURE_CONTRACT,
        "preprocessing": {
            "mean": [float(value) for value in scaler.mean_],
            "scale": [float(value) for value in scaler.scale_],
        },
        "coefficients": [float(value) for value in logistic.coef_[0]],
        "intercept": float(logistic.intercept_[0]),
        "decision": {"fault_threshold": 0.65, "normal_threshold": 0.35},
        "metrics": metrics_by_model["linear_json"],
        "notes": (
            "Pure JSON linear scorer intended for lightweight edge inference. "
            "Synthetic evaluation only."
        ),
    }
    threshold = {
        **_base_artifact(),
        "type": "threshold",
        "model_code": THRESHOLD_CODE,
        "name": THRESHOLD_NAME,
        "version": MODEL_VERSION,
        "algorithm": "engineering-threshold",
        "runtime": "BASELINE",
        "feature_contract": {
            "version": FEATURE_CONTRACT["version"],
            "features": ["rms"],
        },
        "feature": "rms",
        "center": trained.threshold.center,
        "scale": trained.threshold.scale,
        "normal_z": trained.threshold.normal_z,
        "fault_z": trained.threshold.fault_z,
        "decision": {"fault_threshold": 0.65, "normal_threshold": 0.35},
        "metrics": metrics_by_model["threshold_baseline"],
        "notes": "Engineering comparison baseline; synthetic evaluation only.",
    }

    linear_path = artifact_dir / f"{LINEAR_CODE}-{MODEL_VERSION}.json"
    threshold_path = artifact_dir / f"{THRESHOLD_CODE}-{MODEL_VERSION}.json"
    linear_path.write_text(json.dumps(linear, indent=2), encoding="utf-8")
    threshold_path.write_text(json.dumps(threshold, indent=2), encoding="utf-8")

    return {
        "linear": {
            "path": linear_path,
            "relative_path": f"ml/artifacts/{linear_path.name}",
            "sha256": sha256_file(linear_path),
            "artifact": linear,
            "feature_names": FEATURE_NAMES,
        },
        "threshold": {
            "path": threshold_path,
            "relative_path": f"ml/artifacts/{threshold_path.name}",
            "sha256": sha256_file(threshold_path),
            "artifact": threshold,
            "feature_names": ["rms"],
        },
    }


def build_registration_manifest(
    exported: dict[str, dict[str, Any]],
    metrics_by_model: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    def metadata(exported_model: dict[str, Any], *, baseline: bool) -> dict[str, Any]:
        artifact = exported_model["artifact"]
        return {
            "model_code": artifact["model_code"],
            "name": artifact["name"],
            "version": artifact["version"],
            "algorithm": artifact["algorithm"],
            "runtime": artifact["runtime"],
            "feature_contract": artifact["feature_contract"],
            "training_dataset_version": artifact["training_dataset_version"],
            "evaluation_dataset": artifact["evaluation_dataset"],
            "deployment_compatibility": {
                "edge": "petrosense-edge",
                "artifact_format": 1,
                "feature_contract_version": artifact["feature_contract"]["version"],
                "note": (
                    "Threshold baseline is a comparison model; the linear JSON model is the "
                    "selected Stage 4 edge deployment candidate."
                )
                if baseline
                else "Selected Stage 4 lightweight edge deployment candidate.",
            },
            "artifact_path": exported_model["relative_path"],
            "artifact_sha256": exported_model["sha256"],
            "notes": (
                "Synthetic research artefact. Evaluation provenance is SIMULATED; "
                "no real-pump performance claim."
            ),
        }

    def evaluation(metrics: dict[str, Any]) -> dict[str, Any]:
        return {
            "dataset_name": "Synthetic grouped hold-out set",
            "dataset_version": EVALUATION_DATASET,
            "data_provenance": "SIMULATED",
            "evaluation_protocol": "Grouped hold-out by simulated run",
            "split_description": (
                "GroupShuffleSplit by run_id (scenario + seed); no window from a run "
                "appears in both train and test."
            ),
            "sample_count": metrics["sample_count"],
            "balanced_accuracy": metrics["balanced_accuracy"],
            "macro_f1": metrics["macro_f1"],
            "metrics": {
                "coverage": metrics["coverage"],
                "risk": metrics["risk"],
                "false_alert_rate": metrics["false_alert_rate"],
                "precision_fault": metrics["precision_fault"],
                "recall_fault": metrics["recall_fault"],
                "accepted_count": metrics["accepted_count"],
                "abstained_count": metrics["abstained_count"],
            },
            "confusion_matrix": metrics["confusion_matrix"],
            "risk_coverage": metrics["risk_coverage"],
            "calibration": metrics["calibration"],
            "is_verified": True,
            "evaluated_by": "petrosense-ml-stage4",
            "notes": (
                "Verified as a synthetic evaluation record, not as real-world experimental "
                "ground truth."
            ),
        }

    return {
        "dataset_provenance": "SIMULATED",
        "models": [
            {
                "metadata": metadata(exported["threshold"], baseline=True),
                "evaluation": evaluation(metrics_by_model["threshold_baseline"]),
                "activate": False,
            },
            {
                "metadata": metadata(exported["linear"], baseline=False),
                "evaluation": evaluation(metrics_by_model["linear_json"]),
                "activate": True,
            },
        ],
    }
