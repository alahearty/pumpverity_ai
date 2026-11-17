# PUMPVERITY AI

**Uncertainty-aware, offline-first condition monitoring for centrifugal pumps — academic research prototype.**

PUMPVERITY AI is a six-month research prototype for low-cost, vibration-based condition monitoring
of a laboratory centrifugal-pump test rig. It is being developed as an NCDMB-oriented indigenous
technology research project.

> This is not a certified industrial safety system, a predictive-maintenance product or a pump
> protection system. It must not be used for autonomous shutdown. No accuracy, reliability or
> commercial-readiness claim is made until genuine experimental evidence exists. Simulated signals
> are for software integration and demonstration only.

---

## Presentation mode (NCDMB demo)

One command starts the API, web app and a paced simulated edge stream, then opens the browser:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo.ps1 -Reset   # fresh data + 1-minute warm-up history
powershell -File scripts/demo-stop.ps1                             # stop everything
```

Sign in at `http://localhost:5173` as **`admin`** with password **`PumpVerity@2026`** (all test
accounts are listed under [Demo sign-in](#demo-sign-in)). The dark presenter bar at the bottom of
every page switches the simulated rig between scenarios - keys `1`-`5`, `P` to pause - and the
dashboard shows the edge decision live: normal, suspected fault, uncertain (abstain) or
sensor-invalid. The full click-by-click script, talking points and recovery steps are in
[`docs/DEMO-RUNBOOK.md`](docs/DEMO-RUNBOOK.md).

What presentation mode adds (enabled by `PETROSENSE_DEMO_MODE=true`):

- `edge/petrosense_edge/demo.py` - streams one SIMULATED window per second through the real edge
  pipeline (validation → features → hash-verified inference → decision policy → API); it
  reconnects automatically and never back-dates timestamps.
- `/api/v1/demo/control` - presenter scenario selection (engineer/admin only, audited).
- `PETROSENSE_ALERT_DEDUP_PER_SESSION=true` - one open alert per category per session instead of
  one per window (prevents alert storms in continuous streams).
- An operations-console dashboard: live condition header, fault-score timeline against the
  abstention band, event feed and pipeline view.

---

## Current status — 0.6 Engineering Copilot and MCP integration

Implemented and verified:

- React 19 + TypeScript + Vite + Tailwind CSS application shell with the PUMPVERITY visual identity.
- All twelve required screens are navigable, with role-aware navigation and protected routes.
- Functional login, logout, session restore, password show/hide, validation and error handling.
- Short-lived JWT access tokens (held in memory) plus an HttpOnly refresh cookie.
- Four roles (Administrator, Engineer, Researcher, Reviewer) enforced by the backend.
- Administrator-only read-only user list backed by the real database.
- Functional pump registration and editing, transactional initial sensor assignment, sensor
  inventory and active-state management.
- Operator-regime defaults, duplicate-code prevention, validation and audit records for equipment.
- Acquisition-session and signal-window persistence with `SIMULATED` provenance.
- Standalone edge simulation package with seven deterministic scenarios, signal validation, a
  physical-adapter boundary that produces no fabricated data, and a CLI.
- Monitoring overview, live snapshot and authenticated SSE update stream.
- Live Monitoring UI with downsampled waveform, RMS trend, pause/window controls, session context and
  explicit separate equipment/data/connectivity states.
- Sensor Health diagnostics: last valid reading, latest quality, freshness, invalid windows,
  missing-index gaps, validation warnings and latest session context.
- Dashboard driven by real monitoring counts and latest persisted window; condition is shown as
  **Not inferred** until a validated model exists.
- Historical RMS trends and window records with alert-backed event overlays aligned to persisted
  signal windows; date-range filters, model-version markers and exports remain later work.
- Versioned time/spectral feature contract shared by the edge and research pipeline.
- Hash-verified lightweight JSON model loading, inference, uncertainty/abstention and
  sensor-invalid suppression.
- Model registry with synthetic evaluation evidence, validation, activation, rollback and audit.
- Prediction persistence linked to pump, sensor, session, window, model version and operating regime.
- Functional AI Analysis screen showing decision score, uncertainty, data validity, latency,
  explanation, features and model identity.
- Functional Model Management screen with synthetic-evaluation warnings and activation controls.
- Automatic reviewable alerts for `FAULT`, `UNCERTAIN` and `SENSOR_INVALID` predictions, with one
  alert per prediction and configurable auto-creation settings.
- Functional Alerts & Review screen with filters, immutable prediction evidence, acknowledgement,
  append-only engineering reviews, label confirmation/correction and review history.
- Alert and review audit entries; engineer-reviewed labels use `label_source = ENGINEER_REVIEW` and
  are never presented as verified experimental ground truth.
- Context-aware Engineering Copilot across the authenticated application shell, with explicit
  route/pump/sensor/alert context, MCP tool timeline, grounded explanations, suggested questions,
  validated navigation actions and explicit write approval.
- Official-SDK MCP server with 13 namespaced tools, strict schemas, actor/role revalidation,
  structured errors, timeouts, result limits, Streamable HTTP hosting and a memory transport for
  deterministic tests.
- Controlled Copilot write tools for acknowledgement, engineering review/note and monitoring report
  generation; all writes are role-checked, confirmation-gated, idempotent and audited.
- Traceable Copilot conversations and tool invocations; Copilot-generated reports are persisted
  with SHA-256 and simulated-data disclosure and can be downloaded by authenticated users.
- Provider abstraction with a grounded deterministic local planner and optional OpenAI-compatible
  planning; monitoring remains independent when the provider or MCP service is unavailable.
- Reproducible synthetic ML pipeline comparing threshold, random forest and lightweight linear
  models; grouped hold-out, risk–coverage, calibration and model artefacts/report.
- Complete 20-table relational schema with Stage 1–5 and Copilot Alembic migrations.
- Structured audit logging, request IDs, consistent API errors and JSON logs.
- Docker Compose configuration (validated with `docker compose config`) and a GitHub Actions CI
  definition. Container images were not built locally because the Docker daemon was unavailable.
- 74 backend tests, 38 edge tests, 3 ML pipeline tests, 41 frontend tests and 7 Playwright
  end-to-end tests passing locally. Playwright includes pump registration, the twelve-screen map,
  SSE live inference, AI Analysis, alert review, Copilot tool execution/report approval and history
  overlays.

Screens whose subject matter belongs to later stages are clearly marked **Planned scope** and do not
display fabricated measurements, accuracy figures or connectivity values. Alert records are real
persisted workflow outputs derived from stored predictions; synthetic model metrics are labelled as
simulated everywhere they appear.

Deliberately not implemented in this extension:

- complete historical date filters, model-version markers and full report templates;
- configuration editing and user administration writes;
- edge outbox/synchronisation and network-outage controls;
- physical sensor integration and experimental data;
- ONNX/TFLite edge runtimes (only JSON linear and threshold artefacts are supported);
- autonomous multi-agent behaviour, arbitrary MCP tool invocation or industrial actuation.

The staged plan is in [`docs/00-implementation-assessment.md`](docs/00-implementation-assessment.md).
Stage 4 evidence is in [`docs/stage-4-acceptance.md`](docs/stage-4-acceptance.md), Stage 5 evidence
is in [`docs/stage-5-acceptance.md`](docs/stage-5-acceptance.md), and the Copilot architecture and
evidence are in [`docs/copilot-and-mcp.md`](docs/copilot-and-mcp.md) and
[`docs/copilot-acceptance.md`](docs/copilot-acceptance.md).

---

## Architecture

```text
┌──────────────────────── Edge (simulated or physical sensor) ────────────────────────┐
│ acquisition → validation → preprocessing → features → inference → uncertainty       │
│                                          → decision policy → local SQLite + outbox   │
└───────────────────────────────────────┬──────────────────────────────────────────────┘
                                        │ idempotent events, retry/backoff
                              ┌─────────▼─────────┐
                              │ FastAPI + SQLite  │
                              │ auth, monitoring, │
                              │ alerts, reviews,  │
                              │ models, reports   │
                              └─────────┬─────────┘
                                        │ REST + SSE
                              ┌─────────▼─────────┐
                              │ React SPA (12    │
                              │ screens)         │
                              └───────────────────┘
```

0.6 implements the API, database, authentication, application shell, equipment registry,
deterministic simulation/validation, monitoring/SSE, sensor diagnostics, feature extraction,
hash-verified edge inference, uncertainty abstention, model registry, prediction persistence, the
AI Analysis/Model Management interfaces, automatic alerts, engineering review, label provenance,
history event overlays and the context-aware Engineering Copilot. The Copilot orchestrator calls a
separately runnable FastMCP Streamable HTTP server through the official MCP client; tests use the
same MCP protocol over the SDK memory transport. Full report templates and offline synchronisation
remain later work. See [`docs/copilot-and-mcp.md`](docs/copilot-and-mcp.md),
[`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md),
[`ml/README.md`](ml/README.md) and [`docs/simulation/engine.md`](docs/simulation/engine.md).

### Status separation

The data model and UI deliberately keep these dimensions distinct:

| Dimension | Values |
|---|---|
| Equipment condition | `NORMAL`, `FAULT`, `UNCERTAIN` |
| Data quality | `VALID`, `SENSOR_INVALID` |
| Connectivity | `ONLINE`, `OFFLINE_BUFFERING`, `SYNCING`, `SYNCED`, `SYNC_ERROR` |
| Data provenance | `SIMULATED`, `EXPERIMENTAL` |

A sensor-invalid signal must suppress equipment-condition inference. It is never displayed as a
verified normal pump condition.

---

## Repository layout

```text
apps/
  api/                     FastAPI, SQLAlchemy, Alembic, auth/RBAC/audit, tests
  web/                     React SPA, design system, 12 routes, component/E2E tests
edge/                      deterministic simulation, adapters, validation and CLI (Stage 2)
ml/                        reproducible synthetic training/evaluation pipeline (Stage 4)
packages/shared-contracts/ shared TypeScript domain types
simulation/                Stage 6 network/outage scenario specifications and orchestration
docs/                      assessment, architecture, schema, API, UI, security, testing, ADRs
scripts/                   setup and verification scripts
infrastructure/            local Docker notes
```

---

## Quick start (Windows PowerShell)

### Prerequisites

- Python 3.13 (3.12+ is supported by the code; the setup script selects 3.13)
- Node.js 22+ (Node 24 used for development)
- npm 11+
- Optional: Docker Desktop for the containerised stack
- Optional: Google Chrome for the Playwright suite

### Automated setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

The script creates `apps/api/.env` with a random JWT secret and demo password if needed, creates
the virtual environment, installs dependencies, applies the migration, seeds reference data and
four local demo accounts, and runs `npm install`.

### Manual setup

```powershell
Copy-Item apps/api/.env.example apps/api/.env
# Edit apps/api/.env: set a secret of at least 32 characters and a strong demo password

py -3.13 -m venv apps/api/.venv
apps/api/.venv/Scripts/python -m pip install --upgrade pip
apps/api/.venv/Scripts/python -m pip install -e "apps/api[dev]"   # or run pip from apps/api
apps/api/.venv/Scripts/python -m pip install -e edge
apps/api/.venv/Scripts/python -m pip install -e ml

Set-Location apps/api
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.db.seed
Set-Location ../..

npm install
```

### Run locally

Terminal 1:

```powershell
Set-Location apps/api
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (repository root):

```powershell
npm run dev:web
```

Terminal 3 (MCP server used by the Copilot when `PETROSENSE_MCP_TRANSPORT=http`):

```powershell
Set-Location apps/api
.venv/Scripts/python -m app.copilot.server
```

Open `http://localhost:5173`. API docs: `http://localhost:8000/docs`. The MCP endpoint is
`http://127.0.0.1:8010/mcp` and requires the private service token configured through
`PETROSENSE_MCP_SERVICE_TOKEN` (or the API secret fallback). If this service is stopped, Copilot
tools are unavailable but monitoring, edge inference and alert creation continue.

### Demo sign-in

Local test accounts (seeded only when `PETROSENSE_DEMO_PASSWORD` is set). Sign in with the
username or the email.

| Username | Email | Role | Password |
|---|---|---|---|
| `admin` | `admin@petrosense.local` | Administrator | `PumpVerity@2026` |
| `engineer` | `engineer@petrosense.local` | Engineer | `PumpVerity@2026` |
| `researcher` | `researcher@petrosense.local` | Researcher | `PumpVerity@2026` |
| `reviewer` | `reviewer@petrosense.local` | Reviewer | `PumpVerity@2026` |

`scripts/setup.ps1` writes this shared password into the gitignored `apps/api/.env`, and
`scripts/demo.ps1` re-applies whatever `.env` contains on each launch. It is a local, offline
demonstration credential: set a private value before any hosted or shared deployment. It is never
embedded in frontend code.

### Run a simulated acquisition

1. Sign in as an engineer or administrator and register the pump and its initial sensor in **Pumps**.
   Keep **Live Monitoring** open to observe new windows arrive through SSE.
2. With the API running, execute the edge simulator from the repository root:

```powershell
$env:PETROSENSE_EDGE_PASSWORD = "<seeded demo password>"

apps/api/.venv/Scripts/python -m petrosense_edge.cli `
  --pump-code LAB-PUMP-01 `
  --sensor-code VIB-01 `
  --scenario normal `
  --windows 5 `
  --seed 42
```

3. The session and validated windows appear under **Recent simulated acquisition**. If an active
   model exists, the CLI also writes predictions; **Live Monitoring** and **AI Analysis** show the
   decision, score and uncertainty. Use `--scenario imbalance`, `custom_abnormal
   --custom-amplitude 0.01` or `sensor_disconnect` to demonstrate fault, uncertainty and invalid
   paths. All records carry `SIMULATED` provenance.
4. A `FAULT`, `UNCERTAIN` or `SENSOR_INVALID` decision creates one reviewable alert. Open
   **Alerts & Review**, acknowledge it, add notes and confirm/correct the label. The original
   prediction remains unchanged, and **Historical Trends** shows the alert-backed overlay.

### Use the Engineering Copilot

Open the floating **Engineering Copilot** panel after signing in. It receives the current screen,
selected pump/sensor/alert, data mode and connectivity state from the application. Ask a question
such as “What is happening with this pump?”, “Why was this event marked uncertain?”, or “Generate a
monitoring report”.

- Natural-language answers are composed from actual MCP tool results; missing data is reported as
  unavailable.
- Alerts can be acknowledged, reviewed or annotated only after the exact proposed arguments are
  confirmed. The original prediction is never rewritten.
- Report generation creates a traceable JSON artefact with SHA-256 and simulated-data disclosure.
- Synthetic scores are model outputs, not probabilities of mechanical failure. Engineer reviews are
  not verified experimental ground truth.
- The Copilot cannot query unrestricted SQL, execute shell/Python, choose arbitrary MCP targets or
  perform industrial control actions.

See [`docs/copilot-and-mcp.md`](docs/copilot-and-mcp.md) for the architecture, tool contracts,
transports and security boundaries.

See [`edge/README.md`](edge/README.md) for scenario definitions and CLI options. Physical
acquisition returns an explicit "not configured" error and never fabricates measurements.

### Train and register a synthetic model

The model is synthetic and must never be described as real-pump accuracy. Install the research
dependencies, then train/evaluate/export and register through the API:

```powershell
apps/api/.venv/Scripts/python -m pip install -e ml
$env:PETROSENSE_ML_PASSWORD = "<researcher or admin password>"
apps/api/.venv/Scripts/python -m petrosense_ml.pipeline --register
```

This writes the comparison report to `ml/reports/`, artefacts to `ml/artifacts/`, registers both
candidates, validates them and activates the lightweight linear model. The current developer database
has these synthetic models registered (linear active, baseline validated) and no pump/session data;
a fresh setup must run the registration command before inference is available. See
[`ml/README.md`](ml/README.md).

### Docker Compose

```powershell
Copy-Item .env.example .env
# Set PETROSENSE_SECRET_KEY and PETROSENSE_DEMO_PASSWORD in .env
docker compose up --build
```

Open `http://localhost:5173`. See [`infrastructure/README.md`](infrastructure/README.md).

---

## Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

Individual commands:

| Area | Command |
|---|---|
| API lint | `apps/api/.venv/Scripts/ruff check apps/api/app apps/api/tests` |
| API tests | `apps/api/.venv/Scripts/python -m pytest` (run from `apps/api`) |
| Edge lint | `apps/api/.venv/Scripts/ruff check edge/petrosense_edge edge/tests` |
| Edge tests | `apps/api/.venv/Scripts/python -m pytest edge/tests` |
| ML lint | `apps/api/.venv/Scripts/ruff check ml/petrosense_ml ml/tests` |
| ML tests | `apps/api/.venv/Scripts/python -m pytest ml/tests` |
| Web lint | `npm run lint --workspace @petrosense/web` |
| Web tests | `npm run test --workspace @petrosense/web` |
| Web build | `npm run build --workspace @petrosense/web` |

Playwright (requires both servers running and the E2E password env var):

```powershell
$env:PETROSENSE_E2E_EMAIL = "admin@petrosense.local"
$env:PETROSENSE_E2E_PASSWORD = "<seeded demo password>"
npm run test:e2e --workspace @petrosense/web
```

Stage 1–5 evidence is recorded in
[`docs/stage-1-acceptance.md`](docs/stage-1-acceptance.md),
[`docs/stage-2-acceptance.md`](docs/stage-2-acceptance.md),
[`docs/stage-3-acceptance.md`](docs/stage-3-acceptance.md),
[`docs/stage-4-acceptance.md`](docs/stage-4-acceptance.md) and
[`docs/stage-5-acceptance.md`](docs/stage-5-acceptance.md). Copilot architecture and evidence are in
[`docs/copilot-and-mcp.md`](docs/copilot-and-mcp.md) and
[`docs/copilot-acceptance.md`](docs/copilot-acceptance.md). E2E tests are not yet part of the CI
workflow; they were executed locally against the running API, MCP and web servers. Set
`PETROSENSE_E2E_ALLOW_WRITES=1` to include write/live-inference/alert/Copilot tests, and ensure an
active model and the MCP service exist. Write tests create synthetic equipment, reviews and reports
in the target database.

---

## Security notes

- Passwords are hashed with Argon2 via `pwdlib`.
- Access tokens are short-lived (15 minutes by default) and held in memory by the SPA.
- Refresh tokens are stored in an HttpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`.
- Token-version revocation invalidates sessions after a credential reset or administrative action.
- Login failures use a generic message and constant-time dummy verification for unknown accounts.
- Authorisation is checked in the backend; hiding frontend navigation is not treated as security.
- Authentication outcomes are written to an append-only-style audit log.
- `.env` files, databases, model artefacts and datasets are excluded from version control.
- Model upload is not implemented; it will never be treated as arbitrary executable code execution.
- The MCP endpoint is protected by a private service token and is not accessible to the browser.
- Copilot writes require a stored, exact-argument approval and are revalidated server-side.
- Ollama/remote LLM keys remain server-side; no provider key is exposed to React.
- Industrial control integration and automatic pump shutdown are explicitly out of scope.

See [`docs/security/access-control.md`](docs/security/access-control.md).

---

## Scientific integrity rules

1. Simulated and experimental records carry different provenance values throughout storage,
   evaluation and reporting.
2. Synthetic data cannot establish real-world fault-detection performance.
3. Evaluation splits are grouped by acquisition run; overlapping windows never cross splits.
4. Engineer review labels are not automatically promoted to verified experimental ground truth.
5. Original AI predictions are immutable; reviews are appended with reviewer identity and time.
6. Sensor-invalid conditions are reported independently of equipment faults.
7. Uncertainty is an explicit outcome; scores are not described as probabilities of mechanical
   failure without calibration evidence.
8. Reports identify their dataset, model version, timestamps and provenance.

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/00-implementation-assessment.md`](docs/00-implementation-assessment.md) | Stage 0 assessment, architecture, schema, routes, journeys, contracts, plan |
| [`docs/requirements/srs.md`](docs/requirements/srs.md) | Software requirements specification v0.6 |
| [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md) | Component boundaries and data flows |
| [`docs/database/schema.md`](docs/database/schema.md) | Table catalogue, relationships, retention |
| [`docs/ui/screen-specifications.md`](docs/ui/screen-specifications.md) | Twelve screen specifications and acceptance criteria |
| [`docs/hardware/acquisition-integration-contract.md`](docs/hardware/acquisition-integration-contract.md) | Physical/simulated adapter contract template and verification gates |
| [`docs/api/rest-and-events.md`](docs/api/rest-and-events.md) | REST conventions, auth, implemented contracts, SSE |
| [`docs/security/access-control.md`](docs/security/access-control.md) | Authentication, RBAC, audit and threats |
| [`docs/testing/strategy.md`](docs/testing/strategy.md) | Test pyramid, failure scenarios, commands |
| [`docs/simulation/engine.md`](docs/simulation/engine.md) | Deterministic scenario engine, validation and limitations |
| [`ml/README.md`](ml/README.md) | Synthetic training, evaluation, artefact and registration pipeline |
| [`docs/stage-1-acceptance.md`](docs/stage-1-acceptance.md) | Verified Stage 1 evidence and deviations |
| [`docs/stage-2-acceptance.md`](docs/stage-2-acceptance.md) | Verified Stage 2 equipment/simulation evidence |
| [`docs/stage-3-acceptance.md`](docs/stage-3-acceptance.md) | Verified Stage 3 monitoring/SSE/diagnostic evidence |
| [`docs/stage-4-acceptance.md`](docs/stage-4-acceptance.md) | Verified Stage 4 inference/registry/evaluation evidence |
| [`docs/stage-5-acceptance.md`](docs/stage-5-acceptance.md) | Verified Stage 5 alert/review/overlay evidence |
| [`docs/copilot-and-mcp.md`](docs/copilot-and-mcp.md) | Engineering Copilot architecture, MCP tools and boundaries |
| [`docs/copilot-acceptance.md`](docs/copilot-acceptance.md) | Verified Copilot/MCP/approval evidence |
| [`docs/adr/`](docs/adr/) | Architecture decision records |

---

## Known limitations at 0.6

- **Synthetic evidence only.** The ML comparison reaches 1.000 on easily separable synthetic data;
  this is not real-pump accuracy and must never be presented as industrial performance.
- Alerts are created synchronously during prediction ingestion. There is no notification channel,
  background worker, dismissal endpoint or separate assignment API; acknowledgement/review assigns
  the acting reviewer.
- Engineer reviews are append-only judgements, not verified experimental labels or ground truth.
- Experimental acquisition is rejected by the API; only `SIMULATED` sessions can be created.
- ONNX/TFLite runtimes are declared in the schema but not supported by the current edge loader;
  only `LINEAR_JSON` and `BASELINE` artefacts can be activated.
- Model registration is performed by the research pipeline/API; the Model Management UI reviews,
  validates, activates and rolls back but does not upload arbitrary model files.
- There is no physical edge channel, offline buffering or synchronisation yet.
- Historical Trends now supports alert-backed event overlays; date-range filters, model-version
  markers and full report templates remain later work.
- The default Copilot planner is deterministic and local. A remote OpenAI-compatible planner is
  configurable, but no paid external LLM call is required for the test suite.
- Copilot conversations and tool runs are persisted; the panel currently keeps its message view in
  memory rather than reloading old conversations into the UI.
- MCP service-token calls and actor identity are trusted only across the local API/MCP boundary.
  Production deployment requires TLS, network isolation and stronger workload identity.
- The Copilot cannot perform arbitrary queries, shell/Python execution, industrial actuation or
  verified-ground-truth promotion.
- The ML pipeline is not part of the API Docker image and must be installed separately for research.
- The simulator CLI is not containerised and scenario injection is CLI-driven.
- Preprocessing is currently validation, bounded windowing and feature centering/shape statistics;
  configurable band-pass/anti-alias filtering is not implemented.
- Playwright live/SSE, AI Analysis and alert/review tests require writes and an active model; CI
  covers API, edge, ML and web unit/build checks only.
- Route-level code splitting is implemented. The initial bundle is approximately 347 kB minified /
  108 kB gzip; the Recharts-based trend chunk is approximately 370 kB / 107 kB gzip.
- No physical sensor, edge device, verified experimental labels or measured performance exist.

---

## Six-month roadmap

| Stage | Focus | Target |
|---|---|---|
| 1 | Foundation, auth, schema, shell, CI | Month 1 — complete |
| 2 | Pumps, sensors, simulation, validation, local persistence | Month 2 — complete |
| 3 | Dashboard, live monitoring, sensor health, SSE, history view | Months 2–3 — complete |
| 4 | AI pipeline, model registry, uncertainty, analysis screen | Months 3–4 — complete |
| 5 | Alerts, reviews, trends and traceability | Months 4–5 — complete |
| 6 | Offline outbox, synchronisation, restart recovery | Month 5 — next |
| 7 | Reports, settings, user management, model refinements | Months 5–6 |
| 8 | Integration, acceptance, demonstration, research evaluation | Month 6 |

Experimental data acquisition proceeds in parallel with Stages 2–4; it does not wait for the
software to be complete.




