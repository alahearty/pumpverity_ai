# Acquisition hardware integration contract (template)

**Status:** The simulated adapter, validator and persistence path are implemented (Stage 2). Physical
hardware is not yet integrated. No hardware selection, measurement or performance claim has been
made. This document defines what must be true before the physical adapter is treated as verified.

## 1. Adapter boundary

Both adapters implement the same conceptual contract:

```text
start_session(config) -> session_id
read_window() -> {
    sensor_id,
    session_id,
    window_start,
    window_end,
    sampling_rate_hz,
    sample_count,
    samples: float32[],
    units,
    sequence_no,
    adapter_status
}
stop_session(reason)
health() -> {connected, last_sample_at, dropped_samples, adapter_message}
```

- `SimulatedSensorAdapter` is deterministic under a documented seed and always emits `SIMULATED`
  provenance (implemented in `edge/petrosense_edge/adapters.py`).
- `PhysicalSensorAdapter` currently raises `AdapterNotConfiguredError` and must never invent samples
  or fill gaps silently. Missing samples, saturation, timestamp anomalies and disconnection must be
  surfaced to `SignalValidator` when hardware is integrated.

## 2. Open hardware decisions

| Decision | Status |
|---|---|
| Sensor model and sensitivity | Not selected |
| Coupling/mounting method and axis | Not selected |
| ADC / interface and anti-alias filtering | Not selected |
| Edge platform: Raspberry Pi vs ESP32-S3 | Deferred; Raspberry Pi is the initial evaluation preference because Python signal processing and model runtime reduce integration risk |
| Sampling rate and window length | Provisional defaults in settings; must be justified against pump kinematics and anti-alias requirements |
| Time source and timestamp accuracy | Not specified |
| Calibration procedure | Not specified |
| Environmental/EMI precautions | Not specified |

ESP32-S3 and Raspberry Pi must not be assumed to have identical sampling, runtime or memory
capabilities. Any portability claim requires separate measurement.

## 3. Required documentation before experiments

- Exact sensor, ADC and edge-device part numbers and wiring diagram.
- Sampling frequency, resolution, range, coupling and filter characteristics.
- Mounting position, axis, torque, surface preparation and repeatability procedure.
- Calibration certificate or in-house calibration method and uncertainty.
- Timestamp source and observed jitter/drift.
- Buffer size and behaviour on overload.
- Edge runtime version, model artefact hash and inference latency measurement method.
- Data files with acquisition-run identifiers and checksums.

## 4. Validation before use in evaluation

1. Bench test known excitation or calibration source.
2. Verify sampling cadence and timestamp monotonicity under load.
3. Verify disconnection detection and recovery.
4. Verify saturation/out-of-range detection.
5. Demonstrate that invalid input produces `SENSOR_INVALID`, not a condition decision.
6. Record repeatability across remounts.
7. Only then acquire labelled experimental runs.

## 5. Prohibited claims until evidence exists

- "The sensor detects faults with X% accuracy."
- "The edge device runs in Y ms" without measurement.
- "The model is validated" using synthetic data alone.
- "Manufacturer specification equals installed measurement accuracy."
- Any safety, shutdown or production-readiness claim.

## 6. Integration failure handling

- Adapter loss → sensor health event and `SENSOR_INVALID`; no fresh normal decision.
- Buffer overrun → explicit dropped-sample count; window may be rejected.
- Clock discontinuity → window/timestamp validation failure; no silent reordering.
- Network loss → local inference continues; outbox buffers.
- Edge restart → unsent outbox events survive; active session is recovered or explicitly closed.
