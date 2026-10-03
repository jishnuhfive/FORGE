# Security architecture

## Implemented now

- The only application endpoint is public liveness. It returns two fixed values
  with a strict response schema, and exposes no configuration or credentials.
- Pydantic validates configuration and redacts sensitive settings with `SecretStr`.
  Empty environment placeholders do not override development defaults.
- Debug tracebacks are disabled. API documentation is disabled in production mode.
- Native development servers and the database bind to loopback. No wildcard CORS
  middleware is enabled. The Vite dev proxy is a local convenience only.
- Secrets, virtual environments, dependencies, generated output, keys, and local
  data are ignored by Git. `.env.example` uses empty placeholders only.
- Startup commands disable API access logs. No user/CAD telemetry exists.
- Lockfiles, strict checks, unit/browser tests, and `make audit` support dependency
  hygiene. Audits are point-in-time checks, not proof of complete security.

Phase 0 has **not** implemented authentication, sessions, CSRF defense, object-level
authorization, token encryption, request/rate/AI usage limits, CSP, audit persistence,
deletion workflows, or production infrastructure. Do not expose this development
setup publicly or claim those controls work. Forge claims no SOC 2 or other certification.

## Secrets and planned OAuth

Use environment variables locally and a production secret manager when deployed.
Never put keys in frontend files, `VITE_*` variables, source control, artifacts,
URLs, logs, or screenshots. The browser receives session identity and authorized
business data only, never Onshape access/refresh tokens or an OpenAI key.

Onshape OAuth2 will be the sole initial sign-in authority. There is no Forge
password database. Exchange authorization codes on the backend. Require one-time,
expiring, cryptographically random state tied to the initiating session, exact
registered redirect URLs, least-privilege scopes, and PKCE if supported by the
verified Onshape flow. Reject replay and ambiguous account linking.

Encrypt tokens at rest using authenticated encryption with managed keys, versioned
ciphertext, rotation, and no plaintext fallback. Coordinate refreshes to avoid token
races. Revoke sessions on logout; disconnect revokes/unlinks credentials where
supported. Define retention, export, deletion, backup expiry, and provider revocation
semantics before enabling real accounts. Test each path.

## Sessions, CSRF, authorization

Use opaque server-side sessions, rotate on authentication, set bounded lifetime and
inactivity expiry, and mark cookies HttpOnly and Secure in production. Avoid access
tokens in browser local/session storage. For cross-site iframe cookies, SameSite=None
requires Secure but may still be blocked by browsers. Evaluate supported top-level
authentication/bootstrap and storage strategies in real Onshape environments; do
not choose a workaround that exposes provider tokens.

Protect all state-changing session endpoints with verified Origin/Referer rules and
CSRF tokens. SameSite alone is insufficient for an embedded application. Read-only
routes must not mutate state. Validate content type, sizes, IDs, units, and numeric
bounds. Check the current user against every referenced object; UUID opacity is
not authorization. Document ownership, session user, target workspace, and operation
permissions must all agree before any write.

## Iframe, messaging, and browser policy

Use HTTPS. Permit framing only by specifically approved Onshape origins in CSP
`frame-ancestors`; don't set conflicting global `X-Frame-Options: DENY` on the
extension document. Restrict scripts, connections, images, and object sources with
an environment-appropriate CSP. Develop a production policy separately from Vite's
development/HMR requirements.

Use same-origin API hosting by default. If separate origins become necessary,
explicitly allow exact frontend origins/methods/headers; never combine wildcard
origins with credentials. Do not treat the Onshape parent origin as the origin of
Forge's API requests. Validate `postMessage` origin, expected source window, schema,
type, size, context, and stale-event handling; send with an exact `targetOrigin`.
Context IDs and selection events are not proof of resource access.

## AI and CAD operation gate

The model receives only allowlisted high-level tools. Never offer arbitrary HTTP,
raw Onshape requests, shell execution, unrestricted code execution, or credentials.
Strict function schemas constrain shape, but server validation still enforces units,
finite numbers, bounds, policy, ownership, approval, and document-version freshness.
Prompt injection in user text or CAD metadata must not change tool permissions.

Each CAD-changing tool must authenticate, authorize, validate schemas and units,
enforce numeric bounds, record sanitized operation events, verify actual results,
and reconcile uncertain writes. Model-generated success is not verification. Apply
per-user quotas, bounded model turns/tool calls/timeouts, provider spend caps,
write budgets, cancellation, and safe retry limits before live execution.

## Logging, errors, and data handling

Use structured allowlisted event fields: event ID, correlation ID, user reference,
operation name, duration, result code, and safely minimized object references.
Never log authorization headers, OAuth tokens, session cookies, API keys, raw prompts,
complete private CAD payloads, or settings objects. Do not persist hidden model
reasoning. User-facing plans, actions, approval decisions, status, and results are
sufficient for auditability. Avoid logging sensitive query strings in proxies.

Return stable public error codes with correlation IDs; keep sanitized diagnostic
details server-side. Define retention and deletion for account records, inventory,
design histories, provider data, telemetry, audit records, and backups. Minimize
data sent to AI providers and review their retention controls before launch.

## Future launch gates

Before multi-user use, test session/CSRF behavior in embedded desktop browsers,
cross-account/object access, token rotation/revocation, message forgery, prompt
injection, stale approvals, numeric edge cases, quotas, provider failure, and
account deletion. Configure bounded request bodies at ingress and application
boundaries, shared rate limiting, safe error handling, encryption key management,
HTTPS, CSP, dependency scanning, container scanning, and restore-tested backups.
Security hardening must accompany each feature, not wait until Phase 17.
