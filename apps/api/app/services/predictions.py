import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ApiError
from app.db.models import (
    AcquisitionSession,
    Alert,
    ConfigurationSetting,
    ModelVersion,
    Prediction,
    SignalWindow,
    User,
)
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    DataQuality,
    EquipmentCondition,
    ModelStatus,
    PredictionDecision,
)
from app.schemas.predictions import PredictionCreate
from app.services import acquisition as acquisition_service
from app.services.audit import record_audit
from app.services.equipment import get_pump_or_404, get_sensor_or_404
from app.services.models import get_model_or_404

_CONDITION_BY_DECISION = {
    PredictionDecision.NORMAL: EquipmentCondition.NORMAL,
    PredictionDecision.FAULT: EquipmentCondition.FAULT,
    PredictionDecision.UNCERTAIN: EquipmentCondition.UNCERTAIN,
}

_ALERT_SETTING_KEYS = {
    PredictionDecision.FAULT: "alerts.auto_create_for_fault",
    PredictionDecision.UNCERTAIN: "alerts.auto_create_for_uncertain",
    PredictionDecision.SENSOR_INVALID: "alerts.auto_create_for_sensor_invalid",
}

_ALERT_SEVERITY = {
    PredictionDecision.FAULT: AlertSeverity.HIGH,
    PredictionDecision.UNCERTAIN: AlertSeverity.MEDIUM,
    PredictionDecision.SENSOR_INVALID: AlertSeverity.HIGH,
}


def _auto_alert_enabled(db: Session, decision: PredictionDecision) -> bool:
    setting = db.execute(
        select(ConfigurationSetting).where(
            ConfigurationSetting.key == _ALERT_SETTING_KEYS[decision]
        )
    ).scalar_one_or_none()
    if setting is None:
        return True
    return bool(setting.value)


def _create_prediction_alert(
    db: Session,
    prediction: Prediction,
    *,
    pump,
    sensor,
    session: AcquisitionSession,
    model: ModelVersion | None,
    actor: User,
    request: Request,
) -> Alert | None:
    if prediction.decision == PredictionDecision.NORMAL:
        return None
    if not _auto_alert_enabled(db, prediction.decision):
        return None

    category = AlertCategory(prediction.decision.value)
    if prediction.decision == PredictionDecision.FAULT:
        title = f"Fault decision on {pump.pump_code} / {sensor.sensor_code}"
    elif prediction.decision == PredictionDecision.UNCERTAIN:
        title = f"Uncertain decision requires review on {pump.pump_code} / {sensor.sensor_code}"
    else:
        title = f"Sensor-invalid signal on {pump.pump_code} / {sensor.sensor_code}"

    model_text = (
        f"{model.name} v{model.version} ({model.runtime.value})"
        if model is not None
        else "No model inference"
    )
    description = (
        f"{prediction.explanation}\n\n"
        f"Model: {model_text}. "
        f"Data provenance: {prediction.data_provenance.value}."
    )
    alert = Alert(
        event_id=f"alert-{uuid4()}",
        pump_id=prediction.pump_id,
        sensor_id=prediction.sensor_id,
        prediction_id=prediction.id,
        category=category,
        severity=_ALERT_SEVERITY[prediction.decision],
        status=AlertStatus.OPEN,
        title=title,
        description=description,
        origin_device_id=session.source_device_id,
        data_provenance=prediction.data_provenance,
    )
    db.add(alert)
    db.flush()
    record_audit(
        db,
        action="ALERT_CREATED",
        actor=actor,
        entity_type="alert",
        entity_id=alert.id,
        after={
            "category": category.value,
            "severity": alert.severity.value,
            "prediction_id": prediction.id,
            "model_version_id": prediction.model_version_id,
        },
        request=request,
    )
    return alert


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _prediction_options():
    return (
        joinedload(Prediction.pump),
        joinedload(Prediction.sensor),
        joinedload(Prediction.session),
        joinedload(Prediction.window),
        joinedload(Prediction.model_version),
        joinedload(Prediction.operating_regime),
    )


def get_prediction_or_404(db: Session, prediction_id: str) -> Prediction:
    prediction = db.execute(
        select(Prediction)
        .options(*_prediction_options())
        .where(Prediction.id == prediction_id)
    ).scalar_one_or_none()
    if prediction is None:
        raise ApiError(
            status_code=404,
            code="PREDICTION_NOT_FOUND",
            message="Prediction not found.",
        )
    return prediction


