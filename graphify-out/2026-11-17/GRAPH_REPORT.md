# Graph Report - CentriSenseAI  (2026-11-16)

## Corpus Check
- 221 files · ~92,250 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1751 nodes · 3628 edges · 137 communities (103 shown, 34 thin omitted)
- Extraction: 73% EXTRACTED · 27% INFERRED · 0% AMBIGUOUS · INFERRED: 976 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- User
- UI screen specifications
- test_auth.py
- dependencies
- devDependencies
- PetroSense AI — Structured Implementation Assessment
- security.py
- index.ts
- compilerOptions
- 2. Table catalogue
- 4. Functional requirements
- compilerOptions
- System architecture
- PetroSense AI
- react
- package.json
- login
- 2. Implemented endpoints (Stage 1)
- topbar.tsx
- api.ts
- record_audit
- Role
- auth-provider.tsx
- plugins
- package.json
- UserPublic
- guards.test.tsx
- navigation.ts
- FastAPI
- datetime
- RequestContextMiddleware
- users-page.tsx
- common.py
- AppErrorBoundary
- status-badge.tsx
- login-form.tsx
- ADR-0001: Modular monolith API with SQLite-first persistence
- ADR-0002: In-memory access token with HttpOnly refresh cookie
- ADR-0003: Provenance-first schema and orthogonal state dimensions
- ADR-0004: Model artefacts require metadata and compatibility validation
- ADR-0005: SSE for monitoring updates and a transactional outbox for sync
- list_users
- ApiError
- session.py
- stat-card.tsx
- badge.tsx
- button.tsx
- alerts-page.tsx
- analysis-page.tsx
- models-page.tsx
- monitoring-page.tsx
- sensors-page.tsx
- enum_type
- login.spec.ts
- sidebar.tsx
- brand-mark.tsx
- page-header.tsx
- provenance-badge.tsx
- query-error.tsx
- research-notice.tsx
- stage-badge.tsx
- login-page.tsx
- tsconfig.json
- __init__.py
- __init__.py
- history-page.tsx
- pumps-page.tsx
- vite.config.ts
- vitest.config.ts
- README.md
- README.md
- README.md
- README.md
- setup.ts
- petrosense-api
- README.md
- Security and access control
- Acquisition hardware integration contract (template)
- Testing strategy and Stage 1 evidence
- Stage 1 acceptance evidence
- sensor-registration-form.tsx
- Deterministic simulation engine (Stage 2)
- Stage 2 acceptance evidence
- acquisition-service.ts
- test_features.py
- __init__.py
- petrosense-edge
- FastAPI
- record_audit
- auth-provider.tsx
- guards.test.tsx
- Stage 3 acceptance evidence
- RequestContextMiddleware
- use-monitoring-stream.ts
- utcnow
- form-field.tsx
- separator.tsx
- @hookform/resolvers
- @petrosense/shared-contracts
- @testing-library/user-event
- @types/react
- typescript
- @vitejs/plugin-react
- vitest
- __init__.py
- stage4-model-comparison.md
- petrosense-ml
- navigation.ts
- Stage 5 acceptance evidence
- clsx

## God Nodes (most connected - your core abstractions)
1. `SignalWindow` - 49 edges
2. `Provenance` - 46 edges
3. `DataQuality` - 40 edges
4. `Sensor` - 39 edges
5. `SensorType` - 37 edges
6. `Pump` - 36 edges
7. `ModelVersion` - 36 edges
8. `User` - 35 edges
9. `AcquisitionSession` - 35 edges
10. `Prediction` - 33 edges

## Surprising Connections (you probably didn't know these)
- `register_manifest()` --indirect_call--> `client()`  [INFERRED]
  ml/petrosense_ml/register.py → apps/api/tests/conftest.py
- `NavItem` --references--> `Role`  [EXTRACTED]
  apps/web/src/routes/navigation.ts → packages/shared-contracts/src/index.ts
