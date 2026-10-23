# Architecture

## Current implementation — Phase 8 validated; Phase 9 safe Modify and Phase 10 Learn integrated

One React/TypeScript/Vite web client, one FastAPI/Pydantic API and shared presentation
primitives serve desktop browsers. Native clients are not part of Forge.

The Phase 1 Design/Modify/Learn shell remains, now behind an Onshape sign-in gate.
The development UI lab is independent of authentication and remains excluded from
production builds. Build/validation previews remain explicitly synthetic; Phase 6
analysis uses real backend services only after an explicit send.
Phase 4 established four backend CAD REST reads. Phase 5 projects their snapshot
into a bounded CAD Inspector; the compact proof API remains available. Phase 6 adds read-only AI through a provider-independent interface (default Groq; optional OpenAI). The single Phase 9B guarded write is implemented but disabled by default. The extension launch bridge sends
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

| Component        | Responsibility                                                                                      | Current state                                               |
| ---------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Frontend         | Narrow-panel UI, accessible controls, typed API calls, approved plan presentation                   | Authenticated local UI + DEV fixtures                       |
| API              | Configuration, sessions, authorization, validated contracts, orchestration                          | OAuth, sessions, CSRF, reads, checks and guarded Modify     |
| Database         | Users linked to Onshape identity, encrypted token records, sessions, plans, inventory, audit events | Auth, audits, ephemeral proposals and deny fences           |
| AI layer         | Provider adapters, bounded agent loop, allowlisted functions, streamed user-facing status           | Phase 6 backend adapter and read-only agent                 |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | OAuth, read client and private guarded suppression client   |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Deterministic lesson checks; engineering validation planned |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | One Phase 6 read-only inspection tool                       |

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
  The separately authorized deployment foundation adds a production image; native
  development remains unchanged.
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

## Production deployment foundation — not yet hosted

The root Dockerfile builds the locked React workspace and Python API into one
non-root service. FastAPI serves explicit `/` and `/extension` entrypoints and
bounded asset mounts only when production WEB_BUILD_DIR is configured; there is
no catch-all SPA fallback over API/auth/docs routes. Production responses apply
the exact Onshape frame-ancestors policy, no-referrer and nosniff.

Railway configuration targets one public HTTPS origin, private PostgreSQL, explicit
pre-deploy Alembic upgrade, startup schema verification and `/health` liveness.
TLS terminates at Railway; the one-worker launcher ignores forwarding headers.
Validated APP_BASE_URL remains the canonical security origin. Keep one replica
and writes OFF pending a separate scaling/write-coordination review.

See [DEPLOYMENT.md](DEPLOYMENT.md) for build/context inspection, synthetic smoke,
runtime variables, cookie/Onshape URL transition and rollback. No hosted resources
or registration changes have occurred. Secret management, backups, ingress log
review, usage controls and real embedded-session testing remain live-deployment
gates, alongside [SECURITY.md](SECURITY.md) and [ONSHAPE.md](ONSHAPE.md).

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
[PHASE_5_REVIEW.md](PHASE_5_REVIEW.md). Assemblies remain unassigned future work.

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
Phase 7 introduced no dependency, API, migration, permission or database model
change. Phase 8 now attaches the deterministic evaluator described below; the
authored sample itself retains its no-CAD behavior.

## Phase 8 step-check boundary — complete, human validated and merged

`POST /api/learning/check-step` accepts a lesson id, a step id and the validated workspace
context. The server owns the requirement sets (`step_checks/bracket.py`), takes one fresh
bounded read through the existing `cad_gate` (same per-user in-flight guard and cooldown as
the inspector and AI), projects it with `inspect()`, and evaluates pure functions. The browser
cannot supply requirements, statuses, paths, hosts or tokens. Results hold fixed
server-authored findings; nothing is cached or persisted.

The Mounting Bracket lesson uses the existing learning engine. Deterministic
PASS / FAIL / WARNING / UNVERIFIED findings preserve evidence limits and do not
consult the AI. Feature names are not requirements; the supported single-L-profile
alternative is retained. The active step's Forge verification is revoked by a later
non-verified check and restored by a later verified check, independently of learner
completion. Onshape access remains the existing four GETs only.

Final human validation and merge at `81199ea` are confirmed by the user. Preserve
[PHASE_8_REVIEW.md](PHASE_8_REVIEW.md) as the unchanged implementation/validation
record; its earlier provisional status is superseded by this confirmation.

## Phase 9B implemented safe-write boundary

