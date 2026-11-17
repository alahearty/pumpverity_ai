import math
from datetime import UTC, datetime, timedelta

from tests.conftest import auth_headers

HASH = "b" * 64


def _model_payload(code: str, features=None):
    return {
        "model_code": code,
        "name": f"{code} model",
        "version": "0.1.0",
        "algorithm": "engineering-threshold",
        "runtime": "BASELINE",
        "feature_contract": {
            "version": "test-v1",
            "features": features or ["rms"],
        },
        "training_dataset_version": "synthetic-train-v1",
        "evaluation_dataset": "synthetic-eval-v1",
        "deployment_compatibility": {"edge": "petrosense-edge"},
        "artifact_path": f"ml/artifacts/{code}-0.1.0.json",
        "artifact_sha256": HASH,
    }


def _evaluation_payload():
    return {
        "dataset_name": "Synthetic grouped evaluation",
        "dataset_version": "synthetic-eval-v1",
        "data_provenance": "SIMULATED",
        "evaluation_protocol": "grouped hold-out",
        "split_description": "Grouped by simulated run",
        "sample_count": 120,
        "balanced_accuracy": 0.9,
        "macro_f1": 0.89,
        "is_verified": True,
        "evaluated_by": "stage4-test",
    }


def _active_model(client, code="prediction-model", features=None):
    headers = auth_headers(client, "researcher")
    registered = client.post(
        "/api/v1/models",
        json=_model_payload(code, features=features),
        headers=headers,
    )
    assert registered.status_code == 201, registered.text
    model = registered.json()
    evaluation = client.post(
        f"/api/v1/models/{model['id']}/evaluations",
        json=_evaluation_payload(),
        headers=headers,
    )
    assert evaluation.status_code == 201, evaluation.text
    assert client.post(
        f"/api/v1/models/{model['id']}/validate", headers=headers
    ).status_code == 200
    activated = client.post(
        f"/api/v1/models/{model['id']}/activate", headers=headers
    )
    assert activated.status_code == 200, activated.text
    return activated.json()


def _setup_equipment_and_window(client):
    engineer = auth_headers(client, "engineer")
    pump = client.post(
        "/api/v1/pumps",
        json={
            "pump_code": "PRED-PUMP-01",
            "name": "Prediction Test Pump",
            "pump_type": "CENTRIFUGAL",
            "location": "Laboratory",
            "rated_speed_rpm": 2900,
            "sensor": {
                "sensor_code": "PRED-VIB-01",
                "sensor_type": "VIBRATION",
                "mounting_axis": "RADIAL_X",
                "mounting_position": "Drive-end bearing housing",
                "sampling_rate_hz": 2048,
            },
        },
        headers=engineer,
    ).json()
    sensor = pump["sensors"][0]
    session = client.post(
        "/api/v1/acquisition-sessions",
        json={
            "pump_id": pump["id"],
            "sensor_id": sensor["id"],
            "sampling_rate_hz": 2048,
            "data_provenance": "SIMULATED",
            "random_seed": 42,
            "scenario": "normal",
        },
        headers=engineer,
    ).json()

    start = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    duration = 256 / 2048
    samples = [
        math.sin(2 * math.pi * 48.3 * i / 2048) * 0.05 for i in range(256)
    ]
    window = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json={
            "window_index": 0,
            "window_start": start.isoformat(),
            "window_end": (start + timedelta(seconds=duration)).isoformat(),
            "samples": samples,
            "quality_status": "VALID",
            "validation_summary": {
                "metrics": {"rms": 0.035, "peak_abs": 0.05, "units": "g"}
            },
            "features": {"rms": 0.035, "peak_abs": 0.05},
        },
        headers=engineer,
    )
    assert window.status_code == 201, window.text
    return engineer, pump, sensor, session, window.json()


def _prediction_payload(pump, sensor, session, window, model, **overrides):
    return {
        "event_id": "pred-event-001",
        "pump_id": pump["id"],
        "sensor_id": sensor["id"],
        "session_id": session["id"],
        "signal_window_id": window["id"],
        "model_version_id": model["id"],
        "decision": "FAULT",
        "data_quality": "VALID",
        "decision_score": 0.92,
        "uncertainty_score": 0.04,
        "explanation": "Synthetic model accepted an abnormal decision.",
        "latency_ms": 3.4,
        "inferred_at": datetime.now(UTC).isoformat(),
        **overrides,
    }


