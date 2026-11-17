# UI screen specifications

**Version:** 0.6 (Copilot extension)
**Design identity:** Deep Navy `#0B1F33` sidebar/brand, Industrial Blue `#2563EB` primary action,
Teal `#00A6A6` accent, Light Grey `#F5F7FA` canvas. Green = normal/success, red = fault,
amber = uncertain, grey/purple = sensor invalid.

Each section records the target research-depth behaviour. Status labels state what actually exists
in this build. Planned screens deliberately display no fabricated operational values.

---

## Global Engineering Copilot

**Availability:** Authenticated application shell; static sign-in help on Login only.

**Behaviour:** Collapsible bottom-right panel reporting provider/MCP status, current screen, selected
pump/sensor/alert, monitoring mode and connectivity. It displays grounded MCP tool results,
suggested questions, validated navigation actions and exact-argument confirmation for writes. It can
be closed or minimised and never replaces the monitoring workspace. Login cannot invoke MCP
monitoring tools.

---

## Screen 1 — Login

**Route:** `/login` (public)
**Status (Stage 4):** Functional.

**Purpose:** Authenticate research-team accounts and establish a secure, restorable session.

**Roles:** Public route; all four roles authenticate here.

**Components:** Split industrial brand panel; email/username field; password field with show/hide;
submit button with loading state; inline field errors; server error alert with request ID;
session-handling note; research-use disclaimer.

**Actions:** Submit credentials; toggle password visibility; restore session on reload; redirect to
the originally requested protected route; logout from the shell.

**Validation:** Identifier 3–255 characters; password 8–128 characters; trimmed identifier; generic
credential error; no password value echoed in error responses.

**Backend dependencies:** `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`,
`GET /auth/me`.

**Data entities:** `users`, `roles`, `audit_logs`.

**States:** Loading (session restore), idle, submitting, invalid credentials, validation error,
server unreachable, authenticated redirect.

**Acceptance criteria:**

- Invalid credentials show one generic message and never reveal account existence.
- Successful login sets an HttpOnly refresh cookie and returns a short-lived access token.
- Reload restores the session through the refresh cookie without storing the access token in
  persistent browser storage.
- Logout clears the cookie and returns the user to login.
- Successful and failed logins are audited.

---

## Screen 2 — Dashboard overview

**Route:** `/dashboard`
**Status (Stage 4):** Functional monitoring dashboard driven by `/monitoring/overview`: pump, sensor,
session and window counts, latest waveform/trend preview, sensor-health aggregates, data quality,
active alerts count, latest model/evaluation state, recent acquisition activity and current model
decision. Equipment condition is shown only for a current prediction; otherwise it is **Not
inferred**. Decision scores are explicitly not failure probabilities.

**Purpose:** Provide an operational overview of pumps, equipment condition, alerts, sensor health,
edge connectivity, latest model/evaluation and recent events.

**Roles:** All authenticated users.

**Components:** Page header; API/session status cards; planned monitoring cards; live vibration
preview placeholder; recent-events empty state; account/session card; provenance policy card;
research notice.

**Actions:** Refresh real API/system status; navigate to module screens.

**Validation:** Displayed status must come from backend state. No accuracy claim is shown without a
verified evaluation; otherwise "Not yet evaluated".

**Backend dependencies (target):** `GET /monitoring/overview`, `GET /alerts`, `GET /models`,
`GET /models/{id}/evaluations`, SSE stream. Stage 1 uses `GET /health` and `GET /system/info`.

**Data entities:** `pumps`, `sensors`, `alerts`, `predictions`, `model_versions`,
`model_evaluations`, `acquisition_sessions`.

**States:** API loading/online/degraded/unreachable; no pumps; no active acquisition; no model; not
evaluated; empty recent events.

**Acceptance criteria:**

- Equipment condition (Normal/Fault/Uncertain) is distinct from data quality (Valid/Sensor
  Invalid) and connectivity.
- A sensor-invalid condition is never rendered as a verified normal pump.
- Latest model evaluation displays macro-F1, balanced accuracy, dataset and model version only when
  a verified evaluation exists; otherwise "Not yet evaluated".
- All demo/simulated values are labelled.
- Card values are driven by backend responses, not hardcoded metrics.

---

## Screen 3 — Pump registration

**Route:** `/pumps`, `/pumps/new`, detail/edit in later stage
**Status (Stage 4):** Functional. Pump creation with nested initial sensor, pump editing, sensor
association display, operating-regime default and recent simulated session visibility are active.

**Purpose:** Register and maintain the laboratory pump and its sensor assignment.

**Roles:** Administrator, Engineer.

**Components:** Registration form; validation errors; duplicate-code feedback; pump list/detail;
sensor assignment selector; equipment status control.