- `UserQuery` --references--> `Role`  [EXTRACTED]
  apps/web/src/services/users-service.ts → packages/shared-contracts/src/index.ts
- `DatasetMetadata` --uses--> `AdapterConfig`  [INFERRED]
  ml/petrosense_ml/dataset.py → edge/petrosense_edge/contracts.py
- `generate_dataset()` --calls--> `AdapterConfig`  [INFERRED]
  ml/petrosense_ml/dataset.py → edge/petrosense_edge/contracts.py

## Import Cycles
- None detected.

## Communities (137 total, 34 thin omitted)

### Community 0 - "User"
Cohesion: 0.10
Nodes (97): list_users(), Page, Session, User, Base, AcquisitionSession, Alert, AlertReview (+89 more)

### Community 1 - "UI screen specifications"
Cohesion: 0.14
Nodes (14): Cross-screen requirements, Screen 10 — Sensor health, Screen 11 — System settings, Screen 12 — User management, Screen 1 — Login, Screen 2 — Dashboard overview, Screen 3 — Pump registration, Screen 4 — Live monitoring (+6 more)

### Community 2 - "test_auth.py"
Cohesion: 0.06
Nodes (59): auth_headers(), client(), login(), _override_get_db(), _session_payload(), _setup_equipment(), test_create_session_ingest_window_and_stop(), test_duplicate_window_index_is_rejected() (+51 more)

### Community 3 - "dependencies"
Cohesion: 0.08
Nodes (25): dependencies, class-variance-authority, @fontsource-variable/inter, @hookform/resolvers, lucide-react, react, react-dom, react-hook-form (+17 more)

### Community 4 - "devDependencies"
Cohesion: 0.09
Nodes (23): devDependencies, jsdom, oxlint, @playwright/test, tailwindcss, @tailwindcss/vite, @testing-library/jest-dom, @testing-library/react (+15 more)

### Community 5 - "PetroSense AI — Structured Implementation Assessment"
Cohesion: 0.07
Nodes (30): 10. What requires experimental verification, 11. Key risks and mitigations, 12. Stage 1 acceptance criteria, 1. Assessment summary, 2.1 Four logical layers, 2.2 Deployment topology for the research prototype, 2.3 Architectural decisions, 2. Proposed solution architecture (+22 more)

### Community 6 - "security.py"
Cohesion: 0.08
Nodes (40): Client, _calibration(), comparison_report(), decisions_from_scores(), evaluate_model(), Any, ndarray, _risk_coverage() (+32 more)

### Community 7 - "index.ts"
Cohesion: 0.06
Nodes (37): FormValues, schema, SensorRegistrationFormProps, SessionQuery, AcquisitionSession, ALERT_CATEGORIES, ALERT_SEVERITIES, ALERT_STATUSES (+29 more)

### Community 8 - "compilerOptions"
Cohesion: 0.08
Nodes (25): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+17 more)

### Community 9 - "2. Table catalogue"
Cohesion: 0.07
Nodes (27): 1. Relationship overview, 2. Table catalogue, 3. Stage 2 write paths, 4. Stage 3 monitoring queries, 5. Stage 4–5 inference, prediction and alert writes, 6. Traceability chain, 7. Provenance and labelling, 8. Retention and storage budget (+19 more)

### Community 10 - "4. Functional requirements"
Cohesion: 0.08
Nodes (24): 0. Implementation status, 1. Purpose and scope, 2. Stakeholders and roles, 3. Definitions, 4. Functional requirements, 5. Non-functional requirements, 6. Data and status requirements, 7. Assessment and acceptance (+16 more)

### Community 11 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+13 more)

### Community 12 - "System architecture"
Cohesion: 0.12
Nodes (17): 1. Goals and constraints, 2. Logical layers, 3. Deployable boundaries, 4.1 Monitoring and inference, 4.2 Offline synchronisation, 4.3 Model promotion, 4. Primary data flows, 5. State model (+9 more)

