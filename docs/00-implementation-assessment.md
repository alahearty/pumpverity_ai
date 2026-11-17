# PUMPVERITY AI — Structured Implementation Assessment

**Document status:** Stage 0 assessment, v1.0
**Date:** 2026-11-16
**Project:** Design and Experimental Evaluation of a Low-Cost, Uncertainty-Aware Edge-AI Framework for Robust Fault Detection in Centrifugal Pumps Used in Nigeria's Oil and Gas Industry
**Repository state at assessment:** empty directory, no Git history, no existing code to retain

> PUMPVERITY AI is a six-month academic research prototype. It is not a certified industrial
> safety system, not a predictive-maintenance product and not a replacement for a pump
> protection system. No accuracy, reliability or commercial-readiness claim is made until
> genuine experimental evidence exists.

## Implementation progress

| Stage | Status | Evidence |
|---|---|---|
| 1 — Foundation, auth, schema, shell, CI | Complete | [Stage 1 acceptance](stage-1-acceptance.md) |
| 2 — Pumps/sensors, deterministic simulation, validation, acquisition persistence | Complete | [Stage 2 acceptance](stage-2-acceptance.md) |
| 3 — Live monitoring, sensor health, SSE, dashboard/history views | Complete | [Stage 3 acceptance](stage-3-acceptance.md) |
| 4 — AI pipeline, model registry, uncertainty | Complete | [Stage 4 acceptance](stage-4-acceptance.md) |
| 5 — Alerts, reviews, trends and traceability | Complete | [Stage 5 acceptance](stage-5-acceptance.md) |
| 0.6 — Engineering Copilot and MCP extension | Complete | [Copilot architecture](copilot-and-mcp.md), [Copilot acceptance](copilot-acceptance.md) |

Stages 2–5 and the 0.6 Engineering Copilot preserve the architectural constraints below: simulation
is owned by the edge package, the API persists provenance-tagged outputs, physical acquisition
remains unavailable, and the condition model is a synthetic research artefact only. The Copilot
reuses domain services through MCP and never duplicates inference or review logic. The UI shows a
condition only when a current prediction exists; otherwise it displays **Not inferred**, and
synthetic metrics are labelled.

---

## 1. Assessment summary

There is no existing implementation. The architecture below is therefore a greenfield design,
but it deliberately avoids unnecessary platform complexity: one modular FastAPI service, one
React SPA, a separately packaged edge pipeline and an offline synchronisation protocol. The
design keeps simulation, experimental data and verification status explicit at every layer.

The largest scientific risks are not UI or CRUD risks. They are:

1. **Data provenance confusion** — synthetic signals being presented as experimental evidence.
2. **Sensor/fault conflation** — a disconnected or invalid sensor being shown as a healthy pump.
3. **Unsafe model activation** — unvalidated or incompatible model artefacts becoming active.
4. **Leakage in evaluation** — overlapping windows or the same run appearing in train and test sets.
5. **Unsupported uncertainty claims** — a confidence score being described as a failure probability.

The design addresses these as first-class architectural constraints rather than later additions.

---

## 2. Proposed solution architecture

### 2.1 Four logical layers

| Layer | Responsibility | Deployable component |
|---|---|---|
| L1 Physical data acquisition | Read vibration, timestamp and identify pump/sensor; configurable sampling; missing/invalid detection | Edge acquisition adapters (`SimulatedSensorAdapter`, `PhysicalSensorAdapter`) |
| L2 Edge and data services | Ingest, validate, buffer, infer, persist, alert, sync, track connectivity | Edge service (Python package) + central/API sync receiver |
| L3 AI and analytics | Validation → preprocessing → features → inference → uncertainty → decision → persistence | `edge/` pipeline, independently testable; model artefacts from `ml/` |
| L4 Monitoring application | Auth, dashboards, history, reviews, reports, administration | `apps/api` (FastAPI) + `apps/web` (React SPA) |

### 2.2 Deployment topology for the research prototype

