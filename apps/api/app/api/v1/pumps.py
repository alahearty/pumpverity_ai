from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import PumpStatus, PumpType, RoleName
from app.schemas.common import Page
from app.schemas.equipment import PumpCreate, PumpPublic, PumpUpdate
from app.services import equipment as equipment_service

router = APIRouter(prefix="/pumps", tags=["Pumps"])
_WRITE_ACCESS = require_roles(RoleName.ENGINEER)


@router.get("", response_model=Page[PumpPublic], summary="List registered pumps")
def list_pumps(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
    pump_status: PumpStatus | None = Query(default=None, alias="status"),
    pump_type: PumpType | None = Query(default=None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[PumpPublic]:
    pumps, total = equipment_service.list_pumps(
        db,
        page=page,
        page_size=page_size,
        q=q,
        status=pump_status,
        pump_type=pump_type,
    )
    return Page[PumpPublic](
        items=[PumpPublic.from_pump(pump) for pump in pumps],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=PumpPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a pump and optionally its first sensor",
)
def create_pump(
    payload: PumpCreate,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> PumpPublic:
    pump = equipment_service.create_pump(db, payload, actor, request)
    return PumpPublic.from_pump(pump)


@router.get("/{pump_id}", response_model=PumpPublic, summary="Get a pump")
def get_pump(
    pump_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PumpPublic:
    return PumpPublic.from_pump(equipment_service.get_pump_or_404(db, pump_id))


@router.patch("/{pump_id}", response_model=PumpPublic, summary="Update a pump")
def update_pump(
    pump_id: str,
    payload: PumpUpdate,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> PumpPublic:
    pump = equipment_service.update_pump(db, pump_id, payload, actor, request)
    return PumpPublic.from_pump(pump)