### Community 13 - "PetroSense AI"
Cohesion: 0.11
Nodes (19): Architecture, Automated setup, Current status — Stage 5 alerting and engineering review, Docker Compose, Documentation, Known limitations at Stage 5, Manual setup, PetroSense AI (+11 more)

### Community 14 - "react"
Cohesion: 0.10
Nodes (4): EmptyStateProps, PageHeaderProps, queryClient, react

### Community 15 - "package.json"
Cohesion: 0.12
Nodes (15): description, engines, node, name, private, scripts, build:web, dev:web (+7 more)

### Community 16 - "login"
Cohesion: 0.07
Nodes (36): create_session(), get_session(), ingest_window(), list_sessions(), list_windows(), Page, Provenance, Request (+28 more)

### Community 17 - "2. Implemented endpoints (Stage 1)"
Cohesion: 0.08
Nodes (25): 1. Conventions, 2. Implemented endpoints — Stage 1, 3. Implemented endpoints — Stages 2–3, 4. Implemented endpoints — Stages 4–5, 5. Planned endpoint groups, 6. Live updates (SSE) — implemented Stages 3–4, 7. Planned edge synchronisation contract, 8. Compatibility and documentation (+17 more)

### Community 18 - "topbar.tsx"
Cohesion: 0.15
Nodes (8): ApiState(), TopbarProps, DashboardPage(), VERIFICATION_CHECKS, RuntimeInformation(), fetchHealth(), fetchMonitoringOverview(), fetchSystemInfo()

### Community 19 - "api.ts"
Cohesion: 0.21
Nodes (14): ApiClientError, apiFetch(), buildHeaders(), loginWithPassword(), logoutSession(), parseResponse(), parseSseChunk(), rawRequest() (+6 more)

### Community 20 - "record_audit"
Cohesion: 0.06
Nodes (74): ApiError, Any, Exception, datetime, utcnow(), sensor_values(), create_session(), get_session_or_404() (+66 more)

### Community 21 - "Role"
Cohesion: 0.32
Nodes (3): ProtectedLayout(), RequireRole(), auth

### Community 22 - "auth-provider.tsx"
Cohesion: 0.11
Nodes (14): AdapterNotConfiguredError, PhysicalSensorAdapter, datetime, RuntimeError, Raised when a physical adapter has no validated hardware configuration., Documented placeholder for real hardware.      It deliberately produces no measu, SimulatedSensorAdapter, AdapterConfig (+6 more)

### Community 23 - "plugins"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 24 - "package.json"
Cohesion: 0.22
Nodes (8): exports, files, src, name, private, type, types, version

### Community 25 - "UserPublic"
Cohesion: 0.21
Nodes (19): ScenarioDefinition, generate_frame(), generate_frames(), _generate_samples(), _normal_waveform(), datetime, _rng_for(), scenario_registry() (+11 more)

### Community 26 - "guards.test.tsx"
Cohesion: 0.15
Nodes (20): ArgumentParser, main(), _parser(), _prediction_payload(), _print_scenarios(), Any, run(), _sensor_invalid_prediction() (+12 more)

### Community 28 - "navigation.ts"
Cohesion: 0.06
Nodes (59): get_current_user(), get_optional_current_user(), Session, User, require_roles(), _unauthorized(), _clear_refresh_cookie(), list_roles() (+51 more)

### Community 29 - "FastAPI"
Cohesion: 0.12
Nodes (26): create_pump(), get_pump(), list_pumps(), Page, PumpCreate, PumpUpdate, Request, Session (+18 more)

### Community 30 - "datetime"
Cohesion: 0.07
Nodes (31): FormValues, PumpEditFormProps, schema, FormValues, PumpRegistrationForm(), PumpRegistrationFormProps, schema, REGIMES (+23 more)

### Community 31 - "RequestContextMiddleware"
Cohesion: 0.25
Nodes (3): AcquisitionAdapter, datetime, Protocol

### Community 33 - "users-page.tsx"
Cohesion: 0.33
Nodes (4): ROLES, fetchUsers, user, UsersPage()

