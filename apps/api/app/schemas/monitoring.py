from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.domain.enums import (
    ConnectivityStatus,
    DataQuality,
    EquipmentCondition,
    ModelStatus,
    Provenance,
    SensorType,
    SessionStatus,
)
from app.schemas.predictions import PredictionPublic


class WindowPoint(BaseModel):
    window_id: str
    session_id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    window_index: int
    window_start: datetime
    window_end: datetime
    quality_status: DataQuality
    data_provenance: Provenance
    scenario: str | None
    sample_count: int
    rms: float | None
    peak_abs: float | None
    validation_issue_codes: list[str]


class LiveWindow(WindowPoint):
    sampling_rate_hz: float
    units: str | None
    waveform: list[float] | None
    validation_summary: dict[str, Any] | None


class SensorHealthPublic(BaseModel):
    sensor_id: str
    sensor_code: str
    pump_id: str | None
    pump_code: str | None
    sensor_type: SensorType
    is_active: bool
    sampling_rate_hz: float
    total_windows: int
    valid_windows: int
    invalid_windows: int
    missing_window_gaps: int
    last_reading_at: datetime | None
    last_valid_reading_at: datetime | None
    freshness_seconds: float | None
    latest_quality: DataQuality | None
    data_quality: DataQuality | None
    sampling_status: Literal["NO_DATA", "RECENT", "STALE", "SENSOR_INVALID"]
    connection_state: Literal["NO_LIVE_CHANNEL"]
    latest_rms: float | None
    latest_peak_abs: float | None
    latest_scenario: str | None
    provenance: Provenance | None
    latest_validation_issues: list[dict[str, Any]]


class SessionSummary(BaseModel):
    id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    scenario: str | None
    status: SessionStatus
    data_provenance: Provenance
    sampling_rate_hz: float
    started_at: datetime
    ended_at: datetime | None
    window_count: int
    started_by_name: str | None


class LiveSnapshot(BaseModel):
    pump_id: str
    pump_code: str
    pump_name: str
    sensor_id: str
    sensor_code: str
    sensor_type: SensorType
    latest_window: LiveWindow | None
    recent_windows: list[WindowPoint]
    latest_prediction: PredictionPublic | None
    session: SessionSummary | None
    sensor_health: SensorHealthPublic
    equipment_condition: EquipmentCondition | None
    condition_available: bool
    data_quality: DataQuality | None
    edge_connectivity: ConnectivityStatus | None
    edge_note: str
    data_mode: Literal["SIMULATED_REPLAY", "NO_DATA"]
    buffering_state: str | None
    generated_at: datetime


class ModelSummary(BaseModel):
    id: str
    model_code: str
    name: str
    version: str
    status: ModelStatus
    balanced_accuracy: float | None
    macro_f1: float | None
    evaluation_dataset: str | None
    evaluated_at: datetime | None
    data_provenance: Provenance | None


class EvaluationSummary(BaseModel):
    id: str
    model_version_id: str
    dataset_name: str
    dataset_version: str
    data_provenance: Provenance
    balanced_accuracy: float | None
    macro_f1: float | None
    sample_count: int
    evaluated_at: datetime
    is_verified: bool


class MonitoringOverview(BaseModel):
    pumps_total: int
    pumps_active: int
    sensors_total: int
    sensors_active: int
    active_alerts: int
    sessions_total: int
    windows_total: int
    valid_windows: int
    invalid_windows: int
    latest_session: SessionSummary | None
    latest_window: LiveWindow | None
    latest_prediction: PredictionPublic | None
    trend: list[WindowPoint]
    sensors_with_data: int
    sensors_stale: int
    sensors_invalid: int
    sensors_no_data: int
    equipment_condition: EquipmentCondition | None
    condition_available: bool
    data_quality: DataQuality | None
    edge_connectivity: ConnectivityStatus | None
    edge_note: str
    data_mode: Literal["SIMULATED_REPLAY", "NO_DATA"]
    active_model: ModelSummary | None
    latest_evaluation: EvaluationSummary | None
    recent_sessions: list[SessionSummary]
    generated_at: datetime
