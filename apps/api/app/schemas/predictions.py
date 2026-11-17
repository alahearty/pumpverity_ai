from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.db.models import Prediction
from app.domain.enums import (
    DataQuality,
    EquipmentCondition,
    ModelRuntime,
    PredictionDecision,
    Provenance,
)
from app.schemas.equipment import OperatingRegimePublic


class PredictionCreate(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    pump_id: str = Field(min_length=1, max_length=36)
    sensor_id: str = Field(min_length=1, max_length=36)
    session_id: str = Field(min_length=1, max_length=36)
    signal_window_id: str = Field(min_length=1, max_length=36)
    model_version_id: str | None = Field(default=None, max_length=36)
    decision: PredictionDecision
    data_quality: DataQuality
    decision_score: float | None = Field(default=None, ge=0, le=1)
    uncertainty_score: float | None = Field(default=None, ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=4000)
    latency_ms: float | None = Field(default=None, ge=0)
    inferred_at: AwareDatetime

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "PredictionCreate":
        if self.decision == PredictionDecision.SENSOR_INVALID:
            if self.data_quality != DataQuality.SENSOR_INVALID:
                raise ValueError(
                    "SENSOR_INVALID predictions require data_quality=SENSOR_INVALID"
                )
            if self.model_version_id is not None:
                raise ValueError("SENSOR_INVALID predictions must not reference a model")
            if self.decision_score is not None or self.uncertainty_score is not None:
                raise ValueError("SENSOR_INVALID predictions must not include scores")
            return self

        if self.data_quality != DataQuality.VALID:
            raise ValueError("Non-sensor-invalid predictions require VALID data quality")
        if self.model_version_id is None:
            raise ValueError("A model version is required for a condition decision")
        if self.decision_score is None or self.uncertainty_score is None:
            raise ValueError("Condition decisions require decision and uncertainty scores")
        return self


class PredictionModelSummary(BaseModel):
    id: str
    model_code: str
    name: str
    version: str
    runtime: ModelRuntime


class PredictionPublic(BaseModel):
    id: str
    event_id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    session_id: str
    signal_window_id: str
    model: PredictionModelSummary | None
    operating_regime: OperatingRegimePublic | None
    decision: PredictionDecision
    data_quality: DataQuality
    equipment_condition: EquipmentCondition | None
    decision_score: float | None
    uncertainty_score: float | None
    explanation: str
    latency_ms: float | None
    inferred_at: datetime
    data_provenance: Provenance
    created_at: datetime
    window_start: datetime
    window_end: datetime
    window_quality: DataQuality
    sample_count: int
    features: dict[str, Any] | None
    scenario: str | None

    @classmethod
    def from_prediction(cls, prediction: Prediction) -> "PredictionPublic":
        window = prediction.window
        session = prediction.session
        return cls(
            id=prediction.id,
            event_id=prediction.event_id,
            pump_id=prediction.pump_id,
            pump_code=prediction.pump.pump_code,
            sensor_id=prediction.sensor_id,
            sensor_code=prediction.sensor.sensor_code,
            session_id=prediction.session_id,
            signal_window_id=prediction.signal_window_id,
            model=(
                PredictionModelSummary(
                    id=prediction.model_version.id,
                    model_code=prediction.model_version.model_code,
                    name=prediction.model_version.name,
                    version=prediction.model_version.version,
                    runtime=prediction.model_version.runtime,
                )
                if prediction.model_version is not None
                else None
            ),
            operating_regime=(
                OperatingRegimePublic.model_validate(prediction.operating_regime)
                if prediction.operating_regime is not None
                else None
            ),
            decision=prediction.decision,
            data_quality=prediction.data_quality,
            equipment_condition=prediction.equipment_condition,
            decision_score=prediction.decision_score,
            uncertainty_score=prediction.uncertainty_score,
            explanation=prediction.explanation or "",
            latency_ms=prediction.latency_ms,
            inferred_at=prediction.inferred_at,
            data_provenance=prediction.data_provenance,
            created_at=prediction.created_at,
            window_start=window.window_start,
            window_end=window.window_end,
            window_quality=window.quality_status,
            sample_count=window.sample_count,
            features=window.features,
            scenario=session.scenario,
        )
