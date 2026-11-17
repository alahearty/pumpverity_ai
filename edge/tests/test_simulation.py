from datetime import UTC, datetime

import pytest
from petrosense_edge.contracts import AdapterConfig, AdapterState, QualityStatus
from petrosense_edge.simulation import (
    SCENARIOS,
    generate_frame,
    generate_frames,
    scenario_registry,
)
from petrosense_edge.validation import SignalValidator

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def config(**overrides) -> AdapterConfig:
    values = {
        "sensor_id": "sensor-1",
        "pump_id": "pump-1",
        "window_count": 3,
        "seed": 42,
        "scenario": "normal",
    }
    values.update(overrides)
    return AdapterConfig(**values)


def test_scenario_registry_labels_simulation_intent():
    codes = {scenario.code for scenario in scenario_registry()}
    assert {
        "normal",
        "imbalance",
        "cavitation",
        "incipient_fault",
        "custom_abnormal",
        "sensor_disconnect",
        "corrupted_samples",
    } == codes
    for scenario in SCENARIOS.values():
        assert scenario.description
        assert scenario.expected_notes
        assert scenario.expected_quality in {QualityStatus.VALID, QualityStatus.SENSOR_INVALID}


def test_generation_is_deterministic_for_same_seed():
    first = list(generate_frames(config(), START))
    second = list(generate_frames(config(), START))
    assert [frame.samples for frame in first] == [frame.samples for frame in second]
    assert [frame.window_start for frame in first] == [frame.window_start for frame in second]

    different_seed = list(generate_frames(config(seed=43), START))
    assert first[0].samples != different_seed[0].samples


def test_abnormal_scenarios_have_higher_energy_than_normal():
    validator = SignalValidator()
    normal = validator.validate(generate_frame(config(), 0, START))
    imbalance = validator.validate(generate_frame(config(scenario="imbalance"), 0, START))
    cavitation = validator.validate(generate_frame(config(scenario="cavitation"), 0, START))
    incipient = validator.validate(generate_frame(config(scenario="incipient_fault"), 0, START))

    assert normal.status is QualityStatus.VALID
    assert imbalance.status is QualityStatus.VALID
    assert cavitation.status is QualityStatus.VALID
    assert incipient.status is QualityStatus.VALID
    assert float(imbalance.metrics["rms"]) > float(normal.metrics["rms"])
    assert float(cavitation.metrics["rms"]) > float(normal.metrics["rms"])
    assert float(incipient.metrics["rms"]) > float(normal.metrics["rms"])


def test_custom_abnormal_amplitude_is_engineer_controlled():
    validator = SignalValidator()
    low = validator.validate(
        generate_frame(
            config(scenario="custom_abnormal", custom_amplitude_g=0.01),
            0,
            START,
        )
    )
    high = validator.validate(
        generate_frame(
            config(scenario="custom_abnormal", custom_amplitude_g=0.2),
            0,
            START,
        )
    )
    assert float(high.metrics["rms"]) > float(low.metrics["rms"])


def test_sensor_disconnect_has_no_samples():
    frame = generate_frame(config(scenario="sensor_disconnect"), 0, START)
    assert frame.adapter_state is AdapterState.DISCONNECTED
    assert frame.samples == ()
    assert frame.window_end > frame.window_start


def test_corrupted_samples_are_deliberately_invalid():
    frame = generate_frame(config(scenario="corrupted_samples"), 0, START)
    result = SignalValidator().validate(frame)
    codes = {issue.code for issue in result.issues}
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "non_finite_values" in codes


def test_window_timestamps_advance_by_hop():
    frames = list(generate_frames(config(overlap_fraction=0.5), START))
    assert len(frames) == 3
    expected_hop = 0.5
    assert (frames[1].window_start - frames[0].window_start).total_seconds() == pytest.approx(
        expected_hop
    )
    assert (frames[2].window_start - frames[1].window_start).total_seconds() == pytest.approx(
        expected_hop
    )
    assert frames[0].session_id == ""


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError, match="Unknown simulation scenario"):
        generate_frame(config(scenario="not-a-scenario"), 0, START)


def test_naive_start_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_frame(config(), 0, datetime(2026, 11, 16, 12, 0))
