from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.alerts import AlertReviewCreate, AlertReviewPublic
from app.services import alerts as alert_service

router = APIRouter(prefix="/alert-reviews", tags=["Alerts"])
_ALERT_WRITE = require_roles(RoleName.ENGINEER, RoleName.REVIEWER)


@router.post(
    "",
    response_model=AlertReviewPublic,
    summary="Record an engineering review for an alert",
)
def create_review(
    payload: AlertReviewCreate,
    request: Request,
    actor: User = Depends(_ALERT_WRITE),
    db: Session = Depends(get_db),
) -> AlertReviewPublic:
    review = alert_service.create_review(db, payload, actor, request)
    return AlertReviewPublic.from_review(review)
