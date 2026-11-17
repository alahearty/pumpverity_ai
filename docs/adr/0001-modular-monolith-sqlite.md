# ADR-0001: Modular monolith API with SQLite-first persistence

**Status:** Accepted (Stage 1)

## Context

The prototype must support one laboratory pump, a small research team, offline operation and a
six-month delivery. Microservices, Kubernetes and cloud infrastructure would add operational cost
without validating the research question.

## Decision

- Use one FastAPI application with explicit internal modules (`api`, `domain`, `services`,
  `repositories`, `db`).
- Use SQLite with WAL and foreign keys enabled for local persistence and the edge prototype.
- Keep SQLAlchemy models portable so PostgreSQL can replace SQLite centrally later.
- Provide Docker Compose for local development, not production orchestration.
- Keep the edge pipeline as a separate package so inference does not depend on the API process.

## Consequences

Positive: simple deployment, transactional consistency, easy test isolation, offline-friendly,
appropriate for a research team.

Negative: SQLite write concurrency and high-frequency ingestion limits; single-process operational
model; PostgreSQL migration and edge concurrency work remain for later stages.

## Guardrails

- Session and waveform storage are bounded.
- Raw high-frequency data is separated from scalar readings.
- Migration-managed schema (Alembic), no `create_all` in production startup.
