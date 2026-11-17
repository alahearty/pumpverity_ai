# System architecture

**Version:** 0.6 (Engineering Copilot extension)
**Related:** [Implementation assessment](../00-implementation-assessment.md)

## 1. Goals and constraints

The architecture must:

- operate without continuous internet access;
- distinguish equipment faults, sensor validity and connectivity;
- keep simulation and experimental evidence separate;
- support uncertainty-aware abstention and human review;
- remain testable without physical hardware;
- fit a six-month academic project and a small student team;
- avoid unsupported industrial-readiness claims.

Constraints accepted for the prototype:

- one laboratory centrifugal-pump rig initially;
- SQLite local persistence, PostgreSQL optional later;
- one API service, no microservices;
- local test-server synchronisation rather than a production cloud;
- no industrial control integration and no autonomous shutdown.

## 2. Logical layers

| Layer | Components | Stage |
|---|---|---|
| L1 Physical data acquisition | `SimulatedSensorAdapter` (implemented), `PhysicalSensorAdapter` placeholder, scenario generator | 2 |
| L2 Edge and data services | `SignalValidator`, API window ingestion, monitoring/sensor-health queries, SSE updates, local persistence; outbox/sync Stage 6 | 2–3/6 |
| L3 AI and analytics | versioned features, JSON model loading, inference, uncertainty/abstention, decision policy, model registry/predictions | 4 |
| L4 Monitoring application | FastAPI equipment/acquisition/monitoring/model/prediction/alert/review/Copilot/report APIs; React dashboard/live/sensor/history/AI analysis/model management/alerts/Copilot/reports; admin writes later | 1–7 |
| L5 Engineering Copilot | official-SDK FastMCP server; orchestrator; provider adapter; MCP client; approval engine; conversation/tool trace | 0.6 |

The API is not the inference authority. The edge pipeline is. The API stores and serves edge
outputs and hosts the monitoring application.

## 3. Deployable boundaries

### Web (`apps/web`)

- Presentation only; no local condition decisions.
- Talks only to `/api/v1` through one HTTP client.
- Keeps the access token in memory and relies on an HttpOnly refresh cookie.
- TanStack Query for server state; React Hook Form + Zod for forms.
- Role-aware navigation, but never the security boundary.
- Displays data only from backend contracts; planned screens contain no fabricated values.

### API (`apps/api`)

- Versioned REST and SSE.
- Authentication, RBAC, audit logging and report generation.
- Persists users, equipment, models, predictions, alerts, reviews, report jobs, Copilot
  conversations/messages and tool invocations.
- Receives synchronised edge events idempotently (later stage).
- Enforces valid model state transitions and configuration permissions.
- Hosts the Copilot orchestrator; calls the MCP server through the official SDK client and never
  exposes MCP administration or provider credentials to the browser.

### MCP server (`app.copilot.server`)

- Separate process using the official Python MCP SDK and Streamable HTTP (`/mcp`, port 8010).
- Requires a private service token; normal user Bearer tokens are not accepted there.
- Reuses the existing domain services and database; no inference or fault logic is duplicated.
- Exposes 13 namespaced tools with strict Pydantic schemas, actor/role revalidation, timeouts and
  result-size limits.
- The API tests use the same MCP protocol over the SDK in-memory transport for deterministic,
  isolated execution.

### Edge (`edge/`) — Stage 2 implemented boundary

- Generates deterministic simulated windows for seven scenarios and exposes a shared acquisition
  contract.
- Validates signal quality before any model call.
- Sends valid samples or sensor-invalid metadata through explicit API endpoints with `SIMULATED`
  provenance.
- Provides a physical adapter placeholder that raises an explicit not-configured error; it never
  fabricates measurements.
- Feature extraction, inference, local outbox and offline sync remain Stages 4/6.
- The CLI logs in, creates a session, validates each window and stops the session idempotently.

### ML (`ml/`)

- Dataset manifests, grouped splits, experiments, evaluation reports and artefacts.
- Produces model metadata and hash records for registration.
- Remains separate from runtime application source.

### Shared contracts (`packages/shared-contracts`)

- TypeScript enums and DTOs aligned with the Python contracts.
- OpenAPI remains authoritative; generation can replace hand-maintained types later.

## 4. Primary data flows

### 4.1 Monitoring and inference

```text
Sensor → acquisition adapter → timestamped window
      → SignalValidator → (SENSOR_INVALID → persist invalid window metadata, stop)
      → SignalPreprocessor → FeatureExtractor (Stage 4)
      → InferenceEngine → UncertaintyEvaluator → DecisionPolicy (Stage 4)
      → PredictionRepository + AlertRepository (Stages 4/5)
      → local UI / outbox → API → dashboard (Stage 3/6)
```

Stage 2 path:

```text
scenario/seed → SimulatedSensorAdapter → SignalValidator
  → CLI posts window to /acquisition-sessions/{id}/windows
  → API persists session + window (SIMULATED) → Pumps registry view
```

Stage 3 path:

```text
persisted windows
  → /monitoring/overview + /monitoring/live + /sensors/health
  → dashboard, live charts, sensor diagnostics, basic history
  → /monitoring/stream (authenticated SSE, DB poll every ~2s)
  → frontend invalidates queries on reading/sensor_health
```

