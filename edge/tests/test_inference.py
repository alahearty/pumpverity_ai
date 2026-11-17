import hashlib
import json

import pytest
from petrosense_edge.features import FEATURE_CONTRACT
from petrosense_edge.inference import (
    ModelArtifactError,
    load_model_artifact,
)


def write_artifact(tmp_path, artifact: dict) -> tuple[object, str]:
    path = tmp_path / "model.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def linear_artifact(features=None) -> dict:
    names = features or ["rms", "peak_abs"]
    return {
        "format_version": 1,
        "type": "linear",
        "model_code": "test-linear",
        "name": "Test linear model",
        "version": "0.1.0",
        "runtime": "LINEAR_JSON",
        "feature_contract": {"version": "test-v1", "features": names},
        "preprocessing": {"mean": [0.0] * len(names), "scale": [1.0] * len(names)},
        "coefficients": [1.0] + [0.0] * (len(names) - 1),
        "intercept": 0.0,
        "decision": {"fault_threshold": 0.65, "normal_threshold": 0.35},
    }


def test_linear_artifact_loads_hash_checks_and_scores(tmp_path):
    artifact = linear_artifact()
    path, digest = write_artifact(tmp_path, artifact)
    model = load_model_artifact(
        path, expected_sha256=digest, expected_features=["rms", "peak_abs"]
    )
    assert model.label == "Test linear model v0.1.0"
    assert model.score({"rms": 0.0, "peak_abs": 10.0}) == pytest.approx(0.5)
    assert model.score({"rms": 2.0, "peak_abs": 0.0}) > 0.88

    with pytest.raises(ModelArtifactError, match="hash"):
        load_model_artifact(path, expected_sha256="0" * 64)
    with pytest.raises(ModelArtifactError, match="feature contract"):
        load_model_artifact(path, expected_sha256=digest, expected_features=["rms"])


def test_threshold_artifact_scores_severity(tmp_path):
    artifact = {
        "format_version": 1,
        "type": "threshold",
        "model_code": "test-threshold",
        "name": "Test threshold model",
        "version": "0.1.0",
        "runtime": "BASELINE",
        "feature_contract": {"version": "test-v1", "features": ["rms"]},
        "feature": "rms",
        "center": 0.03,
        "scale": 0.01,
        "normal_z": 2.0,
        "fault_z": 3.0,
        "decision": {"fault_threshold": 0.65, "normal_threshold": 0.35},
    }
    path, digest = write_artifact(tmp_path, artifact)
    model = load_model_artifact(path, expected_sha256=digest)
    assert model.score({"rms": 0.03}) == 0.0
    assert model.score({"rms": 0.055}) == pytest.approx(0.5)
    assert model.score({"rms": 0.06}) == 1.0


def test_invalid_artifacts_are_rejected(tmp_path):
    path, digest = write_artifact(tmp_path, {"format_version": 1, "type": "unknown"})
    with pytest.raises(ModelArtifactError):
        load_model_artifact(path, expected_sha256=digest)

    malformed = linear_artifact()
    malformed["coefficients"] = []
    malformed["preprocessing"] = {"mean": [], "scale": []}
    path, digest = write_artifact(tmp_path, malformed)
    with pytest.raises(ModelArtifactError):
        load_model_artifact(path, expected_sha256=digest)

    full = linear_artifact(list(FEATURE_CONTRACT["features"]))
    path, digest = write_artifact(tmp_path, full)
    model = load_model_artifact(path, expected_sha256=digest)
    assert len(model.feature_names) == len(FEATURE_CONTRACT["features"])
