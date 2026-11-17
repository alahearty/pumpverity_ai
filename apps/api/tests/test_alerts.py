from datetime import UTC, datetime, timedelta

from app.db.models import AuditLog, ConfigurationSetting
from sqlalchemy import select
from tests.conftest import auth_headers
from tests.test_predictions import (
    _active_model,
    _prediction_payload,
    _setup_equipment_and_window,
)


def _create_fault_prediction(client, event_id="alert-event-001"):
    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code=f"alert-{event_id}")
    response = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump, sensor, session, window, model, event_id=event_id
        ),
        headers=engineer,
    )
    assert response.status_code == 201, response.text
    return engineer, pump, sensor, session, window, model, response.json()


def test_fault_prediction_creates_one_alert_with_prediction_provenance(client):
    engineer, pump, sensor, session, window, model, prediction = (
        _create_fault_prediction(client)
    )

    listed = client.get(f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] == 1
    alert = body["items"][0]
    assert alert["status"] == "OPEN"
    assert alert["category"] == "FAULT"
    assert alert["severity"] == "HIGH"
    assert alert["prediction_id"] == prediction["id"]
    assert alert["decision"] == "FAULT"
    assert alert["model_name"] == model["name"]
    assert alert["model_version"] == "0.1.0"
    assert alert["data_provenance"] == "SIMULATED"
    assert alert["review_count"] == 0

    detail = client.get(f"/api/v1/alerts/{alert['id']}", headers=engineer).json()
    assert detail["prediction"]["id"] == prediction["id"]
    assert detail["prediction"]["decision"] == "FAULT"
    assert detail["reviews"] == []

    duplicate_event = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump,
            sensor,
            session,
            window,
            model,
            event_id="alert-event-001",
            decision="NORMAL",
        ),
        headers=engineer,
    )
    assert duplicate_event.status_code == 409

    no_alert = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump,
            sensor,
            session,
            window,
            model,
            event_id="alert-event-normal",
            decision="NORMAL",
        ),
        headers=engineer,
    )
    assert no_alert.status_code == 201, no_alert.text
    listed_again = client.get(
        f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer
    ).json()
    assert listed_again["total"] == 1

    uncertain = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump,
            sensor,
            session,
            window,
            model,
            event_id="alert-event-uncertain",
            decision="UNCERTAIN",
            decision_score=0.4,
            uncertainty_score=0.6,
        ),
        headers=engineer,
    )
    assert uncertain.status_code == 201, uncertain.text
    with_uncertain = client.get(
        f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer
    ).json()
    assert with_uncertain["total"] == 2
    uncertain_alert = next(
        item
        for item in with_uncertain["items"]
        if item["prediction_id"] == uncertain.json()["id"]
    )
    assert uncertain_alert["category"] == "UNCERTAIN"
    assert uncertain_alert["severity"] == "MEDIUM"
    assert uncertain_alert["status"] == "OPEN"


def test_acknowledge_review_correct_and_close_alert(client, db):
    engineer, pump, _sensor, _session, _window, _model, prediction = (
        _create_fault_prediction(client, event_id="alert-workflow-001")
    )
    reviewer = auth_headers(client, "reviewer")
    alert = client.get(
        f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer
    ).json()["items"][0]

    acknowledged = client.post(
        f"/api/v1/alerts/{alert['id']}/acknowledge", headers=reviewer
    )
    assert acknowledged.status_code == 200, acknowledged.text
    body = acknowledged.json()
    assert body["status"] == "ACKNOWLEDGED"
    assert body["assigned_reviewer_name"]
    assert body["acknowledged_at"] is not None
    assert body["review_count"] == 1
    assert body["reviews"][0]["action"] == "ACKNOWLEDGE"

    idempotent = client.post(
        f"/api/v1/alerts/{alert['id']}/acknowledge", headers=reviewer
    )
    assert idempotent.status_code == 200
    assert idempotent.json()["review_count"] == 1

    confirmed = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "CONFIRM_LABEL",
            "reviewed_label": "FAULT",
            "notes": "Fault signature confirmed by engineer.",
        },
        headers=engineer,
    )
    assert confirmed.status_code == 200, confirmed.text
    review = confirmed.json()
    assert review["action"] == "CONFIRM_LABEL"
    assert review["label_source"] == "ENGINEER_REVIEW"
    assert review["is_verified_ground_truth"] is False
    assert review["reviewed_label"] == "FAULT"

    detail = client.get(
        f"/api/v1/alerts/{alert['id']}", headers=engineer
    ).json()
    assert detail["status"] == "REVIEWED"
    assert detail["review_count"] == 2
    assert detail["prediction"]["decision"] == prediction["decision"] == "FAULT"

    corrected = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "CORRECT_LABEL",
            "reviewed_label": "UNCERTAIN",
            "notes": "Evidence is inconclusive after inspection.",
        },
        headers=engineer,
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["reviewed_label"] == "UNCERTAIN"
    assert corrected.json()["is_verified_ground_truth"] is False

    reviews = client.get(
        f"/api/v1/alerts/{alert['id']}/reviews", headers=engineer
    ).json()
    assert [review["action"] for review in reviews] == [
        "ACKNOWLEDGE",
        "CONFIRM_LABEL",
        "CORRECT_LABEL",
    ]
    assert all(review["label_source"] == "ENGINEER_REVIEW" for review in reviews)
    assert not any(review["is_verified_ground_truth"] for review in reviews)

    note = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "ADD_NOTE",
            "notes": "Follow-up inspection scheduled.",
        },
        headers=reviewer,
    )
    assert note.status_code == 200, note.text
    assert note.json()["action"] == "ADD_NOTE"

    closed = client.post(
        "/api/v1/alert-reviews",
        json={"alert_id": alert["id"], "action": "CLOSE"},
        headers=engineer,
    )
    assert closed.status_code == 200, closed.text
    closed_alert = client.get(
        f"/api/v1/alerts/{alert['id']}", headers=engineer
    ).json()
    assert closed_alert["status"] == "CLOSED"
    assert closed_alert["closed_at"] is not None

    reopened = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "REVIEW",
            "notes": "Attempt after closure.",
        },
        headers=engineer,
    )
    assert reopened.status_code == 409
    assert reopened.json()["error"]["code"] == "ALERT_CLOSED"

    actions = (
        db.execute(select(AuditLog.action).where(AuditLog.entity_id == alert["id"]))
        .scalars()
        .all()
    )
    assert "ALERT_CREATED" in actions
    assert "ALERT_ACKNOWLEDGED" in actions
    assert "ALERT_REVIEWED" in actions
    assert "ALERT_CLOSED" in actions