**Fields:** Pump ID/code, name, type, laboratory location, rated speed (RPM), sensor ID, mounting
axis, sensor position, operating regime tag, registration date, equipment status.

**Actions:** Create, view, edit, assign sensor, retire pump.

**Validation:** Required fields; positive rated speed; unique pump/sensor codes; valid enum values;
sensor association must exist; no destructive delete.

**Backend dependencies:** `GET/POST /pumps`, `GET/PATCH /pumps/{id}`, `GET/POST /sensors`.

**Data entities:** `pumps`, `sensors`, `operating_regimes`, `audit_logs`.

**States:** Loading, empty registry, validation error, duplicate conflict, saved, forbidden.

**Acceptance criteria:**

- A pump and its vibration sensor can be registered and retrieved.
- Duplicate pump/sensor IDs are rejected with a useful conflict response.
- Registration is attributable to the signed-in engineer.
- Historical records are not deleted when a pump is retired.

---

## Screen 4 — Live monitoring

**Route:** `/monitoring`
**Status (Stage 4):** Functional live replay over persisted simulated windows. Includes waveform and
RMS trend charts, pause/window controls, selected pump/sensor, SSE connection status, current model
decision/uncertainty, sensor diagnostics, session context and separate
condition/quality/connectivity/provenance states. No physical live channel is active; sensor-invalid
windows suppress condition inference. Sensor disconnect/corruption scenarios are injected via the
edge CLI; network outage controls remain Stage 6.

**Purpose:** Observe live validated vibration data and acquisition context with explicit quality and
connectivity state.

**Roles:** Administrator, Engineer, Researcher.

**Components:** Latest-value panel; live waveform chart; sampling/window information; units;
timestamp; decision badge; sensor quality; edge connectivity; local buffering state; window
selector; pause control; live/simulated mode; scenario controls.

**Actions:** Select pump/time window; pause rendering; switch simulation scenarios; simulate sensor
disconnect; simulate network outage; resume.

**Validation:** Reject invalid time windows; simulation is explicitly labelled; stale data is marked.

**Backend dependencies:** `GET /monitoring/live`, `GET /monitoring/stream` (SSE),
`GET /monitoring/overview`, acquisition-session controls.

**Data entities:** `acquisition_sessions`, `sensor_readings`, `signal_windows`, `predictions`,
`sync_outbox`.

**States:** Connecting, live, paused, stale, sensor invalid, offline buffering, syncing, no session,
simulation mode.

**Acceptance criteria:**

- Invalid sensor data suppresses current condition inference and removes any stale normal/fault
  badge.
- The chart shows units and the latest reading timestamp.
- Connectivity state is displayed separately from sensor quality.
- Network loss does not stop local inference; buffering is visible.
- Simulated data is visibly labelled at all times.

---

## Screen 5 — AI analysis and prediction

**Route:** `/analysis`, `/analysis/:predictionId`
**Status (Stage 4–5):** Functional. Lists persisted predictions and shows model version, decision,
decision score, uncertainty, data quality, latency, inference time, operating context, explanation,
signal-window metadata and feature values. The screen states that non-NORMAL decisions create
reviewable alerts and that the prediction remains immutable. Direct prediction-to-alert navigation
is not implemented yet.

**Purpose:** Present one inference with enough context for scientific and engineering review.

**Roles:** Administrator, Engineer, Researcher.

**Components:** Decision panel; score/uncertainty; data validity; model name/version; feature
contract summary; latency; inference time; operating regime; explanation/review reason; links to
alert and historical event.

**Actions:** Open linked alert/event; inspect model details.

**Validation:** Scores are labelled as decision scores, not failure probabilities. Sensor-invalid
records display no model decision. UNCERTAIN records explain which acceptance criterion failed.

**Backend dependencies:** `GET /predictions/{id}`, `GET /alerts/{id}`, `GET /models/{id}`.

**Data entities:** `predictions`, `signal_windows`, `model_versions`, `alerts`,
`operating_regimes`.

**States:** Valid normal, valid fault, valid uncertain, sensor invalid, model unavailable, record
not found.

**Acceptance criteria:**

- The four outcomes are visually and semantically distinct.
- Sensor invalid explicitly states that inference was not attempted.
- Original model output is immutable and traceable.
- Review-required explanations are specific enough to guide an engineer.
- Numerical scores are not misrepresented as probabilities of mechanical failure.

---

## Screen 6 — Fault alerts and engineering review

**Route:** `/alerts`, `/alerts/:alertId`
**Status (Stage 5):** Functional. Auto-created alerts, filters, detail panel, acknowledgement,
append-only reviews and history overlay are active.

**Purpose:** Triage alerts and capture append-only engineering judgement.