def get_for_window(db: Session, window_id: str) -> Prediction | None:
    return db.execute(
        select(Prediction)
        .options(*_prediction_options())
        .where(Prediction.signal_window_id == window_id)
        .order_by(Prediction.inferred_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _feature_contract_compatible(window: SignalWindow, model) -> bool:
    contract = model.feature_contract or {}
    expected = contract.get("features")
    if not isinstance(expected, list) or not expected:
        return False
    features = window.features
    if not isinstance(features, dict):
        return False
    for name in expected:
        value = features.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return False
    return True


def _model_was_active_at(model, inferred_at: datetime) -> bool:
    if model.status == ModelStatus.ACTIVE:
        return True
    if model.status != ModelStatus.RETIRED:
        return False
    activated = _aware(model.activated_at)
    retired = _aware(model.retired_at)
    if activated is not None and inferred_at < activated - timedelta(seconds=5):
        return False
    return not (
        retired is not None and inferred_at > retired + timedelta(seconds=5)
    )


def create_prediction(
    db: Session,
    payload: PredictionCreate,
    actor: User,
    request: Request,
) -> Prediction:
    pump = get_pump_or_404(db, payload.pump_id)
    sensor = get_sensor_or_404(db, payload.sensor_id)
    session = acquisition_service.get_session_or_404(db, payload.session_id)
    window = db.get(SignalWindow, payload.signal_window_id)
    if window is None:
        raise ApiError(
            status_code=404,
            code="WINDOW_NOT_FOUND",
            message="Signal window not found.",
        )
    if sensor.pump_id != pump.id or session.pump_id != pump.id:
        raise ApiError(
            status_code=422,
            code="SENSOR_PUMP_MISMATCH",
            message="Sensor, pump and session references are inconsistent.",
        )
    if session.sensor_id != sensor.id or window.sensor_id != sensor.id:
        raise ApiError(
            status_code=422,
            code="SENSOR_SESSION_MISMATCH",
            message="Signal window and session do not belong to the selected sensor.",
        )
    if window.session_id != session.id:
        raise ApiError(
            status_code=422,
            code="WINDOW_SESSION_MISMATCH",
            message="Signal window does not belong to the selected session.",
        )

    if payload.event_id and db.execute(
        select(Prediction.id).where(Prediction.event_id == payload.event_id)
    ).first():
        raise ApiError(
            status_code=409,
            code="PREDICTION_EXISTS",
            message="A prediction with this event identifier already exists.",
        )

    inferred_at = _aware(payload.inferred_at)
    if inferred_at is None:
        raise ApiError(
            status_code=422,
            code="INVALID_INFERENCE_TIME",
            message="Inference time is required.",
        )

    model = None
    if payload.decision == PredictionDecision.SENSOR_INVALID:
        if window.quality_status != DataQuality.SENSOR_INVALID:
            raise ApiError(
                status_code=422,
                code="DECISION_QUALITY_MISMATCH",
                message="A SENSOR_INVALID prediction requires a sensor-invalid window.",
            )
        if payload.data_quality != DataQuality.SENSOR_INVALID:
            raise ApiError(
                status_code=422,
                code="DECISION_QUALITY_MISMATCH",
                message="A SENSOR_INVALID prediction requires SENSOR_INVALID data quality.",
            )
        equipment_condition = None
    else:
        if window.quality_status != DataQuality.VALID:
            raise ApiError(
                status_code=422,
                code="DECISION_QUALITY_MISMATCH",
                message="Condition decisions are only allowed for valid windows.",
            )
        if payload.model_version_id is None:
            raise ApiError(
                status_code=422,
                code="MODEL_REQUIRED",
                message="A model version is required for a condition decision.",
            )
        model = get_model_or_404(db, payload.model_version_id)
        if not _model_was_active_at(model, inferred_at):
            raise ApiError(
                status_code=422,
                code="MODEL_NOT_ACTIVE_AT_INFERENCE",
                message="The referenced model was not active at the inference time.",
            )
        if not _feature_contract_compatible(window, model):
            raise ApiError(
                status_code=422,
                code="FEATURE_CONTRACT_MISMATCH",
                message="The signal window does not satisfy the model feature contract.",
            )
        equipment_condition = _CONDITION_BY_DECISION[payload.decision]

    prediction = Prediction(
        event_id=payload.event_id,
        pump_id=pump.id,
        sensor_id=sensor.id,
        session_id=session.id,
        signal_window_id=window.id,
        model_version_id=model.id if model is not None else None,
        operating_regime_id=session.regime_id,
        decision=payload.decision,
        data_quality=payload.data_quality,
        equipment_condition=equipment_condition,
        decision_score=payload.decision_score,
        uncertainty_score=payload.uncertainty_score,
        explanation=payload.explanation,
        latency_ms=payload.latency_ms,
        inferred_at=inferred_at,
        data_provenance=session.data_provenance,
    )
    db.add(prediction)
    try:
        db.flush()
        _create_prediction_alert(
            db,
            prediction,
            pump=pump,
            sensor=sensor,
            session=session,
            model=model,
            actor=actor,
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="PREDICTION_EXISTS",
            message="A prediction with this event identifier already exists.",
        ) from exc
    return get_prediction_or_404(db, prediction.id)


def list_predictions(
    db: Session,
    *,
    page: int,
    page_size: int,
    pump_id: str | None = None,
    sensor_id: str | None = None,
    decision: PredictionDecision | None = None,
    model_version_id: str | None = None,
) -> tuple[list[Prediction], int]:
    filters = []
    if pump_id is not None:
        filters.append(Prediction.pump_id == pump_id)
    if sensor_id is not None:
        filters.append(Prediction.sensor_id == sensor_id)
    if decision is not None:
        filters.append(Prediction.decision == decision)
    if model_version_id is not None:
        filters.append(Prediction.model_version_id == model_version_id)

    count_stmt = select(func.count(Prediction.id))
    list_stmt = select(Prediction).options(*_prediction_options())
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.execute(count_stmt).scalar_one()
    predictions = (
        db.execute(
            list_stmt.order_by(Prediction.inferred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(predictions), total


def predictions_since(
    db: Session,
    *,
    pump_id: str,
    sensor_id: str | None,
    since: datetime,
) -> list[Prediction]:
    stmt = (
        select(Prediction)
        .join(AcquisitionSession, Prediction.session_id == AcquisitionSession.id)
        .options(*_prediction_options())
        .where(
            AcquisitionSession.pump_id == pump_id,
            Prediction.inferred_at >= since,
        )
        .order_by(Prediction.inferred_at.asc())
        .limit(100)
    )
    if sensor_id is not None:
        stmt = stmt.where(Prediction.sensor_id == sensor_id)
    return list(db.execute(stmt).scalars().all())
