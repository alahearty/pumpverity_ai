# Stage 5 acceptance evidence

**Date:** 2026-11-16
**Environment:** Windows 11, Python 3.13, Node.js 24, Chrome (Playwright), SQLite
**Versions:** API `0.5.0`, edge `0.5.0`, ML pipeline `0.5.0`, web `0.5.0`, migration
`f320ab275929`
**Scope:** Automatic alerts, acknowledgement, append-only engineering review, label provenance and
historical alert overlays.

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `FAULT`, `UNCERTAIN` and `SENSOR_INVALID` predictions create reviewable alerts | **Met** | `tests/test_alerts.py`; auto settings |
| 2 | `NORMAL` predictions do not create alerts | **Met** | alert API test |
| 3 | At most one alert exists per prediction | **Met** | `uq_alerts_prediction_id`; migration `f320ab275929` |
| 4 | Alert creation is configurable | **Met** | `alerts.auto_create_for_{fault,uncertain,sensor_invalid}`; disabled-setting test |
| 5 | Alert queue supports status, category, severity, pump, sensor, assignment and date filters | **Met (API) / partial UI** | `GET /alerts`; UI exposes status/category/severity/pump |
| 6 | Alert detail retains the source prediction, model, window and provenance | **Met** | `AlertDetail`; UI original-evidence panel |
| 7 | Acknowledgement records reviewer and timestamp and is idempotent | **Met** | `POST /alerts/{id}/acknowledge`; API test |
| 8 | Engineering reviews are append-only and never rewrite the prediction | **Met** | `alert_reviews`; correction test compares original decision |
| 9 | Labels can be confirmed or corrected with validation | **Met** | confirm/correct actions; mismatch/equality tests |
| 10 | Reviewed labels are distinguished from verified ground truth | **Met** | all reviews `ENGINEER_REVIEW`, `is_verified_ground_truth=false` |
| 11 | Alert actions are role-guarded and audited | **Met** | Engineer/Reviewer/Administrator writes; `ALERT_*` audit assertions |
| 12 | History trend overlays use persisted alert-to-window links | **Met** | `RmsTrendChart`; E2E legend/overlay check |
| 13 | Alerts create no real-world accuracy or safety claim | **Met** | UI labels; synthetic-only evidence |

## 2. Executed verification

```text
API ruff check ......................... All checks passed
API pytest .............................. 59 passed
Edge ruff check ........................ All checks passed
Edge pytest ............................. 38 passed
ML ruff check ........................... All checks passed
ML pytest ............................... 3 passed
Web oxlint .............................. 0 errors, 3 fast-refresh warnings
Web vitest .............................. 38 passed
Web tsc + vite build .................... passed (1,019.80 kB / 294.05 kB gzip)
Playwright (writes enabled) ............. 7 passed
Alembic upgrade head ................... Stage 1-5 applied
API health .............................. version 0.5.0
Seed .................................... reference data and alert settings present
```

The Playwright flow now:

1. registers a synthetic pump/sensor and runs normal and imbalance simulation sessions;
2. verifies the live condition and AI Analysis FAULT decision;
3. opens Alerts & Review and filters to the pump;
4. acknowledges the generated fault alert;
5. confirms the label with engineering notes;
6. verifies the appended review and provenance wording;
7. opens Historical Trends and verifies the persisted fault-alert overlay legend.

## 3. Alert and review evidence

Backend tests cover:

- `FAULT` creates a high-severity alert linked to the source prediction;
- `UNCERTAIN` creates a medium-severity alert;
- `SENSOR_INVALID` creates a high-severity alert with no model inference;
- `NORMAL` creates no alert;
- duplicate prediction event IDs are rejected before a second alert can exist;
- disabling `alerts.auto_create_for_fault` suppresses alert creation;
- acknowledgement is idempotent and assigns the acting reviewer;
- confirmation must match the original decision;
- correction must differ from the original decision and is stored as a new review;
- notes are mandatory for review/note actions;
- closed alerts reject further reviews;
- researchers can read but cannot acknowledge/review;
- filters and audit entries are asserted.

After the write-enabled E2E run, the developer SQLite database contained repeated synthetic test
records:

```text
pumps .................. 3
acquisition sessions ... 4
signal windows ......... 8
predictions ............ 8
alerts ................. 4 (2 OPEN, 2 REVIEWED; all FAULT)
alert reviews .......... 4 (2 ACKNOWLEDGE, 2 CONFIRM_LABEL)
label provenance ....... ENGINEER_REVIEW, is_verified_ground_truth=0 for all 4
migration .............. f320ab275929
```

These are E2E/software-integration records with `SIMULATED` provenance, not experimental evidence.
Uncertain and sensor-invalid alert creation is covered by automated API tests rather than this E2E
database sample.

## 4. UI evidence

- Alerts & Review is functional for Engineer, Reviewer and Administrator; researchers can read the
  API but do not receive the navigation entry.
- The queue shows category, severity, status, pump/sensor, age, assignment and review count.
- The detail panel shows the immutable prediction decision, data quality, scores, model version,
  signal-window interval, scenario, source IDs and provenance.
- The review panel supports acknowledge, engineering review, label confirmation/correction, note and
  close actions with inline validation and API errors.
- The timeline displays reviewer identity, action, timestamp, notes, reviewed label and the
  "engineer review - not verified ground truth" statement.
- Historical Trends overlays fault, uncertain and sensor-invalid categories only when a persisted
  alert references the displayed signal window.
- No screen presents a decision score as a failure probability or a review as verified field data.

## 5. Deviations and limitations

1. **Synthetic-only evidence.** No physical pump data, verified labels or real-world accuracy exist.
2. **Date filter is API-only.** `created_from`/`created_to` exist on the API; the current UI exposes
   status, category, severity and pump filters, not a date picker.
3. **Assignment is implicit.** Acknowledgement/review assigns the acting reviewer; there is no
   separate assignment endpoint or dismiss action.
4. **No alert notification path.** Alerts are persisted synchronously with prediction ingestion and
   are not emitted over SSE; there are no email/push notifications or background escalation.
5. **Trend scope.** Alert overlays are implemented; date-range filters, model-version markers and
   report/CSV/PDF exports remain later work.
6. **E2E isolation.** The final write-enabled Playwright run used the developer SQLite database and
   created synthetic test rows. Backend tests remain isolated with an in-memory database.
7. **Review semantics.** Engineer-reviewed labels are engineering judgements, not automatically
   verified experimental ground truth; there is no label-promotion workflow.
