# Stage 2 acceptance evidence

**Date:** 2026-11-16
**Environment:** Windows 11, Python 3.13, Node.js 24, Chrome (Playwright), SQLite
**Isolation:** End-to-end write tests and the simulator ran against a temporary database
`apps/api/data/stage2-verify.db`; the developer database was not used for write verification.
**Versions:** API `0.2.0`, edge package `0.2.0`, migration `a7fc07ebdf60`

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Engineer can register a pump and initial sensor transactionally | **Met** | API tests; Playwright pump registration; database check |
| 2 | Duplicate pump/sensor codes are rejected without partial registration | **Met** | `test_pump_codes_are_normalised_and_duplicates_rejected`, `test_duplicate_nested_sensor_rolls_back_pump` |
| 3 | Pump update, status, operating-regime default and audit trail work | **Met** | `test_update_pump_and_operating_regime` |
| 4 | Sensor registration, pump association, filtering and active-state update work | **Met** | `test_sensor_registration_assignment_and_update`; Sensor UI |
| 5 | Pump/sensor reads are authenticated; writes are engineer/admin only | **Met** | RBAC tests; server-side dependency guards |
| 6 | Deterministic simulation produces repeatable normal and abnormal windows | **Met** | Edge determinism and energy tests |
| 7 | Sensor disconnection and corrupted samples are rejected before inference | **Met** | 26 edge tests; live simulator run produced 4 `SENSOR_INVALID` windows |
| 8 | Simulated sessions/windows are persisted with `SIMULATED` provenance | **Met** | 4 sessions, 12 windows, all `SIMULATED`; API and SQLite checks |
| 9 | Sensor-invalid windows persist metadata without waveform payload | **Met** | 4 invalid windows, 0 payload bytes for those windows |
| 10 | Experimental acquisition is refused until physical hardware is validated | **Met** | `test_session_guards_and_rbac`; API returns `EXPERIMENTAL_ACQUISITION_UNAVAILABLE` |
| 11 | Physical adapter never fabricates measurements | **Met** | `test_physical_adapter_never_fabricates_measurements` |
| 12 | Frontend registration/list/session visibility is backed by the API | **Met** | Pumps/Sensors pages, component tests, Playwright write workflow |
| 13 | All checks remain green and documentation is updated | **Met** | Verification below; Stage 2 docs and API/schema docs updated |

## 2. Executed verification

```text
API ruff check ......................... All checks passed
API pytest ............................. 41 passed
Edge ruff check ........................ All checks passed
Edge pytest ............................ 26 passed
Web oxlint ............................. 0 errors, 3 fast-refresh warnings
Web vitest ............................. 26 passed
Web tsc + vite build ................... passed (chunk-size warning)
Playwright ............................. 6 passed (including UI pump/sensor registration)
```

Playwright was run with `PETROSENSE_E2E_ALLOW_WRITES=1` against the isolated database. Tests covered:

- login/session restore and all twelve screens;
- pump form validation;
- real pump + sensor registration through the browser;
- sensor inventory reflecting the created sensor.

## 3. End-to-end simulated acquisition evidence

The UI-created pump `E2E-1794833625854` / sensor `E2E-VIB-1794833625854` was used for four
simulator runs:

| Scenario | Seed | Windows | Valid | Sensor invalid |
|---|---|---|---|---|
| normal | 42 | 5 | 5 | 0 |
| imbalance | 43 | 3 | 3 | 0 |
| sensor_disconnect | 44 | 2 | 0 | 2 |
| corrupted_samples | 45 | 2 | 0 | 2 |

SQLite verification of the isolated database:

```text
pumps .......................... 1
sensors ........................ 1
sessions ....................... 4
windows ........................ 12
valid_windows .................. 8
invalid_windows ................ 4
payload_bytes .................. 65536   (8 × 2048 samples × float32)
session scenarios .............. normal, imbalance, sensor_disconnect, corrupted_samples
```

Calculated RMS values demonstrated the expected synthetic separation:

```text
normal window RMS .............. ~0.023 g
imbalance window RMS ........... ~0.094 g
sensor_disconnect .............. SENSOR_INVALID [sensor_disconnected, missing_samples]
corrupted_samples .............. SENSOR_INVALID [non_finite_values]
```

These values demonstrate software integration only. They are not experimental pump-fault evidence.

## 4. Configuration and schema changes

- `pumps.default_regime_id` added with FK/index and migration.
- `acquisition_sessions.scenario` added with index and migration.
- New API groups: pumps, sensors, operating regimes and acquisition sessions/windows.
- New edge package under `edge/` with deterministic scenarios and validation.
- CI extended with an edge lint/test job.
- Setup and verification scripts install/lint/test the edge package.

## 5. Deviations and limitations

1. **Live UI simulation trigger:** the simulator is a CLI; the browser cannot start it in Stage 2.
   The Pump Registry explains the command and shows persisted sessions. A live edge-service control
   belongs to Stages 3/6.
2. **Sensor health is inventory-only:** last-valid-reading, missing-sample counts, flatline and
   disconnection diagnostics require live acquisition and are Stage 3.
3. **Network outage/buffering scenarios** are not implemented; they require the Stage 6 outbox.
4. **Docker images not built locally** because the Docker daemon was unavailable. Compose config
   remains valid from Stage 1; the Stage 2 schema is migration-managed.
5. **E2E write tests** are skipped unless `PETROSENSE_E2E_ALLOW_WRITES=1` to avoid polluting a
   developer database.
6. **Frontend bundle size warning** persists; route-level splitting remains deferred.
7. **Simulation scenarios are synthetic.** No physical sensor, edge platform or experimental run has
   been integrated or measured.

## 6. Entry criteria for Stage 3

- Keep API, edge, web and E2E checks green.
- Add read-only monitoring endpoints over persisted sessions/windows.
- Add SSE and live/stale state handling.
- Implement sensor-health diagnostics with last-valid-reading and validation propagation.
- Ensure sensor-invalid transition suppresses any current condition display in the UI.
- Document SSE contracts and live-update acceptance tests.
