from app.db.models import AuditLog
from sqlalchemy import select
from tests.conftest import auth_headers

HASH = "a" * 64


def _model_payload(code: str, version: str = "0.1.0", runtime: str = "BASELINE"):
    return {
        "model_code": code,
        "name": f"{code} research model",
        "version": version,
        "algorithm": "engineering-threshold",
        "runtime": runtime,
        "feature_contract": {"version": "test-v1", "features": ["rms"]},
        "training_dataset_version": "synthetic-train-v1",
        "evaluation_dataset": "synthetic-eval-v1",
        "deployment_compatibility": {"edge": "petrosense-edge", "runtime": runtime},
        "artifact_path": f"ml/artifacts/{code}-{version}.json",
        "artifact_sha256": HASH,
        "notes": "Synthetic research artefact; not experimentally validated.",
    }


def _evaluation_payload(is_verified: bool = True):
    return {
        "dataset_name": "Synthetic grouped evaluation",
        "dataset_version": "synthetic-eval-v1",
        "data_provenance": "SIMULATED",
        "evaluation_protocol": "grouped hold-out by simulated run",
        "split_description": "Runs split by seed and scenario; no window leakage.",
        "sample_count": 180,
        "balanced_accuracy": 0.88,
        "macro_f1": 0.87,
        "metrics": {"false_alert_rate": 0.05, "coverage": 0.92},
        "confusion_matrix": {"NORMAL": {"NORMAL": 80, "FAULT": 5}},
        "risk_coverage": {"0.8": {"risk": 0.04, "coverage": 0.85}},
        "calibration": {"brier": 0.09},
        "is_verified": is_verified,
        "evaluated_by": "stage4-test",
        "notes": "Synthetic metrics only; no real-pump claim.",
    }


def _create_validated_model(client, headers, code: str, runtime: str = "BASELINE"):
    registered = client.post(
        "/api/v1/models", json=_model_payload(code, runtime=runtime), headers=headers
    )
    assert registered.status_code == 201, registered.text
    model = registered.json()
    evaluated = client.post(
        f"/api/v1/models/{model['id']}/evaluations",
        json=_evaluation_payload(),
        headers=headers,
    )
    assert evaluated.status_code == 201, evaluated.text
    validated = client.post(
        f"/api/v1/models/{model['id']}/validate", headers=headers
    )
    assert validated.status_code == 200, validated.text
    return validated.json()


def test_model_lifecycle_activation_and_rollback(client, db):
    researcher = auth_headers(client, "researcher")
    first = _create_validated_model(client, researcher, "threshold-a")
    assert first["status"] == "VALIDATED"
    assert first["latest_evaluation"]["data_provenance"] == "SIMULATED"

    activated = client.post(
        f"/api/v1/models/{first['id']}/activate", headers=researcher
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"

    second = _create_validated_model(client, researcher, "threshold-b", "LINEAR_JSON")
    second_active = client.post(
        f"/api/v1/models/{second['id']}/activate", headers=researcher
    )
    assert second_active.status_code == 200
    assert second_active.json()["status"] == "ACTIVE"

    first_after = client.get(f"/api/v1/models/{first['id']}", headers=researcher).json()
    assert first_after["status"] == "RETIRED"

    active = client.get("/api/v1/models/active", headers=researcher).json()
    assert active["id"] == second["id"]

    rollback = client.post("/api/v1/models/rollback", headers=researcher)
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["id"] == first["id"]
    assert rollback.json()["status"] == "ACTIVE"

    db.expire_all()
    actions = db.execute(select(AuditLog.action)).scalars().all()
    assert "MODEL_REGISTERED" in actions
    assert "MODEL_EVALUATION_ADDED" in actions
    assert "MODEL_VALIDATED" in actions
    assert "MODEL_ACTIVATED" in actions
    assert "MODEL_ROLLED_BACK" in actions


def test_model_registration_and_activation_guards(client):
    engineer = auth_headers(client, "engineer")
    researcher = auth_headers(client, "researcher")

    forbidden = client.post(
        "/api/v1/models", json=_model_payload("forbidden-model"), headers=engineer
    )
    assert forbidden.status_code == 403

    duplicate = client.post(
        "/api/v1/models", json=_model_payload("duplicate-model"), headers=researcher
    )
    assert duplicate.status_code == 201
    duplicate_again = client.post(
        "/api/v1/models", json=_model_payload("duplicate-model"), headers=researcher
    )
    assert duplicate_again.status_code == 409

    no_feature = _model_payload("no-feature")
    no_feature["feature_contract"] = {"version": "bad"}
    bad_contract = client.post(
        "/api/v1/models", json=no_feature, headers=researcher
    )
    assert bad_contract.status_code == 422

    registered = client.post(
        "/api/v1/models", json=_model_payload("unverified-model"), headers=researcher
    ).json()
    unverified = client.post(
        f"/api/v1/models/{registered['id']}/evaluations",
        json=_evaluation_payload(False),
        headers=researcher,
    )
    assert unverified.status_code == 201
    validate_unverified = client.post(
        f"/api/v1/models/{registered['id']}/validate", headers=researcher
    )
    assert validate_unverified.status_code == 422
    assert validate_unverified.json()["error"]["code"] == "EVALUATION_REQUIRED"

    unsupported = client.post(
        "/api/v1/models",
        json=_model_payload("onnx-model", runtime="ONNX"),
        headers=researcher,
    ).json()
    unsupported_eval = client.post(
        f"/api/v1/models/{unsupported['id']}/evaluations",
        json=_evaluation_payload(),
        headers=researcher,
    )
    assert unsupported_eval.status_code == 201
    unsupported_validate = client.post(
        f"/api/v1/models/{unsupported['id']}/validate", headers=researcher
    )
    assert unsupported_validate.status_code == 422
    assert unsupported_validate.json()["error"]["code"] == "RUNTIME_NOT_SUPPORTED"


def test_verified_evaluation_requires_metrics(client):
    researcher = auth_headers(client, "researcher")
    model = client.post(
        "/api/v1/models", json=_model_payload("missing-metrics"), headers=researcher
    ).json()
    payload = _evaluation_payload()
    payload["balanced_accuracy"] = None
    payload["macro_f1"] = None
    response = client.post(
        f"/api/v1/models/{model['id']}/evaluations",
        json=payload,
        headers=researcher,
    )
    assert response.status_code == 422


def test_model_list_filters(client):
    researcher = auth_headers(client, "researcher")
    _create_validated_model(client, researcher, "list-model")
    response = client.get(
        "/api/v1/models?status=VALIDATED&q=list-model", headers=researcher
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["model_code"] == "list-model"
