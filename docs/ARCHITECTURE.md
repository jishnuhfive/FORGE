# Architecture

## Current implementation — Phase 5 inspector live verified

One React/TypeScript/Vite web client, one FastAPI/Pydantic API and shared presentation
primitives serve desktop browsers. Native clients are not part of Forge.

The Phase 1 Design/Modify/Learn shell remains, now behind an Onshape sign-in gate.
The development UI lab is independent of authentication and remains excluded from
production builds. Engineering workflows remain local or explicitly synthetic.
Phase 4 established four backend CAD REST reads. Phase 5 projects their snapshot
into a bounded CAD Inspector; the compact proof API remains available. No AI or CAD
writes are implemented. The extension launch bridge sends
applicationInit, handles documented show messages and normalizes bounded single
FACE/EDGE or clear SELECTION envelopes matching the human's live sanitized captures.

FastAPI owns OAuth code exchange, identity, revocable opaque sessions, encrypted
refresh tokens and CSRF. SQLAlchemy models and Alembic migrations use PostgreSQL.
Browser status calls receive minimized identity, connection status and CSRF data.
No provider credentials cross into the browser. See [AUTHENTICATION.md](AUTHENTICATION.md)
for the sequence, model contracts, cache/refresh tradeoffs and lifecycle semantics.

`GET /health` still means liveness only. Database schema checks run at startup when
DATABASE_URL is supplied. Without credentials the app starts and reports sign-in
unconfigured. Production fails closed on incomplete auth settings. Tests inject
HTTP transports; no runtime setting enables mock sessions.

## Intended component responsibilities

| Component        | Responsibility                                                                                      | Current state                                           |
| ---------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Frontend         | Narrow-panel UI, accessible controls, typed API calls, approved plan presentation                   | Authenticated local UI + DEV fixtures                   |
| API              | Configuration, sessions, authorization, validated contracts, orchestration                          | OAuth, sessions, CSRF, liveness and read snapshots      |
| Database         | Users linked to Onshape identity, encrypted token records, sessions, plans, inventory, audit events | Identity, grants, sessions, states and audit migrations |
| AI layer         | Responses API, bounded agent loop, allowlisted functions, streamed user-facing status               | Documentation only                                      |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | OAuth, identity and four allowlisted CAD reads          |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Documentation only                                      |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | Documentation only                                      |

Backend `auth/` owns identity/security and `db/` owns persistence. `integrations/`
and `validation/` reserve the future CAD/AI and deterministic validation boundaries.
No authentication helper is exposed as a model tool.

## Planned flow and trust boundaries

```text
Onshape parent frame -> origin/schema-checked browser messaging -> Forge web UI
Forge web UI -> authenticated same-origin API -> scoped orchestration
orchestration -> Responses API -> proposed allowlisted tool calls
tool gate -> authorization + approved plan + validated arguments -> Onshape adapter
Onshape adapter -> official REST API -> reinspection -> deterministic validator
API -> minimized PostgreSQL records + sanitized audit events
```

Every arrow crosses an explicit boundary. Browser document/element IDs, selections,
text prompts, CAD metadata, and model output are untrusted inputs. Origin validation
does not establish authorization; the API must independently verify that the
current session may access the exact Onshape resource. Model arguments are requests
for an operation, never evidence of permission or correctness.

Approval must identify the user, target document/workspace/element, immutable plan,
units, operations, and inspected version. Reinspect stale context before executing.
Do not blindly repeat timed-out writes; reconcile the resulting CAD state first.
Keep units and bounds explicit, and treat missing evidence as UNVERIFIED.

## Development decisions

- **npm workspaces:** Node already includes npm. A second package manager or a
  monorepo orchestration framework would add no value for two small workspaces.
- **One uv project:** Python dependencies/lockfile/environment live in `apps/api`.
  Adding a Python workspace is unnecessary until there are multiple Python packages.
- **Native web/API, containerized database:** faster reloads and fewer Dockerfiles.
  Production images are deferred to the deployment phase.
- **Source-exported design system:** Vite compiles the local TypeScript package;
  it is private and not published. It exports semantic tokens, component styles
  and reusable accessible primitives backed by Radix where appropriate.
- **Small local UI state:** React hooks and a hash subscription own Phase 1 UI
  state. No router, global-state framework, motion library or AI SDK was added.
  Five small Radix packages provide focus management, keyboard behavior and
  notifications. The development-only lazy import is eliminated by production
  compilation, including its synthetic fixture module.
- **PostgreSQL 18:** pinned release image, persistent volume mounted at the supported
  parent path, a real health check, and host access limited to loopback.
- **Health is liveness:** database readiness and external-service checks need a
  separate future contract. Returning `ok` does not validate integrations.

This follows the requested layout. Additional configuration, lockfiles, and a
development supervisor support reproducibility; no substantive structural deviation
or alternate framework was introduced.

## Planned deployment

Serve the built SPA and `/api` through one HTTPS origin, with the API and managed
PostgreSQL on private networks. A same-origin proxy avoids permissive CORS. A worker
may become appropriate for long-running operations, but is not part of Phases 0–2.
Use production secret management, encryption key rotation, backups, migration
review, request/rate/usage limits, sanitized telemetry, and deployment gates.

