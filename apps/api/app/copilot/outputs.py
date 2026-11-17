from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    DataQuality,
    EquipmentCondition,
    PredictionDecision,
    Provenance,
    SensorType,
)

SIMULATION_NOTICE = (
    "Persisted simulated data. It is not an experimental measurement, industrial diagnosis "
    "or verified machine-learning ground truth."
)
SCORE_NOTICE = (
    "Decision and uncertainty scores are model outputs, not probabilities of mechanical failure."
)


class PumpSensorStatus(BaseModel):
    sensor_id: str
    sensor_code: str
    sensor_type: SensorType
    is_active: bool
    sampling_rate_hz: float
    sampling_status: str
    latest_quality: DataQuality | None
    latest_rms_g: float | None
    invalid_windows: int
    missing_window_gaps: int
    last_valid_reading_at: datetime | None
    provenance: Provenance | None


class PumpStatusOutput(BaseModel):
    pump_id: str
    pump_code: str
    pump_name: str
    pump_status: str
    location: str
    rated_speed_rpm: int
    sensors: list[PumpSensorStatus]
    equipment_condition: EquipmentCondition | None
    condition_available: bool
    data_quality: DataQuality | None
    latest_prediction_decision: PredictionDecision | None
    latest_window_at: datetime | None
    data_provenance: Provenance | None
    data_mode: str
    edge_connectivity: str
    edge_note: str
    generated_at: datetime
    notice: str = SIMULATION_NOTICE


class PredictionEvidence(BaseModel):
    available: bool
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    prediction_id: str | None = None
    decision: PredictionDecision | None = None
    equipment_condition: EquipmentCondition | None = None
    data_quality: DataQuality | None = None
    decision_score: float | None = None
    uncertainty_score: float | None = None
    explanation: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    model_runtime: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    scenario: str | None = None
    features: dict[str, Any] | None = None
    provenance: Provenance | None = None
    inferred_at: datetime | None = None
    generated_at: datetime
    message: str
    score_notice: str = SCORE_NOTICE


class FaultEventSummary(BaseModel):
    alert_id: str
    category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    title: str
    decision: PredictionDecision | None
    window_start: datetime | None
    window_end: datetime | None
    created_at: datetime
    model_name: str | None
    model_version: str | None
    review_count: int
    provenance: Provenance


class FaultHistoryOutput(BaseModel):
    available: bool
    pump_id: str
    pump_code: str
    events: list[FaultEventSummary]
    total_events: int
    message: str
    generated_at: datetime
    notice: str = SIMULATION_NOTICE


class VibrationPoint(BaseModel):
    timestamp: datetime
    rms_g: float | None
    peak_g: float | None
    quality: DataQuality
    provenance: Provenance
    scenario: str | None


class VibrationSummaryOutput(BaseModel):
    available: bool
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    units: Literal["g"]
    sampling_rate_hz: float
    window_count: int
    valid_window_count: int
    invalid_window_count: int
    latest_rms_g: float | None
    mean_rms_g: float | None
    min_rms_g: float | None
    max_rms_g: float | None
    latest_peak_g: float | None
    latest_window_at: datetime | None
    provenance: Provenance | None
    points: list[VibrationPoint]
    message: str
    generated_at: datetime
    notice: str = SIMULATION_NOTICE


class SensorHealthSummary(BaseModel):
    sensor_id: str
    sensor_code: str
    sensor_type: SensorType
    is_active: bool
    sampling_rate_hz: float
    sampling_status: str
    latest_quality: DataQuality | None
    total_windows: int
    valid_windows: int
    invalid_windows: int
    missing_window_gaps: int
    freshness_seconds: float | None
    last_valid_reading_at: datetime | None
    latest_rms_g: float | None
    latest_peak_g: float | None
    provenance: Provenance | None
    connection_state: str
    validation_issues: list[dict[str, Any]]


class SensorHealthOutput(BaseModel):
    available: bool
    pump_id: str
    pump_code: str
    sensors: list[SensorHealthSummary]
    message: str
    generated_at: datetime
    notice: str = SIMULATION_NOTICE


class EvaluationEvidence(BaseModel):
    dataset_name: str
    dataset_version: str
    provenance: Provenance
    protocol: str
    sample_count: int
    balanced_accuracy: float | None
    macro_f1: float | None
    is_verified: bool
    evaluated_at: datetime
    metrics: dict[str, Any] | None
    notes: str | None


class ModelEvaluationOutput(BaseModel):
    available: bool
    model_id: str | None
    model_code: str | None
    name: str | None
    version: str | None
    status: str | None
    runtime: str | None
    training_dataset_version: str | None
    evaluation_dataset: str | None
    feature_contract: dict[str, Any] | None
    evaluation: EvaluationEvidence | None
    message: str
    generated_at: datetime
    notice: str = (
        "Metrics are synthetic research evidence unless their provenance and verification say "
        "otherwise. They are not real-pump performance claims."
    )


class AlertReviewSummary(BaseModel):
    review_id: str
    reviewer_name: str
    action: str
    reviewed_label: PredictionDecision | None
    notes: str
    label_source: str
    is_verified_ground_truth: bool
    created_at: datetime


class AlertDetailsOutput(BaseModel):
    alert_id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    provenance: Provenance
    assigned_reviewer_name: str | None
    acknowledged_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    prediction: PredictionEvidence | None
    reviews: list[AlertReviewSummary]
    generated_at: datetime
    notice: str = (
        "This alert references an AI prediction and may contain engineer review. Engineer "
        "reviews are not verified experimental ground truth."
    )


class EdgeConnectivityOutput(BaseModel):
    pump_id: str
    pump_code: str
    edge_connectivity: str
    data_mode: str
    buffering_state: str | None
    last_window_at: datetime | None
    last_valid_window_at: datetime | None
    api_note: str
    generated_at: datetime
    notice: str = (
        "The monitoring API connection is not the physical edge-device connection. No physical "
        "live channel is configured in this research build."
    )


class MonitoringOverviewOutput(BaseModel):
    pumps_total: int
    pumps_active: int
    sensors_total: int
    active_alerts: int
    windows_total: int
    valid_windows: int
    invalid_windows: int
    equipment_condition: EquipmentCondition | None
    condition_available: bool
    data_quality: DataQuality | None
    data_mode: str
    active_model_name: str | None
    active_model_version: str | None
    latest_evaluation_f1: float | None
    latest_evaluation_provenance: Provenance | None
    latest_window_at: datetime | None
    latest_prediction_decision: PredictionDecision | None
    generated_at: datetime
    notice: str = SIMULATION_NOTICE


class WriteResultOutput(BaseModel):
    success: bool
    action: str
    target_id: str
    status: str
    message: str
    review_id: str | None = None
    report_id: str | None = None
    report_path: str | None = None
    report_sha256: str | None = None
    includes_simulated_data: bool | None = None
    original_prediction_preserved: bool = True
    generated_at: datetime
    notice: str = (
        "The original AI prediction remains immutable. This action is attributable to the "
        "authorised engineer/reviewer; it is not verified experimental ground truth."
    )
