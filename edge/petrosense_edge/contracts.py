from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class AdapterState(StrEnum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class QualityStatus(StrEnum):
    VALID = "VALID"
    SENSOR_INVALID = "SENSOR_INVALID"


class SignalClass(StrEnum):
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class AdapterConfig:
    sensor_id: str
    pump_id: str
    sampling_rate_hz: float = 2048.0
    window_size: int = 2048
    overlap_fraction: float = 0.5
    rated_speed_rpm: int = 2900
    scenario: str = "normal"
    seed: int = 42
    window_count: int = 5
    units: str = "g"
    custom_amplitude_g: float = 0.1
    custom_frequency_hz: float | None = None

    def __post_init__(self) -> None:
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if self.window_size < 16:
            raise ValueError("window_size must be at least 16 samples")
        if not 0 <= self.overlap_fraction < 1:
            raise ValueError("overlap_fraction must be in [0, 1)")
        if self.rated_speed_rpm <= 0:
            raise ValueError("rated_speed_rpm must be positive")
        if self.window_count < 1:
            raise ValueError("window_count must be at least 1")
        if self.custom_amplitude_g < 0:
            raise ValueError("custom_amplitude_g must not be negative")

    @property
    def window_duration_s(self) -> float:
        return self.window_size / self.sampling_rate_hz

    @property
    def hop_samples(self) -> int:
        return max(1, round(self.window_size * (1 - self.overlap_fraction)))


@dataclass(frozen=True)
class SignalFrame:
    sensor_id: str
    session_id: str
    sequence_no: int
    window_start: datetime
    window_end: datetime
    sampling_rate_hz: float
    samples: tuple[float, ...]
    units: str
    adapter_state: AdapterState
    notes: str = ""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    status: QualityStatus
    issues: tuple[ValidationIssue, ...] = ()
    metrics: dict[str, float | int | str] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.status is QualityStatus.VALID


@dataclass(frozen=True)
class ScenarioDefinition:
    code: str
    label: str
    description: str
    signal_class: SignalClass
    expected_quality: QualityStatus
    expected_notes: str


@runtime_checkable
class AcquisitionAdapter(Protocol):
    @property
    def sensor_id(self) -> str: ...

    @property
    def state(self) -> AdapterState: ...

    def start(self, session_id: str, start_time: datetime | None = None) -> None: ...

    def read(self) -> SignalFrame | None: ...

    def stop(self) -> None: ...
