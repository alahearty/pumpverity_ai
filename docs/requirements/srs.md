# Software requirements specification (v0.6)

**Project:** PUMPVERITY AI
**Research title:** Design and Experimental Evaluation of a Low-Cost, Uncertainty-Aware Edge-AI
Framework for Robust Fault Detection in Centrifugal Pumps Used in Nigeria's Oil and Gas Industry
**Document status:** 0.6 Engineering Copilot baseline
**Related:** [Implementation assessment](../00-implementation-assessment.md),
[screen specifications](../ui/screen-specifications.md), [testing strategy](../testing/strategy.md)

## 0. Implementation status

Stages 1–5 are implemented and verified: foundation/auth/schema/UI shell, pump and sensor
registration, operating-regime defaults, deterministic simulation, signal validation, acquisition
sessions and window persistence, monitoring overview/live snapshots, authenticated SSE updates,
sensor diagnostics, live/dashboard/history views, versioned feature extraction, hash-verified edge
inference, uncertainty/abstention, model registry, prediction persistence, AI Analysis/Model
Management, automatic alerts, acknowledgement, append-only engineering review and historical event
overlays.

Version 0.6 adds a context-aware Engineering Copilot backed by a custom official-SDK MCP server:
13 namespaced read/write tools, Streamable HTTP hosting, role revalidation, grounded tool-result
responses, validated navigation actions, explicit write approvals, conversation/tool traceability
and Copilot-generated monitoring reports. Reports are currently a generated-artefact list/download
rather than a full report-template system. Settings writes, user-administration writes and offline
synchronisation remain later stages. Evidence: [Stage 1](../stage-1-acceptance.md),
[Stage 2](../stage-2-acceptance.md), [Stage 3](../stage-3-acceptance.md),
[Stage 4](../stage-4-acceptance.md), [Stage 5](../stage-5-acceptance.md),
[Copilot architecture](../copilot-and-mcp.md) and [Copilot acceptance](../copilot-acceptance.md).

## 1. Purpose and scope

PUMPVERITY AI is a six-month academic research prototype for vibration-based condition monitoring
of one laboratory centrifugal-pump test rig. It demonstrates an offline-capable edge pipeline that
separates equipment condition (`NORMAL`, `FAULT`, `UNCERTAIN`), sensor validity (`VALID`,
`SENSOR_INVALID`), connectivity and data provenance (`SIMULATED`, `EXPERIMENTAL`).

It is **not** a certified safety system, predictive-maintenance product or autonomous shutdown
system. No real-world accuracy claim is valid without measured experimental evidence.

### In scope

- Pump/sensor registration for one laboratory rig, extensible by design.
- Deterministic simulated acquisition for integration demonstrations.
- Signal validation, preprocessing, feature extraction, inference and uncertainty-aware abstention.
- Local persistence, alerts, human review, history, reports, model registry and administration.
- Offline buffering and synchronisation against a local test server.
- Automated testing and research documentation.

### Out of scope

- Remaining useful life, digital twins, fleet management, commercial deployment.
- Automatic pump shutdown, PLC/SCADA integration, safety-instrumented functions.
- Claims of industrial readiness or certified sensor accuracy.
- Production cloud infrastructure, Kubernetes or microservices.

## 2. Stakeholders and roles

| Stakeholder | Interest |
|---|---|
| Research team (eight ICT Group 2 students) | Build, demonstrate and evaluate the prototype |
| Engineer | Register equipment, monitor, triage alerts and review events |
| Researcher | Design experiments, train/evaluate models, manage model versions |
| Reviewer | Independently review abnormal/uncertain/sensor events |
| Administrator | Accounts, roles, settings, security and audit |
| Academic supervisor / assessor | Reproducibility, scientific defensibility, evidence |
| NCDMB-oriented programme audience | Indigenous research capability demonstration |

## 3. Definitions

| Term | Meaning |
|---|---|
| Equipment condition | Model-derived state for the pump: Normal, Fault, Uncertain |
| Data quality | Whether a signal is suitable for inference: Valid or Sensor Invalid |
| Uncertainty | Model/decision condition where a reliable condition decision cannot be supported |
| Abstention | Returning `UNCERTAIN` instead of forcing Normal/Fault |
| Provenance | Whether data is simulated or experimentally measured |
| Ground truth | Independently verified experimental label, not an engineer review by default |
| Outbox | Durable edge-local event queue for store-and-forward sync |

