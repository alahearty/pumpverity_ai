from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import PredictionDecision, RoleName
from app.schemas.common import Page
from app.schemas.predictions import PredictionCreate, PredictionPublic
from app.services import predictions as prediction_service

router = APIRouter(prefix="/predictions", tags=["Predictions"])
_ACQUISITION_WRITE = require_roles(RoleName.ENGINEER, RoleName.RESEARCHER)


@router.get(
    "",
    response_model=Page[PredictionPublic],
    summary="List persisted predictions",
)
def list_predictions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    pump_id: str | None = Query(default=None, max_length=36),
    sensor_id: str | None = Query(default=None, max_length=36),
    decision: PredictionDecision | None = Query(default=None),
    model_version_id: str | None = Query(default=None, max_length=36),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[PredictionPublic]:
    predictions, total = prediction_service.list_predictions(
        db,
        page=page,
        page_size=page_size,
        pump_id=pump_id,
        sensor_id=sensor_id,
        decision=decision,
        model_version_id=model_version_id,
    )
    return Page[PredictionPublic](
        items=[PredictionPublic.from_prediction(item) for item in predictions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=PredictionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Persist an edge inference result",
)
def create_prediction(
    payload: PredictionCreate,
    request: Request,
    actor: User = Depends(_ACQUISITION_WRITE),
    db: Session = Depends(get_db),
) -> PredictionPublic:
    prediction = prediction_service.create_prediction(db, payload, actor, request)
    return PredictionPublic.from_prediction(prediction)


@router.get(
    "/{prediction_id}",
    response_model=PredictionPublic,
    summary="Get a prediction with model and window context",
)
def get_prediction(
    prediction_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionPublic:
    prediction = prediction_service.get_prediction_or_404(db, prediction_id)
    return PredictionPublic.from_prediction(prediction)
