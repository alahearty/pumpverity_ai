# Testing strategy and 0.6 Copilot evidence

**Version:** 0.6

## 1. Approach

| Layer | Tools | Scope |
|---|---|---|
| Unit | pytest, Vitest, React Testing Library | Validation, auth helpers, status mapping, form validation, composition |
| Integration | pytest + FastAPI TestClient + SQLite | Auth, RBAC, audit, equipment, acquisitions, schema relationships, constraints |
| Edge unit/integration | pytest | Simulation determinism, scenarios, validation, adapters, features, artefact loading, decisions, CLI payloads |
| Research pipeline | pytest + scikit-learn | Grouped split, model comparison, risk–coverage, calibration, artefact export |
| End-to-end | Playwright (Chrome) | Login, all twelve screens, pump/sensor registration, SSE live inference, AI Analysis, alert review, Copilot/MCP/report actions, logout |
| Static | ruff, oxlint, TypeScript (`tsc -b`), Vite build | Python/edge/ML lint, frontend lint, type-check, bundling |
| CI | GitHub Actions | API lint/tests/migration; edge lint/tests; ML lint/tests; web lint/tests/build |

Tests use a temporary file-backed SQLite engine with foreign keys and WAL enabled, allowing the API
and in-memory MCP server to use separate sessions safely. The database is recreated and the four
demo roles/users are seeded before each backend test. The API dependency and MCP session factory are
overridden so tests never touch the developer database. Argon2 parameters are reduced in tests only
to keep the suite fast; production defaults remain unchanged.

## 2. Executed 0.6 results

| Check | Command | Result |
|---|---|---|
| API lint | `ruff check app tests` | Passed |
| API tests | `python -m pytest` | **74 passed** |
| Edge lint | `ruff check edge/petrosense_edge edge/tests` | Passed |
| Edge tests | `python -m pytest edge/tests` | **38 passed** |
| ML lint | `ruff check ml/petrosense_ml ml/tests` | Passed |
| ML tests | `python -m pytest ml/tests` | **3 passed** |
| Web lint | `npm run lint --workspace @petrosense/web` | 0 errors, warnings only |
| Web tests | `npm run test --workspace @petrosense/web` | **41 passed** |
| Web build | `npm run build --workspace @petrosense/web` | Passed; route-split chunks |
| E2E | Playwright with writes and active model | **7 passed** |
| Migrations | `alembic upgrade head` | Stage 1-5 and Copilot migrations applied |
| Seed | `python -m app.db.seed` | Four demo accounts plus alert settings |
| Simulator | CLI against target DB | Session/window/prediction/alert flow exercised |
| MCP | `pytest tests/test_mcp.py` plus live HTTP check | Tool discovery, schemas, actor auth, service token, timeout |

Playwright run details:

- unauthenticated `/dashboard` redirects to `/login`;
- invalid credentials produce the generic audited error;
- administrator signs in, visits all twelve screens, sees the seeded user list, and signs out;
- reload restores the session through the refresh cookie;
- pump form validation is exercised;
- a pump and sensor are registered through the UI on the configured test database and appear in both
  Pumps and Sensor Health screens;
- a normal simulated session is loaded into Live Monitoring with a current model decision;
- an imbalance session is run while the page remains open, and the live view updates through the
  authenticated SSE stream without a manual reload;
- the AI Analysis screen is opened and a FAULT decision, model identity and "not a failure
  probability" context are verified;
- Alerts & Review is opened, the generated fault alert is acknowledged, a label is confirmed with
  notes, and the review timeline/provenance is verified;
- the Engineering Copilot is opened with the selected alert context, retrieves alert evidence via
  MCP, and explains uncertainty/decision-score semantics;
- a monitoring report write proposal requires confirmation, executes through MCP, and opens the
  generated report in Reports & Exports;
- Historical Trends is opened for the same pump and the persisted alert marker/legend is verified;
- Sensor Health provides an explicit “Run Copilot diagnostic” action and displays the MCP result.

Write/SSE/AI/alert/Copilot tests are skipped unless `PETROSENSE_E2E_ALLOW_WRITES=1` and an active
model exists. The default check also requires the separately hosted MCP server. A normal Playwright
run does not write to the developer database; a write-enabled run does create synthetic equipment,
predictions, reviews and reports in the configured target database.

## 3. Backend coverage highlights

- successful login by email and username;
- generic failure for wrong password/unknown/inactive account;
- validation errors do not echo passwords;
- access-token requirement and Bearer challenge;
- refresh cookie rotation and session restore;
- refresh token cannot be used as an access token;
- logout clears the session;
- token-version revocation;
- administrator-only user list, including role filter, search and pagination;
- full Pump → Sensor → Session → Window → Model → Prediction → Alert → Review chain;
- automatic one-alert-per-prediction creation for FAULT/UNCERTAIN/SENSOR_INVALID;
- original prediction immutability after a correction review;
- acknowledgement idempotency, assigned reviewer and timestamp;
- confirmation mismatch, correction equality and closed-alert review rejection;
- label provenance (`ENGINEER_REVIEW`, `is_verified_ground_truth=false`) and role guards;
- alert filters and read-only role access;
- duplicate prediction/sensor identifiers rejected;
- simulated and experimental evaluation provenance remain distinguishable;
- monitoring overview and live snapshot with condition not inferred;
- bounded waveform preview and sensor-invalid waveform suppression;
- sensor diagnostics for last valid reading, quality, freshness, gaps and warnings;
- MCP tool discovery, strict input/output schemas, role/actor validation, invalid equipment IDs,
  service-token enforcement and client timeouts;