## 4. Functional requirements

### FR-01 Acquisition and simulation

- FR-01.1 The system shall provide simulated and physical acquisition adapters behind one contract.
- FR-01.2 The simulated adapter shall support deterministic seeded scenarios: normal, abnormal,
  uncertain, disconnection, corruption, network outage, buffering and restoration.
- FR-01.3 The physical adapter shall document an integration contract; it shall not fabricate data.
- FR-01.4 Readings shall carry sensor ID, session ID, timestamp, sampling rate, units and quality.
- FR-01.5 Sessions shall be bounded to control storage volume.

### FR-02 Signal validation and processing

- FR-02.1 The system shall validate for missing samples, invalid numerics, unexpected timestamps,
  out-of-range values, sustained flatline and disconnection.
- FR-02.2 Invalid signals shall produce `SENSOR_INVALID` and suppress condition inference.
- FR-02.3 The pipeline shall be: validate → preprocess → extract features → infer → assess
  uncertainty → decide → record.
- FR-02.4 The pipeline shall be independently testable without the frontend.
- FR-02.5 Feature extraction shall follow a versioned feature contract shared with model metadata.

### FR-03 Condition monitoring and uncertainty

- FR-03.1 The system shall distinguish `NORMAL`, `FAULT`, `UNCERTAIN` and `SENSOR_INVALID` outcomes.
- FR-03.2 The decision policy shall abstain when acceptance criteria are not met.
- FR-03.3 Uncertainty policy and thresholds shall be documented and configurable by authorised roles.
- FR-03.4 Scores shall not be described as failure probabilities without calibration evidence.
- FR-03.5 Predictions shall record model version, latency, operating regime, provenance and
  originating signal window.

### FR-04 Equipment and sensor management

- FR-04.1 Administrators/engineers shall register pumps with unique IDs and ratings.
- FR-04.2 Sensors shall be assigned to a pump with axis and mounting position.
- FR-04.3 Duplicate IDs and invalid fields shall be rejected.
- FR-04.4 Retirement/deactivation shall preserve historical evidence.

### FR-05 Alerts and human review

- FR-05.1 Fault, uncertain and sensor-invalid events shall be reviewable.
- FR-05.2 Reviewers shall acknowledge and review with identity, action and timestamp.
- FR-05.3 Review labels may confirm or correct an AI output; they shall never overwrite it.
- FR-05.4 Engineer review labels shall not automatically become verified experimental ground truth.
- FR-05.5 Alerts shall be filterable by category, date, status and pump.

### FR-06 History, reports and traceability

- FR-06.1 Historical readings shall be filterable by pump and time range.
- FR-06.2 Fault events, uncertainty markers and sensor-invalid intervals shall be distinct.
- FR-06.3 Reports shall identify dataset, model version, timestamps, filters and provenance.
- FR-06.4 CSV/PDF exports shall be supported for the agreed report types.
- FR-06.5 The chain Pump → Sensor → Session → Window → Prediction → Alert → Review shall remain
  traceable.

### FR-07 Model governance

- FR-07.1 A model registry shall record metadata, feature contract, datasets, metrics, hash,
  compatibility and status.
- FR-07.2 Activation shall require validation and compatibility checks and shall be role-restricted.
- FR-07.3 Activation, rollback and retirement shall be audited.
- FR-07.4 Uploaded artefacts shall not be treated as arbitrary executable code.

### FR-08 Offline-first operation and synchronisation

- FR-08.1 Edge inference, alerting and persistence shall operate without the API/network.
- FR-08.2 A transactional outbox shall store unique events with type, device, timestamp, payload
  version, payload, delivery state and retry metadata.
- FR-08.3 Synchronisation shall use retry/backoff and idempotent receiver processing.
- FR-08.4 Events shall be marked synchronised only after durable acceptance.
- FR-08.5 Unsynchronised events shall survive application restart.
- FR-08.6 Connectivity state shall be displayed separately from equipment/sensor state.

### FR-09 Authentication, authorisation and audit

