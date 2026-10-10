# Security architecture

## Implemented through Phase 2, with Phase 3 launch boundary

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

The human has verified real Onshape login. Additional refresh/revocation evidence
remains governed by the Phase 2 procedure. The human verified one real embedded session; browser-wide compatibility and enterprise stacks remain unverified.
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

## Phase 3 iframe and messaging controls

Use same-origin web/API hosting. For embedding, verify Onshape origin allowlists and
set `frame-ancestors` at hosting; avoid contradictory global frame-denial headers.
If separate API origins become necessary, allow only exact configured origins,
methods and headers. The Onshape parent's origin is not Forge's request origin.

Validate postMessage origin, expected source window, type, size, schema, context and
freshness. Use an exact targetOrigin. Browser document/workspace/selection IDs never
establish object authorization. Phase 3 uses one dedicated listener with an exact
operator-owned origin and parent-window source check. The live selection adapter
accepts only bounded single FACE/EDGE ENTITY references or explicit empty arrays.
Unknown fields are discarded, malformed trusted selections remove stale references,
and lifecycle invalidation prevents delayed messages from reviving them. Selection
references are memory-only and never rendered; they are not authorization. An opt-in DEV-only
observer behind the same origin/source checks can inspect structure without accepting
it as CAD state. It emits only fixed labels/types/capped counts; ID/name/URL values
and unknown property names are redacted, and secret-labelled subtrees suppressed.
Raw payloads are never retained, logged, stored or sent to the backend. Traversal,
output and capture frequency are bounded; browser cloning before delivery is outside
those bounds. Copy requires an explicit click and copies sanitized text only. The
production build removes this path. See [ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md).

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

Phase 3 dev/preview HTML responses restrict frame ancestors to the standard Onshape
origin and suppress referrers. Production ingress must replicate those headers;
Vite build output alone does not configure an ingress. No enterprise wildcard is
accepted. Missing/unapproved server, URL credentials and malformed IDs fail closed.
Untrusted messages cannot change CAD context or selection, and no raw payload/query
is logged or persisted. An unavailable in-frame session keeps the auth gate closed.
CSRF, cookies, token encryption and account ownership controls remain unchanged.

Workspace-style launch queries remain subject to the same ID validation and exact
server/parent checks. Version IDs are never remapped into workspaceId for outgoing
initialization. A workspaceId field alone does not identify a mislabelled version;
the current registration is verified only for workspace use, not version viewing.
The context-label repair changes no OAuth/session/CSRF or diagnostic controls.

The opt-in DEV launch diagnostic exposes only field names, presence/types/lengths,
validation/reason codes and an approved normalized server origin. All query values,
including default personal metadata and secrets, stay out of the report. Suspicious
parameter names and unapproved hosts are redacted. The diagnostic is local inspection
of untrusted launch input, not authorization: it can appear for invalid context while
the bridge remains closed. No raw logging, storage, upload or parser change is added.

After the real sanitized capture, exactly `sessionCompanyId` and `theme` were added
to the accepted ancillary names. These and `clientId` are validated as nonempty
strings up to 128 characters without C0/DEL controls, then discarded. A speculative
client-ID character class was removed because that value is opaque and unused.
Unknown names, credentials in query parameters, duplicate fields, invalid CAD IDs
and untrusted origins still fail closed. Metadata cannot select a company, change
theme, authenticate a user or widen a postMessage/backend destination.
