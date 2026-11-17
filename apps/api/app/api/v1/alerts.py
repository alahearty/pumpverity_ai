from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    RoleName,
)
from app.schemas.alerts import AlertDetail, AlertPublic, AlertReviewPublic
from app.schemas.common import Page
from app.services import alerts as alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])
_ALERT_WRITE = require_roles(RoleName.ENGINEER, RoleName.REVIEWER)


@router.get("", response_model=Page[AlertPublic], summary="List alerts")
def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: AlertStatus | None = Query(default=None),
    category: AlertCategory | None = Query(default=None),
    severity: AlertSeverity | None = Query(default=None),
    pump_id: str | None = Query(default=None, max_length=36),
    sensor_id: str | None = Query(default=None, max_length=36),
    assigned_to: str | None = Query(default=None, max_length=36),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[AlertPublic]:
    alerts, total = alert_service.list_alerts(
        db,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        severity=severity,
        pump_id=pump_id,
        sensor_id=sensor_id,
        assigned_to=assigned_to,
        created_from=created_from,
        created_to=created_to,
    )
    return Page[AlertPublic](
        items=[AlertPublic.from_alert(alert) for alert in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertDetail, summary="Get alert detail")
def get_alert(
    alert_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertDetail:
    alert = alert_service.get_alert_or_404(db, alert_id)
    reviews = sorted(alert.reviews, key=lambda review: review.created_at)
    return AlertDetail.from_alert_detail(alert, reviews)


@router.get(
    "/{alert_id}/reviews",
    response_model=list[AlertReviewPublic],
    summary="List alert reviews",
)
def list_reviews(
    alert_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertReviewPublic]:
    return [
        AlertReviewPublic.from_review(review)
        for review in alert_service.list_reviews(db, alert_id)
    ]


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertDetail,
    summary="Acknowledge an alert",
)
def acknowledge_alert(
    alert_id: str,
    request: Request,
    actor: User = Depends(_ALERT_WRITE),
    db: Session = Depends(get_db),
) -> AlertDetail:
    alert = alert_service.acknowledge_alert(db, alert_id, actor, request)
    reviews = sorted(alert.reviews, key=lambda review: review.created_at)
    return AlertDetail.from_alert_detail(alert, reviews)
