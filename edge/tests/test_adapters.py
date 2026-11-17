from datetime import UTC, datetime

import pytest
from petrosense_edge.adapters import (
    AdapterNotConfiguredError,
    PhysicalSensorAdapter,
    SimulatedSensorAdapter,
)
from petrosense_edge.contracts import AcquisitionAdapter, AdapterConfig, AdapterState
from petrosense_edge.simulation import generate_frame

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def config(**overrides):
    values = {
        "sensor_id": "sensor-1",
        "pump_id": "pump-1",
        "window_count": 3,
        "seed": 42,
    }
    values.update(overrides)
    return AdapterConfig(**values)


def test_simulated_adapter_implements_contract_and_finishes():
    adapter = SimulatedSensorAdapter(config())
    assert isinstance(adapter, AcquisitionAdapter)
    assert adapter.state is AdapterState.DISCONNECTED

    adapter.start("session-1", START)
    frames = []
    while (frame := adapter.read()) is not None:
        frames.append(frame)
    assert len(frames) == 3
    assert all(frame.session_id == "session-1" for frame in frames)
    assert [frame.sequence_no for frame in frames] == [0, 1, 2]
    assert all(frame.samples for frame in frames)
    assert adapter.read() is None

    adapter.stop()
    assert adapter.state is AdapterState.DISCONNECTED


def test_simulated_adapter_requires_start():
    adapter = SimulatedSensorAdapter(config())
    with pytest.raises(RuntimeError, match="started"):
        adapter.read()


def test_physical_adapter_never_fabricates_measurements():
    adapter = PhysicalSensorAdapter(config())
    assert isinstance(adapter, AcquisitionAdapter)
    assert adapter.state is AdapterState.NOT_CONFIGURED
    with pytest.raises(AdapterNotConfiguredError):
        adapter.start("session-1", START)
    with pytest.raises(AdapterNotConfiguredError):
        adapter.read()
    adapter.stop()


def test_frame_generation_matches_adapter_first_frame():
    direct = generate_frame(config(), 0, START)
    adapter = SimulatedSensorAdapter(config())
    adapter.start("session-1", START)
    read = adapter.read()
    assert read is not None
    assert read.samples == direct.samples
    assert read.window_start == direct.window_start
