# Engineering Copilot acceptance evidence

**Date:** 2026-11-17
**Environment:** Windows 11, Python 3.13, Node.js 24, Chrome (Playwright), SQLite
**Versions:** API / edge / ML / web / shared `0.6.0`
**Migrations:** `6ab8b0723c85` (Copilot conversations/invocations) and `b7f0c2a4d910` (model display
name branding)
**MCP:** official Python SDK `mcp 1.30.x`, FastMCP Streamable HTTP at `http://127.0.0.1:8010/mcp`

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Copilot available across authorised screens | **Met** | Global panel in AppShell; Login static help; route context |
| 2 | Correct selected pump/sensor/alert/screen context | **Met** | Typed context, page hooks and context-navigation test |
| 3 | Retrieves actual backend data through MCP | **Met** | 13 official-SDK tools calling existing domain services |
| 4 | Never invents monitoring results | **Met** | Deterministic summaries built only from successful tool runs |
| 5 | Distinguishes simulated vs experimental provenance | **Met** | Structured provenance/mode, notices and report disclosure |
| 6 | Explains Normal, Fault, Uncertain and Sensor Invalid | **Met** | Prediction/alert tools and grounded summariser tests |
| 7 | Distinguishes sensor validity from equipment condition | **Met** | Separate sensor-health and prediction outputs |
| 8 | Validated navigation actions | **Met** | Central dispatcher with route allowlist, ID validation and role checks |
| 9 | Investigates fault alerts | **Met** | Alert + prediction + sensor + model evidence flow |
| 10 | Confirmation for sensitive writes | **Met** | Pending approval stores exact arguments; nothing executes during chat |
| 11 | Every write authorised and audited | **Met** | API role checks, MCP actor/role revalidation, domain audit and invocation rows |
| 12 | Frontend and backend permissions consistent | **Met** | Frontend action checks plus backend/MCP authorisation |
| 13 | Monitoring survives Copilot/LLM failure | **Met** | Provider fallback and MCP outage tests; monitoring remains healthy |
| 14 | Integration tests pass | **Met** | Results below |
| 15 | Existing functionality remains operational | **Met** | Full regression and Playwright suite pass |

## 2. Executed verification

```text
API ruff check ......................... All checks passed
API pytest ............................. 74 passed
Edge ruff check ........................ All checks passed
Edge pytest ............................ 38 passed
ML ruff check .......................... All checks passed
ML pytest .............................. 3 passed
Web oxlint ............................. 0 errors, warnings only
Web vitest ............................. 41 passed
Web tsc + Vite build ................... passed with route-level code splitting
Playwright (writes + external MCP) ..... 7 passed
Alembic upgrade head ................... Stage 1-5 + Copilot migrations applied
API health .............................. version 0.6.0 / database ok
Copilot status .......................... enabled, provider deterministic, MCP available, 13 tools
```

The initial JavaScript bundle is approximately 347 kB minified / 108 kB gzip after route-level
splitting; the Recharts trend chunk is approximately 370 kB / 107 kB gzip.

## 3. MCP protocol evidence

- The separately hosted Streamable HTTP server rejects requests without the private service token
  with HTTP 401.
- An authenticated official-SDK client negotiated the MCP protocol and discovered all 13 tools.
- `pumpverity_get_monitoring_overview` executed over HTTP against the developer database and
  returned actual counts with `SIMULATED_REPLAY` data mode.
- MCP tests cover discovery, schemas, actor/equipment errors, service-token enforcement, timeouts
  and domain-service invocation.
- Copilot tests cover provider fallback, MCP outage, missing context, prompt-injection resistance,
  role-guarded writes, approval idempotency and report download.

## 4. End-to-end engineering workflow

The Playwright scenario:

1. registers synthetic equipment and runs normal/imbalance simulations;
2. verifies Live Monitoring, SSE, AI Analysis and generated alert evidence;
3. acknowledges and reviews the alert;
4. opens the Copilot in Alerts & Review and asks why the event was uncertain;
5. verifies the MCP tool timeline and explanatory safety language;
6. requests a monitoring report, confirms the exact arguments and verifies the generated report in
   Reports & Exports;
7. verifies the historical alert overlay;
8. invokes “Run Copilot diagnostic” on Sensor Health and verifies the returned MCP result.

The original prediction remains the immutable source evidence. The Copilot review is appended as
`ENGINEER_REVIEW` with `is_verified_ground_truth=false`. The report records requester, SHA-256 and
simulated-data inclusion.

## 5. Security and grounding evidence

- React never receives MCP service credentials or provider API keys.
- Every MCP tool resolves the actor and role from the database.
- Tool plans are allowlisted and schema-validated; actor identity is injected server-side.
- Copilot writes are restricted to the selected alert/pump and require stored-argument approval.
- Repeated approval returns the existing result without a duplicate effect.
- Tool failures are reported as failures; no success is fabricated.
- Decision scores are explicitly described as model outputs, not failure probabilities.
- Engineer review is not automatically promoted to verified ground truth.
- Arbitrary SQL, shell/Python execution, URLs, MCP targets and industrial actuation are not exposed.

## 6. Deviations and limitations

1. **Deterministic default planner.** The local grounded planner is the default. An
   OpenAI-compatible provider is implemented through configuration, but no paid external LLM was
   used for this acceptance run.
2. **Two MCP transports.** Development uses separately hosted Streamable HTTP. Automated tests use
   the official SDK memory transport for deterministic isolation; both are real MCP sessions over
   the same server/tool definitions.
3. **Selected-record writes.** Copilot writes are intentionally restricted to the selected
   alert/pump; this is not a general autonomous agent.
4. **Conversation UI reload.** Conversations, messages and tool runs are persisted, but the panel
   starts a fresh message view rather than reloading old conversations into the UI.
5. **Reports.** The report tool generates and downloads a traceable JSON monitoring artefact. Full
   templates, date filters and PDF export remain later work.
6. **No alert push.** No alert/review SSE or notification channel was added.
7. **Test data.** Write-enabled E2E runs created synthetic pumps, predictions, alerts, reviews and
   reports in the developer database. These are not experimental evidence.
8. **Synthetic evidence only.** No real-pump accuracy, hardware connectivity, industrial diagnosis
   or autonomous-control claim is made.
