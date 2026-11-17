import math
import sys
from array import array

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ApiError
from app.db.models import AcquisitionSession, SignalWindow, User, utcnow
from app.domain.enums import DataQuality, Provenance, SessionStatus
from app.schemas.acquisition import AcquisitionSessionCreate, WindowIngest
from app.services.audit import record_audit
from app.services.equipment import (
    get_operating_regime_or_422,
    get_pump_or_404,
    get_sensor_or_404,
)

_SAMPLING_RATE_TOLERANCE = 0.01
_MAX_SAMPLE_MAGNITUDE = 1_000_000.0


def _session_statement():
    return select(AcquisitionSession).options(
        joinedload(AcquisitionSession.pump),
        joinedload(AcquisitionSession.sensor),
        joinedload(AcquisitionSession.regime),
        joinedload(AcquisitionSession.started_by),
    )


def get_session_or_404(db: Session, session_id: str) -> AcquisitionSession:
    session = db.execute(
        _session_statement().where(AcquisitionSession.id == session_id)
    ).scalar_one_or_none()
    if session is None:
        raise ApiError(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message="Acquisition session not found.",
        )
    return session


def get_window_count(db: Session, session_id: str) -> int:
    return db.execute(
        select(func.count(SignalWindow.id)).where(SignalWindow.session_id == session_id)
    ).scalar_one()


