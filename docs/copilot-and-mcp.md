# Engineering Copilot and MCP integration

**Version:** 0.6
**Scope:** Context-aware Engineering Copilot for the PUMPVERITY AI research prototype.

## 1. Repository audit

The extension reuses the existing application rather than introducing a second monitoring stack.

| Area | Existing implementation reused |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind, React Query, React Router, authenticated AppShell |
| Existing screens | Login, Dashboard, Pump Registry, Live Monitoring, AI Analysis, Alerts & Review, Historical Trends, Reports, Model Registry, Sensor Health, Settings, User Management |
| Backend | FastAPI modular monolith, SQLAlchemy, Alembic, Pydantic settings, JWT auth/RBAC/audit |
| Domain services | `monitoring`, `predictions`, `alerts`, `models`, `equipment`, `acquisition`, `audit` |
| Data | SQLite with pumps, sensors, sessions, windows, predictions, alerts, reviews, models, evaluations, report jobs and audit logs |
| Edge/ML | Independent simulation, feature extraction, hash-verified JSON artefact loading, uncertainty policy and research pipeline |

The Copilot does not duplicate acquisition, validation, inference, prediction persistence or alert
review logic. MCP tools call the existing domain services.

## 2. Architecture decision

```text
React Engineering Copilot
  -> authenticated FastAPI /api/v1/copilot/*
  -> Copilot orchestrator (conversation, provider, approvals, actions)
  -> MCP ClientSession (official Python SDK)
  -> FastMCP server, streamable HTTP or memory transport
  -> existing domain services
  -> SQLite
```

Development/runtime uses a separately runnable **Streamable HTTP MCP server**:

```powershell
apps/api/.venv/Scripts/python -m app.copilot.server
# http://127.0.0.1:8010/mcp
```

The default local `.env` points the orchestrator to that endpoint
(`PETROSENSE_MCP_TRANSPORT=http`). Automated API tests use the SDK's in-memory MCP transport for
determinism; both paths use a real `ClientSession`/FastMCP server and the same tool contracts. This
keeps the local prototype single-database while preserving a standards-compliant interface that can
be hosted separately.

The HTTP MCP endpoint is protected by a service token derived from `PETROSENSE_MCP_SERVICE_TOKEN`
or the API secret when unset. It is not reachable with a normal user Bearer token and has no CORS
configuration. React never has the service token.

## 3. MCP tool contracts

All tools use the `pumpverity_` namespace and return structured Pydantic output with timestamps,
units, provenance and limitations. `actor_id` is injected server-side by the orchestrator, not
taken from the language-model plan. Every tool resolves the actor from the database and checks role.

| Tool | Input | Role | Output |
|---|---|---|---|
| `pumpverity_get_monitoring_overview` | actor | all authenticated | aggregate counts, condition, model, data mode |
| `pumpverity_get_pump_status` | actor, pump id/code | all authenticated | pump state, sensors, condition, provenance |
| `pumpverity_get_sensor_health` | actor, pump id/code, optional sensor | all authenticated | validity, freshness, gaps, RMS in g |
| `pumpverity_get_latest_prediction` | actor, pump id/code, optional sensor | all authenticated | decision, scores, uncertainty, model, window |
| `pumpverity_get_fault_history` | actor, pump id/code, optional sensor, limit | all authenticated | alert-backed fault/uncertain/invalid events |
| `pumpverity_get_vibration_summary` | actor, pump id/code, optional sensor, limit | all authenticated | RMS/peak aggregate in g and provenance |
| `pumpverity_get_model_evaluation` | actor, optional model id | all authenticated | model lifecycle and evaluation evidence |
| `pumpverity_get_alert_details` | actor, alert id | all authenticated | alert, retained prediction and reviews |
| `pumpverity_get_edge_connectivity` | actor, pump id/code | all authenticated | data mode, buffering, last reading |
| `pumpverity_acknowledge_alert` | actor, alert id | Engineer/Reviewer/Admin | updated workflow status, audit |
| `pumpverity_mark_alert_reviewed` | actor, alert id, notes | Engineer/Reviewer/Admin | appended `REVIEW`, status, review id |
| `pumpverity_add_engineering_note` | actor, alert id, notes | Engineer/Reviewer/Admin | appended `ADD_NOTE`, review id |
| `pumpverity_generate_monitoring_report` | actor, pump id/code | all authenticated report roles | report job, file hash, simulated-data flag |

Safety rules:

- tool schemas reject unknown arguments;
- input IDs are resolved through domain services, never through raw SQL supplied by a caller;
- sensor health, equipment condition, data quality and connectivity remain distinct;
- all vibration values include `g` and provenance;
- read tools cannot invoke inference or change records;
- write tools cannot update predictions, confirm a fault or promote a review to verified ground truth;
- results are size-limited and tool calls are timed out;
- every invocation is recorded in `copilot_tool_invocations`.

## 4. Copilot orchestration

1. Validate the authenticated session and typed page context (route, screen, selected pump/sensor/alert,
   mode, connectivity).
2. Create or reuse a conversation owned by the user.
3. Discover approved MCP tools.
4. Ask the configured provider for a bounded plan:
   - `deterministic`: local grounded planner, default;
   - `openai_compatible`: optional remote planner using environment configuration.
5. Validate every tool name and JSON-schema argument against the discovered tool and allowlist.
6. Execute read tools through MCP; record success/failure and structured results.
7. For a write, store a **pending approval** with the exact arguments. Nothing is executed.
8. Compose the assistant response from actual tool results, explicitly identifying unavailable data
   and provenance. Scores are described as model outputs, not failure probabilities.
9. Return typed navigation actions and the tool timeline.
10. A separate approval endpoint revalidates role, target and stored arguments before calling the
    write MCP tool exactly once. Repeated approvals return the stored result.

If the remote provider is unavailable, the deterministic grounded planner is used and the response
marks the fallback. If MCP is unavailable, the Copilot says so and monitoring continues. If the
Copilot is disabled, its endpoints report that state without affecting monitoring.

## 5. Frontend structure

- `EngineeringCopilot` fixed, collapsible panel in the authenticated AppShell.
- `CopilotContextProvider` derives route/screen context and accepts explicit page enrichment.
- `EngineeringCopilot` supports close/minimise, context chips, tool timeline, structured result
  cards, suggested questions, navigation actions, write confirmation, cancellation and retry.
- `CopilotActionDispatcher` is centralized in the context provider. It validates action types,
  payload IDs, route allowlists and frontend role access before navigating.
- Existing screens publish selected pump, sensor and alert context through
  `useCopilotPageContext`. Route changes update screen context automatically.
- Login exposes a static sign-in help disclosure only; unauthenticated users have no Copilot API or
  MCP access.
- Reports page lists Copilot-generated report artefacts and exposes authenticated download.

## 6. Conversation and execution traceability

| Table | Purpose |
|---|---|
| `copilot_conversations` | owner, title, latest typed context, timestamps |
| `copilot_messages` | append-only user/assistant/system messages with actions and linked run IDs |
| `copilot_tool_invocations` | tool name, exact arguments, status, result/error, actor, approval/idempotency key and timestamps |

Domain write actions additionally create normal audit entries (`ALERT_ACKNOWLEDGED`,
`ALERT_REVIEWED`, `REPORT_GENERATED`, etc.) and `COPILOT_TOOL_COMPLETED`.

## 7. Security and grounding boundaries

- All Copilot endpoints require authentication.
- Roles are checked in the API and again inside every MCP tool; frontend role context is not trusted.
- Write proposals require an explicit frontend confirmation of the exact stored arguments.
- Only the selected alert can be acknowledged/reviewed by a Copilot write. Reports are restricted to
  the selected pump.
- Arbitrary MCP targets, SQL, shell, Python execution, URLs, component names and industrial
  actuation are not exposed.
- LLM plans are untrusted input; they cannot select unapproved tools, modify actor identity or bypass
  approvals.
- Tool results are untrusted data and are rendered/validated as data, never executed.
- Engineer review remains an engineering judgement and `is_verified_ground_truth=false`.

## 8. Main files

Backend: `app/copilot/{contracts,outputs,tools,server,client,providers,summarizer,orchestrator}.py`,
`app/schemas/{copilot,reports}.py`, `app/api/v1/{copilot,reports}.py`,
`app/services/reports.py`, `app/db/models.py`, migration `6ab8b0723c85`.

Frontend: `components/copilot/engineering-copilot.tsx`,
`providers/copilot-context-provider.tsx`, `services/copilot-service.ts`,
`services/reports-service.ts`, page context hooks and `AppShell` integration.

Tests: `apps/api/tests/test_copilot.py`, `apps/api/tests/test_mcp.py`,
`apps/web/src/components/copilot/engineering-copilot.test.tsx`, and the extended Playwright flow.
