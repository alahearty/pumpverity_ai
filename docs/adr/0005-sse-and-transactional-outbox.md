# ADR-0005: SSE for monitoring updates and a transactional outbox for sync

**Status:** Accepted; SSE implemented in Stage 3, outbox/sync in Stage 6

## Context

Monitoring updates are primarily server-to-client, while edge→server synchronisation must survive
network loss, retries and restarts without duplicate or lost events.

## Decision

- Use Server-Sent Events for reading/prediction/alert/sensor-health/connectivity updates. The stream
  is authenticated, pump-scoped and includes heartbeat events.
- Stages 3–4 emit `reading`, `sensor_health`, `prediction` and `heartbeat` events and detect new
  persisted rows by polling every ~2 seconds. The stream is therefore durable across API processes
  and does not require an in-memory event bus. Alert/connectivity events arrive in later stages.
- Use a transactional outbox on the edge: the domain write and outbox insert commit together.
- Give each event a durable unique ID, type, source device, occurrence time, payload version,
  payload, delivery status and retry metadata.
- Retry with backoff. Mark `DELIVERED` only after the receiver durably commits.
- Make the receiver idempotent by `event_id`; return accepted/duplicate/rejected outcomes.
- Preserve events across restarts and expose sync status to the UI.

## Consequences

Positive: simple live-update transport, reliable offline capture, safe retries, observable failures.

Negative: SSE has one-way semantics and limited request-header support in native EventSource; event
versioning and idempotency require careful tests; payload growth requires retention/batching.

## Open questions

- Authenticated SSE strategy in the browser (cookie/ticket vs fetch-stream).
- Batch size and backoff parameters on the chosen edge platform.
- Conflict/ordering policy for late-arriving events.