- Copilot grounded alert explanation, missing-context handling, prompt-injection resistance,
  provider fallback, MCP outage handling, role-guarded write proposals and exact approval;
- approval idempotency, original-prediction immutability after Copilot review, report generation,
  audit entries, authenticated report download and simulated-data disclosure;
- SSE authentication, content type and heartbeat boundary;
- sensor-invalid suppression in the Live Monitoring UI;
- model registry validation/activation/rollback and role guards;
- prediction ingestion guards, feature-contract validation and immutable evidence;
- sensor-invalid prediction suppression of live condition;
- model version identity and prediction traceability;
- pump/sensor registration, normalisation, duplicate rollback, update and audit;
- operating-regime reference data and default pump regime;
- acquisition session creation/stop, sampling-rate and sensor-pump guards;
- valid/invalid window persistence, duplicate index rejection and timestamp checks;
- experimental acquisition rejection and role restrictions.

## 4. Edge coverage highlights

- deterministic sample generation for a fixed seed;
- scenario registry and expected quality metadata;
- normal vs imbalance/cavitation/incipient energy separation;
- engineer-defined custom abnormal amplitude;
- disconnected and corrupted signal rejection;
- flatline, non-finite, range, timestamp, rate and unit validation;
- simulated adapter contract and finite window iteration;
- physical adapter never fabricates data;
- CLI scenario listing, required arguments and invalid-window payload shape.

## 5. Critical failure scenarios

| # | Scenario | Stage 5 status |
|---|---|---|
| 1 | Sensor disconnection never yields a fresh `NORMAL` prediction | Edge validation, SENSOR_INVALID prediction, monitoring suppression, sensor-health alert and UI suppression **covered** through the inference path. |
| 2 | Uncertain inference creates a reviewable event | **Covered**: UNCERTAIN predictions create an alert; acknowledgement/review flow is tested in API, UI and E2E. |
| 3 | Original prediction unchanged after engineering review | **Covered**: confirmation/correction tests assert appended reviews while the original prediction decision remains unchanged. |
| 4 | Network loss does not stop local inference | Deferred to Stage 6 edge tests |
| 5 | Offline events survive restart | Deferred to Stage 6 |
| 6 | Repeated sync delivery does not duplicate events | Duplicate prediction/window event IDs rejected; receiver idempotency deferred to Stage 6 |
| 7 | Unauthorised users cannot change models or thresholds | Model registry role guards and activation restrictions **covered**; settings write is Stage 7 |
| 8 | Invalid models cannot become active | **Covered**: validation/activation require verified evaluation, hash, feature contract and supported runtime |
| 9 | Simulated data cannot be mistaken for experimental | Provenance schema, simulation-only API guard, UI labels, synthetic evaluation warnings and in-memory API tests **covered**; report enforcement later |
| 10 | Historical events remain traceable to pump/model | **Covered for trends**: alert overlays resolve through persisted signal-window IDs and expose the source prediction/model. Report generation remains Stage 7. |

This table is intentionally honest: a scenario is not marked covered until the relevant feature and
its automated test exist.

## 6. Running tests

Backend:

```powershell
Set-Location apps/api
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check app tests
```

Edge:

```powershell
apps/api/.venv/Scripts/ruff check edge/petrosense_edge edge/tests
apps/api/.venv/Scripts/python -m pytest edge/tests
```

ML research pipeline:

```powershell
apps/api/.venv/Scripts/ruff check ml/petrosense_ml ml/tests
apps/api/.venv/Scripts/python -m pytest ml/tests
apps/api/.venv/Scripts/python -m petrosense_ml.pipeline
```

Frontend:

```powershell
npm run test --workspace @petrosense/web
npm run lint --workspace @petrosense/web
npm run build --workspace @petrosense/web
```

E2E:

```powershell
# Terminal 1
Set-Location apps/api
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# Terminal 2
Set-Location apps/api
.venv/Scripts/python -m app.copilot.server

# Terminal 3
npm run dev:web

# Terminal 4
$env:PETROSENSE_E2E_EMAIL = "admin@petrosense.local"
$env:PETROSENSE_E2E_PASSWORD = "<demo password from apps/api/.env>"
$env:PETROSENSE_E2E_ALLOW_WRITES = "1"   # isolated database preferred
npm run test:e2e --workspace @petrosense/web
```

## 7. Future test expansion

- Copilot: complete (MCP protocol/auth, provider fallback, approval, grounding and E2E).
- Later: outbox restart recovery, retry/backoff, duplicate delivery, receiver idempotency.
- Later: full report templates, configuration audits, full RBAC matrix.
- Later: complete Playwright acceptance across roles/failure scenarios and add E2E to CI.




