# Stage 3 acceptance evidence

**Date:** 2026-11-16
**Environment:** Windows 11, Python 3.13, Node.js 24, Chrome (Playwright), SQLite
**Isolation:** Write/E2E/SSE verification used the temporary database
`apps/api/data/stage3-verify.db`; the developer database remained untouched, and the temporary
database was deleted after verification.
**Versions:** API `0.3.0`, edge package `0.3.0`, migration `bb5d543b303c`

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Monitoring overview and live snapshot are served from persisted windows | **Met** | API tests; dashboard/live UI |
| 2 | Live monitoring shows latest waveform, downsampled preview, RMS trend, sampling metadata and timestamps | **Met** | `/monitoring/live`, Live Monitoring UI |
| 3 | User can pause chart rendering and select the trend window | **Met** | Live Monitoring controls; frontend tests |
| 4 | Authenticated SSE stream delivers heartbeats and new-window events | **Met** | SSE heartbeat test; 7-test Playwright run with live update |
| 5 | An open live page updates after a new simulated scenario without manual reload | **Met** | Playwright live/SSE test: Normal then Imbalance appeared while page was open |
| 6 | Sensor health diagnostics show last valid reading, invalid count, gaps, sampling status and validation warnings | **Met** | `/sensors/health`, Sensor Health UI/tests |
| 7 | Sensor-invalid latest data suppresses the waveform/condition display | **Met** | Manual sensor-disconnect run; Live UI and API state |
| 8 | Equipment condition is not fabricated while no model exists | **Met** | `condition_available=false`, "Not inferred" UI across Dashboard/Live/History |
| 9 | Dashboard uses real backend counts and latest monitoring state | **Met** | `/monitoring/overview`, dashboard UI |
| 10 | Basic historical trend and window records are available | **Met** | Historical data and trends UI |
| 11 | Read access and SSE remain authenticated | **Met** | API 401 guards; SSE auth test |
| 12 | Existing authentication, equipment, simulation and migration checks remain green | **Met** | Full verification below |

## 2. Executed verification

```text
API ruff check ......................... All checks passed
API pytest ............................. 47 passed
Edge ruff check ........................ All checks passed
Edge pytest ............................ 26 passed
Web oxlint ............................. 0 errors, 3 fast-refresh warnings
Web vitest ............................. 30 passed
Web tsc + vite build ................... passed (bundle-size warning)
Playwright ............................. 7 passed (auth, equipment, live/SSE)
Alembic ................................ 3 migrations applied
```

The Playwright live-monitoring test:

1. created a pump/sensor through the API;
2. ran the edge simulator with a `normal` scenario;
3. opened Live Monitoring and selected the pump;
4. confirmed the SSE stream was connected and showed "Not inferred";
5. ran an `imbalance` scenario through the edge CLI while the page stayed open;
6. observed the live view change to the imbalance scenario without a manual reload.

SSE is implemented as an authenticated streaming response with an initial heartbeat, periodic
heartbeats and database-backed new-window polling every two seconds. The browser uses a fetch-based
SSE reader so the Bearer access token is not placed in a URL.

## 3. Sensor-invalid evidence

A `sensor_disconnect` scenario was run against the same isolated sensor after the live/SSE test:

```text
latest_quality ......... SENSOR_INVALID
waveform ............... null
condition_available .... false
sampling status ........ SENSOR_INVALID
invalid windows ........ 2
missing index gaps ..... 0
```

Live Monitoring displayed the sensor-invalid warning, "Not inferred" condition, no current
waveform, and the validation codes `sensor_disconnected` and `missing_samples`. The last valid RMS
remained visible but explicitly labelled as last valid.

## 4. Isolated database summary

```text
pumps .................... 2
sensors .................. 2
sessions ................. 3
windows .................. 6
valid windows ............ 4
invalid windows .......... 2
payload bytes ............ 32768   (4 × 2048 samples × float32)
scenarios ................ normal, imbalance, sensor_disconnect
```

This demonstrates software integration only. It is not evidence of real pump-fault detection.

## 5. Schema/index changes

- `signal_windows (sensor_id, created_at)` index for live/health queries.
- `acquisition_sessions (sensor_id, started_at)` index for latest-session queries.
- Migration `bb5d543b303c` applied.
- No fabricated prediction or alert schema is introduced in Stage 3.

## 6. Deviations and limitations

1. **SSE delivery is database-polled**, not an in-process push bus. It is durable and works across
   API processes, but new-window latency is up to roughly two seconds. Reconnects rely on the
   snapshot/polling fallback for any events written while disconnected.
2. **No physical edge channel exists.** "No live channel" is displayed explicitly; the SSE stream
   is API update delivery, not sensor connectivity.
3. **Condition inference is not implemented.** "Not inferred" is shown instead of forcing a
   Normal/Fault label.
4. **Historical Trends is a basic Stage 3 view.** Date-range filters, event overlays, model-version
   markers and exports remain Stage 5.
5. **Scenario injection is CLI-driven.** Sensor-disconnect and corrupted-sample scenarios are run
   through the edge simulator; the browser does not launch the edge process. Network outage and
   buffering controls remain Stage 6.
6. **The bundle grew to ~975 kB minified** because charting is now included. Route-level code
   splitting remains a later optimisation.
7. **E2E write/SSE tests are skipped by default** unless
   `PETROSENSE_E2E_ALLOW_WRITES=1` and an isolated database are used.
8. **Docker images remain unbuilt locally** because the Docker daemon was unavailable; Compose
   configuration still validates.

## 7. Entry criteria for Stage 4

- Keep monitoring, SSE, equipment and authentication tests green.
- Add signal preprocessing/feature extraction with a versioned feature contract.
- Add model registry, inference and uncertainty policy.
- Replace "Not inferred" only when a validated model is active.
- Preserve sensor-invalid suppression ahead of model inference.
- Add model evaluation evidence and risk–coverage reporting before any accuracy claim.