**Roles:** Administrator, Engineer, Reviewer.

**Components:** Alert queue; filters (status, category, severity, pump); detail panel with original
prediction, model, window and provenance; acknowledge/review form; label confirmation/correction;
notes; reviewer and timestamp timeline.

**Actions:** View, filter, acknowledge, record review, confirm/correct label, add note, close alert.
Assignment is set to the acting reviewer on acknowledgement/review; a separate assignment action is
not implemented.

**Validation:** Reviewer required; notes required for review/note actions; confirmation must match the
original decision; correction must differ; reviewed label must be a valid enum; original AI
prediction cannot be edited.

**Backend dependencies:** `GET /alerts`, `GET /alerts/{id}`,
`POST /alerts/{id}/acknowledge`, `POST /alert-reviews`, `GET /alerts/{id}/reviews`.

**Data entities:** `alerts`, `alert_reviews`, `predictions`, `model_versions`, `users`,
`audit_logs`.

**States:** Open, acknowledged, reviewed, closed, dismissed; loading, empty, forbidden.

**Acceptance criteria:**

- Original AI prediction, model version, reviewer identity and timestamps are retained.
- The review never silently overwrites the original prediction.
- Engineer-reviewed labels are distinguished from verified experimental ground truth.
- Uncertain and sensor-invalid alerts are reviewable.
- Filters and review actions are covered by integration tests.

---

## Screen 7 — Historical data and trends

**Route:** `/history`
**Status (Stage 5):** Functional trend view over the last selected windows: pump/sensor selector,
RMS trend, sensor-invalid rows, window metadata and alert-backed event overlays aligned to persisted
signal windows. Date-range filters, model-version markers and exports remain later work.

**Purpose:** Explore historical readings and events with scientific provenance and traceability.

**Roles:** All authenticated roles.

**Components:** Date/time filters; pump selector; vibration trend; anomaly/event overlay;
operating-regime labels; sensor-invalid intervals; model version indicators; export controls.

**Actions:** Filter, inspect event, export CSV.

**Validation:** Date range order; bounded export size; optional channels only when hardware is
connected.

**Backend dependencies:** `GET /history/readings`, `GET /history/events`,
`GET /history/export`, `GET /predictions`.

**Data entities:** `sensor_readings`, `signal_windows`, `predictions`, `alerts`,
`model_versions`, `operating_regimes`, `acquisition_sessions`.

**States:** Loading, no data for range, partial data, export running, export failed.

**Acceptance criteria:**

- Sensor-invalid intervals are visually distinct from equipment faults.
- Each event can be traced to the correct pump and model version.
- Exports include units, timestamps and provenance.
- Simulated and experimental records are not silently mixed.

---

## Screen 8 — Reports and exports

**Route:** `/reports`
**Status (0.6):** Functional generated-report list and authenticated JSON download. Full report-template generation remains later.

**Purpose:** Produce traceable research and operational reports.

**Roles:** All authenticated roles (report permissions refined per type).

**Components:** Report-type selector; date/pump filters; CSV/PDF controls; generation history table;
download action; provenance disclosure.

**Report types:** Monitoring summary, alert history, model evaluation, sensor health, engineering
review, experimental data export.

**Actions:** Generate, list, download, filter.

**Validation:** Required date range and pump selection where relevant; safe filename; report job
must complete before download.

**Backend dependencies:** `POST /reports`, `GET /reports`, `GET /reports/{id}`,
`GET /reports/{id}/download`.

**Data entities:** `report_jobs`, `predictions`, `alerts`, `model_evaluations`, `audit_logs`.

**States:** Queued, running, completed, failed; empty history.

**Acceptance criteria:**

- Reports identify dataset, model version, timestamps and filters.
- Simulation-derived content is marked as simulated.
- Report generation is attributable to the requester.
- Partial or failed reports are never served as complete.

---

## Screen 9 — Model management

**Route:** `/models`, `/models/:modelId`
**Status (Stage 4):** Functional registry: metadata, artefact hash, feature contract, synthetic
evaluation metrics/provenance, validation, activation and rollback. Registration is performed by the
research pipeline/API; the UI does not upload or execute model files.

**Purpose:** Manage model artefacts with metadata, evaluation evidence, compatibility and safe
activation.

**Roles:** Administrator, Researcher.

**Components:** Registry table; model detail; metadata form; evaluation results; risk–coverage and
calibration views; compatibility indicators; activate/rollback controls; change history.

**Displayed fields:** Model ID, name, version, algorithm, input feature contract, training dataset
version, evaluation dataset, balanced accuracy, macro-F1, risk–coverage, artefact hash, deployment
compatibility, status.

**Actions:** Register, view, validate, activate, retire, roll back.