Set the extension's `frame-ancestors` allowlist at the hosting layer after verifying
registered Onshape environments. Browser third-party-cookie restrictions require
real embedded-session testing. Do not assume an iframe works because the standalone
UI renders. [SECURITY.md](SECURITY.md) records the required controls;
[ONSHAPE.md](ONSHAPE.md) records integration verification gates.

## Phase 2 deployment decisions

- Vite proxies `/auth` and `/api` unchanged to FastAPI; the historical `/api/health`
  liveness proxy is retained. Production hosting must make the same paths available.
- Standard-library primitives provide randomness, hashing and HMAC. cryptography
  provides authenticated encryption; Alembic provides migrations. The existing
  httpx2 transport dependency is now a runtime dependency. No framework change.
- Access tokens remain ephemeral; refresh tokens are encrypted in PostgreSQL.
  Per-grant row locks coordinate workers. A cache miss can add one refresh per
  worker, trading modest provider traffic for less persisted sensitive data.
- Identity includes its configured Onshape stack; company context is operator-owned.
  Multi-stack routing and live enterprise validation remain future work.
- The human reports real OAuth login and genuine right-panel embedding with an
  authenticated display name and launch context verified. Live FACE/EDGE/clear
  structures match the tested adapter; the corrected FACE capture resolves the
  final Phase 3 evidence blocker. Browser-wide iframe compatibility remains limited.

## Phase 3 launch bridge

The existing bundle serves `/extension` and standalone `/`. `onshape/context.ts`
normalizes bounded launch parameters; `policy.ts` owns exact origins and Vite frame
headers; `bridge.ts` owns message/source validation and initialization; the provider
exposes an in-memory React store. The browser never selects a backend API host.
CAD Context consumes normalized context even when embedded AuthGate cannot
see a session. The DEV simulator is a separate lazy component eliminated at build.
No backend production behavior, schema, provider request or dependency changed.

Document/element switches use Action URL navigation and a fresh bridge, not invented
context-change messages. `selection.ts` validates the captured envelope and requested
FACE/EDGE categories; it discards unknown fields and stores only an opaque reference
and normalized type. Malformed trusted selections clear old references. Actual
navigation/bfcache suspension requires a fresh frame; show cannot revive it.
Ordinary browser visibility/focus and show preserve the current launch and selection.
Before any future CAD API exists,
derive the user from the session and independently authorize each object through
that user's server-held grant. Frontend context is never proof of access.

For live schema discovery, `onshape/dev/` provides an explicitly enabled diagnostic.
After the existing bridge validates parent/origin, an in-memory observer projects a
SELECTION envelope to bounded types, fixed field/category labels and redacted values.
It never populates the CAD store. The provider lazy-loads its panel outside AuthGate
so a missing iframe session does not prevent capture. Production eliminates these
modules; there is no alternate origin, backend endpoint or storage path.

The Design composer now reads this same normalized store; its former missing-prop
fallback incorrectly said “No CAD context” even with a valid workspace launch.
Only workspace revisions send applicationInit. Explicit versions remain represented
as versions and show unverified messaging instead of being sent as workspaceId.

`onshape/dev/LaunchDiagnostic` is a separate read-only DEV panel outside AuthGate,
including invalid launch states. It uses the existing parser's status and a tested
field-rule mirror to project only sanitized metadata from the current query on an
explicit click. It adds no message listener or context mutation. Production removes
it; the launch parser and trusted-parent boundary are unchanged.

The real launch capture identified three unused ancillary fields as compatibility
failures. `clientId`, `sessionCompanyId` and `theme` now share a bounded opaque-string
validator and are discarded; they are never part of OnshapeClientContext. The launch
diagnostic shares that rule. Required CAD references, origin trust and revision
semantics are unchanged; no provider-specific client-ID syntax is assumed.

## Phase 4 REST read boundary

`integrations/onshape/` owns the versioned GET allowlist, exact standard-stack
origin, workspace-reference validation, bounded transport, provider models,
normalization, snapshot service and minimized API route. Synchronous HTTP fits
Phase 2's synchronous SQLAlchemy/token manager; FastAPI executes the route in its
worker thread pool. A separate pooled transport has bounded timeouts and no redirects.
No dependencies, migrations or authentication redesign were introduced.

The flow is session → user-owned TokenManager → four allowlisted GETs → strict
provider projection → independent Forge summaries → count/status proof response.
Unknown fields remain in bounded request-local server memory. No private CAD cache
or persistence exists. Source microversions and provider API/schema metadata stay
inside the snapshot; the browser receives completion time and mismatch/unverified
consistency. Separate workspace reads never claim atomicity.

