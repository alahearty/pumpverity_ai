import pytest
from app.core.config import get_settings
from app.db.models import AuditLog
from sqlalchemy import select
from tests.conftest import auth_headers
from tests.test_acquisition import _window_payload
from tests.test_predictions import (
    _active_model,
    _prediction_payload,
    _setup_equipment_and_window,
)


@pytest.fixture()
def demo_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_mode", True)


def test_demo_control_is_hidden_and_locked_when_disabled(client):
    engineer = auth_headers(client, "engineer")
    state = client.get("/api/v1/demo/control", headers=engineer)
    assert state.status_code == 200
    assert state.json()["enabled"] is False
    assert state.json()["presets"] == []

    blocked = client.put("/api/v1/demo/control", json={"preset": "imbalance"}, headers=engineer)
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "DEMO_MODE_DISABLED"


def test_demo_control_requires_authentication(client):
    assert client.get("/api/v1/demo/control").status_code == 401


def test_engineer_changes_preset_with_audit_and_driver_heartbeat(client, db, demo_mode):
    engineer = auth_headers(client, "engineer")
    initial = client.get("/api/v1/demo/control", headers=engineer).json()
    assert initial["enabled"] is True
    assert {preset["expected_outcome"] for preset in initial["presets"]} == {
        "NORMAL",
        "FAULT",
        "UNCERTAIN",
        "SENSOR_INVALID",
    }
    assert initial["driver_online"] is False

    changed = client.put(
        "/api/v1/demo/control", json={"preset": "imbalance"}, headers=engineer
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["preset"] == "imbalance"
    assert changed.json()["updated_by"] == "engineer@petrosense.local"

    audit = db.execute(
        select(AuditLog).where(AuditLog.action == "DEMO_SCENARIO_CHANGED")
    ).scalars().all()
    assert audit and audit[-1].after["preset"] == "imbalance"

    beat = client.post(
        "/api/v1/demo/heartbeat",
        json={"preset": "imbalance", "windows_streamed": 3, "last_decision": "FAULT"},
        headers=engineer,
    )
    assert beat.status_code == 200
    assert beat.json()["driver_online"] is True
    assert beat.json()["driver"]["last_decision"] == "FAULT"

    unknown = client.put("/api/v1/demo/control", json={"preset": "explode"}, headers=engineer)
    assert unknown.status_code == 422

    client.put("/api/v1/demo/control", json={"preset": "normal"}, headers=engineer)


def test_reviewer_cannot_change_demo_scenario(client, demo_mode):
    reviewer = auth_headers(client, "reviewer")
    response = client.put("/api/v1/demo/control", json={"preset": "cavitation"}, headers=reviewer)
    assert response.status_code == 403


def _two_fault_predictions(client):
    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code="dedup-model")
    second_window = client.post(
        f"/api/v1/acquisition-sessions/{session['id']}/windows",
        json=_window_payload(index=1, features={"rms": 0.035, "peak_abs": 0.05}),
        headers=engineer,
    )
    assert second_window.status_code == 201, second_window.text
    for event_id, target in (("dedup-event-1", window), ("dedup-event-2", second_window.json())):
        response = client.post(
            "/api/v1/predictions",
            json=_prediction_payload(pump, sensor, session, target, model, event_id=event_id),
            headers=engineer,
        )
        assert response.status_code == 201, response.text
    alerts = client.get(f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer).json()
    return alerts["total"]


def test_alerts_are_one_per_prediction_by_default(client):
    assert _two_fault_predictions(client) == 2


def test_alert_dedup_keeps_one_open_alert_per_session(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "alert_dedup_per_session", True)
    assert _two_fault_predictions(client) == 1