def test_prediction_persists_and_becomes_current_monitoring_state(client):
    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code="prediction-current")
    response = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(pump, sensor, session, window, model),
        headers=engineer,
    )
    assert response.status_code == 201, response.text
    prediction = response.json()
    assert prediction["decision"] == "FAULT"
    assert prediction["equipment_condition"] == "FAULT"
    assert prediction["model"]["version"] == "0.1.0"
    assert prediction["features"]["rms"] == 0.035
    assert prediction["data_provenance"] == "SIMULATED"

    listed = client.get("/api/v1/predictions?decision=FAULT", headers=engineer)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    detail = client.get(
        f"/api/v1/predictions/{prediction['id']}", headers=engineer
    )
    assert detail.status_code == 200
    assert detail.json()["explanation"].startswith("Synthetic model")

    live = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}", headers=engineer
    ).json()
    assert live["condition_available"] is True
    assert live["equipment_condition"] == "FAULT"
    assert live["latest_prediction"]["id"] == prediction["id"]

    overview = client.get("/api/v1/monitoring/overview", headers=engineer).json()
    assert overview["condition_available"] is True
    assert overview["equipment_condition"] == "FAULT"
    assert overview["latest_prediction"]["decision"] == "FAULT"


def test_sensor_invalid_suppresses_current_condition_but_records_prediction(client):
    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code="prediction-invalid")
    valid = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(pump, sensor, session, window, model),
        headers=engineer,
    )
    assert valid.status_code == 201

    start = datetime(2026, 11, 16, 12, 1, tzinfo=UTC)
    invalid_window = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json={
            "window_index": 1,
            "window_start": start.isoformat(),
            "window_end": (start + timedelta(seconds=1)).isoformat(),
            "samples": [],
            "quality_status": "SENSOR_INVALID",
            "validation_summary": {
                "issues": [{"code": "sensor_disconnected", "message": "Disconnected"}]
            },
        },
        headers=engineer,
    ).json()
    invalid_prediction = client.post(
        "/api/v1/predictions",
        json={
            "event_id": "pred-invalid-001",
            "pump_id": pump["id"],
            "sensor_id": sensor["id"],
            "session_id": session["id"],
            "signal_window_id": invalid_window["id"],
            "model_version_id": None,
            "decision": "SENSOR_INVALID",
            "data_quality": "SENSOR_INVALID",
            "decision_score": None,
            "uncertainty_score": None,
            "explanation": "Signal validation failed; inference was not attempted.",
            "latency_ms": 0.2,
            "inferred_at": datetime.now(UTC).isoformat(),
        },
        headers=engineer,
    )
    assert invalid_prediction.status_code == 201, invalid_prediction.text
    assert invalid_prediction.json()["equipment_condition"] is None

    live = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}", headers=engineer
    ).json()
    assert live["data_quality"] == "SENSOR_INVALID"
    assert live["condition_available"] is False
    assert live["equipment_condition"] is None
    assert live["latest_prediction"]["decision"] == "SENSOR_INVALID"


def test_prediction_guards_and_feature_contract(client):
    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code="prediction-guards")
    payload = _prediction_payload(pump, sensor, session, window, model)

    duplicate = client.post("/api/v1/predictions", json=payload, headers=engineer)
    assert duplicate.status_code == 201
    duplicate_again = client.post(
        "/api/v1/predictions", json=payload, headers=engineer
    )
    assert duplicate_again.status_code == 409
    assert duplicate_again.json()["error"]["code"] == "PREDICTION_EXISTS"

    reviewer = auth_headers(client, "reviewer")
    forbidden = client.post(
        "/api/v1/predictions",
        json={**payload, "event_id": "pred-forbidden-1"},
        headers=reviewer,
    )
    assert forbidden.status_code == 403

    mismatch_model = _active_model(
        client, code="prediction-contract", features=["rms", "kurtosis"]
    )
    mismatch = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump,
            sensor,
            session,
            window,
            mismatch_model,
            event_id="pred-contract-1",
        ),
        headers=engineer,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "FEATURE_CONTRACT_MISMATCH"