GET `/api/onshape/part-studio/snapshot` requires the existing session CSRF token
as a quota-protection header. A bounded per-user process-local gate limits duplicate
reads and cooldowns. Context/account changes and actual navigation invalidate
frontend results; ordinary tab visibility/focus preserves them.
The dev-only diagnostic is lazy-loaded and absent from production assets.
For unresolved mass normalization failures, a development-only callback produces
bounded structure metadata in a response header after ownership is
rechecked. Production does not enable or import this builder. The normal JSON
proof contract is unchanged; DEV alone validates and displays the header through
a lazily imported fixed-vocabulary module. No new read operation is introduced.
The final live capture proves nominal zero, negative lower tolerance, positive
upper tolerance and unavailable assigned mass. Present mass/volume/periphery
(surface area) estimates now require exactly three finite numbers, nonnegative
nominal and `lower <= nominal <= upper`. Tolerance limits may cross zero; unrelated
vector/matrix handling is unchanged. A false `hasMass` suppresses the normalized
mass estimate while preserving volume and the missing count. Partial assigned
mass with a positive missing count yields unverified proof availability.
Field validators identify errors directly, so DEV no longer replays validation
or recomputes failing predicates. It reports fixed field error codes plus pairwise
`greater` / `equal` / `less` comparisons from the failed scalar, with no operands.
`normalize_provider_scalar_estimate` explicitly maps the verified v17
`[nominal, lower, upper]` ordering. Periphery is validated as a scalar surface area
but is not a new summary; axes remain in the bounded request-local provider record.
DEV additionally reports authorized mass sign categories, the strict `hasMass`
boolean, and a zero/positive missing-count category from the first failed mass
record. The minimized proof contract is unchanged. The normal false-availability
message says mass is unavailable and material/density may be missing. The user
verified all four real reads, valid unavailable mass, and clearing of the previous
2/1/1 snapshot when a separate empty Part Studio returned 0/0/0. These are reported
live observations; automated fixtures do not substitute for them. No broader live
browser, configuration, geometry or atomic-snapshot claim is made.
See [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md) for contracts, limits and live verification.

## Phase 5 inspector projection

One explicit Refresh CAD action invokes GET `/api/onshape/part-studio/inspector`.
The shared `acquire` function retains the exact Phase 4 session, CSRF/origin,
reference-validation, quota gate, transport and final ownership checks. It captures
once and projects twice: compact `source` proof plus bounded Forge evidence.
The existing `/snapshot` endpoint retains `forge-cad-read-v1` unchanged and shares
the same gate. The UI never fetches both endpoints for one inspection.

`parameters.py` dispatches only exact reviewed provider classes; `normalize.py`
puts their typed summaries into the existing internal feature records.
`inspector.py` consumes normalized records only, never `ProviderDocument.raw`.
Its `forge-cad-inspector-v1` model separates source statuses, context semantics,
freshness, completeness, ordered features, parts, bodies and physical availability.
The future Phase 6 consumer can use this structure without scraping React; no AI
consumer, prompts or tools are implemented now.

The frontend strictly validates the response before mounting `InspectorView`.
Native details/summary controls, labels, local feature/part filters and wrapped
content fit the panel. Phase 3 selection remains a separate memory-only observation:
no feature/part/body ownership is inferred. Account/context keys remount the reader;
actual page navigation aborts and clears it. Same-frame visibility/focus changes
preserve capture metadata and cause no CAD reads. Nothing persists the evidence.
Names and values are untrusted display text. Exact limits and semantics are in
[PHASE_5_REVIEW.md](PHASE_5_REVIEW.md). Assemblies remain Phase 10.

The 2026-10-14 topology repair preserves optionality and treats empty export arrays
as unknown: the fixed `includeGeometricData=false` contract does not establish
authoritative emptiness. Nonempty arrays produce returned-entry counts; empty,
missing and null arrays remain null through the inspector and render Unknown.
DEV alone supplies a first-body structure callback to the existing transport.
After successful normalization and the final ownership check, a separate bounded
header carries only the three fixed topology fields' presence/type/length. It
creates no read, geometry payload, cache or persistence path. Production neither
installs the callback nor includes its frontend parser and UI.

Phase 5 browser lifecycle repair removes document-hidden handlers from both the
provider and reader. The reader remount key explicitly includes document, revision
kind/ID, element, provider origin, optional microversion and session CSRF identity.
The bridge preserves verified selection on show, ignores wrong origin/window, and
fails closed on supplied context IDs that mismatch its launch. Malformed trusted
selection clears old inspection and selection; a valid update enables explicit
reading again. Authentication focus checks remain `/api/me` only. They keep results
for an unchanged session and clear them on logout, disconnect/revoke or session
rotation. Panel iframe destruction still starts entirely fresh on reopen.

Final Phase 5 human verification passed on 2026-10-14: ordered Sketch/Extrude,
supported/caveated parameters, safe part metadata, 6 faces with unknown edges/vertices,
missing-mass and reported-volume evidence without numeric units, FACE/EDGE/clear,
local filtering, same-frame Chrome tab preservation, and empty Part Studio 0/0/0
with prior evidence cleared. This verifies observed read-only behavior, not selection
ownership, complete CAD semantics, atomic consistency or engineering certification.
The architecture/security boundaries above and production-excluded diagnostics remain.