Stage 4–5 path:

```text
valid persisted window → edge FeatureExtractor (petrosense-time-v1)
  → load active model metadata + hash-verified JSON artefact
  → linear scorer → uncertainty band / DecisionPolicy
  → prediction POST (model version, scores, explanation, latency)
  → API persists immutable prediction → SSE prediction event
  → FAULT / UNCERTAIN / SENSOR_INVALID creates one reviewable alert
  → Live condition + AI Analysis + model registry evidence
  → alert queue → acknowledgement → append-only engineering review (audit)
  → Historical Trends alert overlay (matched by persisted signal window)
```

Copilot path:

```text
authenticated React context (route, pump, sensor, alert, mode, connectivity)
  -> /api/v1/copilot/chat
  -> provider plan (deterministic local or optional remote planner)
  -> allowlist + JSON-schema argument validation + actor injection
  -> MCP ClientSession -> FastMCP tool -> existing domain service -> SQLite
  -> structured tool runs + grounded assistant summary + validated UI actions
  -> write proposal -> exact-argument approval -> MCP write -> audit + resulting action
```

The API checks structural window invariants but does not re-run the full signal validator and does
not make condition decisions. Equipment condition is returned only for the latest valid window when
a matching current prediction exists; otherwise `condition_available=false`. Sensor-invalid windows
force suppression. The edge is the inference authority; the API stores and serves its output.

### 4.2 Offline synchronisation

```text
Edge writes domain row + outbox row in one local transaction
  → background sender marks IN_FLIGHT
  → API validates and durably accepts by unique event_id
  → API acknowledgement
  → edge marks DELIVERED
```

Retries use backoff. The receiving API deduplicates by `event_id`. Events are never marked
synchronised before acknowledgement.

### 4.3 Model promotion

```text
Register artefact + metadata → checksum and contract checks → attach evaluation evidence
→ authorised validate → authorised activate → previous version retired but retained
→ audit record + rollback path
```

## 5. State model

Equipment condition, data quality and connectivity are orthogonal:

- Equipment: `NORMAL`, `FAULT`, `UNCERTAIN`
- Data quality: `VALID`, `SENSOR_INVALID`
- Connectivity: `ONLINE`, `OFFLINE_BUFFERING`, `SYNCING`, `SYNCED`, `SYNC_ERROR`
- Provenance: `SIMULATED`, `EXPERIMENTAL`

Rules:

1. `SENSOR_INVALID` suppresses condition inference.
2. `UNCERTAIN` creates a reviewable event.
3. Connectivity never changes equipment condition.
4. A stale prediction is historical; it is never presented as current.
5. Provenance is not inferred from where a record happens to be displayed.

## 6. Technology choices

| Concern | Choice | Rationale |
|---|---|---|
| API | FastAPI + Pydantic | Typed contracts, OpenAPI, testability |
| ORM/migrations | SQLAlchemy 2 + Alembic | Explicit schema, future PostgreSQL migration |
| Local DB | SQLite WAL | Offline, simple, adequate for one lab |
| Auth | JWT access in memory + HttpOnly refresh cookie | Limits browser token exposure |
| Live updates | SSE | One-way monitoring data, simple reconnect |
| Frontend | React/TypeScript/Vite/Tailwind | Maintainable SPA and design system |
| Charts | Recharts | Local, composable monitoring charts |
| Edge inference | ONNX Runtime preferred | Portable, avoids pickle execution |
| Testing | pytest, Vitest, React Testing Library, Playwright | Layered verification |
| CI | GitHub Actions | Lint, tests, migration and build |

## 7. Failure handling

| Failure | Required behaviour |
|---|---|
| Sensor missing/invalid | Validator rejects it; Stage 5 stores SENSOR_INVALID metadata/prediction, suppresses condition inference and creates a reviewable sensor-health alert. |
| API/network down | Edge inference and local alerts continue; outbox grows |
| Edge restart | Unsynchronised events persist; sender resumes safely |
| Duplicate sync | Receiver returns accepted/already-processed without duplicate rows |
| Model incompatible | Activation rejected; previous active model retained |
| Review conflict | Reviews append; original prediction unchanged |
| Stale UI data | Sensor freshness status marks stale data; live page never presents stale data as current |
| Latest window sensor-invalid | Waveform is withheld, condition remains not inferred, validation issues shown |
| Report generation failure | Job marked failed with error; no partial file served |

## 8. Deferred architecture decisions

- PostgreSQL deployment and migration run-book.
- Physical sensor selection, ADC/wiring contract and Raspberry Pi/ESP32-S3 choice.
- ONNX model contract details and edge runtime benchmarking.
- Per-device session revocation.
- Backup/restore procedure for the laboratory database.
- Report rendering engine and storage.
- In-process SSE fan-out versus the current durable database polling.
- Edge-local persistence/outbox and sync receiver (Stage 6).
- Physical sensor freshness/connectivity semantics (Stage 6).
- ONNX/TFLite edge runtimes and device-side model caching (deferred).
- Alert notification delivery and background escalation (not implemented).
