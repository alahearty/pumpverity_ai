import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from petrosense_edge.contracts import AdapterState, QualityStatus, SignalFrame
from petrosense_edge.validation import SignalValidator

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
RATE = 2048.0
COUNT = 2048


def frame(samples=None, *, units="g", state=AdapterState.CONNECTED, rate=RATE, duration=None):
    values = samples
    if values is None:
        values = tuple(
            math.sin(2 * math.pi * 48.3 * i / RATE) * 0.05 for i in range(COUNT)
        )
    actual_duration = (
        duration if duration is not None else len(values) / rate
    )
    return SignalFrame(
        sensor_id="sensor-1",
        session_id="session-1",
        sequence_no=0,
        window_start=START,
        window_end=START + timedelta(seconds=actual_duration),
        sampling_rate_hz=rate,
        samples=tuple(values),
        units=units,
        adapter_state=state,
    )


def codes(result):
    return {issue.code for issue in result.issues}


def test_valid_window_returns_quality_metrics():
    result = SignalValidator().validate(frame())
    assert result.status is QualityStatus.VALID
    assert result.issues == ()
    assert result.metrics["sample_count"] == COUNT
    assert 0 < float(result.metrics["rms"]) < 1
    assert float(result.metrics["crest_factor"]) > 1


def test_missing_and_disconnected_samples_are_invalid():
    result = SignalValidator().validate(frame((), state=AdapterState.DISCONNECTED))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert {"sensor_disconnected", "missing_samples"} <= codes(result)


def test_insufficient_samples_are_invalid():
    small = tuple(0.1 * math.sin(i) for i in range(32))
    result = SignalValidator().validate(frame(small))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "insufficient_samples" in codes(result)


def test_non_finite_values_are_invalid():
    values = list(frame().samples)
    values[10] = float("nan")
    values[11] = float("inf")
    result = SignalValidator().validate(frame(values))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "non_finite_values" in codes(result)


def test_out_of_range_values_are_invalid():
    values = tuple(100 * math.sin(2 * math.pi * 10 * i / RATE) for i in range(COUNT))
    result = SignalValidator().validate(frame(values))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "out_of_range" in codes(result)


def test_flatline_is_invalid():
    result = SignalValidator().validate(frame(tuple(0.01 for _ in range(COUNT))))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "flatline" in codes(result)


def test_timestamp_mismatch_is_invalid():
    result = SignalValidator().validate(frame(duration=0.2))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "timestamp_mismatch" in codes(result)


def test_sampling_rate_mismatch_is_invalid():
    result = SignalValidator().validate(frame(), expected_sampling_rate_hz=1024)
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "sampling_rate_mismatch" in codes(result)


def test_unexpected_units_are_invalid():
    result = SignalValidator().validate(frame(units="volts"))
    assert result.status is QualityStatus.SENSOR_INVALID
    assert "unexpected_units" in codes(result)


def test_replace_is_available_for_adapter_enrichment():
    original = frame()
    enriched = replace(original, session_id="session-2")
    assert enriched.session_id == "session-2"
    assert original.session_id == "session-1"
