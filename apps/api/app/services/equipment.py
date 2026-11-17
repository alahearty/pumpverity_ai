from typing import Any

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import ApiError
from app.db.models import OperatingRegime, Pump, Sensor, User
from app.domain.enums import MountingAxis, PumpStatus, PumpType, SensorType
from app.schemas.equipment import (
    PumpCreate,
    PumpUpdate,
    SensorRegister,
    SensorUpdate,
    sensor_values,
)
from app.services.audit import record_audit


def _pump_options():
    return (
        selectinload(Pump.sensors),
        joinedload(Pump.default_regime),
        joinedload(Pump.created_by),
    )


def _sensor_options():
    return (joinedload(Sensor.pump),)


def _pump_statement():
    return select(Pump).options(*_pump_options())


def _sensor_statement():
    return select(Sensor).options(*_sensor_options())


def get_pump_or_404(db: Session, pump_id: str) -> Pump:
    pump = db.execute(_pump_statement().where(Pump.id == pump_id)).scalar_one_or_none()
    if pump is None:
        raise ApiError(status_code=404, code="PUMP_NOT_FOUND", message="Pump not found.")
    return pump


def get_sensor_or_404(db: Session, sensor_id: str) -> Sensor:
    sensor = db.execute(_sensor_statement().where(Sensor.id == sensor_id)).scalar_one_or_none()
    if sensor is None:
        raise ApiError(status_code=404, code="SENSOR_NOT_FOUND", message="Sensor not found.")
    return sensor


def get_operating_regime_or_422(db: Session, regime_id: str | None) -> OperatingRegime | None:
    if regime_id is None:
        return None
    regime = db.get(OperatingRegime, regime_id)
    if regime is None or not regime.is_active:
        raise ApiError(
            status_code=422,
            code="INVALID_OPERATING_REGIME",
            message="The selected operating regime is not available.",
        )
    return regime


