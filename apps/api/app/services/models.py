from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import ApiError
from app.db.models import ModelEvaluation, ModelVersion, User, utcnow
from app.domain.enums import ModelRuntime, ModelStatus
from app.schemas.models import ModelEvaluationCreate, ModelRegister
from app.services.audit import record_audit

SUPPORTED_ACTIVATION_RUNTIMES = {
    ModelRuntime.BASELINE,
    ModelRuntime.LINEAR_JSON,
}


def _model_options():
    return (
        joinedload(ModelVersion.registered_by),
        selectinload(ModelVersion.evaluations).joinedload(ModelEvaluation.verified_by),
    )


def sorted_evaluations(model: ModelVersion) -> list[ModelEvaluation]:
    return sorted(model.evaluations, key=lambda evaluation: evaluation.evaluated_at, reverse=True)


def get_model_or_404(db: Session, model_id: str) -> ModelVersion:
    model = db.execute(
        select(ModelVersion).options(*_model_options()).where(ModelVersion.id == model_id)
    ).scalar_one_or_none()
    if model is None:
        raise ApiError(
            status_code=404,
            code="MODEL_NOT_FOUND",
            message="Model version not found.",
        )
    return model


def list_models(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: ModelStatus | None = None,
    runtime: ModelRuntime | None = None,
    q: str | None = None,
) -> tuple[list[ModelVersion], int]:
    filters = []
    if status is not None:
        filters.append(ModelVersion.status == status)
    if runtime is not None:
        filters.append(ModelVersion.runtime == runtime)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                ModelVersion.model_code.ilike(pattern),
                ModelVersion.name.ilike(pattern),
                ModelVersion.version.ilike(pattern),
            )
        )

    count_stmt = select(func.count(ModelVersion.id))
    list_stmt = select(ModelVersion).options(*_model_options())
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.execute(count_stmt).scalar_one()
    models = (
        db.execute(
            list_stmt.order_by(ModelVersion.registered_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(models), total


def get_active_model(db: Session) -> ModelVersion | None:
    return db.execute(
        select(ModelVersion)
        .options(*_model_options())
        .where(ModelVersion.status == ModelStatus.ACTIVE)
        .order_by(ModelVersion.activated_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _audit(
    db: Session,
    *,
    action: str,
    model: ModelVersion,
    actor: User,
    request: Request,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    record_audit(
        db,
        action=action,
        actor=actor,
        entity_type="model_version",
        entity_id=model.id,
        before=before,
        after=after,
        request=request,
    )


def register_model(
    db: Session,
    payload: ModelRegister,
    actor: User,
    request: Request,
) -> ModelVersion:
    existing = db.execute(
        select(ModelVersion.id).where(
            ModelVersion.model_code == payload.model_code,
            ModelVersion.version == payload.version,
        )
    ).first()
    if existing is not None:
        raise ApiError(
            status_code=409,
            code="MODEL_VERSION_EXISTS",
            message="A model with this code and version already exists.",
        )

    model = ModelVersion(
        model_code=payload.model_code,
        name=payload.name,
        version=payload.version,
        algorithm=payload.algorithm,
        runtime=payload.runtime,
        feature_contract=payload.feature_contract,
        training_dataset_version=payload.training_dataset_version,
        evaluation_dataset=payload.evaluation_dataset,
        deployment_compatibility=payload.deployment_compatibility,
        artifact_path=payload.artifact_path,
        artifact_sha256=payload.artifact_sha256,
        status=ModelStatus.REGISTERED,
        registered_by_id=actor.id,
        notes=payload.notes,
    )
    db.add(model)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="MODEL_VERSION_EXISTS",
            message="A model with this code and version already exists.",
        ) from exc

    _audit(
        db,
        action="MODEL_REGISTERED",
        model=model,
        actor=actor,
        request=request,
        after={
            "model_code": model.model_code,
            "version": model.version,
            "runtime": model.runtime.value,
            "artifact_sha256": model.artifact_sha256,
        },
    )
    db.commit()
    return get_model_or_404(db, model.id)


def add_evaluation(
    db: Session,
    model_id: str,
    payload: ModelEvaluationCreate,
    actor: User,
    request: Request,
) -> ModelEvaluation:
    model = get_model_or_404(db, model_id)
    if model.status == ModelStatus.REJECTED:
        raise ApiError(
            status_code=409,
            code="MODEL_REJECTED",
            message="Rejected model versions cannot receive new evaluations.",
        )
    now = utcnow()
    evaluation = ModelEvaluation(
        model_version_id=model.id,
        dataset_name=payload.dataset_name,
        dataset_version=payload.dataset_version,
        data_provenance=payload.data_provenance,
        evaluation_protocol=payload.evaluation_protocol,
        split_description=payload.split_description,
        sample_count=payload.sample_count,
        balanced_accuracy=payload.balanced_accuracy,
        macro_f1=payload.macro_f1,
        metrics=payload.metrics,
        confusion_matrix=payload.confusion_matrix,
        risk_coverage=payload.risk_coverage,
        calibration=payload.calibration,
        is_verified=payload.is_verified,
        verified_by_id=actor.id if payload.is_verified else None,
        verified_at=now if payload.is_verified else None,
        evaluated_by=payload.evaluated_by or actor.full_name,
        evaluated_at=now,
        notes=payload.notes,
    )
    db.add(evaluation)
    db.flush()
    _audit(
        db,
        action="MODEL_EVALUATION_ADDED",
        model=model,
        actor=actor,
        request=request,
        after={
            "evaluation_id": evaluation.id,
            "dataset_name": evaluation.dataset_name,
            "data_provenance": evaluation.data_provenance.value,
            "balanced_accuracy": evaluation.balanced_accuracy,
            "macro_f1": evaluation.macro_f1,
            "is_verified": evaluation.is_verified,
        },
    )
    db.commit()
    db.refresh(evaluation)
    return evaluation


def validate_model(
    db: Session,
    model_id: str,
    actor: User,
    request: Request,
) -> ModelVersion:
    model = get_model_or_404(db, model_id)
    if model.status == ModelStatus.ACTIVE:
        return model
    if model.status == ModelStatus.REJECTED:
        raise ApiError(
            status_code=409,
            code="MODEL_REJECTED",
            message="Rejected model versions cannot be validated.",
        )
    if model.runtime not in SUPPORTED_ACTIVATION_RUNTIMES:
        raise ApiError(
            status_code=422,
            code="RUNTIME_NOT_SUPPORTED",
            message="This runtime is not supported by the Stage 4 edge inference path.",
        )
    features = model.feature_contract.get("features") if model.feature_contract else None
    if not isinstance(features, list) or not features:
        raise ApiError(
            status_code=422,
            code="INVALID_FEATURE_CONTRACT",
            message="The model feature contract is missing a feature list.",
        )
    if len(model.artifact_sha256) != 64:
        raise ApiError(
            status_code=422,
            code="INVALID_ARTIFACT_HASH",
            message="The model artefact hash is invalid.",
        )

    verified = [ev for ev in sorted_evaluations(model) if ev.is_verified]
    if not verified:
        raise ApiError(
            status_code=422,
            code="EVALUATION_REQUIRED",
            message="A verified evaluation is required before validation.",
        )

    before = model.status.value
    model.status = ModelStatus.VALIDATED
    model.validated_at = datetime.now(UTC)
    _audit(
        db,
        action="MODEL_VALIDATED",
        model=model,
        actor=actor,
        request=request,
        before={"status": before},
        after={"status": model.status.value},
    )
    db.commit()
    return get_model_or_404(db, model.id)


def activate_model(
    db: Session,
    model_id: str,
    actor: User,
    request: Request,
) -> ModelVersion:
    model = get_model_or_404(db, model_id)
    if model.status == ModelStatus.ACTIVE:
        return model
    if model.status != ModelStatus.VALIDATED:
        raise ApiError(
            status_code=409,
            code="MODEL_NOT_VALIDATED",
            message="Only a validated model can be activated.",
        )
    if model.runtime not in SUPPORTED_ACTIVATION_RUNTIMES:
        raise ApiError(
            status_code=422,
            code="RUNTIME_NOT_SUPPORTED",
            message="This runtime is not supported by the edge inference path.",
        )
    verified = [ev for ev in sorted_evaluations(model) if ev.is_verified]
    if not verified:
        raise ApiError(
            status_code=422,
            code="EVALUATION_REQUIRED",
            message="A verified evaluation is required before activation.",
        )

    previous_models = (
        db.execute(
            select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE)
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    for previous in previous_models:
        previous.status = ModelStatus.RETIRED
        previous.retired_at = now
        _audit(
            db,
            action="MODEL_RETIRED",
            model=previous,
            actor=actor,
            request=request,
            before={"status": ModelStatus.ACTIVE.value},
            after={"status": ModelStatus.RETIRED.value},
        )

    model.status = ModelStatus.ACTIVE
    model.activated_at = now
    model.retired_at = None
    _audit(
        db,
        action="MODEL_ACTIVATED",
        model=model,
        actor=actor,
        request=request,
        before={"status": ModelStatus.VALIDATED.value},
        after={
            "status": ModelStatus.ACTIVE.value,
            "artifact_sha256": model.artifact_sha256,
            "runtime": model.runtime.value,
        },
    )
    db.commit()
    return get_model_or_404(db, model.id)


def rollback_model(
    db: Session,
    actor: User,
    request: Request,
) -> ModelVersion:
    active = get_active_model(db)
    if active is None:
        raise ApiError(
            status_code=409,
            code="NO_ACTIVE_MODEL",
            message="There is no active model to roll back.",
        )
    previous = db.execute(
        select(ModelVersion)
        .options(*_model_options())
        .where(
            ModelVersion.status == ModelStatus.RETIRED,
            ModelVersion.activated_at.is_not(None),
            ModelVersion.id != active.id,
        )
        .order_by(ModelVersion.activated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous is None:
        raise ApiError(
            status_code=409,
            code="NO_ROLLBACK_MODEL",
            message="No previously active model is available for rollback.",
        )

    now = datetime.now(UTC)
    active.status = ModelStatus.RETIRED
    active.retired_at = now
    previous.status = ModelStatus.ACTIVE
    previous.activated_at = now
    previous.retired_at = None
    _audit(
        db,
        action="MODEL_ROLLED_BACK",
        model=previous,
        actor=actor,
        request=request,
        before={"previous_active_id": active.id},
        after={"active_id": previous.id},
    )
    db.commit()
    return get_model_or_404(db, previous.id)
