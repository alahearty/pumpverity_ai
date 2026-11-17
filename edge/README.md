# Edge simulation, acquisition and validation

Stage 2 implements an independent Python package for deterministic simulated acquisition and
signal validation. It does not import the monitoring API or its database models.

```text
petrosense_edge/
├── contracts.py     # adapter protocol, frames, validation and scenario contracts
├── simulation.py    # seeded scenario generation (normal, abnormal, invalid, custom)
├── validation.py    # signal-quality checks and health metrics
├── adapters.py      # SimulatedSensorAdapter + physical-adapter placeholder
├── api_client.py    # explicit HTTP client used by the simulator CLI
└── cli.py           # simulate a session and persist validated windows through the API
tests/               # 26 simulation, validation and adapter tests
```

## Install and test

From the repository root:

```powershell
apps/api/.venv/Scripts/python -m pip install -e edge
apps/api/.venv/Scripts/ruff check edge/petrosense_edge edge/tests
apps/api/.venv/Scripts/python -m pytest edge/tests
```

Or run `scripts/verify.ps1`, which includes edge lint and tests.

## Scenarios

| Code | Signal class | Expected quality |
|---|---|---|
| `normal` | NORMAL | VALID |
| `imbalance` | ABNORMAL | VALID |
| `cavitation` | ABNORMAL | VALID |
| `incipient_fault` | INCONCLUSIVE | VALID |
| `custom_abnormal` | ABNORMAL | VALID |
| `sensor_disconnect` | INVALID | SENSOR_INVALID |
| `corrupted_samples` | INVALID | SENSOR_INVALID |

Generation is deterministic for a given scenario, seed, window index and configuration. Abnormal
scenarios are synthetic workflow inputs, not experimentally validated pump faults. The incipient
scenario provides mid-level energy for future uncertainty and abstention tests; it does not establish
a model decision.

Network outage, buffering and restoration scenarios are implemented with the Stage 6
synchronisation work (transactional outbox), not in this simulation package yet.

## Run a simulated acquisition

The API must be running, and a pump and sensor must be registered. The simulator logs in with an
engineer or researcher account.

```powershell
$env:PETROSENSE_EDGE_PASSWORD = "<demo password>"

apps/api/.venv/Scripts/python -m petrosense_edge.cli `
  --pump-code LAB-PUMP-01 `
  --sensor-code VIB-01 `
  --scenario normal `
  --windows 5 `
  --seed 42
```

Optional arguments include `--api-base`, `--email`, `--window-size`, `--sampling-rate`,
`--overlap`, `--rated-speed-rpm`, `--custom-amplitude`, `--custom-frequency` and `--device-id`.
Use `--list-scenarios` to print the registry.

For each frame the CLI:

1. validates signal quality;
2. posts valid samples or a sensor-invalid window with its validation summary;
3. stops the session `COMPLETED` or attempts `ABORTED` on failure.

The monitoring API persists sessions and windows with `SIMULATED` provenance. Invalid windows are
stored with no waveform payload; they cannot be mistaken for measured normal data.

## Boundary rules

- No physical measurements are fabricated. `PhysicalSensorAdapter` raises
  `AdapterNotConfiguredError` until the hardware contract is fulfilled.
- `SENSOR_INVALID` must suppress condition inference in later stages.
- The simulator does not bypass the API or write directly to the monitoring database.
- Simulated data cannot establish real-world fault-detection performance.
- Local outbox/offline persistence is a Stage 6 deliverable.
