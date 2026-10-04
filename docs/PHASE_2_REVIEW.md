# Phase 2 implementation and security review

Review date: 2026-10-04. Scope: Onshape OAuth2 identity and account lifecycle only.

**PASS WITH EXTERNAL SETUP REQUIRED** — implementation and automated checks pass;
real OAuth requires human-owned Onshape credentials and registration. No real OAuth,
enterprise account, iframe embedding, CAD API or OpenAI integration was exercised.
No production readiness or third-party certification is claimed. Phase 3 has not begun.

## Delivered architecture and routes

FastAPI handles code exchange, fixed identity retrieval and CSRF-protected account
mutations. PostgreSQL holds minimized identity, encrypted refresh tokens, opaque
session digests, one-use OAuth states and safe audit records. Access tokens remain
in bounded server memory. React receives account status and an in-memory CSRF token.

| Route                        | Result                                                           |
| ---------------------------- | ---------------------------------------------------------------- |
| GET /auth/onshape/start      | Browser-bound state and top-level Onshape redirect               |
| GET /auth/onshape/callback   | One-use state validation, backend exchange/identity, new session |
| GET /api/me                  | Minimal identity, configuration/connection state and CSRF token  |
| POST /auth/logout            | Revoke current session and clear its cookie                      |
| POST /api/onshape/disconnect | Delete local delegated credentials; retain Forge session         |
| POST /api/onshape/check      | Explicit, CSRF-protected identity/authorization verification     |

Alembic `0001_authentication` creates users, onshape_authorizations, sessions,
user_preferences, oauth_states and audit_events. Preferences are a foundation only;
existing UI theme/units remain browser-local. No schema reset or destructive downgrade.

## Verification evidence

| Check                               | Result                                                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Frozen dependency installation      | npm ci and uv sync --locked passed                                                                        |
| make format / make lint             | Prettier, ESLint and Ruff passed                                                                          |
| make typecheck                      | Strict TypeScript and mypy, including migrations/scripts, passed                                          |
| Frontend unit/component tests       | 63 passed, including the existing 45 Phase 1 tests                                                        |
| Backend default suite               | 90 passed; 3 opt-in PostgreSQL tests excluded by default                                                  |
| Explicit real PostgreSQL suite      | All 3 passed; fresh/repeat migration, no drift, one state winner, four independent rotating-token workers |
| Playwright                          | 156 passed across Chromium, Firefox and WebKit, including the existing 132 regression cases               |
| make build                          | Production build passed; development lab/fixtures excluded                                                |
| make compose-check                  | Passed; actual PostgreSQL 18.6 container became healthy                                                   |
| make migrate / make migration-check | Applied additive local schema; no new upgrade operations detected                                         |
| make smoke                          | Real native web/API startup, liveness proxy and clean shutdown passed                                     |
| make audit                          | npm and pip-audit reported no known vulnerabilities                                                       |
| make check                          | Aggregate lint, types, tests, build and Compose validation passed                                         |

Screenshots of the 320 px light/dark sign-in screen were visually reviewed in addition
to axe and overflow checks. The 320/380/480/1280 px workspace regressions still cover
Design, Modify, Learn, settings, history, dialog focus, reduced motion and themes.
Browser OAuth tests use explicit interception/synthetic consent; backend tests
exercise actual routes, redirects, persistence and HTTP transport contracts.
These fixtures do not count as a real-provider or iframe compatibility test.

The initial cryptography constraint selected an older release with audit advisories.
The lockfile now uses 50.0.2; audits and cryptography/authentication tests passed after
upgrading. See the [upstream changelog](https://cryptography.io/en/latest/changelog/).

## Explicit security pass

| Area             | Finding and disposition                                                                                                                                                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OAuth state      | Independent 256-bit state/binding, digests, ten-minute TTL, conditional atomic consumption. Missing/unknown/expired/replayed/mismatched/duplicate callbacks are rejected. PostgreSQL race tested.                                               |
| Redirects        | Only configured exact Forge callback and fixed post-login destinations. Untrusted return parameters rejected. Provider redirects not followed.                                                                                                  |
| Exposure         | Backend-only credentials; no raw token/profile forwarding. No access tokens persisted. Callback query cleared through redirect and no-referrer/no-store response.                                                                               |
| Encryption       | Reviewed Fernet/MultiFernet, explicit format version, key ring and safe corrupt-ciphertext transition. No plaintext fallback.                                                                                                                   |
| Cookies/fixation | Fresh random session on each successful login; previous initiating session revoked. Host-only HttpOnly cookies, Secure + __Host on HTTPS; bounded idle/absolute expiry.                                                                         |
| CSRF             | Exact Origin/Referer plus session-bound HMAC. Null/absent/foreign/malformed origins, wrong session tokens and invalid bodies fail closed. SameSite=None never bypasses checks.                                                                  |
| Ownership        | Account routes derive user exclusively from session; no browser target IDs. Cross-account mutation, identity mismatch and operator stack/company-change tests pass. CAD object authorization remains unimplemented because no CAD routes exist. |
| Refresh          | Row locks, atomic replacement and generation invalidation. Four independent PostgreSQL workers retained the latest rotating token. Revoked/corrupt grants cannot return cached access.                                                          |
| Errors/logging   | Fixed public error codes; no exception interpolation; hidden DB parameters, suppressed HTTP/access logs. Tests exclude secret, code, access/refresh token, cookie and encryption key from logs/public errors/audit.                             |
| Fixtures/secrets | Test-only transports and browser intercepts. No mock env toggle or production mock route. No actual .env/credentials generated. Key helper refuses overwrite and prints no key.                                                                 |
| UI regression    | Session-status outages preserve local drafts. Stale status responses cannot restore UI identity after confirmed logout. Account IDs are not displayed.                                                                                          |

## Limits requiring external verification or deployment work

- Real Onshape registration, consent, profile response, token rotation and revocation
  remain UNVERIFIED. Use [AUTHENTICATION.md](AUTHENTICATION.md), including denial,
  API-restart refresh, logout, disconnect and remote-revoke steps.
- Disconnect proves local removal only. Users revoke remotely through Onshape
  Applications settings. No undocumented revocation endpoint was invented.
- Connected means last verified. Explicit checks discover later remote revocation;
  there is no background provider polling or simulated continuous readiness.
- Enterprise/company association and actual embedded third-party-cookie behavior
  remain unverified. One configured provider stack per deployment is supported.
- PostgreSQL/provider operations cannot form one atomic transaction. A crash after
  external rotation but before commit may require reauthorization.
- Bulk key re-encryption, scheduled retention, self-service account deletion, shared
  rate limiting, ingress policy, secret-manager deployment and production backup/
  restore controls remain documented operational launch requirements.
- Backend development was verified on Apple Silicon macOS. Browser engines passed
  locally; no Windows host or Intel Mac backend was tested.

## Git and handoff

Phase 0 `2b68754` and Phase 1 `31f545a` remain unchanged ancestors. Phase 2 is committed
as `feat: add secure Onshape OAuth authentication` after verification. Nothing is pushed.
Local PostgreSQL and test/dev servers started for verification are stopped, retaining
the database volume. No real local environment file was created.

Human next steps: register the OAuth app, privately populate the ignored environment,
trust the local HTTPS certificate, migrate/start Forge and run the manual smoke
procedure. See [ONSHAPE.md](ONSHAPE.md) for exact current registration fields and
[AUTHENTICATION.md](AUTHENTICATION.md) for commands. No Phase 3 work is authorized.
