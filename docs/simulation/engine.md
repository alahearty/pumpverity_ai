# Deterministic simulation engine (Stage 2)

**Package:** `edge/petrosense_edge`
**Status:** Implemented and tested; simulated acquisition persistence verified end-to-end.

## 1. Purpose

The engine lets the software be demonstrated before physical hardware is available. It produces
repeatable signal windows and explicit invalid cases, drives the edge `SignalValidator`, and sends
results through the real API contracts.

## 2. Boundaries

```text
scenario + seed + window geometry
  → deterministic samples
  → SignalFrame
  → SignalValidator
  → quality status + issues + metrics
  → CLI posts window through /acquisition-sessions/{id}/windows
  → API persists session/window with SIMULATED provenance
```

The package has no database dependency and never writes directly to the API database.

## 3. Scenarios

- `normal` — low-amplitude shaft harmonics and noise.
- `imbalance` — elevated 1x/2x harmonics.
- `cavitation` — broadband/high-frequency energy with modulation.
- `incipient_fault` — mid-level energy for future uncertainty/abstention work.
- `custom_abnormal` — normal baseline plus engineer-defined amplitude/frequency.
- `sensor_disconnect` — adapter disconnect, no samples.
- `corrupted_samples` — NaN, infinity and out-of-range values injected.

All failures are deliberately detectable by `SignalValidator`. The scenario metadata records the
expected signal class and quality, not a condition-model prediction.

## 4. Validation checks

- disconnected adapter / missing samples;
- insufficient sample count;
- non-finite values;
- out-of-range peak;
- flatline/zero variance;
- timestamp/duration mismatch;
- sampling-rate mismatch;
- unexpected units.

Valid results include sample count, duration, RMS, peak, mean, standard deviation and crest factor.
These are signal-health metrics, not trained model features.

## 5. Determinism

For a fixed configuration and seed, generated sample tuples and window timestamps are identical.
Tests assert this and compare abnormal energy against the normal scenario. Determinism is within the
same Python/platform implementation; cross-platform floating-point differences are not claimed as
bit-identical.

## 6. Scientific limitations

- Synthetic signals are not measured pump vibrations.
- Scenario labels are engineering hypotheses, not verified fault ground truth.
- No accuracy, false-alert rate or real-world robustness claim can be derived from this engine.
- Network outage/buffering scenarios belong to Stage 6; they are not simulated here.
- The incipient scenario is a test input for future uncertainty handling, not evidence that a model
  will abstain correctly.

## 7. CLI

See [`edge/README.md`](../../edge/README.md). A typical run:

```powershell
$env:PETROSENSE_EDGE_PASSWORD = "<demo password>"
apps/api/.venv/Scripts/python -m petrosense_edge.cli `
  --pump-code LAB-PUMP-01 --sensor-code VIB-01 `
  --scenario normal --windows 5 --seed 42
```

The resulting session and windows are visible in the Pump Registry screen. All rows are labelled
`SIMULATED`.
