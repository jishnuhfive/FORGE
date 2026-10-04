# Security architecture

## Implemented through Phase 2

Forge uses Onshape OAuth2 only. There are no passwords, JWT login tokens, CAD tools
or AI calls. Authentication establishes an account, not permission to change CAD.

- Strict, secret-redacted backend configuration; production requires complete auth
  configuration, PostgreSQL and HTTPS. Provider URLs are operator-owned HTTPS
  Onshape endpoints with fixed paths. No dynamic browser-selected hosts.
- Ten-minute, 256-bit state bound to a separate HttpOnly browser cookie. Hashed
  database state is atomically consumed before exchange, including failed attempts.
  Duplicate parameters, missing state, mismatches, expiry and replay fail closed.
- Backend-only form code exchange and Bearer identity retrieval. Fixed redirects
  discard sensitive callback queries on success and failure. No browser redirect
  destination is trusted. HTTP redirects from the provider are not followed.
- Minimum identity keyed by provider ID + stack. No email collection or email-based
  merging. An authenticated session exclusively determines account ownership.
- Opaque 256-bit revocable sessions, stored as SHA-256 digests. Rotation on login,
  eight-hour absolute and one-hour idle limits. HttpOnly, host-only, path `/`,
  Secure + `__Host-` on HTTPS. Production forbids insecure cookies.
- Session-bound HMAC CSRF tokens and exact Origin/Referer validation protect all
  account mutations, even with SameSite=None. No wildcard credentialed CORS.
- Refresh tokens encrypted with authenticated Fernet/MultiFernet. Access tokens
  remain in bounded server memory. PostgreSQL locks serialize refresh rotation;
  generation checks invalidate caches across workers and after disconnect.
- Permanent authorization failures remove credentials and require reconnect.
  Transient failures are represented as errors with bounded retry delay, not as
  connected. A check validates the identity behind the token against its owner.
- Fixed audit event/outcome codes. No arbitrary metadata, secrets, authorization
  codes, cookie values, provider payloads or private model reasoning in records.
- Auth responses use no-store, no-referrer and nosniff. Public errors are fixed
  codes/copy. SQL parameters are hidden; API access and HTTP transport logs are
  suppressed. Ingress/APM logging still needs deployment configuration.
- Alembic migrations are explicit and startup checks the schema; no automatic
  table creation/destruction. Destructive migration downgrade is disabled.
- No production mock-auth switch. HTTP transport fixtures exist in backend tests;
  browser interception exists in tests. The UI lab is DEV-only and grants no session.
- `.env`, keys, certificates, caches and artifacts are ignored. `.env.example` uses
  blank placeholders. No secrets are put in `VITE_*` or browser storage. Local
  preferences remain allowlisted; prompts and local CAD previews remain in memory.

See [AUTHENTICATION.md](AUTHENTICATION.md) for flow, failure semantics, key rotation,
logout versus local disconnect, operational retention and local verification.
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md) records the explicit security pass and tests.
Passing tests is not certification or production deployment approval.

## Remaining authentication deployment gates

Real Onshape login/refresh/revocation needs the human-owned application and genuine
credentials. Real embedded browser behavior and enterprise stacks are unverified.
Onshape's documented third-party-cookie requirement is not resolved by merely
setting SameSite=None; top-level/separate-tab authentication is the safe fallback.
No localStorage credentials or weakened CSRF checks are used to bypass restrictions.

Deploy behind HTTPS with exact approved frame ancestors and an appropriate CSP,
private PostgreSQL, least-privilege DB roles, managed secrets and tested backups.
Configure ingress URL/header/body limits and shared login/refresh rate limits,
sanitized metrics, approved retention jobs and account-erasure procedures before
public multi-user deployment. Error handling does not make unrestricted public
exposure safe. These operational controls are not supplied by the local dev server.

Keep old encryption keys until all active grants can be decrypted with the new key.
A crash after provider rotation but before the database commit may require fresh
consent. No local transaction can guarantee rollback of Onshape's external operation.
Disconnect deletes local credentials; users revoke the remote grant in Onshape
My account → Applications. Deletion from backups follows the deployment retention
policy; local deletion is not a claim that every historic backup was erased.

## Future iframe and messaging controls

Use same-origin web/API hosting. For embedding, verify Onshape origin allowlists and
set `frame-ancestors` at hosting; avoid contradictory global frame-denial headers.
If separate API origins become necessary, allow only exact configured origins,
methods and headers. The Onshape parent's origin is not Forge's request origin.

Validate postMessage origin, expected source window, type, size, schema, context and
freshness. Use an exact targetOrigin. Browser document/workspace/selection IDs never
establish object authorization. Phase 2 installs no message listeners.

## Future AI and CAD operation gate

The model receives only allowlisted high-level tools. Never offer arbitrary HTTP,
raw Onshape requests, shell execution, unrestricted code execution, or credentials.
Strict function schemas constrain shape, but server validation must also enforce
units, finite numbers, bounds, ownership, approval and document-version freshness.
Prompt injection in text/CAD metadata cannot alter tool permissions.

Each CAD-changing operation must authenticate, authorize the exact object, validate
schemas/units/bounds, bind approval to the specific plan/version, log sanitized
public actions and verify the result. Reconcile uncertain writes before retrying.
Keep deterministic PASS, WARNING, FAIL and UNVERIFIED separate from model judgment.
Apply quotas and bounded model turns, calls, timeouts, spend and cancellation.
Never persist private chain-of-thought. No engineering certification is claimed.