Phase 9A preparation remains complete. [The runtime review](PHASE_9_REVIEW.md)
records the implemented architecture, proven Gate A and remaining provider-conformance
evidence for Gate B.
Exactly `suppress_terminal_fillet_v1` uses server-resolved inventory, opaque candidate
handles and closed immutable 120-second proposals. The flow is intent → fresh evidence
→ candidate → proposal → explicit approval → one-use claim → fresh state/version check
→ guarded provider write → fresh post-write verification → verified success or
fail-closed uncertainty.
The original sourceMicroversion with rejectMicroversionSkew=true is mandatory;
there is no local-check-only fallback, generic Onshape API or arbitrary FeatureScript.

`cad_edits/` owns deterministic authority and same-origin CSRF-bound routes. A private
fixed v17 write client extends the existing bounded provider boundary with pinned
microversion reads; existing inspector, context, checker and lesson engines remain.
AI has no execution tool. PostgreSQL `0002_safe_edit` adds ephemeral operational
records and durable deny fences. Committed atomic claims, shared user/session/grant
coordination and unique workspace/user fences protect multiple workers. Uncertain
writes are never retried or automatically rolled back. Cleanup cannot remove fences.

The internal development-only `cad_edits/dev_recovery.py` helper supports separately
authorized database administration after independently established settlement.
With writes OFF, it locks user → original session → grant → fence, verifies the
trusted exact orphan, elapsed retention, empty operational table and unique ordered
uncertainty audit window, then commits one exact deletion plus a fixed recovery
audit atomically. It has no route, CLI, browser/AI authority or provider transport;
production mode rejects it. It neither restores proposal authority nor promotes an
uncertain result. Normal persistent-fence and reconciliation behavior is unchanged.

Retained A2 uncertain records have a separate internal development-only operator
path: closed contracts → fixed pinned GET reader → bounded operator coordinator →
provider-free atomic release. It requires independent preserved operation evidence,
hard-expired/revoked historical identity, current connected read authorization,
cache-only credentials, drained writers and independent settlement. Scoped user,
session/grant/fence/record locks protect single-use same-transaction evidence and
exact redacted `operator_recovered` closure. No browser authority, route, CLI, AI
tool, refresh, replay, schema or default changes. See
[retained recovery V1](RETAINED_RECORD_OPERATOR_RECOVERY.md).

The one-time October 20 administrative recovery is CLOSED. Its temporary recovery
modules, enrollment and dedicated reader have been removed; no executable incident
exception remains. Normal retained-record V1 is unchanged. See the
[closed incident record](LEGACY_RETAINED_RETIREMENT.md).

The operation-specific `terminal-fillet-6` policy binds an explicit feature-state
evidence mode into the baseline/digest. A nonempty state map must cover the inventory
exactly and pass every strict status/inactive check. An exactly empty map means
`UNAVAILABLE_EMPTY`, never inferred OK/active; structural suppression, pinned
configuration/version, complete captured definitions and one supported solid-body
result remain mandatory. Partial/malformed/extra maps reject. Verification uses
fresh explicit target suppression and preserved definitions/body output, with strict
state checks whenever the after-map is nonempty. Whole-model health is not claimed.
Old-policy previews cannot execute and must be prepared again.

Per-feature suppression auxiliary modes are also baseline/digest-bound: exactly null
is `NULL_UNAVAILABLE`, with no inferred ordinary state or Boolean. A supported base
object is validated as `ORDINARY_OBJECT`; missing/malformed/specialized/unknown
states reject. Suppressed remains an explicit Boolean. Omitted parent/configured
flags are separate evidence modes: the entire supported top-level structure must
exclude parent suppression, and the pinned independent configuration endpoint must
prove no active configuration inputs. Explicit true/null/wrong-type guards reject.
Raw omissions remain fingerprinted; nothing is synthesized. Required per-feature
modes bind baseline/digest/stale/post-write checks. Guarded write and feature-state
map policy are unchanged; no wider CAD authority or model-health claim is added.

Body revision evidence is required in the baseline/digest. `EXPLICIT_CLEAN_FLAGS`
requires a matching returned `theId` and both marker flags explicitly false.
`EXACT_PINNED_ID_FLAGS_UNAVAILABLE` requires both flags absent, the same explicit
returned ID, and transport proof of a bodydetails read at `m/{same}` after equal
head-before/head-after checks. Missing flags remain unavailable, never false.
Mixed, null, malformed or true flags reject. Both modes require exactly one SOLID
and `NO_ERROR`; all feature/configuration reads share the pinned revision. Fresh
pre-dispatch mode changes invalidate approval. Verification independently re-proves
either accepted mode at the exact new acknowledged revision; invalid evidence
retains uncertainty/fences without retry. No raw body payload or flag defaults
are persisted. Existing original-version write guards remain mandatory.