def test_alert_validation_permissions_and_filters(client):
    engineer, pump, _sensor, _session, _window, _model, _prediction = (
        _create_fault_prediction(client, event_id="alert-guards-001")
    )
    reviewer = auth_headers(client, "reviewer")
    researcher = auth_headers(client, "researcher")
    alert = client.get(
        f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer
    ).json()["items"][0]

    assert client.get("/api/v1/alerts", headers=researcher).status_code == 200
    denied = client.post(
        f"/api/v1/alerts/{alert['id']}/acknowledge", headers=researcher
    )
    assert denied.status_code == 403

    mismatch = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "CONFIRM_LABEL",
            "reviewed_label": "NORMAL",
        },
        headers=engineer,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "LABEL_MISMATCH"

    missing_notes = client.post(
        "/api/v1/alert-reviews",
        json={"alert_id": alert["id"], "action": "REVIEW", "notes": " "},
        headers=engineer,
    )
    assert missing_notes.status_code == 422

    same_correction = client.post(
        "/api/v1/alert-reviews",
        json={
            "alert_id": alert["id"],
            "action": "CORRECT_LABEL",
            "reviewed_label": "FAULT",
        },
        headers=engineer,
    )
    assert same_correction.status_code == 422
    assert same_correction.json()["error"]["code"] == "LABEL_NOT_CORRECTED"

    unlabelled = client.post(
        "/api/v1/alert-reviews",
        json={"alert_id": alert["id"], "action": "CONFIRM_LABEL"},
        headers=engineer,
    )
    assert unlabelled.status_code == 422

    assert (
        client.get(
            f"/api/v1/alerts?status=ACKNOWLEDGED&pump_id={pump['id']}",
            headers=engineer,
        ).json()["total"]
        == 0
    )
    reviewer_ack = client.post(
        f"/api/v1/alerts/{alert['id']}/acknowledge", headers=reviewer
    )
    assert reviewer_ack.status_code == 200
    assert (
        client.get(
            f"/api/v1/alerts?status=ACKNOWLEDGED&pump_id={pump['id']}",
            headers=engineer,
        ).json()["total"]
        == 1
    )
    assert (
        client.get(
            f"/api/v1/alerts?severity=LOW&pump_id={pump['id']}",
            headers=engineer,
        ).json()["total"]
        == 0
    )
    assert (
        client.get(
            f"/api/v1/alerts?category=SENSOR_INVALID&pump_id={pump['id']}",
            headers=engineer,
        ).json()["total"]
        == 0
    )


def test_sensor_invalid_prediction_creates_sensor_alert_without_model(client):
    engineer, pump, sensor, session, _window, _model, _prediction = (
        _create_fault_prediction(client, event_id="alert-invalid-001")
    )

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
    )
    assert invalid_window.status_code == 201, invalid_window.text
    invalid_prediction = client.post(
        "/api/v1/predictions",
        json={
            "event_id": "alert-invalid-event-001",
            "pump_id": pump["id"],
            "sensor_id": sensor["id"],
            "session_id": session["id"],
            "signal_window_id": invalid_window.json()["id"],
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

    alerts = client.get(
        f"/api/v1/alerts?category=SENSOR_INVALID&pump_id={pump['id']}",
        headers=engineer,
    ).json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "HIGH"
    assert alert["decision"] == "SENSOR_INVALID"
    assert alert["model_name"] is None
    assert alert["prediction_id"] == invalid_prediction.json()["id"]


def test_auto_alert_creation_can_be_disabled_by_setting(client, db):
    setting = db.execute(
        select(ConfigurationSetting).where(
            ConfigurationSetting.key == "alerts.auto_create_for_fault"
        )
    ).scalar_one()
    setting.value = False
    db.commit()

    engineer, pump, sensor, session, window = _setup_equipment_and_window(client)
    model = _active_model(client, code="alert-disabled")
    response = client.post(
        "/api/v1/predictions",
        json=_prediction_payload(
            pump,
            sensor,
            session,
            window,
            model,
            event_id="alert-disabled-event",
        ),
        headers=engineer,
    )
    assert response.status_code == 201, response.text
    alerts = client.get(
        f"/api/v1/alerts?pump_id={pump['id']}", headers=engineer
    ).json()
    assert alerts["total"] == 0

