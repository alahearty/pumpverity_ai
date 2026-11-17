from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import Provenance, RoleName, SessionStatus
from app.schemas.acquisition import (
    AcquisitionSessionCreate,
    AcquisitionSessionPublic,
    AcquisitionSessionStop,
    WindowIngest,
    WindowPublic,
)
from app.schemas.common import Page
from app.services import acquisition as acquisition_service

router = APIRouter(prefix="/acquisition-sessions", tags=["Acquisition"])
_ACQUISITION_WRITE = require_roles(RoleName.ENGINEER, RoleName.RESEARCHER)


def _session_payload(db: Session, session) -> AcquisitionSessionPublic:
    return AcquisitionSessionPublic.from_session(
        session, acquisition_service.get_window_count(db, session.id)
    )


@router.get(
    "",
    response_model=Page[AcquisitionSessionPublic],
    summary="List acquisition sessions",
)
def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    pump_id: str | None = Query(default=None, max_length=36),
    session_status: SessionStatus | None = Query(default=None, alias="status"),
    provenance: Provenance | None = Query(default=None),
    scenario: str | None = Query(default=None, max_length=80),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[AcquisitionSessionPublic]:
    rows, total = acquisition_service.list_sessions(
        db,
        page=page,
        page_size=page_size,
        pump_id=pump_id,
        status=session_status,
        provenance=provenance,
        scenario=scenario,
    )
    return Page[AcquisitionSessionPublic](
        items=[
            AcquisitionSessionPublic.from_session(session, window_count)
            for session, window_count in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=AcquisitionSessionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Start an acquisition session",
)
def create_session(
    payload: AcquisitionSessionCreate,
    request: Request,
    actor: User = Depends(_ACQUISITION_WRITE),
    db: Session = Depends(get_db),
) -> AcquisitionSessionPublic:
    session = acquisition_service.create_session(db, payload, actor, request)
    return _session_payload(db, session)


@router.get(
    "/{session_id}",
    response_model=AcquisitionSessionPublic,
    summary="Get an acquisition session",
)
def get_session(
    session_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionSessionPublic:
    session = acquisition_service.get_session_or_404(db, session_id)
    return _session_payload(db, session)


@router.post(
    "/{session_id}/stop",
    response_model=AcquisitionSessionPublic,
    summary="Stop an acquisition session idempotently",
)
def stop_session(
    session_id: str,
    payload: AcquisitionSessionStop,
    request: Request,
    actor: User = Depends(_ACQUISITION_WRITE),
    db: Session = Depends(get_db),
) -> AcquisitionSessionPublic:
    session = acquisition_service.stop_session(db, session_id, payload.status, actor, request)
    return _session_payload(db, session)


@router.post(
    "/{session_id}/windows",
    response_model=WindowPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a validated signal window",
)
def ingest_window(
    session_id: str,
    payload: WindowIngest,
    _actor: User = Depends(_ACQUISITION_WRITE),
    db: Session = Depends(get_db),
) -> WindowPublic:
    window = acquisition_service.ingest_window(db, session_id, payload)
    return WindowPublic.from_window(window)


@router.get(
    "/{session_id}/windows",
    response_model=Page[WindowPublic],
    summary="List persisted signal windows for a session",
)
def list_windows(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[WindowPublic]:
    windows, total = acquisition_service.list_windows(
        db, session_id, page=page, page_size=page_size
    )
    return Page[WindowPublic](
        items=[WindowPublic.from_window(window) for window in windows],
        total=total,
        page=page,
        page_size=page_size,
    )
