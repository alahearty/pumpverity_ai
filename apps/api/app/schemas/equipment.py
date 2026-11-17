from datetime import datetime
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.db.models import Pump, Sensor, utcnow
from app.domain.enums import (
    MountingAxis,
    OperatingRegimeCode,
    PumpStatus,
    PumpType,
    SensorType,
)

CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"


def _normalise_code(value: str) -> str:
    return value.strip().upper()


class OperatingRegimePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: OperatingRegimeCode
    name: str
    description: str
    is_active: bool


class SensorCreate(BaseModel):
    sensor_code: str = Field(min_length=1, max_length=64, pattern=CODE_PATTERN)
    sensor_type: SensorType = SensorType.VIBRATION
    manufacturer: str | None = Field(default=None, max_length=120)
    model_name: str | None = Field(default=None, max_length=120)
    mounting_axis: MountingAxis = MountingAxis.UNKNOWN
    mounting_position: str = Field(min_length=1, max_length=160)
    sampling_rate_hz: float = Field(default=2048.0, gt=0, le=1_000_000)
    is_active: bool = True
    installed_at: AwareDatetime | None = None

    @field_validator("sensor_code", mode="before")
    @classmethod
    def normalise_sensor_code(cls, value: str) -> str:
        return _normalise_code(value)

    @field_validator("manufacturer", "model_name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("mounting_position")
    @classmethod
    def strip_mounting_position(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class SensorRegister(SensorCreate):
    pump_id: str | None = Field(default=None, max_length=36)


class SensorUpdate(BaseModel):
    pump_id: str | None = Field(default=None, max_length=36)
    sensor_type: SensorType | None = None
    manufacturer: str | None = Field(default=None, max_length=120)
    model_name: str | None = Field(default=None, max_length=120)
    mounting_axis: MountingAxis | None = None
    mounting_position: str | None = Field(default=None, min_length=1, max_length=160)
    sampling_rate_hz: float | None = Field(default=None, gt=0, le=1_000_000)
    is_active: bool | None = None

    @field_validator("manufacturer", "model_name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("mounting_position")
    @classmethod
    def strip_mounting_position(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class SensorPublic(BaseModel):
    id: str
    sensor_code: str
    pump_id: str | None
    pump_code: str | None
    sensor_type: SensorType
    manufacturer: str | None
    model_name: str | None
    mounting_axis: MountingAxis
    mounting_position: str
    sampling_rate_hz: float
    is_active: bool
    installed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_sensor(cls, sensor: Sensor) -> Self:
        return cls(
            id=sensor.id,
            sensor_code=sensor.sensor_code,
            pump_id=sensor.pump_id,
            pump_code=sensor.pump.pump_code if sensor.pump is not None else None,
            sensor_type=sensor.sensor_type,
            manufacturer=sensor.manufacturer,
            model_name=sensor.model_name,
            mounting_axis=sensor.mounting_axis,
            mounting_position=sensor.mounting_position,
            sampling_rate_hz=sensor.sampling_rate_hz,
            is_active=sensor.is_active,
            installed_at=sensor.installed_at,
            created_at=sensor.created_at,
            updated_at=sensor.updated_at,
        )


class PumpBase(BaseModel):
    pump_code: str = Field(min_length=1, max_length=64, pattern=CODE_PATTERN)
    name: str = Field(min_length=1, max_length=160)
    pump_type: PumpType = PumpType.CENTRIFUGAL
    location: str = Field(min_length=1, max_length=255)
    rated_speed_rpm: int = Field(gt=0, le=100_000)
    default_regime_id: str | None = Field(default=None, max_length=36)
    status: PumpStatus = PumpStatus.ACTIVE
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("pump_code", mode="before")
    @classmethod
    def normalise_pump_code(cls, value: str) -> str:
        return _normalise_code(value)

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class PumpCreate(PumpBase):
    sensor: SensorCreate | None = None


class PumpUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    pump_type: PumpType | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    rated_speed_rpm: int | None = Field(default=None, gt=0, le=100_000)
    default_regime_id: str | None = Field(default=None, max_length=36)
    status: PumpStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "location")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class PumpPublic(BaseModel):
    id: str
    pump_code: str
    name: str
    pump_type: PumpType
    location: str
    rated_speed_rpm: int
    default_regime: OperatingRegimePublic | None
    status: PumpStatus
    notes: str | None
    sensors: list[SensorPublic]
    registered_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_pump(cls, pump: Pump) -> Self:
        return cls(
            id=pump.id,
            pump_code=pump.pump_code,
            name=pump.name,
            pump_type=pump.pump_type,
            location=pump.location,
            rated_speed_rpm=pump.rated_speed_rpm,
            default_regime=(
                OperatingRegimePublic.model_validate(pump.default_regime)
                if pump.default_regime is not None
                else None
            ),
            status=pump.status,
            notes=pump.notes,
            sensors=[SensorPublic.from_sensor(sensor) for sensor in pump.sensors],
            registered_at=pump.registered_at,
            created_at=pump.created_at,
            updated_at=pump.updated_at,
        )


def sensor_values(payload: SensorCreate) -> dict:
    return {
        "sensor_code": payload.sensor_code,
        "sensor_type": payload.sensor_type,
        "manufacturer": payload.manufacturer or None,
        "model_name": payload.model_name or None,
        "mounting_axis": payload.mounting_axis,
        "mounting_position": payload.mounting_position,
        "sampling_rate_hz": payload.sampling_rate_hz,
        "is_active": payload.is_active,
        "installed_at": payload.installed_at or utcnow(),
    }
