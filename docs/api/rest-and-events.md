# REST and live-event contracts

**Base path:** `/api/v1`
**Stage:** Stages 1–5 plus the 0.6 Copilot extension implement authentication, health, runtime
information, the administrator user list, pumps, sensors, operating regimes, simulated acquisition
sessions/windows, monitoring overview/live snapshots, sensor diagnostics, authenticated SSE, the
model registry, prediction persistence, AI analysis data, alert creation, acknowledgement,
append-only engineering review, context-aware Copilot conversations, MCP tool execution, approvals
and Copilot-generated reports. Later endpoint groups are specified as contracts, not claimed as
implemented.

## 1. Conventions

- JSON request and response bodies (`application/json`).
- Bearer access token: `Authorization: Bearer <jwt>`.
- Refresh token: HttpOnly cookie named `petrosense_refresh`, path `/api/v1/auth`.
- Timestamps: ISO 8601 UTC.
- Pagination: `page` (1-based), `page_size` (1–100), response `items`, `total`, `page`, `page_size`.
- Request correlation: `X-Request-ID` response header and `request_id` in errors.
- Role checks are enforced server-side.
- Error envelope:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email/username or password.",
    "request_id": "b871…",
    "details": []
  }
}
```

Validation errors return `422 VALIDATION_ERROR`. Details contain `field`, `message` and `type`;
raw input values (including passwords) are not echoed.

## 2. Implemented endpoints — Stage 1

### `POST /auth/login`

Request:

```json
{ "identifier": "engineer@petrosense.local", "password": "…" }
```

Response `200`:

```json
{
  "access_token": "…",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "…",
    "email": "engineer@petrosense.local",
    "username": "engineer",
    "full_name": "Chinedu Okafor",
    "role": "ENGINEER",
    "is_active": true,
    "must_change_password": false,
    "created_at": "2026-11-16T10:54:00Z",
    "last_login_at": "2026-11-16T11:09:00Z"
  }
}
```

- Sets the refresh cookie.
- Failed, unknown-account and inactive-account logins return the same `401 INVALID_CREDENTIALS`.
- Failure and success are audited.

### `POST /auth/refresh`

- No request body; requires the refresh cookie.
- Returns the same `TokenResponse` shape and rotates the refresh cookie.
- `401 SESSION_EXPIRED` when the cookie is absent/invalid, the account is inactive, or
  `token_version` no longer matches.

### `POST /auth/logout`

- Clears the refresh cookie and audits the logout when a valid access token is supplied.
- Returns `{ "message": "Signed out." }`.

### `GET /auth/me`

- Returns `UserPublic` for the authenticated access token.
- `401 UNAUTHENTICATED` with `WWW-Authenticate: Bearer` when missing/invalid.

### `GET /auth/roles`

- Returns the four supported role values and labels. Authenticated users only.
- UI navigation metadata only; it does not grant permissions.

### `GET /users` — administrator only

Query: `page`, `page_size`, `q` (name/email/username search), `role`, `is_active`.

Response: paginated `UserPublic` items. Never includes `password_hash`. Non-administrator roles
receive `403 FORBIDDEN`; unauthenticated requests receive `401 UNAUTHENTICATED`.

### `GET /health`

Public liveness/readiness response:

```json
{
  "status": "ok",
  "service": "PUMPVERITY AI",
  "version": "0.6.0",
  "environment": "development",
  "database": "ok",
  "timestamp": "2026-11-16T12:07:59Z"
}
```

Returns `503` if the database check fails. This checks the API database, not edge connectivity.

### `GET /system/info`

Authenticated. Returns non-sensitive runtime information: version, environment, database dialect,
auth scheme, token lifetimes, current role and research data mode. Never returns secrets.

## 3. Implemented endpoints — Stages 2–3

### `GET /operating-regimes`

Authenticated read-only reference data. Returns the seeded regimes (`STEADY_STATE`, `STARTUP`,
`SHUTDOWN`, `VARIABLE_LOAD`, `UNKNOWN`).

### Pumps

- `GET /pumps` — all authenticated roles. Query: `page`, `page_size`, `q`, `status`, `pump_type`.
  Returns a page of pumps with nested sensors and default regime.
- `POST /pumps` — Engineer/Administrator. Creates a pump and, optionally, its first sensor in one
  transaction. Pump and sensor codes are trimmed and uppercased.
- `GET /pumps/{id}` — authenticated.
- `PATCH /pumps/{id}` — Engineer/Administrator. Updates mutable identity, ratings, status, notes and
  default operating regime. `pump_code` is immutable.

Create request:

```json
{
  "pump_code": "LAB-PUMP-01",
  "name": "Laboratory Centrifugal Pump",
  "pump_type": "CENTRIFUGAL",
  "location": "Thermofluids Laboratory",
  "rated_speed_rpm": 2900,
  "default_regime_id": null,
  "status": "ACTIVE",
  "notes": "Initial research rig registration.",
  "sensor": {
    "sensor_code": "VIB-01",
    "sensor_type": "VIBRATION",
    "manufacturer": "Research Instruments",
    "model_name": "ACC-100",
    "mounting_axis": "RADIAL_X",
    "mounting_position": "Drive-end bearing housing",
    "sampling_rate_hz": 2048,
    "is_active": true
  }
}
```

Errors include `PUMP_CODE_EXISTS`, `SENSOR_CODE_EXISTS`, `INVALID_OPERATING_REGIME` and validation
errors. Creation/update writes `PUMP_CREATED`, `PUMP_UPDATED` and `SENSOR_CREATED` audit entries.

### Sensors

- `GET /sensors` — all authenticated roles. Query: `page`, `page_size`, `q`, `pump_id`, `is_active`.
- `POST /sensors` — Engineer/Administrator. Registers a sensor and optional pump assignment.
- `GET /sensors/{id}` — authenticated.
- `PATCH /sensors/{id}` — Engineer/Administrator. Assignment, mounting, sampling rate and active
  state are mutable. `sensor_code` is immutable.

- `GET /sensors/health` — authenticated. Optional `pump_id` filter. Returns per-sensor diagnostics
  derived from persisted windows: total/valid/invalid counts, missing-index gaps, last reading,
  last valid reading, freshness, latest quality, sampling status (`NO_DATA`, `RECENT`, `STALE`,
  `SENSOR_INVALID`), fixed `NO_LIVE_CHANNEL` connection state, last valid RMS/peak, latest
  scenario/provenance and current validation issues.

### Acquisition sessions

- `GET /acquisition-sessions` — all authenticated roles. Query: `page`, `page_size`, `pump_id`,
  `status`, `provenance`, `scenario`. Includes `window_count`.
- `POST /acquisition-sessions` — Engineer/Researcher/Administrator. Creates an active session.
- `GET /acquisition-sessions/{id}` — authenticated.
- `POST /acquisition-sessions/{id}/stop` — Engineer/Researcher/Administrator. Body
  `{"status":"COMPLETED"}` or `ABORTED`; repeated stops are idempotent.
- `POST /acquisition-sessions/{id}/windows` — Engineer/Researcher/Administrator. Persists one
  validated window.
- `GET /acquisition-sessions/{id}/windows` — authenticated. Paginated metadata; waveform bytes are
  never returned.

Session create request:

```json
{
  "pump_id": "…",
  "sensor_id": "…",
  "regime_id": null,
  "sampling_rate_hz": 2048,
  "data_provenance": "SIMULATED",
  "random_seed": 42,
  "scenario": "normal",
  "source_device_id": "edge-sim-cli",
  "notes": "Deterministic simulation."
}
```

Stage 2 rules:

- Only `SIMULATED` is accepted; `EXPERIMENTAL` returns
  `422 EXPERIMENTAL_ACQUISITION_UNAVAILABLE`.
- Sensor must belong to the pump (`SENSOR_PUMP_MISMATCH`) and be active (`SENSOR_INACTIVE`).
- Sampling rate must match the sensor configuration within 1% (`SAMPLING_RATE_MISMATCH`).
- The pump's default regime is used when no regime is supplied.
- Start and stop are audited.

Valid window request:

```json
{
  "window_index": 0,
  "window_start": "2026-11-16T12:00:00Z",
  "window_end": "2026-11-16T12:00:01Z",
  "samples": [0.01, 0.02, 0.01],
  "quality_status": "VALID",
  "validation_summary": {"metrics": {"rms": 0.023}},
  "features": null
}
```

Ingestion checks:

- session must be active (`SESSION_NOT_ACTIVE` otherwise);
- duplicate `window_index` returns `409 WINDOW_EXISTS`;
- valid windows require finite samples and timestamps consistent with sample count/rate;
- sensor-invalid windows must omit samples and include a validation summary;
- payloads are stored as little-endian float32; provenance is inherited from the session;
- the API does not re-run the full signal validator and does not make condition decisions.

### Monitoring

- `GET /monitoring/overview` — authenticated dashboard summary: pump/sensor/session/window counts,
  active alerts, latest session/window, a 30-window trend, sensor-health aggregates, data quality,
  active model/latest evaluation, recent sessions. `equipment_condition` is `null` and
  `condition_available=false` until a validated model exists.
- `GET /monitoring/live?pump_id=…&sensor_id=…&limit=25` — authenticated snapshot with latest window,
  downsampled waveform (≤512 points), recent window points, latest session, sensor health and
  separate condition/quality/connectivity/provenance fields. If `sensor_id` is omitted, the first
  active vibration sensor is used. No NORMAL/FAULT value is fabricated.
- `GET /monitoring/stream?pump_id=…&sensor_id=…` — authenticated SSE stream. Sends an immediate
  heartbeat, `reading` events for valid windows, `sensor_health` events for invalid windows and a
  heartbeat every 15 seconds. New windows are detected by database polling every ~2 seconds.
  `max_events` is a diagnostic bound used by tests; normal clients omit it. The browser uses a
  fetch-based SSE reader with the Bearer access token (no token in the URL).

## 4. Implemented endpoints — Stages 4–5 and Copilot

### Models

- `GET /models` — authenticated. Query: `page`, `page_size`, `status`, `runtime`, `q`. Returns model
  versions with their latest evaluation.
- `POST /models` — Researcher/Administrator. Registers metadata only: model code/version, algorithm,
  runtime, feature contract, training/evaluation dataset versions, deployment compatibility,
  artefact path and SHA-256. Duplicate code/version returns `409`. The API does not upload or execute
  an artefact.
- `GET /models/active` — authenticated. Returns the active model or `null`. Used by the edge to
  discover the current model.
- `GET /models/{id}` — authenticated. Returns metadata plus all evaluations.
- `POST /models/{id}/evaluations` — Researcher/Administrator. Attaches evaluation evidence. A
  verified evaluation requires balanced accuracy and macro-F1; provenance is explicit.
- `POST /models/{id}/validate` — Researcher/Administrator. Requires a verified evaluation, valid
  feature contract, artefact hash and a supported runtime (`BASELINE` or `LINEAR_JSON`).
- `POST /models/{id}/activate` — Researcher/Administrator. Requires `VALIDATED`; retires the current
  active model and audits the transition. Only one model is active.
- `POST /models/rollback` — Researcher/Administrator. Restores the most recently active retired
  version.

Activation is metadata/policy validation, not execution. The edge verifies the artefact hash and
feature contract before loading it. ONNX, scikit-learn and TFLite runtime values may be registered
but are rejected for activation in the current build.

### Predictions

- `POST /predictions` — Engineer/Researcher/Administrator (edge-originated).
- `GET /predictions` — all authenticated roles. Filters: `pump_id`, `sensor_id`, `decision`,
  `model_version_id`.
- `GET /predictions/{id}` — authenticated prediction detail.

Prediction ingestion rules:

- pump, sensor, session and signal window references must be consistent;
- `event_id` is unique (`409 PREDICTION_EXISTS` otherwise);
- model decisions require a `VALID` window, an active-at-inference model version and a window
  feature vector satisfying the model feature contract;
- `UNCERTAIN` is stored as an explicit decision and remains reviewable;
- `SENSOR_INVALID` requires a sensor-invalid window and forbids a model or scores;
- provenance is derived from the acquisition session;
- original predictions are immutable; alert creation and engineering review are appended separately;
- `FAULT`, `UNCERTAIN` and `SENSOR_INVALID` decisions create at most one alert per prediction when
  the corresponding `alerts.auto_create_for_*` setting is enabled.

Example condition prediction:

```json
{
  "event_id": "pred-...",
  "pump_id": "…",
  "sensor_id": "…",
  "session_id": "…",
  "signal_window_id": "…",
  "model_version_id": "…",
  "decision": "UNCERTAIN",
  "data_quality": "VALID",
  "decision_score": 0.393,
  "uncertainty_score": 0.393,
  "explanation": "Score lies inside the uncertainty band.",
  "latency_ms": 0.18,
  "inferred_at": "2026-11-16T16:38:00Z"
}
```

### Alerts

- `GET /alerts` — all authenticated roles. Filters: `page`, `page_size`, `status`, `category`,
  `severity`, `pump_id`, `sensor_id`, `assigned_to`, `created_from`, `created_to`. Items include the
  source prediction decision, model identity, window interval, review count and assignment.
- `GET /alerts/{id}` — alert detail with the retained prediction and ordered review trail.
- `POST /alerts/{id}/acknowledge` — Engineer/Reviewer/Administrator. Moves `OPEN` to
  `ACKNOWLEDGED`, assigns the acting reviewer when unassigned, records an `ACKNOWLEDGE` review and
  writes an audit entry. Repeated acknowledgement is idempotent.
- `GET /alerts/{id}/reviews` — authenticated ordered review trail.
- `POST /alert-reviews` — Engineer/Reviewer/Administrator. Appends an engineering judgement.

Alert creation is synchronous with prediction ingestion. A prediction can own at most one alert
(`uq_alerts_prediction_id`). Alerts inherit provenance from the prediction/session. They are not yet
emitted on the SSE stream.

Review rules:

- actions are `REVIEW`, `CONFIRM_LABEL`, `CORRECT_LABEL`, `ADD_NOTE` and `CLOSE`;
- `REVIEW` and `ADD_NOTE` require at least three characters of notes;
- `CONFIRM_LABEL` requires the original decision and rejects a mismatch (`422 LABEL_MISMATCH`);
- `CORRECT_LABEL` requires a different label (`422 LABEL_NOT_CORRECTED`);
- only label actions may carry `reviewed_label`;
- `CLOSE` sets `closed_at`; closed/dismissed alerts reject further reviews with `409 ALERT_CLOSED`;
- every review uses `label_source = ENGINEER_REVIEW` and `is_verified_ground_truth = false`;
- the original prediction row is never updated.


### Engineering Copilot

All endpoints require an authenticated Bearer token. Context and response fields use camelCase
aliases matching the shared TypeScript contracts.

- `GET /copilot/status` � provider/MCP availability, transport and tool count.
- `POST /copilot/chat` � body: `message`, optional `conversationId`, typed `context`. Returns the
  assistant message, tool runs, availability and an optional pending approval. Write tools are never
  executed here.
- `GET /copilot/conversations/{id}` � owner-scoped conversation, messages, tool runs and pending
  approvals.
- `POST /copilot/tools/{toolName}` � explicit read-only tool invocation. Write tool names return
  `403 COPILOT_TOOL_NOT_ALLOWED`.
- `POST /copilot/approvals/{id}/approve` � revalidate and execute the exact stored write arguments.
  Repeating the call returns the existing result; no duplicate side effect.
- `POST /copilot/approvals/{id}/reject` � close a pending write without executing it.

The Copilot orchestrator calls a custom official-SDK FastMCP server. Production/development uses
Streamable HTTP (`http://127.0.0.1:8010/mcp`) with a private service token; automated tests use the
same MCP protocol over the SDK memory transport. MCP tools are not exposed through the browser.

