from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import ModelEvaluation, ModelVersion
from app.domain.enums import ModelRuntime, ModelStatus, Provenance


class ModelEvaluationCreate(BaseModel):
    dataset_name: str = Field(min_length=1, max_length=160)
    dataset_version: str = Field(min_length=1, max_length=120)
    data_provenance: Provenance
    evaluation_protocol: str = Field(min_length=1, max_length=255)
    split_description: str = Field(min_length=1)
    sample_count: int = Field(ge=0)
    balanced_accuracy: float | None = Field(default=None, ge=0, le=1)
    macro_f1: float | None = Field(default=None, ge=0, le=1)
    metrics: dict[str, Any] | None = None
    confusion_matrix: dict[str, Any] | None = None
    risk_coverage: Any = None
    calibration: dict[str, Any] | None = None
    is_verified: bool = False
    evaluated_by: str | None = Field(default=None, max_length=160)
    notes: str | None = None

    @model_validator(mode="after")
    def verified_requires_metrics(self) -> "ModelEvaluationCreate":
        if self.is_verified and (
            self.balanced_accuracy is None or self.macro_f1 is None
        ):
            raise ValueError(
                "A verified evaluation must include balanced_accuracy and macro_f1."
            )
        return self


class ModelEvaluationPublic(BaseModel):
    id: str
    model_version_id: str
    dataset_name: str
    dataset_version: str
    data_provenance: Provenance
    evaluation_protocol: str
    split_description: str
    sample_count: int
    balanced_accuracy: float | None
    macro_f1: float | None
    metrics: dict[str, Any] | None
    confusion_matrix: dict[str, Any] | None
    risk_coverage: Any
    calibration: dict[str, Any] | None
    is_verified: bool
    verified_by_name: str | None
    verified_at: datetime | None
    evaluated_by: str
    evaluated_at: datetime
    notes: str | None

    @classmethod
    def from_evaluation(cls, evaluation: ModelEvaluation) -> "ModelEvaluationPublic":
        return cls(
            id=evaluation.id,
            model_version_id=evaluation.model_version_id,
            dataset_name=evaluation.dataset_name,
            dataset_version=evaluation.dataset_version,
            data_provenance=evaluation.data_provenance,
            evaluation_protocol=evaluation.evaluation_protocol,
            split_description=evaluation.split_description,
            sample_count=evaluation.sample_count,
            balanced_accuracy=evaluation.balanced_accuracy,
            macro_f1=evaluation.macro_f1,
            metrics=evaluation.metrics,
            confusion_matrix=evaluation.confusion_matrix,
            risk_coverage=evaluation.risk_coverage,
            calibration=evaluation.calibration,
            is_verified=evaluation.is_verified,
            verified_by_name=(
                evaluation.verified_by.full_name if evaluation.verified_by else None
            ),
            verified_at=evaluation.verified_at,
            evaluated_by=evaluation.evaluated_by,
            evaluated_at=evaluation.evaluated_at,
            notes=evaluation.notes,
        )


class ModelRegister(BaseModel):
    model_code: str = Field(
        min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
    )
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(
        min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$"
    )
    algorithm: str = Field(min_length=1, max_length=120)
    runtime: ModelRuntime
    feature_contract: dict[str, Any]
    training_dataset_version: str = Field(min_length=1, max_length=120)
    evaluation_dataset: str = Field(min_length=1, max_length=160)
    deployment_compatibility: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str = Field(min_length=1, max_length=500)
    artifact_sha256: str = Field(
        min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$"
    )
    notes: str | None = None

    @field_validator("feature_contract")
    @classmethod
    def validate_contract(cls, value: dict[str, Any]) -> dict[str, Any]:
        features = value.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("feature_contract.features must be a non-empty list")
        if not all(isinstance(feature, str) and feature for feature in features):
            raise ValueError("feature_contract.features must contain non-empty strings")
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def lower_hash(cls, value: str) -> str:
        return value.lower()


class ModelPublic(BaseModel):
    id: str
    model_code: str
    name: str
    version: str
    algorithm: str
    runtime: ModelRuntime
    feature_contract: dict[str, Any]
    training_dataset_version: str
    evaluation_dataset: str
    deployment_compatibility: dict[str, Any]
    artifact_path: str
    artifact_sha256: str
    status: ModelStatus
    registered_by_name: str | None
    registered_at: datetime
    validated_at: datetime | None
    activated_at: datetime | None
    retired_at: datetime | None
    notes: str | None
    latest_evaluation: ModelEvaluationPublic | None

    @classmethod
    def from_model(
        cls,
        model: ModelVersion,
        latest_evaluation: ModelEvaluation | None = None,
    ) -> "ModelPublic":
        return cls(
            id=model.id,
            model_code=model.model_code,
            name=model.name,
            version=model.version,
            algorithm=model.algorithm,
            runtime=model.runtime,
            feature_contract=model.feature_contract,
            training_dataset_version=model.training_dataset_version,
            evaluation_dataset=model.evaluation_dataset,
            deployment_compatibility=model.deployment_compatibility,
            artifact_path=model.artifact_path,
            artifact_sha256=model.artifact_sha256,
            status=model.status,
            registered_by_name=(
                model.registered_by.full_name if model.registered_by else None
            ),
            registered_at=model.registered_at,
            validated_at=model.validated_at,
            activated_at=model.activated_at,
            retired_at=model.retired_at,
            notes=model.notes,
            latest_evaluation=(
                ModelEvaluationPublic.from_evaluation(latest_evaluation)
                if latest_evaluation is not None
                else None
            ),
        )


class ModelDetail(ModelPublic):
    evaluations: list[ModelEvaluationPublic]

    @classmethod
    def from_model_detail(
        cls,
        model: ModelVersion,
        evaluations: list[ModelEvaluation],
    ) -> "ModelDetail":
        latest = evaluations[0] if evaluations else None
        base = ModelPublic.from_model(model, latest).model_dump()
        return cls(
            **base,
            evaluations=[
                ModelEvaluationPublic.from_evaluation(evaluation)
                for evaluation in evaluations
            ],
        )


class SupportedRuntimeList(BaseModel):
    supported: list[ModelRuntime]