- FR-09.1 Only authenticated users shall access protected routes and API resources.
- FR-09.2 Four roles shall be supported: Administrator, Engineer, Researcher, Reviewer.
- FR-09.3 Permissions shall be enforced by the backend.
- FR-09.4 Authentication events and administrative/scientific changes shall be audited.
- FR-09.5 Passwords shall be securely hashed; credentials/secrets shall not be exposed to the SPA or
  repository.
- FR-09.6 Sessions shall expire and support logout and revocation.

### FR-10 Monitoring interface

- FR-10.1 At least twelve screens shall be navigable with consistent industrial styling.
- FR-10.2 Live and simulated data shall be explicitly distinguishable.
- FR-10.3 Sensor-invalid status shall never be presented as verified normal condition.
- FR-10.4 Displayed states shall be driven by backend state, not hardcoded labels.
- FR-10.5 Empty, loading and error states shall be explicit.

### FR-11 Configuration and administration

- FR-11.1 Authorised users shall configure sampling, windows, thresholds, retention, sync, device
  identity and export preferences.
- FR-11.2 Changes shall be validated, role-restricted and audited.
- FR-11.3 User accounts shall support activation/deactivation, role assignment and credential reset.
- FR-11.4 The last administrator shall not be deactivated (Stage 7 rule).

### FR-12 Research reproducibility

- FR-12.1 Datasets, code revisions, seeds, feature contracts and artefact hashes shall be recorded.
- FR-12.2 Train/test splits shall group by acquisition run and avoid overlapping-window leakage.
- FR-12.3 Evaluation shall report balanced accuracy, macro-F1, precision/recall, confusion matrix,
  false-alert rate, risk–coverage, calibration and edge latency/memory where measured.
- FR-12.4 Simulated and experimental evaluation datasets shall remain distinguishable.

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Local operation without continuous internet access |
| NFR-02 | API p95 latency for ordinary local reads below 500 ms on the lab machine (target) |
| NFR-03 | Inference latency and memory measured, not assumed, on the selected edge device |
| NFR-04 | Responsive UI usable on desktop and tablet; keyboard navigation and visible focus |
| NFR-05 | Structured logs with request IDs; no secrets or passwords logged |
| NFR-06 | Automated tests for core workflows and failure scenarios |
| NFR-07 | Reproducible setup via documented dependencies, migration and seed scripts |
| NFR-08 | Bounded storage with retention and session limits |
| NFR-09 | Defensible scientific claims; no fabricated metrics or hardware results |
| NFR-10 | Clear separation of simulation and experiment in storage, UI and reports |

## 6. Data and status requirements

- Equipment condition and data quality are separate fields and UI elements.
- Connectivity has its own state machine.
- Provenance is mandatory on acquisition, window, prediction, alert and evaluation records.
- Original predictions are immutable; reviews are append-only.
- Unique durable event IDs support deduplicated synchronisation.
- High-frequency waveforms are not stored as unbounded ordinary reading rows.

## 7. Assessment and acceptance

The prototype is acceptable at the end of the six months when:

- all twelve screens are navigable and functional at the intended research depth;
- simulated acquisition drives the complete monitoring workflow;
- sensor-invalid input suppresses condition inference;
- alerts persist and are reviewable without overwriting AI output;
- history and reports remain traceable to pump, dataset and model version;
- model registration/activation is guarded and audited;
- permissions are enforced server-side;
- local inference and buffered events survive network loss/restart;
- duplicate sync does not create duplicates;
- automated tests cover the critical failure scenarios;
- simulation is clearly distinguished from experimental data;
- no unsupported industrial-readiness claim is made.

Stage-specific acceptance is recorded in the [implementation assessment](../00-implementation-assessment.md)
and [Stage 1 acceptance evidence](../stage-1-acceptance.md).

## 8. Assumptions and constraints

- The laboratory rig and sensor are not yet integrated; the physical adapter contract precedes
  measurement.
- One development team of eight students, six months, local infrastructure.
- Raspberry Pi is the initial edge platform candidate; ESP32-S3 compatibility is not assumed.
- PostgreSQL and wider deployment are optional later work.
- Experimental data acquisition begins before the software is fully complete.