### Reports

- `GET /reports` � authenticated list of generated report jobs.
- `GET /reports/{id}` � report metadata.
- `GET /reports/{id}/download` � authenticated JSON download of a generated report artefact.

Reports are created by the approved `pumpverity_generate_monitoring_report` Copilot tool and always
record their requester, SHA-256 and simulated-data disclosure.

## 5. Planned endpoint groups

| Group | Planned endpoints | Stage |
|---|---|---|
| History exports | `GET /history/export` | Later |
| Settings | `GET/PATCH /system-settings`, `GET /system-settings/{key}/history` | 7 |
| Edge sync | `POST /edge-sync/events`, `GET /edge-sync/status` | 6 |
| Audit | `GET /audit-logs` (administrator) | 7 |

## 6. Live updates (SSE) — implemented Stages 3–4

`GET /monitoring/stream?pump_id={id}` with a Bearer token. Event names currently emitted:

- `reading` — new valid persisted window
- `sensor_health` — new sensor-invalid window
- `prediction` — new persisted model prediction
- `heartbeat` — immediate connection heartbeat and 15-second keepalive

Future event names reserved for later stages: `alert`, `connectivity`. Alert records and reviews are
created synchronously today, but alert events are not yet streamed.

Envelope:

```json
{
  "event_id": "…",
  "event_type": "reading",
  "occurred_at": "2026-11-16T12:00:00Z",
  "pump_id": "…",
  "payload_version": 1,
  "payload": {}
}
```

