import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from petrosense_edge.decision import DecisionThresholds
from petrosense_edge.features import FeatureExtractionError, vector_for_contract


class ModelArtifactError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedModel:
    name: str
    version: str
    model_code: str
    artifact: dict[str, Any]
    feature_names: list[str]
    thresholds: DecisionThresholds

    @property
    def label(self) -> str:
        return f"{self.name} v{self.version}"

    def score(self, features: dict[str, float]) -> float:
        artifact_type = self.artifact.get("type")
        if artifact_type == "linear":
            return self._linear_score(features)
        if artifact_type == "threshold":
            return self._threshold_score(features)
        raise ModelArtifactError(f"Unsupported artifact type: {artifact_type!r}")

    def _linear_score(self, features: dict[str, float]) -> float:
        vector = vector_for_contract(features, self.feature_names)
        means = self.artifact["preprocessing"]["mean"]
        scales = self.artifact["preprocessing"]["scale"]
        coefficients = self.artifact["coefficients"]
        intercept = float(self.artifact["intercept"])
        if not (len(means) == len(scales) == len(coefficients) == len(vector)):
            raise ModelArtifactError("Linear artifact dimensions do not match its feature contract")
        logit = intercept
        for value, mean, scale, coefficient in zip(
            vector, means, scales, coefficients, strict=True
        ):
            if scale == 0:
                raise ModelArtifactError("Artifact scale values must be non-zero")
            logit += float(coefficient) * ((value - float(mean)) / float(scale))
        return _sigmoid(logit)

    def _threshold_score(self, features: dict[str, float]) -> float:
        feature_name = str(self.artifact["feature"])
        vector = vector_for_contract(features, [feature_name])
        center = float(self.artifact["center"])
        scale = float(self.artifact["scale"])
        fault_z = float(self.artifact["fault_z"])
        normal_z = float(self.artifact["normal_z"])
        if scale <= 0 or fault_z <= normal_z:
            raise ModelArtifactError("Invalid threshold baseline parameters")
        z = (vector[0] - center) / scale
        score = (z - normal_z) / (fault_z - normal_z)
        return max(0.0, min(1.0, score))


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_artifact(
    path: Path,
    *,
    expected_sha256: str,
    expected_features: list[str] | None = None,
) -> LoadedModel:
    if not path.exists():
        raise ModelArtifactError(f"Model artifact not found: {path}")
    actual_hash = sha256_file(path)
    if actual_hash.lower() != expected_sha256.lower():
        raise ModelArtifactError(
            "Model artifact hash does not match the registered metadata"
        )
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelArtifactError(f"Model artifact is not valid JSON: {exc}") from exc

    if artifact.get("format_version") != 1:
        raise ModelArtifactError("Unsupported model artifact format version")
    contract = artifact.get("feature_contract")
    if not isinstance(contract, dict):
        raise ModelArtifactError("Artifact is missing a feature contract")
    names = contract.get("features")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        raise ModelArtifactError("Artifact feature contract is invalid")
    if expected_features is not None and names != expected_features:
        raise ModelArtifactError(
            "Artifact feature contract does not match the registered metadata"
        )

    decision = artifact.get("decision") or {}
    thresholds = DecisionThresholds(
        fault_threshold=float(decision.get("fault_threshold", 0.65)),
        normal_threshold=float(decision.get("normal_threshold", 0.35)),
    )
    artifact_type = artifact.get("type")
    if artifact_type == "linear":
        preprocessing = artifact.get("preprocessing") or {}
        if not isinstance(preprocessing.get("mean"), list) or not isinstance(
            preprocessing.get("scale"), list
        ):
            raise ModelArtifactError("Linear artifact is missing preprocessing vectors")
        if not isinstance(artifact.get("coefficients"), list):
            raise ModelArtifactError("Linear artifact is missing coefficients")
        if len(preprocessing["mean"]) != len(names):
            raise ModelArtifactError("Artifact preprocessing does not match features")
    elif artifact_type == "threshold":
        if artifact.get("feature") not in names:
            raise ModelArtifactError("Threshold feature is not in the feature contract")
    else:
        raise ModelArtifactError(f"Unsupported artifact type: {artifact_type!r}")

    return LoadedModel(
        name=str(artifact.get("name", "Unnamed model")),
        version=str(artifact.get("version", "0.0.0")),
        model_code=str(artifact.get("model_code", "")),
        artifact=artifact,
        feature_names=list(names),
        thresholds=thresholds,
    )


__all__ = [
    "FeatureExtractionError",
    "LoadedModel",
    "ModelArtifactError",
    "load_model_artifact",
    "sha256_file",
]
