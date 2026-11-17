# ADR-0003: Provenance-first schema and orthogonal state dimensions

**Status:** Accepted (Stage 1)

## Context

The highest scientific risks in this project are presenting synthetic results as measured
performance and confusing sensor failures with healthy equipment. A single ambiguous status field
would make both failures easy.

## Decision

- Store `SIMULATED` or `EXPERIMENTAL` provenance on acquisition sessions, signal windows,
  predictions, alerts and model evaluations.
- Keep equipment condition (`NORMAL`, `FAULT`, `UNCERTAIN`), data quality (`VALID`,
  `SENSOR_INVALID`) and connectivity (`ONLINE`, `OFFLINE_BUFFERING`, `SYNCING`, `SYNCED`,
  `SYNC_ERROR`) as independent values.
- Treat `SENSOR_INVALID` as a decision outcome that suppresses condition inference.
- Store engineer reviews append-only with `label_source` and `is_verified_ground_truth=false`.
- Require reports and UI to expose provenance and never mix datasets implicitly.

## Consequences

Positive: defensible traceability, testable invariants, clear UI semantics, reduced risk of false
claims.

Negative: more columns and UI states; report queries must filter provenance explicitly; more tests.

## Enforcement

- Database fields are mandatory where applicable.
- Integration tests assert distinct provenance and immutable predictions.
- Planned UI acceptance requires sensor-invalid suppression and simulated-data labels.