Implementation notes:

- authenticated and pump/sensor-scoped;
- the client reconnects after normal close or error with a 3-second delay;
- the server polls the database every ~2 seconds, so delivery latency is bounded but not instant;
- the stream is API update delivery, not physical edge connectivity;
- no stale prediction may be presented as current after a sensor-invalid transition;
- the frontend invalidates monitoring queries on `reading`/`sensor_health` and leaves the last chart
  frozen only when the user explicitly pauses it.

## 7. Planned edge synchronisation contract

`POST /edge-sync/events` receives a batch of outbox events:

```json
{
  "source_device_id": "edge-lab-01",
  "events": [
    {
      "event_id": "pred-…",
      "event_type": "prediction.created",
      "occurred_at": "2026-11-16T12:00:00Z",
      "payload_version": 1,
      "payload": {}
    }
  ]
}
```

Required receiver behaviour:

- authenticate the device/user and validate event schema/version;
- deduplicate by `event_id` and domain uniqueness constraints;
- process each event idempotently;
- return per-event outcomes (`accepted`, `duplicate`, `rejected`) with reasons;
- only acknowledge after durable database commit;
- reject events whose payload violates provenance or referential rules.

## 8. Compatibility and documentation

- `/docs` exposes OpenAPI generated by FastAPI; it is authoritative for implemented endpoints.
- Breaking changes require a new path version (`/api/v2`), not silent contract changes.
- Model feature contracts are application-level contracts and must be validated at registration
  and activation, independently of REST versioning.

