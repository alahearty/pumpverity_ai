import math
import sys
from array import array
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ApiError
from app.db.models import (
    AcquisitionSession,
    Alert,
    ModelEvaluation,
    ModelVersion,
    Pump,
    Sensor,
    SignalWindow,
)
from app.domain.enums import AlertStatus, DataQuality, ModelStatus, SensorType
from app.schemas.monitoring import (
    EvaluationSummary,
    LiveSnapshot,
    LiveWindow,
    ModelSummary,
    MonitoringOverview,
    SensorHealthPublic,
    SessionSummary,
    WindowPoint,
)
from app.schemas.predictions import PredictionPublic
from app.services import predictions as prediction_service
from app.services.equipment import get_pump_or_404, get_sensor_or_404

STALE_AFTER_SECONDS = 300
MAX_WAVEFORM_POINTS = 512


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _window_options():
    return (
        joinedload(SignalWindow.session).joinedload(AcquisitionSession.pump),
        joinedload(SignalWindow.session).joinedload(AcquisitionSession.sensor),
        joinedload(SignalWindow.session).joinedload(AcquisitionSession.started_by),
        joinedload(SignalWindow.session).joinedload(AcquisitionSession.regime),
    )


def _session_options():
    return (
        joinedload(AcquisitionSession.pump),
        joinedload(AcquisitionSession.sensor),
        joinedload(AcquisitionSession.started_by),
        joinedload(AcquisitionSession.regime),
    )


def _metric(window: SignalWindow, key: str) -> float | None:
    summary = window.validation_summary
    if not isinstance(summary, dict):
        return None
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        return None
    value = metrics.get(key)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _issue_codes(window: SignalWindow) -> list[str]:
    summary = window.validation_summary
    if not isinstance(summary, dict):
        return []
    issues = summary.get("issues")
    if not isinstance(issues, list):
        return []
    codes = []
    for issue in issues:
        if isinstance(issue, dict) and issue.get("code"):
            codes.append(str(issue["code"]))
    return codes


def _validation_issues(window: SignalWindow) -> list[dict[str, Any]]:
    summary = window.validation_summary
    if not isinstance(summary, dict):
        return []
    issues = summary.get("issues")
    if not isinstance(issues, list):
        return []
    return [issue for issue in issues if isinstance(issue, dict)]


def _window_point(window: SignalWindow) -> WindowPoint:
    session = window.session
    pump = session.pump
    sensor = session.sensor
    return WindowPoint(
        window_id=window.id,
        session_id=window.session_id,
        pump_id=pump.id,
        pump_code=pump.pump_code,
        sensor_id=sensor.id,
        sensor_code=sensor.sensor_code,
        window_index=window.window_index,
        window_start=as_utc(window.window_start),
        window_end=as_utc(window.window_end),
        quality_status=window.quality_status,
        data_provenance=window.data_provenance,
        scenario=session.scenario,
        sample_count=window.sample_count,
        rms=_metric(window, "rms"),
        peak_abs=_metric(window, "peak_abs"),
        validation_issue_codes=_issue_codes(window),
    )


def _decode_waveform(window: SignalWindow) -> list[float] | None:
    if window.quality_status != DataQuality.VALID:
        return None
    if not window.signal_payload or window.sample_count == 0:
        return None
    values = array("f")
    values.frombytes(window.signal_payload)
    if sys.byteorder != "little":
        values.byteswap()
    samples = list(values)
    if len(samples) > MAX_WAVEFORM_POINTS:
        step = math.ceil(len(samples) / MAX_WAVEFORM_POINTS)
        samples = samples[::step]
        last = float(values[-1])
        if samples[-1] != last:
            if len(samples) >= MAX_WAVEFORM_POINTS:
                samples[-1] = last
            else:
                samples.append(last)
    return samples


def _live_window(window: SignalWindow) -> LiveWindow:
    point = _window_point(window)
    summary = window.validation_summary if isinstance(window.validation_summary, dict) else None
    units = None
    if summary:
        metrics = summary.get("metrics")
        if isinstance(metrics, dict):
            units = metrics.get("units")
    return LiveWindow(
        **point.model_dump(),
        sampling_rate_hz=window.sampling_rate_hz,
        units=str(units) if units else None,
        waveform=_decode_waveform(window),
        validation_summary=summary,
    )


