# Architecture

## Current implementation — Phase 7 learning foundation, human acceptance passed

One React/TypeScript/Vite web client, one FastAPI/Pydantic API and shared presentation
primitives serve desktop browsers. Native clients are not part of Forge.

The Phase 1 Design/Modify/Learn shell remains, now behind an Onshape sign-in gate.
The development UI lab is independent of authentication and remains excluded from
production builds. Build/validation previews remain explicitly synthetic; Phase 6
analysis uses real backend services only after an explicit send.
Phase 4 established four backend CAD REST reads. Phase 5 projects their snapshot
into a bounded CAD Inspector; the compact proof API remains available. Phase 6 adds read-only AI through a provider-independent interface (default Groq; optional OpenAI). CAD writes remain unimplemented. The extension launch bridge sends
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
| AI layer         | Provider adapters, bounded agent loop, allowlisted functions, streamed user-facing status           | Phase 6 backend adapter and read-only agent             |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | OAuth, identity and four allowlisted CAD reads          |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Documentation only                                      |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | One Phase 6 read-only inspection tool                   |

Backend `auth/` owns identity/security and `db/` owns persistence. `integrations/`
and `validation/` own the provider-adapter and planned deterministic validation boundaries.
No authentication helper is exposed as a model tool. `ai/` owns Phase 6 orchestration.

## Planned flow and trust boundaries

