# Security and access control

**Version:** 0.6 (Copilot extension)
**Scope:** Local research deployment. This is not a security certification or industrial control
security assessment.

## 1. Authentication

- Passwords are hashed with Argon2 through `pwdlib`; plaintext passwords are never stored or logged.
- Access tokens are signed JWTs (HS256), expire after 15 minutes by default and contain `sub`,
  `role`, `ver`, `type`, `jti`, `iat` and `exp`.
- The access token is returned in the login response and held in JavaScript memory by the SPA. It is
  not written to `localStorage` or `sessionStorage`.
- The refresh token is also a JWT but is delivered only as an HttpOnly, SameSite=Lax cookie scoped
  to `/api/v1/auth`. It expires after 7 days by default and is rotated on refresh.
- Logout deletes the cookie. `token_version` supports global invalidation of outstanding tokens
  after a credential reset or administrative revocation.
- Unknown accounts undergo dummy password verification to reduce timing-based account enumeration.
- Failed logins always return the same error message and are audited with the attempted identifier,
  request ID, IP and user agent.

**Production hardening still required:** HTTPS, `PETROSENSE_COOKIE_SECURE=true`, login rate
limiting/lockout, a trusted reverse proxy, and secret rotation procedures.

## 2. Role model

| Capability | Administrator | Engineer | Researcher | Reviewer |
|---|---|---|---|---|
| Login, own session | Yes | Yes | Yes | Yes |
| View dashboard/history/reports | Yes | Yes | Yes | Yes |
| Register/edit pumps and sensors | Yes | Yes | No | No |
| Start/stop sessions and ingest windows | Yes | Yes | Yes | No |
| Read equipment and acquisition history | Yes | Yes | Yes | Yes |
| Live monitoring / sensor health | Yes | Yes | Yes | No (UI; read APIs remain authenticated) |
| AI analysis | Yes | Yes | Yes | No |
| Alert read APIs | Yes | Yes | Yes | Yes |
| Acknowledge/review alerts | Yes | Yes | No | Yes |
| Model registry and activation | Yes | No | Yes | No |
| Settings write | Yes (Stage 7) | No | No | No |
| User management | Yes | No | No | No |

Implementation rule: `require_roles()` treats Administrator as allowed for declared role areas. All
checks execute in the API. The SPA hides inaccessible navigation, but direct URL access still hits
the backend guard.

## 3. Audit logging

Audited in Stages 1–5:

- `AUTH_LOGIN_SUCCEEDED`
- `AUTH_LOGIN_FAILED`
- `AUTH_LOGOUT`
- `PUMP_CREATED`
- `PUMP_UPDATED`
- `SENSOR_CREATED`
- `SENSOR_UPDATED`
- `ACQUISITION_SESSION_STARTED`
- `ACQUISITION_SESSION_STOPPED`
- `MODEL_REGISTERED`
- `MODEL_EVALUATION_ADDED`
- `MODEL_VALIDATED`
- `MODEL_ACTIVATED`
- `MODEL_RETIRED`
- `MODEL_ROLLED_BACK`
- `ALERT_CREATED`
- `ALERT_ACKNOWLEDGED`
- `ALERT_REVIEWED`
- `ALERT_CLOSED`
- `REPORT_GENERATED`
- `COPILOT_TOOL_COMPLETED`

Each entry records actor (when known), actor label, action, entity type/id, IP address, user agent,
request ID and timestamp. Failed logins have no authenticated actor but retain the attempted
identifier.

Later stages add audits for configuration changes and user administration. Report generation and
Copilot tool completions are audited; audit rows and alert reviews are append-only by application
policy.

## 4. Secrets and configuration

- `PETROSENSE_SECRET_KEY` is required and must be at least 32 characters.
- Secrets live in gitignored `.env` files or deployment secret stores.
- `.env.example` contains placeholders only.
- The frontend receives no API secrets or database credentials.
- The demo password is seeded from an environment variable and only its Argon2 hash is stored.
- Docker images do not embed secrets; Compose requires them at runtime.

## 5. Input and output safety

