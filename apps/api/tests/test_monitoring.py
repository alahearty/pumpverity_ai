import math
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models import SignalWindow
from sqlalchemy import select
from tests.conftest import auth_headers


def _setup_equipment(client):
    headers = auth_headers(client, "engineer")
    pump = client.post(
        "/api/v1/pumps",
        json={
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
        },
        headers=headers,
    ).json()
    return headers, pump, pump["sensors"][0]


def _create_session(client, headers, pump, sensor, scenario="normal"):
    response = client.post(
        "/api/v1/acquisition-sessions",
        json={
            "pump_id": pump["id"],
            "sensor_id": sensor["id"],
            "sampling_rate_hz": 2048,
            "data_provenance": "SIMULATED",
            "random_seed": 42,
            "scenario": scenario,
            "source_device_id": "monitoring-test",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _window_payload(index, quality="VALID"):
    start = datetime(2026, 11, 16, 12, 0, tzinfo=UTC) + timedelta(seconds=index * 2)
    sample_count = 2048
    end = start + timedelta(seconds=sample_count / 2048)
    samples = (
        [
            math.sin(2 * math.pi * 48.3 * i / 2048) * 0.05
            for i in range(sample_count)
        ]
        if quality == "VALID"
        else []
    )
    return {
        "window_index": index,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "samples": samples,
        "quality_status": quality,
        "validation_summary": (
            {
                "issues": [{"code": "sensor_disconnected", "message": "Disconnected"}],
                "metrics": {"sample_count": 0, "units": "g"},
            }
            if quality == "SENSOR_INVALID"
            else {
                "metrics": {
                    "rms": 0.035,
                    "peak_abs": 0.05,
                    "units": "g",
                    "sample_count": sample_count,
                },
                "issues": [],
            }
        ),
    }


def _ingest(client, headers, session_id, payload):
    response = client.post(
        f"/api/v1/acquisition-sessions/{session_id}/windows",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_live_snapshot_empty_and_overview(client):
    headers, pump, _sensor = _setup_equipment(client)

    live = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}", headers=headers
    )
    assert live.status_code == 200, live.text
    body = live.json()
    assert body["latest_window"] is None
    assert body["recent_windows"] == []
    assert body["equipment_condition"] is None
    assert body["condition_available"] is False
    assert body["data_quality"] is None
    assert body["edge_connectivity"] is None
    assert body["data_mode"] == "NO_DATA"
    assert body["sensor_health"]["sampling_status"] == "NO_DATA"
    assert body["sensor_health"]["connection_state"] == "NO_LIVE_CHANNEL"

    health = client.get("/api/v1/sensors/health", headers=headers)
    assert health.status_code == 200
    assert health.json()[0]["sensor_code"] == "VIB-01"
    assert health.json()[0]["total_windows"] == 0

    overview = client.get("/api/v1/monitoring/overview", headers=headers)
    assert overview.status_code == 200
    summary = overview.json()
    assert summary["pumps_total"] == 1
    assert summary["sensors_total"] == 1
    assert summary["windows_total"] == 0
    assert summary["equipment_condition"] is None
    assert summary["condition_available"] is False
    assert summary["active_model"] is None
    assert summary["latest_evaluation"] is None
    assert summary["active_alerts"] == 0


def test_live_snapshot_after_valid_and_invalid_windows(client):
    headers, pump, sensor = _setup_equipment(client)
    session = _create_session(client, headers, pump, sensor)
    _ingest(client, headers, session["id"], _window_payload(0))
    _ingest(client, headers, session["id"], _window_payload(1))
    _ingest(client, headers, session["id"], _window_payload(2, "SENSOR_INVALID"))

    live = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}&sensor_id={sensor['id']}&limit=10",
        headers=headers,
    )
    assert live.status_code == 200, live.text
    body = live.json()
    assert body["latest_window"]["quality_status"] == "SENSOR_INVALID"
    assert body["latest_window"]["waveform"] is None
    assert body["latest_window"]["validation_issue_codes"] == ["sensor_disconnected"]
    assert len(body["recent_windows"]) == 3
    assert body["recent_windows"][0]["rms"] == pytest.approx(0.035)
    assert body["recent_windows"][2]["rms"] is None
    assert body["data_quality"] == "SENSOR_INVALID"
    assert body["condition_available"] is False
    assert body["data_mode"] == "SIMULATED_REPLAY"

    health = body["sensor_health"]
    assert health["total_windows"] == 3
    assert health["valid_windows"] == 2
    assert health["invalid_windows"] == 1
    assert health["sampling_status"] == "SENSOR_INVALID"
    assert health["last_valid_reading_at"] is not None
    assert health["latest_validation_issues"][0]["code"] == "sensor_disconnected"

    overview = client.get("/api/v1/monitoring/overview", headers=headers).json()
    assert overview["windows_total"] == 3
    assert overview["valid_windows"] == 2
    assert overview["invalid_windows"] == 1
    assert overview["latest_window"]["quality_status"] == "SENSOR_INVALID"
    assert len(overview["trend"]) == 3
    assert overview["sensors_invalid"] == 1
    assert overview["data_quality"] == "SENSOR_INVALID"