```text
Onshape parent frame -> origin/schema-checked browser messaging -> Forge web UI
Forge web UI -> authenticated same-origin API -> scoped orchestration
orchestration -> AiProvider -> Groq Chat (default) / OpenAI Responses (optional)
provider tool proposal -> fixed allowlisted tool gate
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

## Phase 6 read-only AI boundary

Design's explicit send uses authenticated same-origin POST `/api/ai/ask`. A bounded
server agent handles read questions with two stateless provider requests around one no-argument
`inspect_current_cad` call. The tool invokes the existing session-owned Phase 4
capture and Phase 5 inspector; no provider operation or authorization is added.
`acquire_bound` centralizes this reuse and final session/grant validation.
The model receives minimized inspector evidence and normalized selection, with no
CAD target, provider host, session/user ID, geometry or credential. A strict final
schema selects server-owned fact statements/statuses; suggestions remain unverified.

`ai/provider.py` defines the provider-neutral protocol; `ai/providers.py` selects
exactly one adapter from server configuration. Groq Chat (`ai/groq.py`) is the
default with `openai/gpt-oss-120b` and low effort. The retained OpenAI Responses
adapter (`ai/adapter.py`) is optional with `gpt-6.1-sol` and high effort. The agent
owns policy, grounding and CAD authorization; adapters own API translation and
request-local continuation. Shared `ai/transport.py` uses existing httpx2, fixed
endpoints, bounded responses, safe errors and no retries. No SDK, competing HTTP
stack or database migration is required. Neither selected provider requires the
other key, and there is no automatic fallback or browser provider selection.

Groq requires two distinct stages: a single local tool request, then strict JSON
schema without tools or streaming. Both request `include_reasoning:false`; unexpected
reasoning is discarded. Optional OpenAI uses `store:false`, no background mode,
and only ephemeral encrypted reasoning for continuation. Provider retention policies
still apply. Groq's free organization quota is finite; capacity failures require
explicit retry and never trigger a paid provider.

NDJSON relays only real coarse progress and one normalized final response/error.
No readable reasoning is forwarded or persisted. The panel stores at most three
exchanges in memory. Exact context/account changes clear them; ordinary same-context
browser visibility preserves them without reads. See [AI_AGENT.md](AI_AGENT.md) for
official contracts, budgets, schemas, privacy, failure semantics and limitations,
and [PHASE_6_REVIEW.md](PHASE_6_REVIEW.md) for the completed live Groq acceptance and final repository gate.

Phase 6 live-response presentation repair: `ai/presentation.py` formats broad
inventory answers deterministically from the existing bounded inspector. Specific
questions retain canonical fact selection. Internal `ModelAnswer.suggestion_ids`
selects reviewed optional next-step text; the public response contract retains
`discussion`, assembled by Forge. No model-authored factual summary or semantic
upgrade from activity to sketch completion is admitted through suggestions.
Empty evidence statements fail validation. The frontend conditionally mounts
expanded evidence, avoiding Chrome's hidden-details rich-copy list artifacts.
The user verified the final inventory, parameter, mass, Evidence, selection,
validation, write-capability and context-lifecycle behavior with real Groq.
The complete repository gate also passes. No Phase 7 behavior is introduced.

The selection-grounding repair closes the remaining model-authored output fields:
`ModelAnswer.assumption_ids` and `question_ids` resolve through reviewed server
catalogs, while public assumptions/questions remain string arrays. `ai/selection.py`
formats category-only facts and explicit ownership/measurement unknowns without
access to inventory counts. Selection-specific questions bypass general overview
presentation and omit every optional sidecar. Counts of bodies/parts/features never
become an ownership join. No new tool, provider call, CAD read, selection reference
or frontend production contract is introduced. The user verified the repaired
FACE and EDGE behavior live, including singleton-inventory ownership unknowns.

The write-request repair routes explicit CAD modification requests through
provider-neutral `ai/writes.py` and `resolve_write`, before any provider call.
The same session/context-bound inspection supplies optional captured feature order;
Forge supplies read-only capability and unknown width/controlling-dimension facts.
This produces a validated public answer without model output or a fabricated tool
call. Normal reads keep strict model parsing (`ai/output.py`) and fail closed on
invalid output. Session/freshness/permission/cancellation controls apply to both.
`ai/diagnostics.py` reports fixed, content-free metadata only in development; the
user's live diagnostic confirmed Groq HTTP 400 `tool_use_failed` at the forced
initial inspection stage. The browser contract is unchanged. See AI_AGENT and
PHASE_6_REVIEW for evidence and live retest steps.

## Phase 6.5 material and presentation boundary

The shared design-system package now owns semantic visual tokens, an original SVG
identity and one progressively enhanced web glass material. Its SVG map and CSS
filter operate only inside Forge. Pointer illumination schedules at most one frame
at a time during interaction and cancels on leave, unmount or document hiding.
No cross-origin parent capture, graphics framework, font request, new network path,
backend change, dependency or migration was introduced.

Analysis request/lifecycle code is retained. A pure `AnswerContent` view groups
evidence by existing status and presents uncertainty before optional evidence.
Expanded rows still mount conditionally. The lab imports the same presentation
with synthetic fixtures; production tree shaking excludes the lab and fixtures.
Local preferences gain only a strict boolean for reduced transparency, with dark
as the new default and explicit prior themes retained. See the canonical
[design system](FORGE_DESIGN_SYSTEM.md) and [review](PHASE_6_5_REVIEW.md).

The second visual-review pass adds a conservative frontend display formatter over
server-owned evidence statement grammar. It only condenses exact compatible
inventory prose; it performs no engineering calculations, ownership joins or
requests. Ambiguous/missing/unknown/suppressed facts keep original prose. The full
original answer mounts inside Evidence for condensed overviews. Response schemas,
API, provider and deterministic grounding remain unchanged. The diagnostic dialog
uses a DEV-only external view store (retaining an early open request) and local event from Workspace menu → Developer; production removes
its import and menu action. UI Lab owns three internal logo candidates and A/B/C
material comparison; only the chosen oblique-plane identity ships in public assets.
See [the second-review record](PHASE_6_5_REFINEMENT_REVIEW.md).

Phase 6.5 was visually approved after two human-review passes. The approved design
language is frozen; future authorized work must reuse it. The final pass changes
only server-owned product text (capability, selection, freshness, units, mass and
validation), Settings consistency and the CSS fallback declaration order needed to
survive minification. Evidence IDs/statuses, response schemas, provider/tool routing,
OAuth, sessions, parent validation, CAD reads and deterministic refusal remain
unchanged. The compact overview formatter recognizes the finalized mass wording;
it still falls back conservatively. See [the final record](PHASE_6_5_FINAL_REVIEW.md).

## Phase 7 learning boundary

`learning/lesson.ts` defines closed, bounded, serializable authored lesson, step,
vocabulary and future requirement metadata. `sample.ts` supplies one three-step
Sketch to solid lesson; `catalog.ts` validates before presentation and distinguishes
empty/unavailable/invalid/load-failure states. No React nodes or external requests
belong in lesson content. The local catalog is synchronous; there is no network
loading service or provider fallback.

`learning/session.ts` is a pure reducer with setup, introduction, active and completed
states. Stable step IDs guard delayed events; learner marking precedes advancement.
Hint level and vocabulary observations are monotonic until reset. Selectors derive
counts rather than letting views mutate counters. `LearningProvider` owns the
in-memory session above mode tabs and hash subpages. It resets learning on session
CSRF identity/connection changes without remounting unrelated account UI. Sign-out
unmounts the authenticated workspace. Same-session status refreshes preserve learning.
No lesson state is tied to CAD identity because the sample consumes no CAD evidence;
actual iframe/page reload or destruction starts fresh.

`features/Learn.tsx` composes setup, introduction, current step, disclosures, hints,
progress and completion. Focus follows explicit flow transitions, while hint and
vocabulary requests keep their control focus. UI Lab's state selector is DEV-only.
The production lesson is real authored educational content, not a synthetic CAD
result. It makes no AI/CAD calls and requires no provider key. All CAD authorization,
business logic and future engineering evaluation remain backend responsibilities.
No dependency, API, migration, permission or database model changed. Phase 8 may
attach deterministic evaluation to the metadata; no evaluator exists here.

## Phase 9A preparation — future architecture only

[The safe-write specification](PHASE_9_SAFE_WRITE_SPEC.md) selects one future
terminal standard Fillet suppression. It designs server-owned inventory targets,
immutable short-lived proposals, exact session/object/document-microversion
approval, cross-worker single consumption, provider revision rejection and fresh
deterministic verification. Short-lived PostgreSQL operational state and safety
fences are proposed for 9B; no schema or runtime code is added here. In particular,
the current four-read non-atomic snapshot is insufficient for write approval.

Phase 8B is external work awaiting validation/merge. Integrate its actual evidence
contracts only after merge; do not invent another checker/evidence framework.
Provider suppression payload and reject-on-skew update semantics require real
disposable-document conformance gates. Phase 9B, write permissions, write routes,
tools and active approval controls remain unimplemented and unauthorized in 9A.