```text
┌─────────────────────────── Edge device (Raspberry Pi target, or lab PC) ───────────────────────────┐
│  PhysicalSensorAdapter / SimulatedSensorAdapter                                                    │
│        │ bounded windows + quality flags                                                           │
│        ▼                                                                                           │
│  SignalValidator → SignalPreprocessor → FeatureExtractor → InferenceEngine                         │
│        │                                         │                                                 │
│        │                                         ▼                                                 │
│        │                                  UncertaintyEvaluator → DecisionPolicy                    │
│        ▼                                                                                           │
│  Local SQLite (readings, windows, predictions, alerts, outbox, settings, model registry cache)     │
│        │                                                                                           │
│        └── transactional outbox ──(retry/backoff, idempotent event IDs)──► central API             │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                 │
                                                              ┌──────────────────▼─────────────────┐
                                                              │ FastAPI (apps/api)                 │
                                                              │ auth, RBAC, pumps, sensors,        │
                                                              │ monitoring, predictions, alerts,  │
                                                              │ reviews, history, reports, models,│
                                                              │ settings, audit, edge-sync        │
                                                              └──────────────────┬─────────────────┘
                                                                                 │ REST + SSE
                                                              ┌──────────────────▼─────────────────┐
                                                              │ React SPA (apps/web)               │
                                                              │ 12 screens, role-aware navigation  │
                                                              └────────────────────────────────────┘
```

For the first demonstrable build the edge service may run on the same laboratory computer as the
API. The boundary remains real: edge persistence and inference must not depend on the API being
reachable. The API is the dashboard/synchronisation server; the edge is the monitoring authority.

### 2.3 Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Service style | Modular monolith, not microservices | Fits a six-month student project; keeps transactions and deployment simple |
| Local database | SQLite in WAL mode | Offline-first, zero administration; PostgreSQL can replace it later via SQLAlchemy |
| Live updates | Server-Sent Events (SSE) | One-way telemetry/alerts; simpler than WebSocket, automatic reconnect semantics |
| Auth | Short-lived JWT access token held in memory + HttpOnly refresh cookie | Avoids bearer tokens in long-lived browser storage; enables session restore |
| Authorisation | Backend dependency checks, not UI hiding | Required by the specification and security review |
| Model runtime | ONNX Runtime preferred; scikit-learn/joblib only for trusted local artefacts | ONNX avoids arbitrary pickle execution; activation still requires metadata/compatibility checks |
| Simulation | Deterministic seeded generator with mandatory `SIMULATED` provenance | Demonstrations must never masquerade as experimental data |
| Raw storage | Bounded acquisition sessions, waveform windows separate from scalar readings | Avoids unbounded high-frequency row growth |
| Uncertainty | Selective classification with documented threshold and risk–coverage evaluation | Abstention is an explicit product behaviour, not a hidden confidence cut-off |
| Ground truth | Separate verification status and reviewer identity; review labels are not automatically ground truth | Preserves scientific defensibility |

---

## 3. Component boundaries

### 3.1 Frontend (`apps/web`)

Owns presentation and client-side interaction state only. It never computes condition decisions,
never labels a sensor-invalid reading as normal, and never treats cached data as fresh. Server
state is fetched through TanStack Query; forms use React Hook Form + Zod; the API is reached
through a single typed client that handles access-token refresh.

### 3.2 Backend (`apps/api`)

Owns authentication, authorisation, persistence of users/pumps/sensors/models/alerts/reviews,
report generation, audit logging and the edge-sync receiver. It exposes versioned REST under
`/api/v1` plus an SSE monitoring stream. It must not perform edge-only inference as a shortcut:
the edge pipeline is the inference authority, and the API stores and serves its outputs.

### 3.3 Edge (`edge/`)

Owns acquisition adapters, signal validation, preprocessing, feature extraction, inference,
uncertainty evaluation, decision policy, local persistence, local alerts and outbox
synchronisation. It runs with no internet connection and restarts safely. It is a Python package
tested independently of the UI.

### 3.4 Machine learning (`ml/`)

Owns dataset manifests, feature contracts, reproducible experiments, evaluation reports and model
artefacts. It is deliberately separate from application source. Every artefact records its
training dataset version, feature contract, code revision, random seeds and evaluation evidence.

### 3.5 Shared contracts (`packages/shared-contracts`)

TypeScript domain enums and DTO types consumed by the web app, kept aligned with the Python
contracts. API schemas remain authoritative; a later stage can generate client types from OpenAPI.

---

## 4. Initial database schema

Full definitions live in [`docs/database/schema.md`](database/schema.md) and in
`apps/api/app/db/models.py`. The required entities and their key relationships are:

```text
roles 1──* users
pumps 1──* sensors
pumps 1──* acquisition_sessions
sensors 1──* acquisition_sessions
operating_regimes 1──* acquisition_sessions
acquisition_sessions 1──* sensor_readings
acquisition_sessions 1──* signal_windows
signal_windows 1──* predictions
model_versions 1──* predictions
model_versions 1──* model_evaluations
predictions 1──* alerts
alerts 1──* alert_reviews
users 1──* alerts (assigned reviewer)
users 1──* alert_reviews (reviewer)
users 1──* audit_logs (actor, nullable for failed logins)
sync_outbox is an edge-local durable event queue
report_jobs records generated report artefacts
```

