from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    DataQuality,
    DeliveryStatus,
    EquipmentCondition,
    LabelSource,
    ModelRuntime,
    ModelStatus,
    MountingAxis,
    OperatingRegimeCode,
    PredictionDecision,
    Provenance,
    PumpStatus,
    PumpType,
    ReportStatus,
    ReportType,
    ReviewAction,
    RoleName,
    SensorType,
    SessionStatus,
)


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_type(enum_class: type[StrEnum], name: str, length: int = 40) -> SAEnum:
    return SAEnum(
        enum_class,
        name=name,
        native_enum=False,
        values_callable=lambda enum: [member.value for member in enum],
        validate_strings=True,
        create_constraint=True,
        length=length,
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[RoleName] = mapped_column(
        enum_type(RoleName, "role_name", 32), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list[User]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role_active", "role_id", "is_active"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    role: Mapped[Role] = relationship(back_populates="users")
    pumps_created: Mapped[list[Pump]] = relationship(back_populates="created_by")
    sessions_started: Mapped[list[AcquisitionSession]] = relationship(
        back_populates="started_by"
    )
    alert_assignments: Mapped[list[Alert]] = relationship(
        back_populates="assigned_reviewer", foreign_keys="Alert.assigned_reviewer_id"
    )
    alert_reviews: Mapped[list[AlertReview]] = relationship(back_populates="reviewer")
    config_changes: Mapped[list[ConfigurationSetting]] = relationship(
        back_populates="updated_by"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="actor")
    report_jobs: Mapped[list[ReportJob]] = relationship(back_populates="requested_by")
    model_versions_registered: Mapped[list[ModelVersion]] = relationship(
        back_populates="registered_by"
    )
    evaluations_verified: Mapped[list[ModelEvaluation]] = relationship(
        back_populates="verified_by"
    )


class Pump(Base):
    __tablename__ = "pumps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pump_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    pump_type: Mapped[PumpType] = mapped_column(
        enum_type(PumpType, "pump_type", 32), default=PumpType.CENTRIFUGAL, nullable=False
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    rated_speed_rpm: Mapped[int] = mapped_column(Integer, nullable=False)
    default_regime_id: Mapped[str | None] = mapped_column(
        ForeignKey("operating_regimes.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[PumpStatus] = mapped_column(
        enum_type(PumpStatus, "pump_status", 32), default=PumpStatus.ACTIVE, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    created_by: Mapped[User | None] = relationship(back_populates="pumps_created")
    default_regime: Mapped[OperatingRegime | None] = relationship(
        back_populates="default_pumps", foreign_keys=[default_regime_id]
    )
    sensors: Mapped[list[Sensor]] = relationship(back_populates="pump")
    sessions: Mapped[list[AcquisitionSession]] = relationship(back_populates="pump")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="pump")
    alerts: Mapped[list[Alert]] = relationship(back_populates="pump")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sensor_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    pump_id: Mapped[str | None] = mapped_column(
        ForeignKey("pumps.id", ondelete="RESTRICT"), index=True
    )
    sensor_type: Mapped[SensorType] = mapped_column(
        enum_type(SensorType, "sensor_type", 32), default=SensorType.VIBRATION, nullable=False
    )
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model_name: Mapped[str | None] = mapped_column(String(120))
    mounting_axis: Mapped[MountingAxis] = mapped_column(
        enum_type(MountingAxis, "mounting_axis", 32),
        default=MountingAxis.UNKNOWN,
        nullable=False,
    )
    mounting_position: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    sampling_rate_hz: Mapped[float] = mapped_column(Float, nullable=False, default=2048.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    pump: Mapped[Pump | None] = relationship(back_populates="sensors")
    sessions: Mapped[list[AcquisitionSession]] = relationship(back_populates="sensor")
    readings: Mapped[list[SensorReading]] = relationship(back_populates="sensor")
    windows: Mapped[list[SignalWindow]] = relationship(back_populates="sensor")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="sensor")
    alerts: Mapped[list[Alert]] = relationship(back_populates="sensor")


class OperatingRegime(Base):
    __tablename__ = "operating_regimes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[OperatingRegimeCode] = mapped_column(
        enum_type(OperatingRegimeCode, "operating_regime_code", 32),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list[AcquisitionSession]] = relationship(back_populates="regime")
    default_pumps: Mapped[list[Pump]] = relationship(back_populates="default_regime")


class AcquisitionSession(Base):
    __tablename__ = "acquisition_sessions"
    __table_args__ = (
        Index("ix_acquisition_sessions_pump_started", "pump_id", "started_at"),
        Index("ix_acquisition_sessions_sensor_started", "sensor_id", "started_at"),
        Index("ix_acquisition_sessions_provenance", "data_provenance", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pump_id: Mapped[str] = mapped_column(
        ForeignKey("pumps.id", ondelete="RESTRICT"), nullable=False
    )
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False
    )
    regime_id: Mapped[str | None] = mapped_column(
        ForeignKey("operating_regimes.id", ondelete="RESTRICT"), index=True
    )
    started_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    source_device_id: Mapped[str | None] = mapped_column(String(120), index=True)
    sampling_rate_hz: Mapped[float] = mapped_column(Float, nullable=False)
    data_provenance: Mapped[Provenance] = mapped_column(
        enum_type(Provenance, "acquisition_provenance", 24), nullable=False
    )
    random_seed: Mapped[int | None] = mapped_column(Integer)
    scenario: Mapped[str | None] = mapped_column(String(80), index=True)
    status: Mapped[SessionStatus] = mapped_column(
        enum_type(SessionStatus, "session_status", 24),
        default=SessionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pump: Mapped[Pump] = relationship(back_populates="sessions")
    sensor: Mapped[Sensor] = relationship(back_populates="sessions")
    regime: Mapped[OperatingRegime | None] = relationship(back_populates="sessions")
    started_by: Mapped[User | None] = relationship(back_populates="sessions_started")
    readings: Mapped[list[SensorReading]] = relationship(back_populates="session")
    windows: Mapped[list[SignalWindow]] = relationship(back_populates="session")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="session")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_no", name="uq_readings_session_sequence"),
        Index("ix_sensor_readings_session_recorded", "session_id", "recorded_at"),
        Index("ix_sensor_readings_sensor_recorded", "sensor_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("acquisition_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    quality_status: Mapped[DataQuality] = mapped_column(
        enum_type(DataQuality, "reading_quality", 24), nullable=False
    )
    validation_message: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[AcquisitionSession] = relationship(back_populates="readings")
    sensor: Mapped[Sensor] = relationship(back_populates="readings")


class SignalWindow(Base):
    __tablename__ = "signal_windows"
    __table_args__ = (
        UniqueConstraint("session_id", "window_index", name="uq_signal_windows_session_index"),
        Index("ix_signal_windows_session_start", "session_id", "window_start"),
        Index("ix_signal_windows_sensor_created", "sensor_id", "created_at"),
        Index("ix_signal_windows_provenance", "data_provenance", "window_start"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("acquisition_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False
    )
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sampling_rate_hz: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_encoding: Mapped[str] = mapped_column(String(32), nullable=False, default="float32-le")
    signal_payload: Mapped[bytes | None] = mapped_column(LargeBinary)
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    quality_status: Mapped[DataQuality] = mapped_column(
        enum_type(DataQuality, "signal_window_quality", 24), nullable=False
    )
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    data_provenance: Mapped[Provenance] = mapped_column(
        enum_type(Provenance, "signal_window_provenance", 24), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[AcquisitionSession] = relationship(back_populates="windows")
    sensor: Mapped[Sensor] = relationship(back_populates="windows")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="window")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("model_code", "version", name="uq_model_versions_code_version"),
        Index("ix_model_versions_status", "status", "registered_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    runtime: Mapped[ModelRuntime] = mapped_column(
        enum_type(ModelRuntime, "model_runtime", 24), default=ModelRuntime.ONNX, nullable=False
    )
    feature_contract: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    training_dataset_version: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    evaluation_dataset: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    evaluation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    deployment_compatibility: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[ModelStatus] = mapped_column(
        enum_type(ModelStatus, "model_status", 24),
        default=ModelStatus.REGISTERED,
        nullable=False,
    )
    registered_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    registered_by: Mapped[User | None] = relationship(back_populates="model_versions_registered")
    evaluations: Mapped[list[ModelEvaluation]] = relationship(back_populates="model_version")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="model_version")


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"
    __table_args__ = (
        Index("ix_model_evaluations_model_evaluated", "model_version_id", "evaluated_at"),
        Index("ix_model_evaluations_provenance", "data_provenance", "evaluated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_name: Mapped[str] = mapped_column(String(160), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    data_provenance: Mapped[Provenance] = mapped_column(
        enum_type(Provenance, "evaluation_provenance", 24), nullable=False
    )
    evaluation_protocol: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    split_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    balanced_accuracy: Mapped[float | None] = mapped_column(Float)
    macro_f1: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confusion_matrix: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_coverage: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    calibration: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_by: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text)

    model_version: Mapped[ModelVersion] = relationship(back_populates="evaluations")
    verified_by: Mapped[User | None] = relationship(back_populates="evaluations_verified")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_pump_inferred", "pump_id", "inferred_at"),
        Index("ix_predictions_decision_inferred", "decision", "inferred_at"),
        Index("ix_predictions_provenance", "data_provenance", "inferred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    pump_id: Mapped[str] = mapped_column(
        ForeignKey("pumps.id", ondelete="RESTRICT"), nullable=False
    )
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("acquisition_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    signal_window_id: Mapped[str | None] = mapped_column(
        ForeignKey("signal_windows.id", ondelete="RESTRICT"), index=True
    )
    model_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), index=True
    )
    operating_regime_id: Mapped[str | None] = mapped_column(
        ForeignKey("operating_regimes.id", ondelete="RESTRICT"), index=True
    )
    decision: Mapped[PredictionDecision] = mapped_column(
        enum_type(PredictionDecision, "prediction_decision", 24), nullable=False
    )
    data_quality: Mapped[DataQuality] = mapped_column(
        enum_type(DataQuality, "prediction_data_quality", 24), nullable=False
    )
    equipment_condition: Mapped[EquipmentCondition | None] = mapped_column(
        enum_type(EquipmentCondition, "prediction_equipment_condition", 24)
    )
    decision_score: Mapped[float | None] = mapped_column(Float)
    uncertainty_score: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    inferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_provenance: Mapped[Provenance] = mapped_column(
        enum_type(Provenance, "prediction_provenance", 24), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pump: Mapped[Pump] = relationship(back_populates="predictions")
    sensor: Mapped[Sensor] = relationship(back_populates="predictions")
    session: Mapped[AcquisitionSession] = relationship(back_populates="predictions")
    window: Mapped[SignalWindow | None] = relationship(back_populates="predictions")
    model_version: Mapped[ModelVersion | None] = relationship(back_populates="predictions")
    operating_regime: Mapped[OperatingRegime | None] = relationship()
    alerts: Mapped[list[Alert]] = relationship(back_populates="prediction")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("prediction_id", name="uq_alerts_prediction_id"),
        Index("ix_alerts_status_created", "status", "created_at"),
        Index("ix_alerts_pump_created", "pump_id", "created_at"),
        Index("ix_alerts_category_created", "category", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    pump_id: Mapped[str] = mapped_column(
        ForeignKey("pumps.id", ondelete="RESTRICT"), nullable=False
    )
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False
    )
    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("predictions.id", ondelete="RESTRICT"), index=True
    )
    category: Mapped[AlertCategory] = mapped_column(
        enum_type(AlertCategory, "alert_category", 24), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        enum_type(AlertSeverity, "alert_severity", 16), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        enum_type(AlertStatus, "alert_status", 24), default=AlertStatus.OPEN, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    origin_device_id: Mapped[str | None] = mapped_column(String(120), index=True)
    data_provenance: Mapped[Provenance] = mapped_column(
        enum_type(Provenance, "alert_provenance", 24), nullable=False
    )
    assigned_reviewer_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    pump: Mapped[Pump] = relationship(back_populates="alerts")
    sensor: Mapped[Sensor] = relationship(back_populates="alerts")
    prediction: Mapped[Prediction | None] = relationship(back_populates="alerts")
    assigned_reviewer: Mapped[User | None] = relationship(
        back_populates="alert_assignments", foreign_keys=[assigned_reviewer_id]
    )
    reviews: Mapped[list[AlertReview]] = relationship(back_populates="alert")


class AlertReview(Base):
    __tablename__ = "alert_reviews"
    __table_args__ = (Index("ix_alert_reviews_alert_created", "alert_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[ReviewAction] = mapped_column(
        enum_type(ReviewAction, "review_action", 32), nullable=False
    )
    reviewed_label: Mapped[PredictionDecision | None] = mapped_column(
        enum_type(PredictionDecision, "reviewed_label", 24)
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    label_source: Mapped[LabelSource] = mapped_column(
        enum_type(LabelSource, "review_label_source", 24),
        default=LabelSource.ENGINEER_REVIEW,
        nullable=False,
    )
    is_verified_ground_truth: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    alert: Mapped[Alert] = relationship(back_populates="reviews")
    reviewer: Mapped[User] = relationship(back_populates="alert_reviews")


class ConfigurationSetting(Base):
    __tablename__ = "configuration_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    updated_by: Mapped[User | None] = relationship(back_populates="config_changes")


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"
    __table_args__ = (
        Index("ix_sync_outbox_delivery", "delivery_status", "next_retry_at"),
        Index("ix_sync_outbox_occurred", "occurred_at"),
    )

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source_device_id: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        enum_type(DeliveryStatus, "outbox_delivery_status", 24),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    actor_label: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    entity_id: Mapped[str | None] = mapped_column(String(80))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")


class ReportJob(Base):
    __tablename__ = "report_jobs"
    __table_args__ = (Index("ix_report_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    report_type: Mapped[ReportType] = mapped_column(
        enum_type(ReportType, "report_type", 40), nullable=False
    )
    status: Mapped[ReportStatus] = mapped_column(
        enum_type(ReportStatus, "report_status", 24),
        default=ReportStatus.QUEUED,
        nullable=False,
    )
    requested_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    includes_simulated_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requested_by: Mapped[User | None] = relationship(back_populates="report_jobs")


class CopilotConversation(Base):
    __tablename__ = "copilot_conversations"
    __table_args__ = (
        Index("ix_copilot_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    messages: Mapped[list[CopilotMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    invocations: Mapped[list[CopilotToolInvocation]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"
    __table_args__ = (
        Index("ix_copilot_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[CopilotConversation] = relationship(back_populates="messages")


class CopilotToolInvocation(Base):
    __tablename__ = "copilot_tool_invocations"
    __table_args__ = (
        Index("ix_copilot_invocations_conversation_created", "conversation_id", "created_at"),
        Index("ix_copilot_invocations_status_created", "status", "created_at"),
        Index("ix_copilot_invocations_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[CopilotConversation | None] = relationship(
        back_populates="invocations"
    )
    actor: Mapped[User] = relationship(foreign_keys=[actor_user_id])
