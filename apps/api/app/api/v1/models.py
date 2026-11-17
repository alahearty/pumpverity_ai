from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import ModelRuntime, ModelStatus, RoleName
from app.schemas.common import Page
from app.schemas.models import (
    ModelDetail,
    ModelEvaluationCreate,
    ModelEvaluationPublic,
    ModelPublic,
    ModelRegister,
)
from app.services import models as model_service

router = APIRouter(prefix="/models", tags=["Models"])
_WRITE_ACCESS = require_roles(RoleName.RESEARCHER)


@router.get("", response_model=Page[ModelPublic], summary="List model versions")
def list_models(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    model_status: ModelStatus | None = Query(default=None, alias="status"),
    runtime: ModelRuntime | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ModelPublic]:
    models, total = model_service.list_models(
        db,
        page=page,
        page_size=page_size,
        status=model_status,
        runtime=runtime,
        q=q,
    )
    items = []
    for model in models:
        evaluations = model_service.sorted_evaluations(model)
        items.append(
            ModelPublic.from_model(model, evaluations[0] if evaluations else None)
        )
    return Page[ModelPublic](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ModelPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register model metadata and artefact hash",
)
def register_model(
    payload: ModelRegister,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> ModelPublic:
    model = model_service.register_model(db, payload, actor, request)
    evaluations = model_service.sorted_evaluations(model)
    return ModelPublic.from_model(model, evaluations[0] if evaluations else None)


@router.get(
    "/active",
    response_model=ModelPublic | None,
    summary="Get the active model, if any",
)
def active_model(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelPublic | None:
    model = model_service.get_active_model(db)
    if model is None:
        return None
    evaluations = model_service.sorted_evaluations(model)
    return ModelPublic.from_model(model, evaluations[0] if evaluations else None)


@router.post(
    "/rollback",
    response_model=ModelPublic,
    summary="Roll back to the most recently active retired model",
)
def rollback_model(
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> ModelPublic:
    model = model_service.rollback_model(db, actor, request)
    evaluations = model_service.sorted_evaluations(model)
    return ModelPublic.from_model(model, evaluations[0] if evaluations else None)


@router.get(
    "/{model_id}",
    response_model=ModelDetail,
    summary="Get model details and evaluations",
)
def get_model(
    model_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelDetail:
    model = model_service.get_model_or_404(db, model_id)
    return ModelDetail.from_model_detail(
        model, model_service.sorted_evaluations(model)
    )


@router.post(
    "/{model_id}/evaluations",
    response_model=ModelEvaluationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an evaluation result",
)
def add_evaluation(
    model_id: str,
    payload: ModelEvaluationCreate,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> ModelEvaluationPublic:
    evaluation = model_service.add_evaluation(db, model_id, payload, actor, request)
    return ModelEvaluationPublic.from_evaluation(evaluation)


@router.post(
    "/{model_id}/validate",
    response_model=ModelPublic,
    summary="Validate a model against its verified evaluation",
)
def validate_model(
    model_id: str,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> ModelPublic:
    model = model_service.validate_model(db, model_id, actor, request)
    evaluations = model_service.sorted_evaluations(model)
    return ModelPublic.from_model(model, evaluations[0] if evaluations else None)


@router.post(
    "/{model_id}/activate",
    response_model=ModelPublic,
    summary="Activate a validated model and retire the current one",
)
def activate_model(
    model_id: str,
    request: Request,
    actor: User = Depends(_WRITE_ACCESS),
    db: Session = Depends(get_db),
) -> ModelPublic:
    model = model_service.activate_model(db, model_id, actor, request)
    evaluations = model_service.sorted_evaluations(model)
    return ModelPublic.from_model(model, evaluations[0] if evaluations else None)
