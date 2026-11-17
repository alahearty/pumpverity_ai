from app.db.models import AuditLog, Pump, Sensor
from sqlalchemy import select
from tests.conftest import auth_headers

PUMP_PAYLOAD = {
    "pump_code": "LAB-PUMP-01",
    "name": "Laboratory Centrifugal Pump",
    "pump_type": "CENTRIFUGAL",
    "location": "Thermofluids Laboratory",
    "rated_speed_rpm": 2900,
    "status": "ACTIVE",
    "notes": "Initial research rig registration.",
    "sensor": {
        "sensor_code": "VIB-01",
        "sensor_type": "VIBRATION",
        "manufacturer": "Research Instruments",
        "model_name": "ACC-100",
        "mounting_axis": "RADIAL_X",
        "mounting_position": "Drive-end bearing housing",
        "sampling_rate_hz": 2048,
        "is_active": True,
    },
}


def _create_pump(client, headers, **overrides):
    payload = {
        **PUMP_PAYLOAD,
        **overrides,
        "sensor": {**PUMP_PAYLOAD["sensor"], **overrides.get("sensor", {})},
    }
    return client.post("/api/v1/pumps", json=payload, headers=headers)


def test_engineer_registers_pump_with_sensor(client, db):
    headers = auth_headers(client, "engineer@petrosense.local")
    response = _create_pump(client, headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pump_code"] == "LAB-PUMP-01"
    assert body["rated_speed_rpm"] == 2900
    assert body["status"] == "ACTIVE"
    assert body["default_regime"] is None
    assert len(body["sensors"]) == 1
    assert body["sensors"][0]["sensor_code"] == "VIB-01"
    assert body["sensors"][0]["pump_code"] == "LAB-PUMP-01"

    list_response = client.get("/api/v1/pumps", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/v1/pumps/{body['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Laboratory Centrifugal Pump"

    db.expire_all()
    actions = db.execute(select(AuditLog.action).order_by(AuditLog.id)).scalars().all()
    assert "PUMP_CREATED" in actions
    assert "SENSOR_CREATED" in actions


def test_pump_codes_are_normalised_and_duplicates_rejected(client):
    headers = auth_headers(client, "engineer")
    payload = {
        **PUMP_PAYLOAD,
        "pump_code": " lab-pump-01 ",
        "sensor": {**PUMP_PAYLOAD["sensor"], "sensor_code": " vib-01 "},
    }
    response = client.post("/api/v1/pumps", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["pump_code"] == "LAB-PUMP-01"
    assert response.json()["sensors"][0]["sensor_code"] == "VIB-01"

    duplicate_pump = _create_pump(client, headers, pump_code="LAB-PUMP-01")
    assert duplicate_pump.status_code == 409
    assert duplicate_pump.json()["error"]["code"] == "PUMP_CODE_EXISTS"


def test_duplicate_nested_sensor_rolls_back_pump(client, db):
    headers = auth_headers(client, "engineer")
    _create_pump(client, headers)

    response = _create_pump(
        client,
        headers,
        pump_code="LAB-PUMP-02",
        name="Second Pump",
        sensor={"sensor_code": "VIB-01"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SENSOR_CODE_EXISTS"

    pumps = db.execute(select(Pump)).scalars().all()
    sensors = db.execute(select(Sensor)).scalars().all()
    assert len(pumps) == 1
    assert len(sensors) == 1


def test_pump_validation_rejects_invalid_fields(client):
    headers = auth_headers(client, "engineer")
    zero_speed = _create_pump(client, headers, rated_speed_rpm=0)
    assert zero_speed.status_code == 422
    assert zero_speed.json()["error"]["code"] == "VALIDATION_ERROR"

    bad_code = _create_pump(client, headers, pump_code="bad code!")
    assert bad_code.status_code == 422

    blank_name = _create_pump(client, headers, name="   ")
    assert blank_name.status_code == 422


def test_pump_write_requires_engineer_role(client):
    researcher_headers = auth_headers(client, "researcher")
    response = _create_pump(client, researcher_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    assert client.get("/api/v1/pumps", headers=researcher_headers).status_code == 200
    assert client.get("/api/v1/pumps").status_code == 401


def test_update_pump_and_operating_regime(client, db):
    headers = auth_headers(client, "engineer")
    created = _create_pump(client, headers).json()

    regimes = client.get("/api/v1/operating-regimes", headers=headers).json()
    steady = next(item for item in regimes if item["code"] == "STEADY_STATE")

    response = client.patch(
        f"/api/v1/pumps/{created['id']}",
        json={
            "name": "Laboratory Pump A",
            "status": "MAINTENANCE",
            "rated_speed_rpm": 2950,
            "default_regime_id": steady["id"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Laboratory Pump A"
    assert body["status"] == "MAINTENANCE"
    assert body["rated_speed_rpm"] == 2950
    assert body["default_regime"]["code"] == "STEADY_STATE"

    db.expire_all()
    audit = db.execute(
        select(AuditLog).where(AuditLog.action == "PUMP_UPDATED")
    ).scalar_one()
    assert audit.before["name"] == "Laboratory Centrifugal Pump"
    assert audit.after["name"] == "Laboratory Pump A"


def test_sensor_registration_assignment_and_update(client):
    engineer = auth_headers(client, "engineer")
    pump = _create_pump(client, engineer).json()

    second_pump = _create_pump(
        client,
        engineer,
        pump_code="LAB-PUMP-02",
        name="Second Pump",
        sensor={"sensor_code": "VIB-02"},
    ).json()

    sensor_response = client.post(
        "/api/v1/sensors",
        json={
            "sensor_code": "TEMP-01",
            "pump_id": pump["id"],
            "sensor_type": "TEMPERATURE",
            "mounting_position": "Pump casing",
            "mounting_axis": "UNKNOWN",
            "sampling_rate_hz": 10,
        },
        headers=engineer,
    )
    assert sensor_response.status_code == 201, sensor_response.text
    sensor = sensor_response.json()
    assert sensor["pump_code"] == "LAB-PUMP-01"

    listed = client.get(
        f"/api/v1/sensors?pump_id={pump['id']}", headers=engineer
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    reassigned = client.patch(
        f"/api/v1/sensors/{sensor['id']}",
        json={"pump_id": second_pump["id"], "is_active": False},
        headers=engineer,
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["pump_code"] == "LAB-PUMP-02"
    assert reassigned.json()["is_active"] is False

    duplicate = client.post(
        "/api/v1/sensors",
        json={
            "sensor_code": "TEMP-01",
            "sensor_type": "TEMPERATURE",
            "mounting_position": "Duplicate",
            "sampling_rate_hz": 10,
        },
        headers=engineer,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SENSOR_CODE_EXISTS"


def test_operating_regimes_require_authentication(client):
    assert client.get("/api/v1/operating-regimes").status_code == 401
    headers = auth_headers(client, "reviewer")
    response = client.get("/api/v1/operating-regimes", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 5
