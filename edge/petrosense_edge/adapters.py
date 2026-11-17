import dataclasses
from datetime import UTC, datetime, timedelta

from petrosense_edge.contracts import (
    AdapterConfig,
    AdapterState,
    SignalFrame,
)
from petrosense_edge.simulation import generate_frame


class AdapterNotConfiguredError(RuntimeError):
    """Raised when a physical adapter has no validated hardware configuration."""


class SimulatedSensorAdapter:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        self._state = AdapterState.DISCONNECTED
        self._session_id: str | None = None
        self._start_time: datetime | None = None
        self._next_index = 0

    @property
    def sensor_id(self) -> str:
        return self.config.sensor_id

    @property
    def state(self) -> AdapterState:
        return self._state

    def start(self, session_id: str, start_time: datetime | None = None) -> None:
        if not session_id:
            raise ValueError("session_id is required")
        self._session_id = session_id
        self._start_time = start_time or datetime.now(UTC)
        self._next_index = 0
        self._state = AdapterState.CONNECTED

    def read(self) -> SignalFrame | None:
        if self._session_id is None or self._start_time is None:
            raise RuntimeError("Adapter must be started before reading")
        if self._next_index >= self.config.window_count:
            return None

        hop_seconds = self.config.hop_samples / self.config.sampling_rate_hz
        frame_start = self._start_time + timedelta(
            seconds=self._next_index * hop_seconds
        )
        frame = generate_frame(self.config, self._next_index, frame_start)
        frame = dataclasses.replace(frame, session_id=self._session_id)
        self._next_index += 1
        return frame

    def stop(self) -> None:
        self._session_id = None
        self._start_time = None
        self._state = AdapterState.DISCONNECTED


class PhysicalSensorAdapter:
    """Documented placeholder for real hardware.

    It deliberately produces no measurements. Integration requires the sensor, ADC, mounting,
    calibration and edge-platform contract described in
    ``docs/hardware/acquisition-integration-contract.md``.
    """

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    @property
    def sensor_id(self) -> str:
        return self.config.sensor_id

    @property
    def state(self) -> AdapterState:
        return AdapterState.NOT_CONFIGURED

    def start(self, session_id: str, start_time: datetime | None = None) -> None:
        raise AdapterNotConfiguredError(
            "Physical sensor integration is not configured. No hardware measurements exist."
        )

    def read(self) -> SignalFrame | None:
        raise AdapterNotConfiguredError(
            "Physical sensor integration is not configured. No hardware measurements exist."
        )

    def stop(self) -> None:
        return None
