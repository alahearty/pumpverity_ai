from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from app.db.models import AcquisitionSession, SignalWindow
from app.domain.enums import DataQuality, Provenance, SessionStatus
from app.schemas.equipment import OperatingRegimePublic


class AcquisitionSessionCreate(BaseModel):
    pump_id: str = Field(min_length=1, max_length=36)
    sensor_id: str = Field(min_length=1, max_length=36)
    regime_id: str | None = Field(default=None, max_length=36)
    sampling_rate_hz: float = Field(gt=0, le=1_000_000)
    data_provenance: Provenance = Provenance.SIMULATED
    random_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    scenario: str = Field(default="manual", min_length=1, max_length=80)
    source_device_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("scenario", "source_device_id", "notes")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class AcquisitionSessionStop(BaseModel):
    status: SessionStatus = SessionStatus.COMPLETED

    @field_validator("status")
    @classmethod
    def validate_terminal_status(cls, value: SessionStatus) -> SessionStatus:
        if value not in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
            raise ValueError("status must be COMPLETED or ABORTED")
        return value


class WindowIngest(BaseModel):
    window_index: int = Field(ge=0, le=10_000_000)
    window_start: AwareDatetime
    window_end: AwareDatetime
    samples: list[float] = Field(default_factory=list, max_length=131_072)
    quality_status: DataQuality
    validation_summary: dict[str, Any] | None = None
    features: dict[str, Any] | None = None

    @field_validator("window_end")
    @classmethod
    def validate_window_end(cls, value: datetime, info) -> datetime:
        window_start = info.data.get("window_start")
        if window_start is not None and value < window_start:
            raise ValueError("window_end must not precede window_start")
        return value


class WindowPublic(BaseModel):
    id: str
    session_id: str
    window_index: int
    window_start: datetime
    window_end: datetime
    sampling_rate_hz: float
    sample_count: int
    quality_status: DataQuality
    data_provenance: Provenance
    validation_summary: dict[str, Any] | None
    features: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_window(cls, window: SignalWindow) -> "WindowPublic":
        return cls(
            id=window.id,
            session_id=window.session_id,
            window_index=window.window_index,
            window_start=window.window_start,
            window_end=window.window_end,
            sampling_rate_hz=window.sampling_rate_hz,
            sample_count=window.sample_count,
            quality_status=window.quality_status,
            data_provenance=window.data_provenance,
            validation_summary=window.validation_summary,
            features=window.features,
            created_at=window.created_at,
        )


class AcquisitionSessionPublic(BaseModel):
    id: str
    pump_id: str
    pump_code: str
    sensor_id: str
    sensor_code: str
    regime: OperatingRegimePublic | None
    started_by_id: str | None
    started_by_name: str | None
    sampling_rate_hz: float
    data_provenance: Provenance
    random_seed: int | None
    scenario: str | None
    status: SessionStatus
    source_device_id: str | None
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    window_count: int
    created_at: datetime

    @classmethod
    def from_session(
        cls, session: AcquisitionSession, window_count: int
    ) -> "AcquisitionSessionPublic":
        regime = (
            OperatingRegimePublic.model_validate(session.regime)
            if session.regime is not None
            else None
        )
        return cls(
            id=session.id,
            pump_id=session.pump_id,
            pump_code=session.pump.pump_code,
            sensor_id=session.sensor_id,
            sensor_code=session.sensor.sensor_code,
            regime=regime,
            started_by_id=session.started_by_id,
            started_by_name=session.started_by.full_name if session.started_by else None,
            sampling_rate_hz=session.sampling_rate_hz,
            data_provenance=session.data_provenance,
            random_seed=session.random_seed,
            scenario=session.scenario,
            status=session.status,
            source_device_id=session.source_device_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            notes=session.notes,
            window_count=window_count,
            created_at=session.created_at,
        )


__all__ = [
    "AcquisitionSessionCreate",
    "AcquisitionSessionPublic",
    "AcquisitionSessionStop",
    "WindowIngest",
    "WindowPublic",
]