def test_valid_waveform_is_bounded_and_preserves_metrics(client):
    headers, pump, sensor = _setup_equipment(client)
    session = _create_session(client, headers, pump, sensor)
    _ingest(client, headers, session["id"], _window_payload(0))

    live = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}", headers=headers
    ).json()
    latest = live["latest_window"]
    assert latest["quality_status"] == "VALID"
    assert latest["sample_count"] == 2048
    assert 0 < len(latest["waveform"]) <= 512
    assert latest["units"] == "g"
    assert latest["rms"] == pytest.approx(0.035)
    assert live["sensor_health"]["sampling_status"] == "RECENT"


def test_sensor_health_missing_gaps_stale_and_pump_filter(client, db):
    headers, pump, sensor = _setup_equipment(client)
    session = _create_session(client, headers, pump, sensor)
    _ingest(client, headers, session["id"], _window_payload(0))
    _ingest(client, headers, session["id"], _window_payload(2))

    health = client.get(
        f"/api/v1/sensors/health?pump_id={pump['id']}", headers=headers
    ).json()[0]
    assert health["missing_window_gaps"] == 1

    old = datetime.now(UTC) - timedelta(seconds=600)
    for window in db.execute(select(SignalWindow)).scalars().all():
        window.created_at = old
    db.commit()

    stale = client.get("/api/v1/sensors/health", headers=headers).json()[0]
    assert stale["sampling_status"] == "STALE"
    assert stale["freshness_seconds"] > 300


def test_monitoring_auth_and_sensor_guards(client):
    headers, pump, _sensor = _setup_equipment(client)
    assert (
        client.get(f"/api/v1/monitoring/live?pump_id={pump['id']}").status_code == 401
    )
    unknown = client.get(
        "/api/v1/monitoring/live?pump_id=00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert unknown.status_code == 404

    other_pump = client.post(
        "/api/v1/pumps",
        json={
            "pump_code": "LAB-PUMP-02",
            "name": "Second Pump",
            "pump_type": "CENTRIFUGAL",
            "location": "Laboratory",
            "rated_speed_rpm": 2900,
            "sensor": {
                "sensor_code": "VIB-02",
                "sensor_type": "VIBRATION",
                "mounting_axis": "RADIAL_X",
                "mounting_position": "Bearing housing",
                "sampling_rate_hz": 2048,
            },
        },
        headers=headers,
    ).json()
    mismatch = client.get(
        f"/api/v1/monitoring/live?pump_id={pump['id']}&sensor_id={other_pump['sensors'][0]['id']}",
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "SENSOR_PUMP_MISMATCH"


def test_sse_authentication_and_heartbeat(client):
    headers, pump, _sensor = _setup_equipment(client)
    assert (
        client.get(f"/api/v1/monitoring/stream?pump_id={pump['id']}").status_code == 401
    )

    with client.stream(
        "GET",
        f"/api/v1/monitoring/stream?pump_id={pump['id']}&max_events=1",
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = []
        for line in response.iter_lines():
            lines.append(line)
            if line == "":
                break
    assert "event: heartbeat" in lines
    assert any('"status":"connected"' in line for line in lines)