Writes default OFF and were returned OFF after human testing. Known OAuth2Write
consent remains mandatory; this merge changes no permission. Gate A proved one
approved terminal-Fillet suppression and Forge verified success from fresh evidence.
Gate B reached the pause and the human advanced the workspace; stale suppression
did not apply. Provider-side rejection audit confirmation was deferred, so full
provider conformance is not claimed.

The first human-approved suppression reached uncertainty; the full reconstruction
is in the runtime review. Policy 6 now requests full sketch definitions for the
safe-write path (noSketchGeometry=false, geometry IDs still excluded), binding all
returned definition fields under unchanged transport caps. The only mutable hash
exclusion remains the terminal suppressed flag. All eight final comparisons run
before rejection; fixed failed checks/stages are durably audited and DEV logs are
sanitized. No lost-ack reconciliation promotion or automatic fence release is added.
Phase 10's separate main history is integrated by this merge without squashing.

## Phase 10 learning extensions

The Phase 7/8 session reducer gains per-step `expectation` and `investigations` state and an optional
`transfer` sub-state (separate progress for the challenge). A `check-result` action now carries the
server's compact per-requirement findings, so investigations open, resolve and revoke from the latest
deterministic result alone. Guidance fading (`full` / `reduced` / `independent`) is computed in the
reducer from currently resolved same-family investigations. The backend change is additive: one new step id,
`transfer-single-profile`, in the existing `step_checks` catalog. No endpoint, table, scope or write path
is added.

Learn and Modify remain separate. Learn's flow is failed/warning check → observation
→ learner prediction → possible explanation → try-next guidance → explicit re-check
→ resolution/reopen → optional transfer challenge. The student makes every Learn
CAD change. Modify performs only its one supported explicitly approved write.
Phase 10 requires no Modify execution, write scope or write flag; its predictions
are ungraded and its transfer counts are not mastery scores. See
[the learning review](PHASE_10_REVIEW.md) for automated results and the pending
real-Onshape human validation plan.

## Phase 11 tutor boundary

