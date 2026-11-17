from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.common import Page
from app.schemas.equipment import SensorPublic, SensorRegister, SensorUpdate
from app.schemas.monitoring import SensorHealthPublic
from app.services import equipment as equipment_service
from app.services import monitoring as monitoring_service

router = APIRouter(prefix="/sensors", tags=["Sensors"])
_WRITE_ACCESS = require_roles(RoleName.ENGINEER)


@router.get("", response_model=Page[SensorPublic], summary="List sensors")
def list_sensors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
    pump_id: str | None = Query(default=None, max_length=36),
    is_active: bool | None = Query(default=None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SensorPublic]:
    sensors, total = equipment_service.list_sensors(
        db,
        page=page,
        page_size=page_size,
        q=q,
        pump_id=pump_id,
        is_active=is_active,
    )
    return Page[SensorPublic](
        items=[SensorPublic.from_sensor(sensor) for sensor in sensors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=SensorPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a sensor",
)
def create_sensor(
    payload: SensorRegister,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> SensorPublic:
    sensor = equipment_service.create_sensor(db, payload, actor, request)
    return SensorPublic.from_sensor(sensor)


@router.get(
    "/health",
    response_model=list[SensorHealthPublic],
    summary="Sensor diagnostics from persisted windows",
)
def sensor_health(
    pump_id: str | None = Query(default=None, max_length=36),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SensorHealthPublic]:
    return monitoring_service.list_sensor_health(db, pump_id=pump_id)


@router.get("/{sensor_id}", response_model=SensorPublic, summary="Get a sensor")
def get_sensor(
    sensor_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SensorPublic:
    sensor = equipment_service.get_sensor_or_404(db, sensor_id)
    return SensorPublic.from_sensor(sensor)


@router.patch("/{sensor_id}", response_model=SensorPublic, summary="Update a sensor")
def update_sensor(
    sensor_id: str,
    payload: SensorUpdate,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> SensorPublic:
    sensor = equipment_service.update_sensor(db, sensor_id, payload, actor, request)
    return SensorPublic.from_sensor(sensor)