Key invariants:

- `sensor_readings` and `signal_windows` carry the acquisition session and therefore the pump.
- A `prediction` always links to its window, model version, pump, sensor and session; a
  `SENSOR_INVALID` prediction may have no model version because no inference was attempted.
- `predictions.event_id` and `alerts.event_id` are globally unique durable identifiers used for
  idempotent synchronisation.
- Original prediction values are never updated by an `alert_review`; reviews are append-only.
- `model_version.status` transitions are validated in a service, not by accepting arbitrary writes.
- Simulated and experimental records are distinguished by provenance columns and cannot be mixed
  silently in evaluation or reporting queries.
- Users are deactivated, pumps are retired and evidence rows are not hard-deleted through the UI.

---

## 5. Route map for the 12 screens

| # | Screen | Route | Roles | Stage | Delivery state |
|---|---|---|---|---|---|
| 1 | Login | `/login` | Public | 1 | Functional |
| 2 | Dashboard overview | `/` or `/dashboard` | All authenticated | 3 | Functional |
| 3 | Pump registration | `/pumps` | Administrator, Engineer | 2 | Functional |
| 4 | Live monitoring | `/monitoring` | Administrator, Engineer, Researcher | 3 | Functional |
| 5 | AI analysis and prediction | `/analysis` and `/analysis/:predictionId` | Administrator, Engineer, Researcher | 4 | Functional |
| 6 | Fault alerts and review | `/alerts`, `/alerts/:alertId` | Administrator, Engineer, Reviewer | 5 | Functional |
| 7 | Historical data and trends | `/history` | Administrator, Engineer, Researcher, Reviewer | 5 | Functional; alert overlays |
| 8 | Reports and exports | `/reports` | Administrator, Engineer, Researcher, Reviewer | 0.6 | Generated-report list/download; full templates later |
| 9 | Model management | `/models`, `/models/:modelId` | Administrator, Researcher | 4 | Functional |
| 10 | Sensor health | `/sensors` | Administrator, Engineer, Researcher | 3 | Functional |
| 11 | System settings | `/settings` | Administrator (write), all (read-only subset) | 7 | Route + planned-scope page |
| 12 | User management | `/users` | Administrator | 7 | Read-only user list with backend RBAC |
| — | Not found | `*` | Public | 1 | Functional |

Detailed per-screen specifications (purpose, roles, components, actions, validation, dependencies,
entities, states and acceptance criteria) are in
[`docs/ui/screen-specifications.md`](ui/screen-specifications.md).

---

## 6. Main user journeys

### J1 — Engineer: observe a pump and review an abnormal event

1. Engineer signs in; dashboard loads pump and edge health from the server.
2. Engineer registers the laboratory pump and its vibration sensor, then starts a bounded
   acquisition session in simulated mode (`SIMULATED` provenance visible).
3. Live monitoring shows signal quality, decision, latency and buffering state.
4. A fault decision creates an alert with the original prediction and model version preserved.
5. Engineer opens the alert, acknowledges it, inspects the related window and adds notes.
6. Engineer confirms or corrects the label; the review is stored with identity and timestamp.

### J2 — Researcher: evaluate and promote a model

1. Researcher uploads/registers a model artefact and its metadata.
2. API validates artefact hash, feature contract, runtime compatibility and evaluation evidence.
3. Researcher reviews balanced accuracy, macro-F1, risk–coverage and confusion matrix on a
   clearly labelled evaluation dataset.
4. Authorised researcher activates the validated version; the previous version remains available
   for rollback. Every state change is audited.

### J3 — Reviewer: handle an uncertain event

1. Reviewer opens an `UNCERTAIN` alert, which is reviewable by design.
2. Reviewer inspects quality status, uncertainty score, operating regime and model version.
3. Reviewer records an engineering assessment; the original AI output remains unchanged.
4. The result is marked as an engineering review, not automatically as verified ground truth.

### J4 — Offline operation and synchronisation

1. Network is lost; edge status becomes `OFFLINE_BUFFERING`, local inference continues.
2. Predictions and alerts persist locally with unique event IDs.
3. The edge restarts; unsynchronised events remain in the outbox.
4. Network returns; the synchroniser enters `SYNCING`, sends events with retries.
5. The receiver deduplicates by event ID and acknowledges durable acceptance.
6. Events become `SYNCED` only after acknowledgement; failures are visible and retryable.