def _window_count(db: Session, session_id: str) -> int:
    return db.execute(
        select(func.count(SignalWindow.id)).where(SignalWindow.session_id == session_id)
    ).scalar_one()


def _session_summary(session: AcquisitionSession, window_count: int) -> SessionSummary:
    return SessionSummary(
        id=session.id,
        pump_id=session.pump_id,
        pump_code=session.pump.pump_code,
        sensor_id=session.sensor_id,
        sensor_code=session.sensor.sensor_code,
        scenario=session.scenario,
        status=session.status,
        data_provenance=session.data_provenance,
        sampling_rate_hz=session.sampling_rate_hz,
        started_at=as_utc(session.started_at),
        ended_at=as_utc(session.ended_at),
        window_count=window_count,
        started_by_name=session.started_by.full_name if session.started_by else None,
    )


def _latest_window_for_sensor(
    db: Session, sensor_id: str, quality: DataQuality | None = None
) -> SignalWindow | None:
    stmt = (
        select(SignalWindow)
        .options(*_window_options())
        .where(SignalWindow.sensor_id == sensor_id)
        .order_by(SignalWindow.created_at.desc(), SignalWindow.id.desc())
        .limit(1)
    )
    if quality is not None:
        stmt = stmt.where(SignalWindow.quality_status == quality)
    return db.execute(stmt).scalar_one_or_none()