### Community 34 - "common.py"
Cohesion: 0.09
Nodes (25): live_snapshot(), overview(), _poll_predictions(), _poll_windows(), Any, datetime, LiveSnapshot, MonitoringOverview (+17 more)

### Community 36 - "status-badge.tsx"
Cohesion: 0.40
Nodes (4): STATUS_MAP, StatusBadge(), StatusBadgeProps, StatusTone

### Community 37 - "login-form.tsx"
Cohesion: 0.40
Nodes (4): LoginForm(), LoginFormProps, loginSchema, LoginValues

### Community 39 - "ADR-0001: Modular monolith API with SQLite-first persistence"
Cohesion: 0.33
Nodes (5): ADR-0001: Modular monolith API with SQLite-first persistence, Consequences, Context, Decision, Guardrails

### Community 40 - "ADR-0002: In-memory access token with HttpOnly refresh cookie"
Cohesion: 0.33
Nodes (5): ADR-0002: In-memory access token with HttpOnly refresh cookie, Consequences, Context, Decision, Follow-ups

### Community 41 - "ADR-0003: Provenance-first schema and orthogonal state dimensions"
Cohesion: 0.33
Nodes (5): ADR-0003: Provenance-first schema and orthogonal state dimensions, Consequences, Context, Decision, Enforcement

### Community 42 - "ADR-0004: Model artefacts require metadata and compatibility validation"
Cohesion: 0.33
Nodes (5): ADR-0004: Model artefacts require metadata and compatibility validation, Consequences, Context, Decision, Verification required in Stage 4

### Community 43 - "ADR-0005: SSE for monitoring updates and a transactional outbox for sync"
Cohesion: 0.33
Nodes (5): ADR-0005: SSE for monitoring updates and a transactional outbox for sync, Consequences, Context, Decision, Open questions

### Community 44 - "list_users"
Cohesion: 0.26
Nodes (4): ApiClient, EdgeApiError, Any, RuntimeError

### Community 45 - "ApiError"
Cohesion: 0.12
Nodes (20): AlertDetail, create_review(), AlertReviewCreate, Request, Session, User, acknowledge_alert(), get_alert() (+12 more)

### Community 49 - "badge.tsx"
Cohesion: 0.67
Nodes (3): Badge(), BadgeProps, badgeVariants

### Community 50 - "button.tsx"
Cohesion: 0.67
Nodes (3): Button(), ButtonProps, buttonVariants

### Community 51 - "alerts-page.tsx"
Cohesion: 0.10
Nodes (21): ACTION_META, AlertDetailPanel(), AlertFilters, AlertReviewActions(), AlertsPage(), CATEGORY_OPTIONS, DEFAULT_FILTERS, isClosed() (+13 more)

### Community 52 - "analysis-page.tsx"
Cohesion: 0.23
Nodes (9): AnalysisPage(), DECISION_OPTIONS, featureEntries(), formatScore(), PredictionDetail(), ACTIVE_MODEL, fetchActiveModel, fetchPredictions (+1 more)

### Community 53 - "models-page.tsx"
Cohesion: 0.11
Nodes (20): metricValue(), ModelCard(), ModelsPage(), activateModel, EVALUATION, fetchActiveModel, fetchModels, MODEL (+12 more)

### Community 54 - "monitoring-page.tsx"
Cohesion: 0.11
Nodes (13): formatMetric(), LiveMonitoringPage(), STREAM_STATUS, FAULT_PREDICTION, fetchLiveSnapshot, fetchPumps, HEALTH, PUMP (+5 more)

### Community 55 - "sensors-page.tsx"
Cohesion: 0.17
Nodes (10): SensorsPage(), createSensor, fetchPumps, fetchSensorHealth, fetchSensors, HEALTH, PUMP, SENSOR (+2 more)

### Community 58 - "enum_type"
Cohesion: 0.67
Nodes (3): enum_type(), StrEnum, SAEnum

### Community 59 - "login.spec.ts"
Cohesion: 0.39
Nodes (4): repositoryRoot, runSimulator(), signIn(), SCREENS