### J5 — Sensor failure

1. Sensor disconnects or sends corrupted samples.
2. `SignalValidator` returns `SENSOR_INVALID` and suppresses condition inference.
3. The UI shows grey/purple sensor-invalid status, not a green normal status.
4. An alert is created for sensor health; previous predictions remain historical, never "current".

---

## 7. REST and live-event contracts

Base path: `/api/v1`. Authentication uses a Bearer access token; the refresh token is an
HttpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`. Errors use a single envelope:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email/username or password.",
    "request_id": "…",
    "details": []
  }
}
```

### 7.1 Endpoint groups

| Group | Representative endpoints | Stage |
|---|---|---|
| `/auth` | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me` | 1 |
| `/users` | `GET /users`, `POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-credentials` | 1 (read), 7 (write) |
| `/pumps` | `GET/POST /pumps`, `GET/PATCH /pumps/{id}` | 2 |
| `/sensors` | `GET/POST /sensors`, `GET/PATCH /sensors/{id}`, `GET /sensors/health` | 2–3 |
| `/acquisition-sessions` | `POST /acquisition-sessions`, `POST …/{id}/stop`, `GET …/{id}` | 2 |
| `/monitoring` | `GET /monitoring/overview`, `GET /monitoring/live`, `GET /monitoring/stream` (SSE) | 3 |
| `/predictions` | `GET /predictions`, `GET /predictions/{id}` | 4 |
| `/alerts` | `GET /alerts`, `GET /alerts/{id}`, `POST /alerts/{id}/acknowledge` | 5 |
| `/alert-reviews` | `POST /alert-reviews`, `GET /alerts/{id}/reviews` | 5 |
| `/history` | Existing `GET /monitoring/live` windows plus `GET /alerts` event overlays; export later | 3/5 |
| `/models` | `GET/POST /models`, `POST /models/{id}/validate`, `POST /models/{id}/activate`, `POST /models/{id}/rollback` | 4 |
| `/copilot` | `GET /copilot/status`, `POST /copilot/chat`, conversations, read tools, approvals | 0.6 |
| `/reports` | `GET /reports`, `GET /reports/{id}`, `GET /reports/{id}/download` | 0.6 |
| `/system-settings` | `GET/PATCH /system-settings`, `GET /system-settings/{key}/history` | 7 |
| `/edge-sync` | `POST /edge-sync/events` (idempotent), `GET /edge-sync/status` | 6 |
| `/audit-logs` | `GET /audit-logs` | 7 |
| `/health` | `GET /health`, `GET /system/info` | 1 |

### 7.2 Live events (SSE)

`GET /api/v1/monitoring/stream?pump_id={id}` emits named events:
`reading`, `prediction`, `sensor_health`, `heartbeat`; `alert` and `connectivity` remain future events.
Each event carries `event_id`, `occurred_at`, `pump_id`, `payload_version` and the payload.
Reconnect uses `Last-Event-ID` where possible. Streams are authenticated and pump-scoped.

Full request/response sketches and state-transition rules are in
[`docs/api/rest-and-events.md`](api/rest-and-events.md).

---

## 8. Staged implementation plan

| Stage | Deliverable | Target month | Verification gate |
|---|---|---|---|
| 1 | Foundation: repo, ADRs, schema/migrations, auth/RBAC/audit, design system, Docker, CI, initial tests | 1 | API tests, web lint/test/build, login demonstrated, migration applied |
| 2 | Pumps, sensors, deterministic simulation, acquisition contracts, validation, local persistence | 2 — complete | Pump/sensor workflow tests, simulation determinism tests, invalid-signal tests |
| 3 | Dashboard, live monitoring, sensor health, SSE/live status, history visualisation | 2–3 — complete | Live UI driven by backend, stale-data suppression test, sensor-disconnect demo |
| 4 | AI pipeline, baseline/model integration, registry, uncertainty, AI analysis screen | 3–4 — complete | Pipeline unit tests, model activation guards, risk–coverage evidence |
| 5 | Alerts, acknowledgement, review, label provenance, trends | 4–5 — complete | Review immutability test, alert-to-review integration test |
| 6 | Outbox, synchronisation, connectivity, restart recovery, offline demos | 5 — next | Duplicate delivery, restart persistence and sync idempotency tests |
| 7 | Reports, settings, user management, model-management refinements | 5–6 | Report traceability, configuration audit, RBAC matrix tests |
| 8 | Integration, acceptance tests, documentation, demonstration scripts | 6 | End-to-end 12-screen acceptance run and limitations review |

Experimental data acquisition starts in parallel with Stages 2–4 so that real rig data exists
before the final evaluation. Synthetic data is used only for software integration until replaced
or complemented by measured runs.

### Stage 1 scope (this increment)

In scope:

- repository layout, Git-ready ignore rules, environment templates;
- architecture decision records and initial documentation set;
- complete initial relational schema and Alembic migration;
- password hashing, JWT access tokens, HttpOnly refresh cookie, logout, session restore;
- four roles, server-side role checks, audit logging of authentication events;
- admin-only read-only user listing;
- consistent API errors, request IDs, structured logging, CORS, health endpoint;
- React + TypeScript + Vite + Tailwind design system and application shell;
- functional login/logout/session restore and protected routing for all 12 screen routes;
- backend and frontend automated tests, CI workflow and Docker Compose definition.

Explicitly out of scope for Stage 1: pump registration persistence, acquisition, simulation,
signal processing, model inference, alerts, reviews, reports, settings persistence and model
activation. Their screens are present as clearly labelled planned-scope pages, not fake features.

---

## 9. What can run without hardware

- The full API, database, authentication and dashboard shell.
- The deterministic simulation adapter and every signal/ML workflow (Stages 2–6).
- The edge outbox, restart recovery and sync tests against a local server.
- Model training/evaluation on synthetic or public datasets, clearly labelled as such.
- Every automated test in this repository, on a normal laptop or CI runner.

## 10. What requires experimental verification

- Actual vibration sensor accuracy, mounting repeatability and calibration.
- Real centrifugal-pump fault signatures and label validity.
- Real-data balanced accuracy, macro-F1, false-alert rate and risk–coverage.
- Sensor-invalid detection thresholds on the real acquisition chain.
- Edge inference latency, memory footprint and thermal behaviour on the selected device.
- Field/network conditions in the laboratory environment.
- Any claim of industrial readiness, safety or commercial applicability (not targeted).

Public or synthetic datasets can support methodology development but cannot establish
real-world pump fault-detection performance.

---

## 11. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Synthetic data presented as experimental | Mandatory provenance field; UI badges; reports include provenance; evaluation queries filter by provenance |
| Stale prediction shown as current after sensor loss | Freshness window + data-quality gate; UI suppresses inference when invalid; test asserts no fresh NORMAL |
| Model activation bypass | Server-side transition rules, hash/metadata/compatibility validation, audit trail |
| Review overwrites AI output | Append-only reviews; prediction row immutable through review APIs |
| Train/test leakage | Group splits by acquisition run and held-out operating condition; dataset manifest records grouping |
| Overconfident uncertainty claims | Calibrated/selective policy documented; risk–coverage curves; abstention on low confidence |
| Unbounded raw data growth | Bounded sessions, windowed storage, retention settings, storage budget documented |
| Offline duplicate events | Unique event IDs, receiver idempotency, outbox delivery states, retry/backoff |
| Credentials in frontend or repo | HttpOnly refresh cookie, in-memory access token, `.env` excluded, dev-only seeded demo password |

---

## 12. Stage 1 acceptance criteria

Stage 1 is accepted only when all of the following are demonstrated:

- [ ] Repository and documentation structure exist and describe the architecture, schema, routes,
      contracts, security model and testing strategy.
- [ ] `alembic upgrade head` creates the complete initial schema on an empty SQLite database.
- [ ] Seeded administrator, engineer, researcher and reviewer accounts can authenticate.
- [ ] Invalid credentials return a generic error, are audited, and do not reveal account existence.
- [ ] Access tokens are short-lived; refresh uses an HttpOnly cookie; logout clears the session;
      session restore works after a browser reload.
- [ ] Deactivated users and revoked token versions are rejected.
- [ ] Backend role checks reject an engineer from the administrator-only user list.
- [ ] Every authentication event is recorded in the audit log with actor/context where available.
- [ ] API errors follow the documented envelope and include a request ID.
- [ ] The web app builds, lints and passes component tests.
- [ ] Login, protected routing, logout and role-aware navigation are covered by frontend tests.
- [ ] All 12 screen routes are navigable and clearly marked as planned scope where not yet
      implemented; no fabricated condition, accuracy or connectivity values are displayed.
- [ ] Docker Compose configuration is valid and documented, and CI definitions exist.
- [ ] Known limitations and the Stage 1 verification evidence are recorded.

The next increment (Stage 2) begins only after these criteria are met or deviations are documented.