- Pydantic schemas validate request shape and bounds.
- Validation errors omit raw input values, preventing password echo.
- SQL access uses SQLAlchemy expressions; no string-concatenated SQL is used for user input.
- React escapes rendered text by default; the app does not use `dangerouslySetInnerHTML`.
- API responses set `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and
  `Cache-Control: no-store`.
- CORS is restricted to explicit development origins with credentials enabled.
- Monitoring JSON endpoints expose window metadata and only a bounded, downsampled waveform preview;
  raw waveform bytes are not returned on every live/history refresh.
- The SSE stream is authenticated with the Bearer access token and is pump/sensor-scoped. The token is
  not placed in the stream URL. Event payloads contain window and prediction metadata, not full
  waveforms.
- Model registration through the API records metadata and a SHA-256 only. The API does not upload,
  deserialize or execute model files.
- The current edge loader supports only checked JSON linear/threshold artefacts and verifies the
  registered SHA-256 and feature contract before loading. ONNX/TFLite support is not implemented.
- Prediction ingestion validates pump/sensor/session/window consistency, event ID uniqueness,
  window quality, model active-at-inference timing and feature-contract compatibility.
- A SENSOR_INVALID prediction cannot reference a model or contain scores.
- Scores are model outputs, not probabilities of mechanical failure; UI text states this explicitly.

## 6. CSRF and session threats

- Access tokens are sent explicitly in the Authorization header and are not ambient credentials.
- The refresh cookie is HttpOnly and SameSite=Lax; refresh/logout are POST requests.
- Future state-changing endpoints should keep JSON content types, origin checks where appropriate,
  and avoid cookie-authenticated state changes without CSRF protection.
- XSS would still permit requests from the page; a strict CSP at the reverse proxy is recommended
  before any wider deployment.

## 7. Offline synchronisation security (planned)

- Edge events are authenticated and device-identified.
- Event payloads are schema-versioned and validated.
- Receiver processing is idempotent by `event_id`.
- Rejected events are reported explicitly; they are not silently discarded.
- Provenance fields cannot be overridden by client payloads without server validation.

## 8. Explicit non-goals

- Industrial control system integration.
- Automatic pump shutdown or actuator commands.
- Safety-instrumented-system certification.
- Multi-tenant or internet-scale identity federation.
- Formal penetration-test evidence for the Stage 2 prototype.

## 9. Engineering Copilot and MCP boundary

- React calls only authenticated `/api/v1/copilot/*` endpoints. It never receives MCP service
  credentials or provider API keys.
- The MCP server is separately hosted over Streamable HTTP and requires a private service token.
  Normal user Bearer tokens are not accepted at the MCP endpoint.
- Every MCP tool resolves and revalidates the actor and role against the database. The actor ID is
  injected by the orchestrator, not selected by the language model.
- The orchestrator uses an allowlisted tool catalog and validates strict JSON-schema arguments.
  Arbitrary tool names, SQL, shell, Python and URLs are rejected.
- Read tools cannot mutate data. Write tools require a pending approval containing the exact
  arguments; approval revalidates role, target and schema before execution.
- Copilot write actions are restricted to the selected alert or pump. The original prediction is
  never updated and engineer reviews are never marked verified ground truth.
- Repeated approvals return the stored result and do not duplicate effects.
- Provider plans are untrusted. The browser receives deterministic summaries composed from
  structured MCP results, so an unavailable, misconfigured or manipulated planner cannot invent a
  successful tool result.
- MCP tool results are treated as data and are not executed as markup or JavaScript.
- MCP calls have timeouts and result-size limits; failures are returned honestly and never turn
  into a success claim.

## 10. Known 0.6 limitations

- No login rate limiting or account lockout.
- No per-device refresh-session revocation; `token_version` is global per account.
- No CSRF token because no cookie-authenticated state-changing domain endpoints exist yet. This must
  be revisited when configuration/review endpoints are added.
- CSP and HSTS are not set by the API; these belong at the reverse proxy in a production deployment.
- Acquisition writes are authenticated user actions; a dedicated device identity and signed edge
  credentials are required before offline deployment.
- The API accepts only simulated acquisition. This is a deliberate scientific-integrity guard, not a
  substitute for physical hardware validation.
- Window ingestion is not audited per window; session lifecycle and equipment changes are audited.
- Alert creation is audited; raw prediction ingestion is validated but not separately audited per
  row.
- The current SSE implementation polls the database and is not a dedicated message broker. It is
  authenticated but has no per-stream rate limiting. Alerts/reviews do not emit SSE events yet.
- SSE indicates API update delivery, not physical sensor connectivity; the UI labels both separately.
- Model evaluation and metrics are synthetic; they are not a security or safety assurance.
- Alert reviews are append-only through the API, but there is no cryptographic tamper evidence or
  database-level write restriction.
- There is no notification delivery, assignment endpoint, alert dismissal endpoint or background
  escalation worker.
- Model files are trusted local research artefacts; there is no signature chain or sandboxed model
  runtime yet.
- Prediction ingestion is user-authenticated; dedicated device identity/credentials arrive with Stage 6.
- Audit logs are append-only by policy, not cryptographically tamper-evident.
- The local MCP service token is a workload credential, not a production identity system. Use TLS,
  network isolation and stronger workload identity before deployment.
- Copilot conversation/tool rows and reports are not cryptographically signed. They rely on database
  access control and application-level append-only rules.
- The deterministic planner is safer but less flexible than a remote LLM; the remote provider path
  has not been validated against a paid production model in this research environment.
- Alerts and reviews are still not emitted as SSE events; Copilot tool execution does not create a
  new real-time push channel.


