import math
from datetime import UTC, datetime, timedelta

from app.db.models import AuditLog, SignalWindow
from sqlalchemy import select
from tests.conftest import auth_headers

PUMP_PAYLOAD = {
    "pump_code": "LAB-PUMP-01",
    "name": "Laboratory Centrifugal Pump",
    "pump_type": "CENTRIFUGAL",
    "location": "Thermofluids Laboratory",
    "rated_speed_rpm": 2900,
    "sensor": {
        "sensor_code": "VIB-01",
        "sensor_type": "VIBRATION",
        "mounting_axis": "RADIAL_X",
        "mounting_position": "Drive-end bearing housing",
        "sampling_rate_hz": 2048,
    },
}


def _setup_equipment(client):
    headers = auth_headers(client, "engineer")
    pump = client.post("/api/v1/pumps", json=PUMP_PAYLOAD, headers=headers).json()
    return headers, pump, pump["sensors"][0]


def _session_payload(pump, sensor, **overrides):
    return {
        "pump_id": pump["id"],
        "sensor_id": sensor["id"],
        "sampling_rate_hz": 2048,
        "data_provenance": "SIMULATED",
        "random_seed": 42,
        "scenario": "normal",
        "source_device_id": "edge-test-01",
        **overrides,
    }


def _window_payload(index=0, quality="VALID", **overrides):
    sample_count = 256
    start = datetime(2026, 11, 16, 12, 0, tzinfo=UTC) + timedelta(seconds=index * 0.125)
    end = start + timedelta(seconds=sample_count / 2048)
    samples = [
        math.sin(2 * math.pi * 48.3 * i / 2048) * 0.05
        for i in range(sample_count)
    ]
    return {
        "window_index": index,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "samples": samples if quality == "VALID" else [],
        "quality_status": quality,
        "validation_summary": (
            {"issues": [{"code": "sensor_disconnected"}]}
            if quality == "SENSOR_INVALID"
            else {"metrics": {"rms": 0.035}}
        ),
        **overrides,
    }


def test_create_session_ingest_window_and_stop(client, db):
    headers, pump, sensor = _setup_equipment(client)

    created = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    session = created.json()
    assert session["pump_code"] == "LAB-PUMP-01"
    assert session["sensor_code"] == "VIB-01"
    assert session["data_provenance"] == "SIMULATED"
    assert session["scenario"] == "normal"
    assert session["status"] == "ACTIVE"
    assert session["window_count"] == 0

    window = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json=_window_payload(),
        headers=headers,
    )
    assert window.status_code == 201, window.text
    assert window.json()["sample_count"] == 256
    assert window.json()["quality_status"] == "VALID"
    assert window.json()["data_provenance"] == "SIMULATED"

    detail = client.get(f"/api/v1/acquisition-sessions/{session['id']}", headers=headers)
    assert detail.json()["window_count"] == 1

    windows = client.get(
        f"/api/v1/acquisition-sessions/{session['id']}/windows", headers=headers
    )
    assert windows.status_code == 200
    assert windows.json()["total"] == 1

    stopped = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/stop",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "COMPLETED"
    assert stopped.json()["ended_at"] is not None

    repeated = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/stop",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "COMPLETED"

    after_stop = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json=_window_payload(index=1),
        headers=headers,
    )
    assert after_stop.status_code == 409
    assert after_stop.json()["error"]["code"] == "SESSION_NOT_ACTIVE"

    db.expire_all()
    actions = db.execute(select(AuditLog.action).order_by(AuditLog.id)).scalars().all()
    assert actions.count("ACQUISITION_SESSION_STARTED") == 1
    assert actions.count("ACQUISITION_SESSION_STOPPED") == 1
    stored = db.execute(select(SignalWindow)).scalar_one()
    assert stored.signal_payload is not None
    assert stored.sample_count == 256


def test_sensor_invalid_window_is_persisted_without_payload(client, db):
    headers, pump, sensor = _setup_equipment(client)
    session = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor, scenario="sensor_disconnect"),
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json=_window_payload(quality="SENSOR_INVALID"),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["quality_status"] == "SENSOR_INVALID"
    assert response.json()["sample_count"] == 0

    stored = db.execute(select(SignalWindow)).scalar_one()
    assert stored.signal_payload is None
    assert stored.validation_summary["issues"][0]["code"] == "sensor_disconnected"


def test_invalid_window_payload_rules(client):
    headers, pump, sensor = _setup_equipment(client)
    session = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor),
        headers=headers,
    ).json()
    url = f"/api/v1/acquisition-sessions/{session['id']}/windows"

    empty_valid = client.post(url, json=_window_payload(samples=[]), headers=headers)
    assert empty_valid.status_code == 422
    assert empty_valid.json()["error"]["code"] == "INVALID_WINDOW_PAYLOAD"

    invalid_with_samples = client.post(
        url,
        json=_window_payload(quality="SENSOR_INVALID", samples=[0.1, 0.2]),
        headers=headers,
    )
    assert invalid_with_samples.status_code == 422

    missing_summary = client.post(
        url,
        json=_window_payload(quality="SENSOR_INVALID", validation_summary=None),
        headers=headers,
    )
    assert missing_summary.status_code == 422
    assert missing_summary.json()["error"]["code"] == "VALIDATION_SUMMARY_REQUIRED"

    mismatch = client.post(
        url,
        json=_window_payload(window_end="2026-11-16T12:00:10+00:00"),
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "WINDOW_TIMESTAMP_MISMATCH"


def test_duplicate_window_index_is_rejected(client):
    headers, pump, sensor = _setup_equipment(client)
    session = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor),
        headers=headers,
    ).json()
    url = f"/api/v1/acquisition-sessions/{session['id']}/windows"

    assert client.post(url, json=_window_payload(), headers=headers).status_code == 201
    duplicate = client.post(url, json=_window_payload(), headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "WINDOW_EXISTS"


def test_session_guards_and_rbac(client):
    headers, pump, sensor = _setup_equipment(client)
    researcher = auth_headers(client, "researcher")
    reviewer = auth_headers(client, "reviewer")

    provenance = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor, data_provenance="EXPERIMENTAL"),
        headers=headers,
    )
    assert provenance.status_code == 422
    assert provenance.json()["error"]["code"] == "EXPERIMENTAL_ACQUISITION_UNAVAILABLE"

    mismatch = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor, sampling_rate_hz=1024),
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "SAMPLING_RATE_MISMATCH"

    forbidden = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor),
        headers=reviewer,
    )
    assert forbidden.status_code == 403

    allowed = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(pump, sensor, scenario="researcher-run"),
        headers=researcher,
    )
    assert allowed.status_code == 201
    assert allowed.json()["started_by_name"] == "Fatima Yusuf"

    listed = client.get(
        "/api/v1/acquisition-sessions?provenance=SIMULATED", headers=reviewer
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_sensor_must_belong_to_session_pump(client):
    headers, _pump, sensor = _setup_equipment(client)
    other_pump = client.post(
        "/api/v1/pumps",
        json={
            **PUMP_PAYLOAD,
            "pump_code": "LAB-PUMP-02",
            "sensor": {**PUMP_PAYLOAD["sensor"], "sensor_code": "VIB-02"},
        },
        headers=headers,
    ).json()

    response = client.post(
        "/api/v1/acquisition-sessions",
        json=_session_payload(other_pump, sensor),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SENSOR_PUMP_MISMATCH"