def _latest_window(db: Session) -> SignalWindow | None:
    return db.execute(
        select(SignalWindow)
        .options(*_window_options())
        .order_by(SignalWindow.created_at.desc(), SignalWindow.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _latest_session(
    db: Session,
    *,
    pump_id: str | None = None,
    sensor_id: str | None = None,
) -> AcquisitionSession | None:
    stmt = select(AcquisitionSession).options(*_session_options())
    if pump_id is not None:
        stmt = stmt.where(AcquisitionSession.pump_id == pump_id)
    if sensor_id is not None:
        stmt = stmt.where(AcquisitionSession.sensor_id == sensor_id)
    return db.execute(
        stmt.order_by(AcquisitionSession.started_at.desc()).limit(1)
    ).scalar_one_or_none()


def _missing_window_gaps(db: Session, session_id: str, sensor_id: str) -> int:
    indexes = (
        db.execute(
            select(SignalWindow.window_index).where(
                SignalWindow.session_id == session_id,
                SignalWindow.sensor_id == sensor_id,
            )
        )
        .scalars()
        .all()
    )
    if not indexes:
        return 0
    expected = max(indexes) + 1
    return max(0, expected - len(set(indexes)))


def get_sensor_health(db: Session, sensor: Sensor) -> SensorHealthPublic:
    quality_rows = db.execute(
        select(SignalWindow.quality_status, func.count(SignalWindow.id))
        .where(SignalWindow.sensor_id == sensor.id)
        .group_by(SignalWindow.quality_status)
    ).all()
    counts = dict(quality_rows)
    valid_windows = int(counts.get(DataQuality.VALID, 0))
    invalid_windows = int(counts.get(DataQuality.SENSOR_INVALID, 0))
    total_windows = valid_windows + invalid_windows

    latest = _latest_window_for_sensor(db, sensor.id)
    latest_valid = (
        latest
        if latest is not None and latest.quality_status == DataQuality.VALID
        else _latest_window_for_sensor(db, sensor.id, DataQuality.VALID)
    )

    latest_session = latest.session if latest is not None else _latest_session(
        db, sensor_id=sensor.id
    )
    missing_gaps = (
        _missing_window_gaps(db, latest_session.id, sensor.id)
        if latest_session is not None
        else 0
    )

    now = datetime.now(UTC)
    last_reading_at = as_utc(latest.window_end) if latest is not None else None
    last_valid_at = as_utc(latest_valid.window_end) if latest_valid is not None else None
    freshness = None
    if latest is not None:
        created = as_utc(latest.created_at)
        if created is not None:
            freshness = max(0.0, (now - created).total_seconds())

    if latest is None:
        sampling_status = "NO_DATA"
    elif latest.quality_status == DataQuality.SENSOR_INVALID:
        sampling_status = "SENSOR_INVALID"
    elif freshness is not None and freshness > STALE_AFTER_SECONDS:
        sampling_status = "STALE"
    else:
        sampling_status = "RECENT"

    return SensorHealthPublic(
        sensor_id=sensor.id,
        sensor_code=sensor.sensor_code,
        pump_id=sensor.pump_id,
        pump_code=sensor.pump.pump_code if sensor.pump is not None else None,
        sensor_type=sensor.sensor_type,
        is_active=sensor.is_active,
        sampling_rate_hz=sensor.sampling_rate_hz,
        total_windows=total_windows,
        valid_windows=valid_windows,
        invalid_windows=invalid_windows,
        missing_window_gaps=missing_gaps,
        last_reading_at=last_reading_at,
        last_valid_reading_at=last_valid_at,
        freshness_seconds=round(freshness, 2) if freshness is not None else None,
        latest_quality=latest.quality_status if latest is not None else None,
        data_quality=latest.quality_status if latest is not None else None,
        sampling_status=sampling_status,
        connection_state="NO_LIVE_CHANNEL",
        latest_rms=_metric(latest_valid, "rms") if latest_valid is not None else None,
        latest_peak_abs=(
            _metric(latest_valid, "peak_abs") if latest_valid is not None else None
        ),
        latest_scenario=latest.session.scenario if latest is not None else None,
        provenance=latest.data_provenance if latest is not None else None,
        latest_validation_issues=(
            _validation_issues(latest)
            if latest is not None and latest.quality_status == DataQuality.SENSOR_INVALID
            else []
        ),
    )


def list_sensor_health(db: Session, *, pump_id: str | None = None) -> list[SensorHealthPublic]:
    stmt = select(Sensor).options(joinedload(Sensor.pump))
    if pump_id is not None:
        stmt = stmt.where(Sensor.pump_id == pump_id)
    sensors = db.execute(stmt.order_by(Sensor.sensor_code.asc())).scalars().all()
    return [get_sensor_health(db, sensor) for sensor in sensors]


def resolve_pump_sensor(
    db: Session, *, pump_id: str, sensor_id: str | None = None
) -> tuple[Pump, Sensor]:
    pump = get_pump_or_404(db, pump_id)
    if sensor_id is not None:
        sensor = get_sensor_or_404(db, sensor_id)
        if sensor.pump_id != pump.id:
            raise ApiError(
                status_code=422,
                code="SENSOR_PUMP_MISMATCH",
                message="The selected sensor is not assigned to this pump.",
            )
        return pump, sensor

    sensors = (
        db.execute(
            select(Sensor)
            .options(joinedload(Sensor.pump))
            .where(Sensor.pump_id == pump.id, Sensor.is_active.is_(True))
            .order_by(Sensor.sensor_code.asc())
        )
        .scalars()
        .all()
    )
    if not sensors:
        raise ApiError(
            status_code=422,
            code="NO_ACTIVE_SENSOR",
            message="The pump has no active sensor for monitoring.",
        )
    vibration = next(
        (sensor for sensor in sensors if sensor.sensor_type == SensorType.VIBRATION),
        sensors[0],
    )
    return pump, vibration


def get_live_snapshot(
    db: Session,
    *,
    pump_id: str,
    sensor_id: str | None = None,
    limit: int = 25,
) -> LiveSnapshot:
    pump, sensor = resolve_pump_sensor(db, pump_id=pump_id, sensor_id=sensor_id)
    windows = (
        db.execute(
            select(SignalWindow)
            .options(*_window_options())
            .where(SignalWindow.sensor_id == sensor.id)
            .order_by(SignalWindow.created_at.desc(), SignalWindow.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    windows = list(reversed(windows))
    latest = windows[-1] if windows else None
    session = _latest_session(db, sensor_id=sensor.id)
    if session is None and latest is not None:
        session = latest.session
    session_summary = (
        _session_summary(session, _window_count(db, session.id))
        if session is not None
        else None
    )
    health = get_sensor_health(db, sensor)
    prediction = (
        prediction_service.get_for_window(db, latest.id) if latest is not None else None
    )
    condition_available = bool(
        prediction is not None
        and latest is not None
        and latest.quality_status == DataQuality.VALID
        and prediction.data_quality == DataQuality.VALID
        and prediction.equipment_condition is not None
    )
    latest_prediction = (
        PredictionPublic.from_prediction(prediction)
        if prediction is not None
        else None
    )

    return LiveSnapshot(
        pump_id=pump.id,
        pump_code=pump.pump_code,
        pump_name=pump.name,
        sensor_id=sensor.id,
        sensor_code=sensor.sensor_code,
        sensor_type=sensor.sensor_type,
        latest_window=_live_window(latest) if latest is not None else None,
        recent_windows=[_window_point(window) for window in windows],
        latest_prediction=latest_prediction,
        session=session_summary,
        sensor_health=health,
        equipment_condition=(
            prediction.equipment_condition if condition_available and prediction else None
        ),
        condition_available=condition_available,
        data_quality=latest.quality_status if latest is not None else None,
        edge_connectivity=None,
        edge_note=(
            "No live edge channel is configured. Values are persisted simulated windows; "
            "offline sync and physical connectivity arrive in Stage 6."
        ),
        data_mode="SIMULATED_REPLAY" if latest is not None else "NO_DATA",
        buffering_state=None,
        generated_at=datetime.now(UTC),
    )


def _count(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return int(db.execute(stmt).scalar_one())


def get_overview(db: Session) -> MonitoringOverview:
    pumps_total = _count(db, Pump)
    pumps_active = _count(db, Pump, Pump.status == "ACTIVE")
    sensors_total = _count(db, Sensor)
    sensors_active = _count(db, Sensor, Sensor.is_active.is_(True))
    sessions_total = _count(db, AcquisitionSession)
    windows_total = _count(db, SignalWindow)
    valid_windows = _count(db, SignalWindow, SignalWindow.quality_status == DataQuality.VALID)
    invalid_windows = _count(
        db, SignalWindow, SignalWindow.quality_status == DataQuality.SENSOR_INVALID
    )
    active_alerts = _count(
        db,
        Alert,
        Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
    )

    latest_window = _latest_window(db)
    latest_session = _latest_session(db)
    latest_session_summary = (
        _session_summary(latest_session, _window_count(db, latest_session.id))
        if latest_session is not None
        else None
    )

    trend: list[WindowPoint] = []
    if latest_window is not None:
        trend_windows = (
            db.execute(
                select(SignalWindow)
                .options(*_window_options())
                .where(SignalWindow.sensor_id == latest_window.sensor_id)
                .order_by(SignalWindow.created_at.desc(), SignalWindow.id.desc())
                .limit(30)
            )
            .scalars()
            .all()
        )
        trend = [_window_point(window) for window in reversed(list(trend_windows))]

    sensor_health = list_sensor_health(db)
    sensors_with_data = sum(1 for item in sensor_health if item.total_windows > 0)
    sensors_stale = sum(1 for item in sensor_health if item.sampling_status == "STALE")
    sensors_invalid = sum(
        1 for item in sensor_health if item.sampling_status == "SENSOR_INVALID"
    )
    sensors_no_data = sum(1 for item in sensor_health if item.sampling_status == "NO_DATA")

    active_model_row = db.execute(
        select(ModelVersion)
        .where(ModelVersion.status == ModelStatus.ACTIVE)
        .order_by(ModelVersion.activated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    latest_evaluation_row = db.execute(
        select(ModelEvaluation)
        .options(joinedload(ModelEvaluation.model_version))
        .order_by(ModelEvaluation.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    active_model = None
    if active_model_row is not None:
        model_eval = db.execute(
            select(ModelEvaluation)
            .where(ModelEvaluation.model_version_id == active_model_row.id)
            .order_by(ModelEvaluation.evaluated_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        active_model = ModelSummary(
            id=active_model_row.id,
            model_code=active_model_row.model_code,
            name=active_model_row.name,
            version=active_model_row.version,
            status=active_model_row.status,
            balanced_accuracy=model_eval.balanced_accuracy if model_eval else None,
            macro_f1=model_eval.macro_f1 if model_eval else None,
            evaluation_dataset=model_eval.dataset_name if model_eval else None,
            evaluated_at=as_utc(model_eval.evaluated_at) if model_eval else None,
            data_provenance=model_eval.data_provenance if model_eval else None,
        )

    latest_evaluation = (
        EvaluationSummary(
            id=latest_evaluation_row.id,
            model_version_id=latest_evaluation_row.model_version_id,
            dataset_name=latest_evaluation_row.dataset_name,
            dataset_version=latest_evaluation_row.dataset_version,
            data_provenance=latest_evaluation_row.data_provenance,
            balanced_accuracy=latest_evaluation_row.balanced_accuracy,
            macro_f1=latest_evaluation_row.macro_f1,
            sample_count=latest_evaluation_row.sample_count,
            evaluated_at=as_utc(latest_evaluation_row.evaluated_at),
            is_verified=latest_evaluation_row.is_verified,
        )
        if latest_evaluation_row is not None
        else None
    )

    window_count_subquery = (
        select(func.count(SignalWindow.id))
        .where(SignalWindow.session_id == AcquisitionSession.id)
        .correlate(AcquisitionSession)
        .scalar_subquery()
    )
    recent_rows = db.execute(
        select(AcquisitionSession, window_count_subquery.label("window_count"))
        .options(*_session_options())
        .order_by(AcquisitionSession.started_at.desc())
        .limit(5)
    ).all()
    recent_sessions = [
        _session_summary(session, window_count) for session, window_count in recent_rows
    ]

    latest_prediction_row = (
        prediction_service.get_for_window(db, latest_window.id)
        if latest_window is not None
        else None
    )
    condition_available = bool(
        latest_prediction_row is not None
        and latest_window is not None
        and latest_window.quality_status == DataQuality.VALID
        and latest_prediction_row.data_quality == DataQuality.VALID
        and latest_prediction_row.equipment_condition is not None
    )

    return MonitoringOverview(
        pumps_total=pumps_total,
        pumps_active=pumps_active,
        sensors_total=sensors_total,
        sensors_active=sensors_active,
        active_alerts=active_alerts,
        sessions_total=sessions_total,
        windows_total=windows_total,
        valid_windows=valid_windows,
        invalid_windows=invalid_windows,
        latest_session=latest_session_summary,
        latest_window=_live_window(latest_window) if latest_window is not None else None,
        latest_prediction=(
            PredictionPublic.from_prediction(latest_prediction_row)
            if latest_prediction_row is not None
            else None
        ),
        trend=trend,
        sensors_with_data=sensors_with_data,
        sensors_stale=sensors_stale,
        sensors_invalid=sensors_invalid,
        sensors_no_data=sensors_no_data,
        equipment_condition=(
            latest_prediction_row.equipment_condition
            if condition_available and latest_prediction_row is not None
            else None
        ),
        condition_available=condition_available,
        data_quality=latest_window.quality_status if latest_window is not None else None,
        edge_connectivity=None,
        edge_note=(
            "No live edge channel is configured; values are persisted simulated windows. "
            "Synchronisation status becomes available in Stage 6."
        ),
        data_mode="SIMULATED_REPLAY" if latest_window is not None else "NO_DATA",
        active_model=active_model,
        latest_evaluation=latest_evaluation,
        recent_sessions=recent_sessions,
        generated_at=datetime.now(UTC),
    )


def windows_since(
    db: Session,
    *,
    pump_id: str,
    sensor_id: str | None,
    since: datetime,
) -> list[SignalWindow]:
    stmt = (
        select(SignalWindow)
        .join(AcquisitionSession, SignalWindow.session_id == AcquisitionSession.id)
        .options(*_window_options())
        .where(
            AcquisitionSession.pump_id == pump_id,
            SignalWindow.created_at >= since,
        )
        .order_by(SignalWindow.created_at.asc(), SignalWindow.id.asc())
        .limit(100)
    )
    if sensor_id is not None:
        stmt = stmt.where(SignalWindow.sensor_id == sensor_id)
    return list(db.execute(stmt).scalars().all())


def stream_window_event(window: SignalWindow) -> dict[str, Any]:
    point = _window_point(window)
    event_type = (
        "sensor_health"
        if point.quality_status == DataQuality.SENSOR_INVALID
        else "reading"
    )
    return {
        "event_type": event_type,
        "occurred_at": point.window_end.isoformat(),
        "pump_id": point.pump_id,
        "payload_version": 1,
        "payload": point.model_dump(mode="json"),
    }