### Community 62 - "page-header.tsx"
Cohesion: 0.09
Nodes (17): ACK_REVIEW, acknowledgeAlert, ACKNOWLEDGED_DETAIL, ALERT, authState, createAlertReview, DETAIL, fetchAlert (+9 more)

### Community 74 - "history-page.tsx"
Cohesion: 0.19
Nodes (11): EVENT_META, formatWindowTime(), RmsTrendChart(), RmsTrendChartProps, WaveformChartProps, HistoryPage(), issueCodes(), Alert (+3 more)

### Community 76 - "pumps-page.tsx"
Cohesion: 0.10
Nodes (42): create_prediction(), get_prediction(), list_predictions(), Page, PredictionDecision, Request, Session, User (+34 more)

### Community 81 - "README.md"
Cohesion: 0.12
Nodes (14): 1. Purpose, 2. Boundaries, 3. Scenarios, 4. Validation checks, 5. Determinism, 6. Scientific limitations, 7. CLI, Deterministic simulation engine (Stage 2) (+6 more)

### Community 82 - "README.md"
Cohesion: 0.22
Nodes (8): Dataset, Evaluation, Install and test, Limitations, Machine-learning research pipeline, Registration safety, Run the pipeline, Selected edge artefact

### Community 84 - "README.md"
Cohesion: 0.43
Nodes (13): SignalValidator, codes(), frame(), test_flatline_is_invalid(), test_insufficient_samples_are_invalid(), test_missing_and_disconnected_samples_are_invalid(), test_non_finite_values_are_invalid(), test_out_of_range_values_are_invalid() (+5 more)

### Community 99 - "Security and access control"
Cohesion: 0.18
Nodes (10): 1. Authentication, 2. Role model, 3. Audit logging, 4. Secrets and configuration, 5. Input and output safety, 6. CSRF and session threats, 7. Offline synchronisation security (planned), 8. Explicit non-goals (+2 more)

### Community 100 - "Acquisition hardware integration contract (template)"
Cohesion: 0.25
Nodes (7): 1. Adapter boundary, 2. Open hardware decisions, 3. Required documentation before experiments, 4. Validation before use in evaluation, 5. Prohibited claims until evidence exists, 6. Integration failure handling, Acquisition hardware integration contract (template)

### Community 101 - "Testing strategy and Stage 1 evidence"
Cohesion: 0.25
Nodes (8): 1. Approach, 2. Executed Stage 5 results, 3. Backend coverage highlights, 4. Edge coverage highlights, 5. Critical failure scenarios, 6. Running tests, 7. Future test expansion, Testing strategy and Stage 5 evidence

### Community 102 - "Stage 1 acceptance evidence"
Cohesion: 0.33
Nodes (6): 1. Acceptance criteria, 2. Executed verification, 3. Deviations and known issues, 4. Scientific integrity check, 5. Entry criteria for Stage 2, Stage 1 acceptance evidence

### Community 103 - "sensor-registration-form.tsx"
Cohesion: 0.36
Nodes (18): activate_model(), add_evaluation(), _audit(), get_active_model(), get_model_or_404(), list_models(), _model_options(), ModelEvaluation (+10 more)

### Community 104 - "Deterministic simulation engine (Stage 2)"
Cohesion: 0.22
Nodes (13): DecisionThresholds, load_model_artifact(), LoadedModel, ModelArtifactError, Path, ValueError, sha256_file(), _sigmoid() (+5 more)

### Community 105 - "Stage 2 acceptance evidence"
Cohesion: 0.29
Nodes (7): 1. Acceptance criteria, 2. Executed verification, 3. End-to-end simulated acquisition evidence, 4. Configuration and schema changes, 5. Deviations and limitations, 6. Entry criteria for Stage 3, Stage 2 acceptance evidence

### Community 106 - "acquisition-service.ts"
Cohesion: 0.24
Nodes (18): activate_model(), active_model(), add_evaluation(), get_model(), list_models(), ModelRuntime, ModelStatus, Page (+10 more)