`apps/api/src/forge_api/tutor/` adds `POST /api/learning/tutor`. Check my step issues an opaque evidence token
(HMAC keyed by the caller's session credential); the tutor verifies it and builds a bounded context from the
server's own lesson catalog and checker labels. The model may request only the existing read-only
`inspect_current_cad` call, through the existing gate and projection. It returns a strict structure; the server
prints verified observations itself. No new provider, table, scope or write path; the browser keeps at most three
exchanges in memory. See [PHASE_11_TUTOR_SPEC.md](PHASE_11_TUTOR_SPEC.md).

## Hackathon Modify A1 backend core

A1 adds a closed five-operation semantic plan/resolver/executor behind backend
interfaces, with no new browser route or AI tool. It reuses Phase 9 admission,
claims, fences, authority locks and pinned evidence; the original browser workflow
and evidence policy remain intact. One to five operations execute sequentially,
advancing only from verified revisions and stopping on any failure/uncertainty.
Typed plan/status envelopes reuse existing operational tables without migration.
See [the A1 contract and limitations](HACKATHON_MODIFY_A1.md). CAD writes remain OFF;
new operation conformance is not live-proven, and Phase 9 Gate B audit remains deferred.

## Natural-language Modify planner (B1)

`POST /api/modify/plan` takes `{context, request}`, runs a fresh A1 `discover()`, asks the
operator-selected model (no tools) to choose handles and values from a minimal catalog,
validates the output server-side, builds the `SemanticPlan` with the server-owned
`target_catalog` and returns A1's authoritative `prepare()` preview or a clarification.
It never approves or executes. See [HACKATHON_MODIFY_B1.md](HACKATHON_MODIFY_B1.md).

## Generalized human approval transport (A2)

`cad_edits/plan_routes.py` adds approve/cancel/status under `/api/modify/plans/{handle}`
beside the unchanged Phase 9 routes. Explicit human approval alone invokes A1's
executor, with a bounded NDJSON observer and application-owned task that survives
consumer disconnect. PostgreSQL conditionally cancels only pending plans, retaining
status-only journals. Claims, fences, verification, revision chaining and execution
budgets stay in A1. No new UI, CAD operation, AI tool, dependency or migration.
See [the stable B2 API and stream contract](HACKATHON_MODIFY_A2.md).

B2 now connects the live Modify tab to that pipeline: natural-language planning,
exact multi-operation review, explicit human approval and bounded progress/status.
Authority remains in component memory and the backend; see [B2](HACKATHON_MODIFY_B2.md).

## Modify recovery reliability hotfix

[Recovery hotfix](MODIFY_RECOVERY_HOTFIX.md) adds session-owned server discovery,
read-only single-terminal-suppression reconciliation and a deterministic planning
fast path before AI fallback. `reconciled_current_state` proves present-state
agreement without attributing the original write. Live fences retain the bounded
reconciliation payload until safe closure; resolved status records expire after
15 minutes. Consumed handles never regain approval power.

## Phase 12 — deterministic model graph (implemented; automated gate passed)

`forge_api.model_graph` adds an internal immutable `forge-model-graph-v1` contract,
a pure builder and narrow typed queries over an existing normalized read Snapshot.
It preserves IDs and returned feature order beneath the ID-removing Inspector,
with explicit per-source capture/revision/completeness provenance. No additional
provider acquisition, public endpoint or runtime subsystem migration is introduced.

The graph separates requested workspace/Part Studio references, returned feature /
part/body inventory and bounded browser selection observations. Requested context
containment stays unknown. Feature order does not become dependency; selection
references never gain inferred ownership or topology correspondence. Invalid or
mixed-context/revision evidence rejects, and sequential-read consistency remains
unverified. Deployment, authentication, CAD-write and recovery code are unchanged.
See [PHASE_12_FORGE_MODEL_GRAPH.md](PHASE_12_FORGE_MODEL_GRAPH.md) for the prior
evidence inventory, schema, bounds, integration boundary and validation status.

## Phase 13 — direct CAD Inspector feature inventory

**COMPLETE — HUMAN READ-ONLY VALIDATION PASSED — MERGED INTO MAIN**

Phase 13 human read-only validation passed and the phase merged into main at
`c200f0af5695a3c603074bdf3e640965a8d84171`, preserving implementation commit
`7696aa0e51002725811379123f498cb91da1e3ff` and human-validation documentation commit
`bef41d2e13cca67e7436f06e4c09564e232867e8` without squashing. Railway remains unhosted.

Phase 13 made the direct Inspector endpoint call `inspect_graph`. `acquire` retains the
request-validated immutable WorkspaceReference independently of the acquired Snapshot;
unchanged `acquire_bound` finishes its session/grant revalidation before graph creation.
`GraphQuery.ordered_features()` supplies feature identity/order/index, with checked
same-Snapshot provider-ID correspondence for rich display evidence. Shared presentation
preserves the public contract, source proof, parts/body provider order and physical
metadata. AI, Tutor, Step Checks, Modify and compact proof retain their existing paths.

Rejected graph/equivalence evidence becomes the existing fixed `invalid_response`
unavailable Inspector response; there is no legacy Snapshot fallback. Authorization
stops preserve their fixed code while discarding earlier evidence. No extra acquisition,
cache, persistence, endpoint, frontend exposure or authority is added. See
[Phase 13 boundaries and equivalence review](PHASE_13_INSPECTOR_GRAPH_ADOPTION.md).

Reads remain sequential/non-atomic. Graph adoption is limited to direct CAD Inspector
feature inventory/order; AI/Tutor/Learn/Modify were not graph-migrated by Phase 13.
No ownership inference, dependency DAG, topology continuity guarantee,
engineering-correctness claim or new CAD authority is introduced.

## Phase 14 — graph-grounded Ask Forge

Normal read-only Ask Forge is the next graph consumer, through the existing explicit
POST and authorized `acquire_bound`. After final session/grant validation, a private
pure helper builds one graph from that exact normalized Snapshot and the independent
validated request WorkspaceReference. It supplies both the Phase 13 feature projection
and GraphQuery structural facts. Full inventory correspondence uses exact opaque
provider IDs before truncation; rich parameters, parts, bodies, source/capture and
physical evidence still come from the same Snapshot. Public Inspector/answer schemas
and UI are unchanged.

The AI projection adds at most 19 adjacent AVAILABLE returned-order facts, at most
one completeness-proven terminal within the existing 20-feature cap, and a server-owned
semantics fact. It never serializes graph nodes/edges, provider/context IDs or
provenance to a model or browser. Canonical selection remains the only CAD-claim
authority. The 65,536-byte evidence bound includes these facts and caveats; overflow
fails closed. Graph or correspondence failure discards evidence with the existing
unavailable behavior, never legacy structural fallback; authorization stops preserve
their existing errors. Final agent revalidation and cancellation still prevent AI
use of discarded evidence.

PRECEDES means returned order, not dependency. No ownership inference, selected-face/
edge ownership, dependency DAG, topology continuity or engineering correctness is
introduced. Direct Inspector remains Phase 13; Tutor/Learn/Check my step/Modify are
unmigrated. The recognized write-request capability path remains deterministic with
zero model calls or writes. At most four sequential/non-atomic GETs, no extra provider
read, persistence, scope, public graph API or new CAD authority. Railway remains
unhosted. See [Phase 14](PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md).