def list_pumps(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    status: str | None = None,
    pump_type: str | None = None,
) -> tuple[list[Pump], int]:
    filters = []
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Pump.pump_code.ilike(pattern),
                Pump.name.ilike(pattern),
                Pump.location.ilike(pattern),
            )
        )
    if status is not None:
        filters.append(Pump.status == status)
    if pump_type is not None:
        filters.append(Pump.pump_type == pump_type)

    count_stmt = select(func.count(Pump.id))
    list_stmt = _pump_statement()
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = db.execute(count_stmt).scalar_one()
    pumps = (
        db.execute(
            list_stmt.order_by(Pump.registered_at.desc(), Pump.pump_code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(pumps), total


def list_sensors(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    pump_id: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Sensor], int]:
    filters = []
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Sensor.sensor_code.ilike(pattern),
                Sensor.mounting_position.ilike(pattern),
                Sensor.manufacturer.ilike(pattern),
                Sensor.model_name.ilike(pattern),
            )
        )
    if pump_id is not None:
        filters.append(Sensor.pump_id == pump_id)
    if is_active is not None:
        filters.append(Sensor.is_active == is_active)

    count_stmt = select(func.count(Sensor.id))
    list_stmt = _sensor_statement()
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = db.execute(count_stmt).scalar_one()
    sensors = (
        db.execute(
            list_stmt.order_by(Sensor.sensor_code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(sensors), total


def list_operating_regimes(db: Session) -> list[OperatingRegime]:
    return list(
        db.execute(select(OperatingRegime).order_by(OperatingRegime.code.asc())).scalars().all()
    )


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _snapshot_pump(pump: Pump) -> dict[str, Any]:
    return {
        "pump_code": pump.pump_code,
        "name": pump.name,
        "pump_type": _enum_value(pump.pump_type),
        "location": pump.location,
        "rated_speed_rpm": pump.rated_speed_rpm,
        "default_regime_id": pump.default_regime_id,
        "status": _enum_value(pump.status),
        "notes": pump.notes,
    }


def _snapshot_sensor(sensor: Sensor) -> dict[str, Any]:
    return {
        "sensor_code": sensor.sensor_code,
        "pump_id": sensor.pump_id,
        "sensor_type": _enum_value(sensor.sensor_type),
        "manufacturer": sensor.manufacturer,
        "model_name": sensor.model_name,
        "mounting_axis": _enum_value(sensor.mounting_axis),
        "mounting_position": sensor.mounting_position,
        "sampling_rate_hz": sensor.sampling_rate_hz,
        "is_active": sensor.is_active,
        "installed_at": sensor.installed_at.isoformat() if sensor.installed_at else None,
    }


def _pump_code_exists(db: Session, pump_code: str) -> bool:
    return db.execute(select(Pump.id).where(Pump.pump_code == pump_code)).first() is not None


def _sensor_code_exists(db: Session, sensor_code: str) -> bool:
    return (
        db.execute(select(Sensor.id).where(Sensor.sensor_code == sensor_code)).first()
        is not None
    )


def _commit_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(status_code=409, code="EQUIPMENT_CONFLICT", message=message) from exc


def create_pump(db: Session, payload: PumpCreate, actor: User, request: Request) -> Pump:
    if _pump_code_exists(db, payload.pump_code):
        raise ApiError(
            status_code=409,
            code="PUMP_CODE_EXISTS",
            message="A pump with this code already exists.",
        )
    if payload.sensor is not None and _sensor_code_exists(db, payload.sensor.sensor_code):
        raise ApiError(
            status_code=409,
            code="SENSOR_CODE_EXISTS",
            message="A sensor with this code already exists.",
        )
    get_operating_regime_or_422(db, payload.default_regime_id)

    pump = Pump(
        pump_code=payload.pump_code,
        name=payload.name,
        pump_type=payload.pump_type,
        location=payload.location,
        rated_speed_rpm=payload.rated_speed_rpm,
        default_regime_id=payload.default_regime_id,
        status=payload.status,
        notes=payload.notes or None,
        created_by_id=actor.id,
    )
    db.add(pump)

    sensor = None
    if payload.sensor is not None:
        sensor = Sensor(pump=pump, **sensor_values(payload.sensor))
        db.add(sensor)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="EQUIPMENT_CONFLICT",
            message="The pump or sensor identifier is already in use.",
        ) from exc

    record_audit(
        db,
        action="PUMP_CREATED",
        actor=actor,
        entity_type="pump",
        entity_id=pump.id,
        after=_snapshot_pump(pump),
        request=request,
    )
    if sensor is not None:
        record_audit(
            db,
            action="SENSOR_CREATED",
            actor=actor,
            entity_type="sensor",
            entity_id=sensor.id,
            after=_snapshot_sensor(sensor),
            request=request,
        )

    _commit_or_conflict(db, "The pump or sensor identifier is already in use.")
    return get_pump_or_404(db, pump.id)


def update_pump(
    db: Session, pump_id: str, payload: PumpUpdate, actor: User, request: Request
) -> Pump:
    pump = get_pump_or_404(db, pump_id)
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return pump
    if values.get("pump_type") is not None:
        values["pump_type"] = PumpType(values["pump_type"])
    if values.get("status") is not None:
        values["status"] = PumpStatus(values["status"])
    if "default_regime_id" in values:
        pump.default_regime = get_operating_regime_or_422(db, values["default_regime_id"])
        values.pop("default_regime_id")

    before = _snapshot_pump(pump)
    for field, value in values.items():
        setattr(pump, field, value.strip() if isinstance(value, str) else value)
    db.flush()

    record_audit(
        db,
        action="PUMP_UPDATED",
        actor=actor,
        entity_type="pump",
        entity_id=pump.id,
        before=before,
        after=_snapshot_pump(pump),
        request=request,
    )
    db.commit()
    return get_pump_or_404(db, pump.id)


def create_sensor(
    db: Session, payload: SensorRegister, actor: User, request: Request
) -> Sensor:
    if _sensor_code_exists(db, payload.sensor_code):
        raise ApiError(
            status_code=409,
            code="SENSOR_CODE_EXISTS",
            message="A sensor with this code already exists.",
        )
    pump = None
    if payload.pump_id is not None:
        pump = get_pump_or_404(db, payload.pump_id)

    sensor = Sensor(pump=pump, **sensor_values(payload))
    db.add(sensor)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="EQUIPMENT_CONFLICT",
            message="The sensor identifier is already in use.",
        ) from exc

    record_audit(
        db,
        action="SENSOR_CREATED",
        actor=actor,
        entity_type="sensor",
        entity_id=sensor.id,
        after=_snapshot_sensor(sensor),
        request=request,
    )
    _commit_or_conflict(db, "The sensor identifier is already in use.")
    return get_sensor_or_404(db, sensor.id)


def update_sensor(
    db: Session, sensor_id: str, payload: SensorUpdate, actor: User, request: Request
) -> Sensor:
    sensor = get_sensor_or_404(db, sensor_id)
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return sensor
    if values.get("sensor_type") is not None:
        values["sensor_type"] = SensorType(values["sensor_type"])
    if values.get("mounting_axis") is not None:
        values["mounting_axis"] = MountingAxis(values["mounting_axis"])
    if "pump_id" in values:
        pump_id = values.pop("pump_id")
        sensor.pump = get_pump_or_404(db, pump_id) if pump_id is not None else None

    before = _snapshot_sensor(sensor)
    for field, value in values.items():
        setattr(sensor, field, value.strip() if isinstance(value, str) else value)
    db.flush()

    record_audit(
        db,
        action="SENSOR_UPDATED",
        actor=actor,
        entity_type="sensor",
        entity_id=sensor.id,
        before=before,
        after=_snapshot_sensor(sensor),
        request=request,
    )
    db.commit()
    return get_sensor_or_404(db, sensor.id)
