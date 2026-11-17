from datetime import UTC, datetime

from petrosense_edge.cli import _window_payload, main
from petrosense_edge.contracts import AdapterState, QualityStatus, SignalFrame
from petrosense_edge.validation import ValidationResult


def test_list_scenarios_exits_successfully(capsys):
    exit_code = main(["--list-scenarios"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "normal" in output
    assert "sensor_disconnect" in output
    assert "corrupted_samples" in output


def test_simulation_requires_codes(capsys):
    exit_code = main([])
    assert exit_code == 2
    assert "required" in capsys.readouterr().err


def test_invalid_window_payload_has_no_samples():
    frame = SignalFrame(
        sensor_id="sensor-1",
        session_id="session-1",
        sequence_no=4,
        window_start=datetime(2026, 11, 16, 12, 0, tzinfo=UTC),
        window_end=datetime(2026, 11, 16, 12, 0, 1, tzinfo=UTC),
        sampling_rate_hz=2048,
        samples=(),
        units="g",
        adapter_state=AdapterState.DISCONNECTED,
    )
    result = ValidationResult(
        status=QualityStatus.SENSOR_INVALID,
        issues=(),
        metrics={"sample_count": 0},
    )
    payload = _window_payload(frame, result)
    assert payload["samples"] == []
    assert payload["quality_status"] == "SENSOR_INVALID"
    assert payload["validation_summary"]["simulated"] is True
