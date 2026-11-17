from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.db.models import Alert, AlertReview
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    DataQuality,
    LabelSource,
    PredictionDecision,
    Provenance,
    ReviewAction,
)
from app.schemas.predictions import PredictionPublic


class AlertReviewCreate(BaseModel):
    alert_id: str = Field(min_length=1, max_length=36)
    action: ReviewAction
    reviewed_label: PredictionDecision | None = None
    notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def validate_review_shape(self) -> Self:
        if self.action is ReviewAction.ACKNOWLEDGE:
            raise ValueError("Use the acknowledge endpoint for acknowledgement.")
        if (
            self.action in {ReviewAction.CONFIRM_LABEL, ReviewAction.CORRECT_LABEL}
            and self.reviewed_label is None
        ):
            raise ValueError("A label is required for label confirmation or correction.")
        if self.action in {ReviewAction.REVIEW, ReviewAction.ADD_NOTE} and (
            len(self.notes.strip()) < 3
        ):
            raise ValueError("Notes are required for a review or note action.")
        return self


class AlertReviewPublic(BaseModel):
    id: str
    alert_id: str
    reviewer_id: str
    reviewer_name: str
    action: ReviewAction
    reviewed_label: PredictionDecision | None
    notes: str
    label_source: LabelSource
    is_verified_ground_truth: bool
    created_at: datetime

    @classmethod
    def from_review(cls, review: AlertReview) -> "AlertReviewPublic":
        return cls(
            id=review.id,
            alert_id=review.alert_id,
            reviewer_id=review.reviewer_id,
            reviewer_name=review.reviewer.full_name if review.reviewer else "Unknown reviewer",
            action=review.action,
            reviewed_label=review.reviewed_label,
            notes=review.notes,
            label_source=review.label_source,
            is_verified_ground_truth=review.is_verified_ground_truth,
            created_at=review.created_at,
        )


class AlertPublic(BaseModel):
    id: str
    event_id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    prediction_id: str | None
    signal_window_id: str | None
    window_start: datetime | None
    window_end: datetime | None
    category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    decision: PredictionDecision | None
    data_quality: DataQuality | None
    decision_score: float | None
    uncertainty_score: float | None
    model_name: str | None
    model_version: str | None
    data_provenance: Provenance
    assigned_reviewer_id: str | None
    assigned_reviewer_name: str | None
    acknowledged_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    review_count: int

    @classmethod
    def from_alert(cls, alert: Alert) -> "AlertPublic":
        prediction = alert.prediction
        model = prediction.model_version if prediction is not None else None
        window = prediction.window if prediction is not None else None
        return cls(
            id=alert.id,
            event_id=alert.event_id,
            pump_id=alert.pump_id,
            pump_code=alert.pump.pump_code,
            sensor_id=alert.sensor_id,
            sensor_code=alert.sensor.sensor_code,
            prediction_id=alert.prediction_id,
            signal_window_id=prediction.signal_window_id if prediction else None,
            window_start=window.window_start if window else None,
            window_end=window.window_end if window else None,
            category=alert.category,
            severity=alert.severity,
            status=alert.status,
            title=alert.title,
            description=alert.description,
            decision=prediction.decision if prediction else None,
            data_quality=prediction.data_quality if prediction else None,
            decision_score=prediction.decision_score if prediction else None,
            uncertainty_score=prediction.uncertainty_score if prediction else None,
            model_name=model.name if model else None,
            model_version=model.version if model else None,
            data_provenance=alert.data_provenance,
            assigned_reviewer_id=alert.assigned_reviewer_id,
            assigned_reviewer_name=(
                alert.assigned_reviewer.full_name if alert.assigned_reviewer else None
            ),
            acknowledged_at=alert.acknowledged_at,
            closed_at=alert.closed_at,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            review_count=len(alert.reviews),
        )


class AlertDetail(AlertPublic):
    prediction: PredictionPublic | None
    reviews: list[AlertReviewPublic]

    @classmethod
    def from_alert_detail(
        cls, alert: Alert, reviews: list[AlertReview]
    ) -> "AlertDetail":
        base = AlertPublic.from_alert(alert).model_dump()
        return cls(
            **base,
            prediction=PredictionPublic.from_prediction(alert.prediction)
            if alert.prediction is not None
            else None,
            reviews=[AlertReviewPublic.from_review(review) for review in reviews],
        )


class AlertSummary(BaseModel):
    total: int
    open: int
    acknowledged: int
    reviewed: int
    closed: int
    dismissed: int
    fault: int
    uncertain: int
    sensor_invalid: int
