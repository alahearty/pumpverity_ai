# ADR-0002: In-memory access token with HttpOnly refresh cookie

**Status:** Accepted (Stage 1)

## Context

The monitoring SPA needs a restorable secure session without embedding credentials or keeping
long-lived bearer tokens in persistent browser storage. The prototype runs on a local server.

## Decision

- Hash passwords with Argon2 (`pwdlib`).
- Issue a short-lived JWT access token (default 15 minutes) returned in the login response and kept
  in JavaScript memory only.
- Issue a longer refresh JWT (default 7 days) as an HttpOnly, SameSite=Lax cookie scoped to
  `/api/v1/auth`; rotate it on refresh.
- Check `token_version` on every authenticated request so credential resets/revocation invalidate
  outstanding tokens.
- Enforce role checks in the API through dependency injection.

## Consequences

Positive: access token is unavailable to persistent browser storage; reload restore works; logout
and global revocation are simple; the frontend has no secrets.

Negative: stateless refresh tokens cannot be revoked per device; a page reload requires a refresh
round-trip; CSRF/cookie rules must be revisited when cookie-authenticated state-changing domain
endpoints are added.

## Follow-ups

- Add rate limiting and lockout before network exposure.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Evaluate per-device refresh-session records if multi-device use becomes important.