**Validation:** Artefact hash and metadata; feature contract; runtime compatibility; evaluation
provenance; only validated compatible versions may activate; activation is role-restricted and
audited.

**Backend dependencies:** `GET/POST /models`, `POST /models/{id}/validate`,
`POST /models/{id}/activate`, `POST /models/{id}/rollback`.

**Data entities:** `model_versions`, `model_evaluations`, `predictions`, `audit_logs`.

**States:** Registered, validated, active, retired, rejected; loading, empty.

**Acceptance criteria:**

- Upload is not executable code execution.
- A model cannot become active without metadata and compatibility checks.
- The previous version remains available for rollback.
- Evaluation metrics are shown with dataset provenance and are never invented.

---

## Screen 10 — Sensor health

**Route:** `/sensors`
**Status (Stage 4):** Functional diagnostics: registration, pump association, active state, last valid
reading/RMS, latest quality, sampling/freshness status, invalid-window and missing-gap counts, and
current validation warnings. Connection is explicitly `NO_LIVE_CHANNEL`; no physical sensor stream is
claimed.

**Purpose:** Evaluate sensor validity and freshness before inference.

**Roles:** Administrator, Engineer, Researcher.

**Components:** Sensor list; association; type; last valid reading; sampling status; connection
state; missing-data count; validation warnings; data-quality badge.

**Detection:** Missing samples, invalid numeric values, unexpected timestamps, out-of-range values,
sustained flatline, disconnection.

**Actions:** View sensor detail; filter by pump/status; (later) edit assignment.

**Validation:** Sensor-invalid state must propagate to the decision policy; stale data must not
appear current.

**Backend dependencies:** `GET /sensors`, `GET /sensors/health`,
`GET /monitoring/overview`.

**Data entities:** `sensors`, `sensor_readings`, `signal_windows`, `predictions`, `alerts`.

**States:** Connected/valid, stale, disconnected, sensor invalid, loading, empty.

**Acceptance criteria:**

- Sensor failure is independent of equipment fault status.
- Last valid reading time makes staleness visible.
- No fresh normal inference is generated from invalid data.
- Validation warnings are retained and reviewable.

---

## Screen 11 — System settings

**Route:** `/settings`
**Status (Stage 4):** Read-only runtime information is functional; editable settings are planned for
Stage 7.

**Purpose:** Configure sampling, signal windows, alert/uncertainty thresholds, retention, sync,
device identity, export preferences and model configuration.

**Roles:** Read: all authenticated; write: Administrator (permission matrix refined later).

**Components:** Runtime information (current); grouped settings forms (planned); validation
messages; audit-history view.

**Actions:** View settings, modify authorised values, reset to documented defaults, view change
history.

**Validation:** Numeric ranges; window size/overlap compatibility; threshold ordering; retention
bounds; device identity required; all changes validated before apply.

**Backend dependencies:** `GET/PATCH /system-settings`,
`GET /system-settings/{key}/history`, `GET /system/info`.

**Data entities:** `configuration_settings`, `audit_logs`, `model_versions`, `sync_outbox`.

**States:** Loading, read-only, editable, saving, validation error, forbidden.

**Acceptance criteria:**

- Sensitive changes are restricted by backend role checks.
- Every change is audited with before/after values.
- Invalid configuration cannot be applied.
- Secrets are never returned to the browser.

---

## Screen 12 — User management

**Route:** `/users`
**Status (Stage 4):** Functional read-only account list for administrators.

**Purpose:** Administer research-team accounts and roles.

**Roles:** Administrator only.

**Components:** Account table; search; role filter; status badge; pagination; (planned) create/edit
dialog; activation toggle; role assignment; credential reset.

**Actions:** View accounts (current); add, edit, activate/deactivate, assign role, reset credentials
(Stage 7).

**Validation:** Unique email/username; valid role; password policy; cannot deactivate the last
administrator; token-version invalidation on credential reset; all actions audited.

**Backend dependencies:** `GET /users` (current); future `POST/PATCH /users`,
`POST /users/{id}/reset-credentials`.

**Data entities:** `users`, `roles`, `audit_logs`.

**States:** Loading, populated, empty, forbidden, API error.

**Acceptance criteria:**

- User list is visible only to administrators, enforced by the API.
- Passwords and password hashes are never returned.
- Account changes (Stage 7) are attributable and audited.
- Role changes take effect on subsequent authorisation checks.

---

## Cross-screen requirements

- Headings, navigation, cards and tables use the shared design system.
- All operational values are backend-driven with timestamps and units.
- Loading, empty, error and forbidden states are explicit.
- Every screen is responsive and keyboard-accessible.
- Planned features are labelled; no screen claims an unverified accuracy or readiness level.
- Simulation provenance is visible wherever simulated data appears.

