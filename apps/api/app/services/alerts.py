from datetime import datetime

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import ApiError
from app.db.models import Alert, AlertReview, Prediction, User, utcnow
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    LabelSource,
    ReviewAction,
)
from app.schemas.alerts import AlertReviewCreate
from app.services.audit import record_audit


def _alert_options():
    return (
        joinedload(Alert.pump),
        joinedload(Alert.sensor),
        joinedload(Alert.assigned_reviewer),
        joinedload(Alert.prediction).joinedload(Prediction.model_version),
        joinedload(Alert.prediction).joinedload(Prediction.window),
        joinedload(Alert.prediction).joinedload(Prediction.session),
        joinedload(Alert.prediction).joinedload(Prediction.pump),
        joinedload(Alert.prediction).joinedload(Prediction.sensor),
        joinedload(Alert.prediction).joinedload(Prediction.operating_regime),
        selectinload(Alert.reviews).joinedload(AlertReview.reviewer),
    )


def get_alert_or_404(db: Session, alert_id: str) -> Alert:
    alert = db.execute(
        select(Alert).options(*_alert_options()).where(Alert.id == alert_id)
    ).scalar_one_or_none()
    if alert is None:
        raise ApiError(
            status_code=404,
            code="ALERT_NOT_FOUND",
            message="Alert not found.",
        )
    return alert


def list_alerts(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: AlertStatus | None = None,
    category: AlertCategory | None = None,
    severity: AlertSeverity | None = None,
    pump_id: str | None = None,
    sensor_id: str | None = None,
    assigned_to: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[Alert], int]:
    filters = []
    if status is not None:
        filters.append(Alert.status == status)
    if category is not None:
        filters.append(Alert.category == category)
    if severity is not None:
        filters.append(Alert.severity == severity)
    if pump_id is not None:
        filters.append(Alert.pump_id == pump_id)
    if sensor_id is not None:
        filters.append(Alert.sensor_id == sensor_id)
    if assigned_to is not None:
        filters.append(Alert.assigned_reviewer_id == assigned_to)
    if created_from is not None:
        filters.append(Alert.created_at >= created_from)
    if created_to is not None:
        filters.append(Alert.created_at <= created_to)

    count_stmt = select(func.count(Alert.id))
    list_stmt = select(Alert).options(*_alert_options())
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.execute(count_stmt).scalar_one()
    alerts = (
        db.execute(
            list_stmt.order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(alerts), total


def list_reviews(db: Session, alert_id: str) -> list[AlertReview]:
    get_alert_or_404(db, alert_id)
    return list(
        db.execute(
            select(AlertReview)
            .options(joinedload(AlertReview.reviewer))
            .where(AlertReview.alert_id == alert_id)
            .order_by(AlertReview.created_at.asc())
        )
        .scalars()
        .all()
    )


def acknowledge_alert(
    db: Session,
    alert_id: str,
    actor: User,
    request: Request,
) -> Alert:
    alert = get_alert_or_404(db, alert_id)
    if alert.status in {AlertStatus.CLOSED, AlertStatus.DISMISSED}:
        raise ApiError(
            status_code=409,
            code="ALERT_CLOSED",
            message="Closed or dismissed alerts cannot be acknowledged.",
        )
    if alert.status is AlertStatus.OPEN:
        now = utcnow()
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = now
        if alert.assigned_reviewer_id is None:
            alert.assigned_reviewer = actor
        review = AlertReview(
            alert=alert,
            reviewer=actor,
            action=ReviewAction.ACKNOWLEDGE,
            notes="Alert acknowledged.",
            label_source=LabelSource.ENGINEER_REVIEW,
            is_verified_ground_truth=False,
        )
        db.add(review)
        db.flush()
        record_audit(
            db,
            action="ALERT_ACKNOWLEDGED",
            actor=actor,
            entity_type="alert",
            entity_id=alert.id,
            after={"status": alert.status.value, "review_id": review.id},
            request=request,
        )
        db.commit()
    return get_alert_or_404(db, alert_id)


def create_review(
    db: Session,
    payload: AlertReviewCreate,
    actor: User,
    request: Request,
) -> AlertReview:
    alert = get_alert_or_404(db, payload.alert_id)
    if alert.status in {AlertStatus.CLOSED, AlertStatus.DISMISSED}:
        raise ApiError(
            status_code=409,
            code="ALERT_CLOSED",
            message="Closed or dismissed alerts cannot be reviewed.",
        )
    prediction = alert.prediction
    if payload.action is ReviewAction.CONFIRM_LABEL and (
        prediction is None or payload.reviewed_label != prediction.decision
    ):
        raise ApiError(
            status_code=422,
            code="LABEL_MISMATCH",
            message="Confirmed label must match the original prediction decision.",
        )
    if payload.action is ReviewAction.CORRECT_LABEL:
        if payload.reviewed_label is None:
            raise ApiError(
                status_code=422,
                code="LABEL_REQUIRED",
                message="A corrected label is required.",
            )
        if prediction is not None and payload.reviewed_label == prediction.decision:
            raise ApiError(
                status_code=422,
                code="LABEL_NOT_CORRECTED",
                message="A corrected label must differ from the original prediction.",
            )
    if payload.action not in {
        ReviewAction.CONFIRM_LABEL,
        ReviewAction.CORRECT_LABEL,
    } and payload.reviewed_label is not None:
        raise ApiError(
            status_code=422,
            code="LABEL_NOT_ALLOWED",
            message="Only confirmation or correction actions may carry a label.",
        )

    now = utcnow()
    before_status = alert.status
    if payload.action is ReviewAction.CLOSE:
        alert.status = AlertStatus.CLOSED
        alert.closed_at = now
    elif payload.action is ReviewAction.ADD_NOTE:
        if alert.status is AlertStatus.OPEN:
            alert.status = AlertStatus.ACKNOWLEDGED
    else:
        alert.status = AlertStatus.REVIEWED

    if alert.acknowledged_at is None:
        alert.acknowledged_at = now
    if alert.assigned_reviewer_id is None:
        alert.assigned_reviewer = actor

    review = AlertReview(
        alert=alert,
        reviewer=actor,
        action=payload.action,
        reviewed_label=payload.reviewed_label,
        notes=payload.notes.strip(),
        label_source=LabelSource.ENGINEER_REVIEW,
        is_verified_ground_truth=False,
    )
    db.add(review)
    db.flush()

    audit_action = (
        "ALERT_CLOSED" if payload.action is ReviewAction.CLOSE else "ALERT_REVIEWED"
    )
    record_audit(
        db,
        action=audit_action,
        actor=actor,
        entity_type="alert",
        entity_id=alert.id,
        before={"status": before_status.value},
        after={
            "status": alert.status.value,
            "review_id": review.id,
            "action": payload.action.value,
            "reviewed_label": payload.reviewed_label.value
            if payload.reviewed_label is not None
            else None,
            "is_verified_ground_truth": False,
        },
        request=request,
    )
    db.commit()
    return review
