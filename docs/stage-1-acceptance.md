# Stage 1 acceptance evidence

**Date:** 2026-11-16
**Environment:** Windows 11, PowerShell 5.1, Python 3.13.13, Node.js 24.22.2, npm 11.19.1,
Google Chrome (Playwright channel), SQLite local file, Docker CLI 29.2.1 (daemon unavailable)
**API dependency versions observed:** FastAPI 0.163.1, SQLAlchemy 2.1.8, Alembic 1.20.1
**Web dependency versions observed:** React 19.3.1, Vite 8.3.8, TypeScript 7.0.2,
Vitest 5.1.0, Playwright 1.65.1

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Repository and documentation structure describe architecture, schema, routes, contracts, security and testing | **Met** | `docs/`, `README.md`, ADRs, screen specifications, API/security/testing documents |
| 2 | `alembic upgrade head` creates the complete initial schema on an empty SQLite database | **Met** | Migration `45fcb5e34b91` applied; 17 tables created |
| 3 | Seeded administrator, engineer, researcher and reviewer accounts can authenticate | **Met** | `python -m app.db.seed`; login tested by HTTP and Playwright |
| 4 | Invalid credentials return a generic error, are audited, and do not reveal account existence | **Met** | `test_invalid_credentials_are_generic_and_audited`, `test_unknown_account_returns_same_error` |
| 5 | Short-lived access token, HttpOnly refresh cookie, logout and reload restore | **Met** | Auth tests plus Playwright reload test; cookie flags asserted |
| 6 | Deactivated users and revoked token versions are rejected | **Met** | `test_inactive_user_cannot_login`, `test_token_version_revocation_invalidates_existing_access_token` |
| 7 | Backend role checks reject non-administrators from the user list | **Met** | `test_engineer_cannot_list_users`; API returns 403 |
| 8 | Authentication events are recorded in the audit log | **Met** | Failed-login audit test; success/logout audit paths implemented |
| 9 | API errors follow the documented envelope and include a request ID | **Met** | Error handler tests; `X-Request-ID` asserted |
| 10 | Web application builds, lints and passes component tests | **Met** | 19 tests passed, 0 lint errors, production build passed |
| 11 | Login, protected routing, logout and role-aware navigation are covered by frontend tests | **Met** | Login form, route guard, navigation and Playwright tests |
| 12 | All 12 screen routes are navigable and planned scope is clear; no fabricated status values | **Met** | Playwright visits all 12 screens; planned-scope banners and empty states |
| 13 | Docker Compose configuration is valid and CI definitions exist | **Partially met** | `docker compose config --quiet` passed; images were not built because the Docker daemon was unavailable; `.github/workflows/ci.yml` present |
| 14 | Known limitations and verification evidence recorded | **Met** | This document, README, testing strategy |

## 2. Executed verification

```text
scripts/verify.ps1
  API ruff check .................... All checks passed
  API pytest ........................ 27 passed, 1 warning
  Web oxlint ........................ 0 errors, 3 warnings
  Web vitest ........................ 19 passed
  Web tsc + vite build .............. passed (chunk-size warning)

npm run test:e2e --workspace @petrosense/web
  Playwright ........................ 4 passed

docker compose config --quiet ....... valid
```

HTTP smoke check:

```text
POST /api/v1/auth/login ............. 200, ADMINISTRATOR
GET  /api/v1/auth/me ................ 200
GET  /api/v1/health ................. 200, database ok
GET  http://127.0.0.1:5173/login .... 200
```

Playwright coverage:

1. Anonymous `/dashboard` redirects to `/login`.
2. Invalid credentials show the generic error and remain on login.
3. Administrator signs in, visits all twelve screens, sees the seeded account list, signs out.
4. A page reload restores the session from the HttpOnly refresh cookie.

## 3. Deviations and known issues

1. **Docker images were not built.** Docker CLI and Compose are installed, but the Docker Desktop
   Linux engine was not running. Compose configuration validates. A CI or local daemon-enabled build
   should be run before declaring the container path verified.
2. **E2E is not in CI yet.** The Playwright suite runs locally against the API and Vite dev server.
   Adding a seeded-stack E2E job is scheduled before Stage 8 acceptance.
3. **Seeded email addresses use `.local`.** Pydantic `EmailStr` rejects this special-use domain, so
   `UserPublic.email` is a bounded string. Account-creation validation in Stage 7 should use a
   deliberate policy for laboratory/local domains rather than a generic public-email validator.
4. **Test warning:** current FastAPI/Starlette emits a deprecation warning suggesting `httpx2` for
   `TestClient`. Tests pass; dependency review is deferred.
5. **Frontend lint warnings:** three `react/only-export-components` fast-refresh warnings for shared
   variant exports and the auth hook. They are not correctness failures; splitting those exports is
   optional cleanup.
6. **Bundle size warning:** the production JS bundle is approximately 539 kB minified (165 kB gzip).
   Route-level code splitting is a later optimisation.
7. **Dashboard build-status list is static project evidence**, not live monitoring data. The test
   counts in that list were updated to match this acceptance run. It must not be interpreted as an
   operational metric.
8. **User management is read-only** in Stage 1. Create, edit, deactivate and credential reset are
   Stage 7 scope; the backend already rejects non-administrator access.

## 4. Scientific integrity check

- No live measurements, accuracy figures or hardware results are displayed.
- Simulated provenance is labelled on the dashboard and planned monitoring surfaces.
- Sensor-invalid status is distinct from equipment condition in the design system and data model.
- The interface explicitly states that the system is not certified for industrial safety or
  autonomous shutdown.
- Model evaluation is displayed as "Not yet evaluated" because no evaluation exists.

## 5. Entry criteria for Stage 2

- Stage 1 API, web and E2E checks remain green after the Stage 2 schema/API additions.
- Pump and sensor registration contracts are added with migration and integration tests.
- The simulated adapter produces deterministic, provenance-tagged sessions.
- A sensor-invalid path is implemented and tested before any condition inference is exposed.
- Documentation is updated with the acquisition adapter contract and new endpoints.