def list_sessions(
    db: Session,
    *,
    page: int,
    page_size: int,
    pump_id: str | None = None,
    status: SessionStatus | None = None,
    provenance: Provenance | None = None,
    scenario: str | None = None,
) -> tuple[list[tuple[AcquisitionSession, int]], int]:
    filters = []
    if pump_id is not None:
        filters.append(AcquisitionSession.pump_id == pump_id)
    if status is not None:
        filters.append(AcquisitionSession.status == status)
    if provenance is not None:
        filters.append(AcquisitionSession.data_provenance == provenance)
    if scenario:
        filters.append(AcquisitionSession.scenario == scenario.strip())

    window_count = (
        select(func.count(SignalWindow.id))
        .where(SignalWindow.session_id == AcquisitionSession.id)
        .correlate(AcquisitionSession)
        .scalar_subquery()
    )
    count_stmt = select(func.count(AcquisitionSession.id))
    list_stmt = select(AcquisitionSession, window_count.label("window_count")).options(
        joinedload(AcquisitionSession.pump),
        joinedload(AcquisitionSession.sensor),
        joinedload(AcquisitionSession.regime),
        joinedload(AcquisitionSession.started_by),
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(
        list_stmt.order_by(AcquisitionSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def create_session(
    db: Session,
    payload: AcquisitionSessionCreate,
    actor: User,
    request: Request,
) -> AcquisitionSession:
    pump = get_pump_or_404(db, payload.pump_id)
    sensor = get_sensor_or_404(db, payload.sensor_id)

    if sensor.pump_id != pump.id:
        raise ApiError(
            status_code=422,
            code="SENSOR_PUMP_MISMATCH",
            message="The selected sensor is not assigned to this pump.",
        )
    if not sensor.is_active:
        raise ApiError(
            status_code=422,
            code="SENSOR_INACTIVE",
            message="The selected sensor is inactive.",
        )
    if payload.data_provenance != Provenance.SIMULATED:
        raise ApiError(
            status_code=422,
            code="EXPERIMENTAL_ACQUISITION_UNAVAILABLE",
            message=(
                "Experimental acquisition is not enabled in this build. "
                "Connect and validate physical hardware before recording measured data."
            ),
        )
    if sensor.sampling_rate_hz <= 0 or (
        abs(payload.sampling_rate_hz - sensor.sampling_rate_hz) / sensor.sampling_rate_hz
        > _SAMPLING_RATE_TOLERANCE
    ):
        raise ApiError(
            status_code=422,
            code="SAMPLING_RATE_MISMATCH",
            message="Session sampling rate must match the configured sensor sampling rate.",
        )

    regime_id = payload.regime_id or pump.default_regime_id
    get_operating_regime_or_422(db, regime_id)

    session = AcquisitionSession(
        pump_id=pump.id,
        sensor_id=sensor.id,
        regime_id=regime_id,
        started_by_id=actor.id,
        source_device_id=payload.source_device_id or "api-simulator",
        sampling_rate_hz=payload.sampling_rate_hz,
        data_provenance=payload.data_provenance,
        random_seed=payload.random_seed,
        scenario=payload.scenario,
        status=SessionStatus.ACTIVE,
        notes=payload.notes or None,
    )
    db.add(session)
    db.flush()

    record_audit(
        db,
        action="ACQUISITION_SESSION_STARTED",
        actor=actor,
        entity_type="acquisition_session",
        entity_id=session.id,
        after={
            "pump_id": session.pump_id,
            "sensor_id": session.sensor_id,
            "scenario": session.scenario,
            "data_provenance": session.data_provenance.value,
            "sampling_rate_hz": session.sampling_rate_hz,
            "random_seed": session.random_seed,
        },
        request=request,
    )
    db.commit()
    return get_session_or_404(db, session.id)


def stop_session(
    db: Session,
    session_id: str,
    terminal_status: SessionStatus,
    actor: User,
    request: Request,
) -> AcquisitionSession:
    session = get_session_or_404(db, session_id)
    if session.status != SessionStatus.ACTIVE:
        return session
    if terminal_status not in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
        raise ApiError(
            status_code=422,
            code="INVALID_SESSION_STATUS",
            message="A session can only be stopped as COMPLETED or ABORTED.",
        )

    before_status = session.status
    session.status = terminal_status
    session.ended_at = utcnow()
    record_audit(
        db,
        action="ACQUISITION_SESSION_STOPPED",
        actor=actor,
        entity_type="acquisition_session",
        entity_id=session.id,
        before={"status": before_status.value},
        after={"status": terminal_status.value, "ended_at": session.ended_at.isoformat()},
        request=request,
    )
    db.commit()
    return get_session_or_404(db, session_id)


def ingest_window(
    db: Session,
    session_id: str,
    payload: WindowIngest,
) -> SignalWindow:
    session = get_session_or_404(db, session_id)
    if session.status != SessionStatus.ACTIVE:
        raise ApiError(
            status_code=409,
            code="SESSION_NOT_ACTIVE",
            message="Windows can only be ingested into an active acquisition session.",
        )

    existing = db.execute(
        select(SignalWindow.id).where(
            SignalWindow.session_id == session_id,
            SignalWindow.window_index == payload.window_index,
        )
    ).first()
    if existing is not None:
        raise ApiError(
            status_code=409,
            code="WINDOW_EXISTS",
            message="A window with this index already exists for the session.",
        )

    signal_payload = None
    sample_count = 0

    if payload.quality_status is DataQuality.VALID:
        if not payload.samples:
            raise ApiError(
                status_code=422,
                code="INVALID_WINDOW_PAYLOAD",
                message="A valid window must contain samples.",
            )
        if not all(math.isfinite(value) for value in payload.samples):
            raise ApiError(
                status_code=422,
                code="INVALID_WINDOW_PAYLOAD",
                message="Windows accepted as valid must contain finite sample values.",
            )
        if any(abs(value) > _MAX_SAMPLE_MAGNITUDE for value in payload.samples):
            raise ApiError(
                status_code=422,
                code="INVALID_WINDOW_PAYLOAD",
                message="Sample magnitude exceeds the ingestion safety limit.",
            )
        sample_count = len(payload.samples)
        expected_duration = sample_count / session.sampling_rate_hz
        actual_duration = (payload.window_end - payload.window_start).total_seconds()
        tolerance = max(0.02, 2 / session.sampling_rate_hz)
        if abs(actual_duration - expected_duration) > tolerance:
            raise ApiError(
                status_code=422,
                code="WINDOW_TIMESTAMP_MISMATCH",
                message="Window timestamps do not match the declared sample count and rate.",
            )
        packed = array("f", payload.samples)
        if sys.byteorder != "little":
            packed.byteswap()
        signal_payload = packed.tobytes()
    else:
        if payload.samples:
            raise ApiError(
                status_code=422,
                code="INVALID_WINDOW_PAYLOAD",
                message="Sensor-invalid windows must not include sample payloads.",
            )
        if not payload.validation_summary:
            raise ApiError(
                status_code=422,
                code="VALIDATION_SUMMARY_REQUIRED",
                message="Sensor-invalid windows must include a validation summary.",
            )

    window = SignalWindow(
        session_id=session.id,
        sensor_id=session.sensor_id,
        window_index=payload.window_index,
        window_start=payload.window_start,
        window_end=payload.window_end,
        sampling_rate_hz=session.sampling_rate_hz,
        sample_count=sample_count,
        payload_encoding="float32-le",
        signal_payload=signal_payload,
        features=payload.features,
        quality_status=payload.quality_status,
        validation_summary=payload.validation_summary,
        data_provenance=session.data_provenance,
    )
    db.add(window)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="WINDOW_EXISTS",
            message="A window with this index already exists for the session.",
        ) from exc
    return window


def list_windows(
    db: Session,
    session_id: str,
    *,
    page: int,
    page_size: int,
) -> tuple[list[SignalWindow], int]:
    get_session_or_404(db, session_id)
    total = get_window_count(db, session_id)
    windows = (
        db.execute(
            select(SignalWindow)
            .where(SignalWindow.session_id == session_id)
            .order_by(SignalWindow.window_index.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(windows), total