### Community 108 - "test_features.py"
Cohesion: 0.16
Nodes (17): FeatureExtractionError, FeatureExtractor, _goertzel_amplitude(), ValueError, vector_for_contract(), config(), features_for(), test_abnormal_scenarios_raise_features() (+9 more)

### Community 111 - "FastAPI"
Cohesion: 0.23
Nodes (20): _auto_alert_enabled(), _aware(), create_prediction(), _create_prediction_alert(), _feature_contract_compatible(), get_for_window(), get_prediction_or_404(), list_predictions() (+12 more)

### Community 112 - "record_audit"
Cohesion: 0.22
Nodes (9): scripts, build, dev, lint, preview, test, test:coverage, test:e2e (+1 more)

### Community 113 - "auth-provider.tsx"
Cohesion: 0.25
Nodes (9): AuthContext, AuthContextValue, AuthProvider(), AuthState, AuthStatus, stateFromSession(), AuthSession, LoginRequest (+1 more)

### Community 114 - "guards.test.tsx"
Cohesion: 0.22
Nodes (9): 1. Acceptance criteria, 2. Executed verification, 3. Model evaluation evidence (synthetic), 4. Edge inference evidence, 5. Isolated database summary, 6. UI evidence, 7. Deviations and limitations, 8. Entry criteria for Stage 5 (+1 more)

### Community 115 - "Stage 3 acceptance evidence"
Cohesion: 0.25
Nodes (8): 1. Acceptance criteria, 2. Executed verification, 3. Sensor-invalid evidence, 4. Isolated database summary, 5. Schema/index changes, 6. Deviations and limitations, 7. Entry criteria for Stage 4, Stage 3 acceptance evidence

### Community 116 - "RequestContextMiddleware"
Cohesion: 0.40
Nodes (4): name, private, type, version

### Community 120 - "utcnow"
Cohesion: 0.21
Nodes (9): DecisionOutcome, DecisionPolicy, DecisionResult, StrEnum, Selective-classification uncertainty from the model confidence.      The score i, UncertaintyEvaluator, test_decision_policy_supports_normal_fault_and_abstention(), test_decision_thresholds_are_ordered() (+1 more)

### Community 123 - "@hookform/resolvers"
Cohesion: 0.32
Nodes (4): PlannedCapability, PlannedScreenProps, UnauthorizedPageProps, Role

### Community 133 - "navigation.ts"
Cohesion: 0.32
Nodes (6): canAccess(), NAV_SECTIONS, NavItem, NavSection, ROUTE_META, routeMeta()

### Community 134 - "Stage 5 acceptance evidence"
Cohesion: 0.33
Nodes (6): 1. Acceptance criteria, 2. Executed verification, 3. Alert and review evidence, 4. UI evidence, 5. Deviations and limitations, Stage 5 acceptance evidence

## Knowledge Gaps
- **462 isolated node(s):** `petrosense-api`, `$schema`, `typescript`, `oxc`, `react/rules-of-hooks` (+457 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SignalWindow` connect `User` to `test_auth.py`, `pumps-page.tsx`, `FastAPI`, `login`, `record_audit`, `navigation.ts`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `test_sensor_health_missing_gaps_stale_and_pump_filter()` connect `navigation.ts` to `User`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `generate_frame()` connect `UserPublic` to `test_features.py`, `guards.test.tsx`, `navigation.ts`, `auth-provider.tsx`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `SignalWindow` (e.g. with `Base` and `AlertCategory`) actually correct?**
  _`SignalWindow` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `Provenance` (e.g. with `AcquisitionSession` and `Alert`) actually correct?**
  _`Provenance` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `DataQuality` (e.g. with `AcquisitionSession` and `Alert`) actually correct?**
  _`DataQuality` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `Sensor` (e.g. with `Base` and `AlertCategory`) actually correct?**
  _`Sensor` has 38 INFERRED edges - model-reasoned connections that need verification._