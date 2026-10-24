# Security architecture

## Implemented through Phase 6 read-only AI

Forge uses Onshape OAuth2 only. There are no passwords, JWT login tokens, CAD mutation tools
or AI CAD mutation capabilities. Explicit Phase 6 requests call the configured hosted AI provider; four backend
CAD reads are allowlisted. Authentication establishes an account, not permission to change CAD.

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
and navigation suspension prevents delayed messages from reviving them. Ordinary
browser visibility/focus does not invalidate the same validated frame. Selection
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
origin and suppress referrers. The deployment foundation now supplies these headers
from FastAPI in production too; platform-generated errors still require live ingress
review. Vite build output alone does not configure an ingress. No enterprise wildcard is
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

## Phase 4 CAD reads

The browser sends only validated document/workspace/element references and explicit
workspace revision kind. The session determines user ownership; Onshape checks
that user's grant against each exact object. Expired tokens use the existing
refresh architecture. No credentials, raw CAD bodies or provider errors reach the
browser. Missing known OAuth2Read and unknown-scope 403 outcomes remain distinct;
no undocumented scope bitmask is interpreted.

The CAD adapter permits only four fixed GET templates at the exact HTTPS standard
Onshape origin. Enterprise auth support does not widen this allowlist. URL credentials,
private/loopback/arbitrary hosts, paths in origins and redirects fail closed.
The new GET also requires the existing session-bound CSRF header; absent GET Origin
is allowed only with that header, while a mismatched Origin or cross-site Fetch
Metadata is rejected. Existing mutation routes and CSRF policy remain unchanged.

Responses are bounded before normalization; compressed payloads, invalid JSON,
nonfinite values, duplicate keys and excess depth/collection sizes are rejected.
No CAD response is persisted/cached. The final session/grant check discards data
following in-flight logout/disconnect. Frontend reference/account/navigation changes
abort reads and clear prior summaries. Response cache policy is always no-store.

Telemetry includes fixed operation/outcome, status class, duration/retry count and
random correlation only. Ingress/APM must omit query strings for the CAD endpoint
as well as auth paths: queries contain private CAD references. Do not enable raw
HTTP request/response logging. The per-process user gate is not a substitute for
deployment-wide admission/rate limits. Default-configuration, non-atomic reads and
provider-native unverified mass units cannot establish engineering correctness.
Only `ENVIRONMENT=development` enables the mass failure structure builder. It
emits known field names, types, array lengths/categories and fixed validation
codes through a bounded header after the existing final session/grant check.
It never copies numeric CAD values, body keys, unknown names, exception messages or
inputs. Production omits the header and does not import that development module.
The DEV UI uses an additional strict vocabulary validator before rendering a
bounded manual-copy text area; both validator and UI are absent from production
assets. The normal count/status response and existing log fields are unchanged.
Scalar field validators now emit fixed `negative_nominal` or `bounds_order` codes
at the actual field. The DEV builder uses these codes without replaying validators
or copying error messages/context. Body-key locations are removed by position, including keys equal to
known field names. DEV can also emit only fixed predicate codes and three
pairwise comparison enums (`greater`, `equal`, `less`) for a failed finite scalar
triple. It never emits the compared numbers or their record key. The frontend
allows these optional fields only for mass/volume/periphery `invalid_bounds`, rejects
unknown keys/values, and retains the 4096-character input and 8192-character
display limits. The user's authorized sign capture adds only `massSigns` with
three `negative` / `zero` / `positive` enums, the known `hasMass` boolean, and
`massMissingCountCategory` as `zero` / `positive`. These come from the first
failed mass record, with strict number/boolean/integer checks; missing or malformed
facts are omitted. Neither numeric operands nor the missing count are exposed.
The frontend rejects extra fields, numeric signs, invalid enums and facts without
a mass bounds failure. Production excludes these facts with the DEV diagnostic.
Present physical scalar estimates require exactly three strict finite numbers,
nonnegative nominal and ordered bounds; negative lower tolerances do not weaken
these controls. Missing/nullable optional estimates remain unknown. A false mass
flag suppresses the normalized mass estimate, and a positive missing count prevents
a partial assigned estimate from claiming verified availability in the proof UI.
No numeric mass data, missing count or private CAD references enter the browser.
The final repository review confirms four fixed Onshape CAD GETs only: no CAD
POST/PUT/PATCH/DELETE, arbitrary proxy, caller-selected provider path or host.
Existing OAuth tokens remain backend-only, refresh tokens encrypted, and session
ownership/CSRF unchanged. The user's real read and empty-context tests verify the
observed integration behavior; source review and regression tests establish the
read-only security boundary. No security certification or broader production
readiness is inferred from these checks.
See [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md) for the full boundary and evidence.

## Phase 5 browser data boundary

The inspector intentionally exposes more private CAD metadata than the compact
Phase 4 proof. Its explicit allowlist includes bounded display names, supported
literal parameter values, ordinal positions, suppression, part metadata, topology
counts and physical availability. Both APIs reuse the same authentication and
read gate. The new endpoint accepts the same four context fields and secret CSRF
header; no new provider operation, host, path, method, permission or retry exists.
The final ownership check precedes either projection.

Neither response includes raw provider payloads, arbitrary custom properties,
feature/body/part IDs, source microversions, FeatureScript source, query strings,
geometry, tokens, headers or exception bodies. Parameter labels may derive from
bounded readable parameter names; opaque hexadecimal IDs use ordinal labels.
Quantity expressions are literal strings only, never evaluated or used to infer
units. Custom feature namespaces stay server-side. Unknown classes cannot inject
summaries, even by sending fields named like the internal projection.

Provider bounds are unchanged. Inspector limits add 100 features, 200 parts,
200 bodies, 16 parameters per feature and whole-value display omission beyond
256 UTF-8 bytes (parameter labels derive from at most 80 ASCII characters).
Completeness and omitted counts remain explicit; missing, null or unverified empty
topology is never zero.
The frontend rejects unknown fields, wrong types, inconsistent counts/statuses,
unsupported versions and responses above 2 MiB before JSON parsing.
React escapes all display text and does not make provider URLs clickable.

No inspector data is persisted, cached, sent to analytics or logged. This includes
names, searches and parameter values. Existing logs contain fixed outcomes only;
ingress/APM must suppress both CAD endpoint queries and bodies. DEV diagnostics
receive the compact proof and separately validated structure headers, never raw
provider records, and remain absent from production assets. Test/lab fixtures are
invented and never production fallback.
Mass/volume numbers remain withheld with `provider_native_unverified` units.
Passing this gate is not security certification or production approval.

The topology investigation adds a development-only `X-Forge-Body-Structure` header,
at most 512 ASCII characters, after successful bounded body normalization and final
session/grant ownership validation. It describes only the first returned body's
faces/edges/vertices: fixed presence boolean, array/missing category and bounded
length/null. It copies no IDs, coordinates, geometry, unknown keys, provider values,
tokens or URLs. Empty arrays remain structure facts, not verified topology zeros.
No header is emitted for body errors, no bodies, non-development environments or
lost ownership. The client clears previous structure before every body read. The
DEV browser validates exact keys, types and bounds; production ignores even an
injected header and excludes the parser/UI. Neither structure nor CAD data is logged
or persisted. Manual capture steps are in the Phase 5 review; no live raw capture
is authorized or needed.

The browser lifecycle repair keeps exact origin and parent-window checks, strict
launch parsing, GET-only REST and CSRF/session ownership unchanged. Inspection keys
use validated IDs plus revision kind, origin, microversion and session CSRF identity;
display labels never establish sameness. Ordinary hidden/visible or blur/focus
preserves the last capture with its original uncertainty metadata. Focus may run the
existing session check, never a CAD read. Malformed trusted selection clears private
inspection and opaque references; valid selection recovery does not read CAD.
Supplied document/workspace/element fields must match the current launch or context
is rejected. Untrusted messages are ignored so they can neither alter valid state
nor revive an invalid one. Actual navigation/bfcache suspension still clears evidence
and cannot be undone by a show message lacking identity. A destroyed/recreated
panel frame has fresh state and one applicationInit. No state is persisted.

Final Phase 5 human verification passed on 2026-10-14: ordered Sketch/Extrude,
supported/caveated parameters, safe part metadata, 6 faces with unknown edges/vertices,
missing-mass and reported-volume evidence without numeric units, FACE/EDGE/clear,
local filtering, same-frame Chrome tab preservation, and empty Part Studio 0/0/0
with prior evidence cleared. This verifies observed read-only behavior, not selection
ownership, complete CAD semantics, atomic consistency or engineering certification.
The architecture/security boundaries above and production-excluded diagnostics remain.

## Phase 6 external AI and prompt injection

Only explicit Design send transfers the disclosed prompt, up to six public prior
messages and bounded current CAD evidence to the configured hosted AI provider. No call occurs on launch,
selection, Refresh CAD or browser visibility. The root ignored `.env` owns the
selected SecretStr API key and reviewed provider/model/effort; no frontend config or model argument
can select a key, endpoint, target, user or host. The only function accepts `{}`.
POST auth/CSRF/origin and strict bounded input precede model spend. Session/grant
checks precede and follow the tool and final answer. Onshape independently checks
each object through the owning grant. Existing CAD GET-only policy remains.

CAD strings/history are untrusted data below the fixed agent policy. The backend
rejects unknown tools, nonempty arguments, duplicate calls and a second tool round.
The model selects canonical evidence IDs; Forge resolves their statements/statuses.
It cannot create a verified fact. Optional suggestions select reviewed next-step IDs, never free-form factual
claims; the server renders their wording. Active suppression state is never
promoted to sketch completion/correctness. Assumptions and questions also select
reviewed IDs; arbitrary model-authored strings are rejected. Optional hypotheses
are clearly conditional engineering cases and cannot assert selection ownership.
Questions request user requirements, not unsupported selected-geometry inspection. A narrow local harmful-device/
secret filter plus model policy/refusal protects ordinary product scope; neither
constitutes a complete semantic safety classifier. No arbitrary network/code tool
exists, and model text never authorizes an action.

The provider-neutral agent and fixed tool policy apply equally to Groq (default)
and OpenAI (operator-selected optional). Provider/model/effort/keys are server-only;
invalid provider selection or missing selected key fails closed. Neither provider
requires the other's key; there is no automatic paid fallback. Provider HTTP details
are isolated from the agent and the unchanged CAD authorization boundary.

Groq Chat requests suppress reasoning with `include_reasoning:false` and omit its
unsupported `store` flag. Its tool round is followed by strict JSON schema with no
tools; any additional tool attempt fails closed. Per Groq's [data documentation](https://console.groq.com/docs/your-data),
inference content is not retained by default, but reliability/abuse exceptions may
retain it for up to 30 days or longer if legally required. Usage metadata remains.
Admins can enable ZDR in account Data Controls; Forge does not assume it is enabled.
Optional OpenAI Responses use `store:false`, no background mode, Conversation objects
or stored response chains. Opaque encrypted state exists only during the single
bounded continuation. The [OpenAI data controls policy](https://developers.openai.com/api/docs/guides/your-data),
rechecked 2026-10-16, separately permits abuse-monitoring retention up to 30 days
(with legal/safety exceptions) and prompt-cache state up to 24 hours.
`store:false` does not disable those separate policies.
Neither provider is claimed to guarantee zero retention for the configured account.

No prompts/evidence/answers/reasoning enter logs, PostgreSQL, localStorage or analytics.
Log fields are random Forge request ID, sanitized provider request ID and status
class only; keep ingress/APM bodies disabled. Raw provider failures never reach the
browser. Groq quota/oversized-capacity errors map to a fixed Forge capacity state,
with bounded retry-after, no automatic retry and no provider switch.
Size/call/token/time/admission budgets, cancellation, context clearing and explicit
retry prevent runaway loops. A cancelled in-flight read may finish bounded GETs
but cannot trigger another AI round or modify CAD. Full controls and residual
limitations are in [AI_AGENT.md](AI_AGENT.md). The user reported final real Groq
verification passed on 2026-10-16; no production readiness, certification or
Phase 7 authorization is implied.

The first user-reported Groq inventory test verified the provider/tool/grounding
path for one real Part Studio. Final human verification subsequently covered
all Phase 6 live acceptance cases; it does not establish universal model quality. The live
response repair keeps the CAD inspector unchanged, uses deterministic overview
presentation, rejects blank evidence and mounts evidence rows only when expanded
(to avoid Chrome rich-copy empty list markup). Targeted mocked regression checks
are recorded separately from the earlier full gate in PHASE_6_REVIEW.

Selection grounding is a hard server boundary: normalized FACE/EDGE category is
not an ownership mapping. A unique part/body/feature, recent Extrude, visible shape
or conversation assertion cannot establish owning part/body/feature or selected
measurements. Direct selection answers contain only server-owned category/unknown
facts, no suggestions/assumptions/follow-ups. Canonical selected dimensions,
surface/curve type, face area/normal and adjacent edge geometry stay unknown.
The current tool exposes no selected-entity inspection capability. Both providers
reject legacy free-text assumptions/questions and unknown catalog IDs. Tests
exercise singleton inventory and malicious outputs without live inference.

Explicit write-request capability responses are server-owned after the existing
bound inspection, without any model request or generated tool call. They state that Forge performed no CAD writes
for this request, not that the entire Onshape workspace could not have changed
concurrently. Width/controlling parameters remain explicitly unknown. No malformed
model result or fabricated call is accepted to enter this branch. Normal read
requests retain strict parsing, nonempty-answer checks, unknown/duplicate-ID
rejection and model safety refusal. The narrow local safety check precedes both
branches; authorization, freshness, admission and cancellation remain enforced.

Development-only `ai_validation` warnings contain fixed reason/provider/stage,
safe numeric HTTP status, allowlisted field path and a random Forge correlation.
Groq error code/type/parameter values are exact allowlisted literals only;
unrecognized strings, error messages and `failed_generation` are excluded.
Pydantic input/context/messages, unrecognized field names, exception text, prompts,
CAD strings and all provider bodies remain excluded. Production suppresses these
warnings entirely and retains generic public errors. Mocked privacy tests exercise
invalid enum values, private extra-field names, malformed JSON and final public
validation errors. No diagnostic grants permission, changes dispatch or retries.

## Phase 6.5 visual material controls

Presentation-only work retains the Phase 0–6 authorization, grounding, provider,
privacy and CAD read boundaries. SVG/filter decoration sees Forge-owned rendering
only. It neither captures nor inspects the cross-origin Onshape viewport. No canvas
text, external material code, renderer package or remote font is introduced.
Status groups reuse validated response statuses; visual styling never upgrades
unknown/unverified facts to verified or implies engineering validation.

The transparency preference is reconstructed from `p.reduceTransparency === true`;
no arbitrary CSS, query parameter or stored object is applied. Existing explicit
system/light/dark themes survive. Launch/selection development diagnostics remain
DEV-only lazy imports behind Workspace menu → Developer (or a signed-out DEV
recovery action), then explicit diagnostic enable/show controls.
Screenshots/traces use synthetic data only. The privacy explanation at the composer
still discloses explicit transfer to the configured hosted service and distinguishes
local memory from provider retention. No permission or OAuth scope changes.

The refinement's compact inventory is formatting only. Unique evidence IDs,
verified canonical count/feature/part/body statements and matching canonical answer
paragraphs are required; failures keep prose. Unknown is never zero and selected
FACE/EDGE is never joined to an inventory body. Unmatched extra paragraphs remain
visible, and the exact original answer is available on evidence expansion. Quoted
names remain React text. Exact repeated uncertainty strings can collapse on demand;
new strings remain visible. The Data use action and menu Privacy retain transfer,
in-memory conversation and provider-retention disclosures, also stated in onboarding.
The local Developer view store/event opens only a development view and grants no backend access.

The final approved freeze includes intentional backend **copy-only** edits to
canonical capability/selection/uncertainty statements. No routing, permissions,
transport, model policy, schemas, fact IDs/statuses or engineering logic changes.
Product text no longer exposes internal phases/provider terminology. Selection
ownership remains unknown; units/currentness/snapshot consistency stay unverified;
missing mass is never zero. Refusal continues to inspect authorized CAD with zero
provider requests and zero CAD writes. Production forced-color/reduced-transparency
filter overrides are ordered to remain intact after CSS minification. Private
configuration and manual CAD review captures stay ignored and outside the commit.

Forced-color mode maps semantic colors to system Canvas/CanvasText/LinkText and
ButtonFace/ButtonText, so text and control contrast follow the user’s system palette.
This adaptation does not change the approved normal appearance.

## Phase 7 learning privacy and authority

Learner experience, selected goal, step markers, hint levels and opened term IDs
exist only in the current authenticated panel's React session. No learning records,
analytics, mastery scores, accounts, storage entries or database tables are added.
Ordinary navigation preserves the state; reset, reload, panel destruction, logout,
expiry, session rotation and connection teardown clear it. Same-session status
refreshes and ordinary visibility preserve it. The sample contains no CAD references
and does not bind learning progress to a model.

Closed bounded authored lesson validation precedes use. Content is plain React text,
not HTML, executable rules or React-node payloads. Future check metadata only names
supported requirement shapes; it cannot execute code or report a result. Marking a
step done explicitly records learner self-report, never CAD validation. Hints are
reviewed local content. The fundamentals sample invokes no AI endpoint, Onshape endpoint, background
polling, telemetry or browser-storage operation. The existing `/api/me` lifecycle is
unchanged. No credentials enter lesson data or presentation. OAuth scopes, CSRF,
backend evidence and the read-only tool boundary remain unchanged. Phase 8 checking
now uses the separately authorized controls below; CAD writes remain future work
requiring explicit authorization and independent controls.

## Phase 8 Check my step — complete, human validated and merged

Explicit, authenticated POST with exact Origin and session-bound CSRF; strict closed request
schema (extra fields rejected, errors never echo identifiers); 4 KiB body bound. Reuses
`acquire_bound`, so read-permission, grant-state and session-revocation checks and the
per-user gate apply. Only the four existing GET reads can reach Onshape; there is no write,
FeatureScript or scope change. Status is computed server-side from evidence; unknown evidence
is UNVERIFIED. No lesson state, history or results are stored on the server.

The Mounting Bracket checker owns PASS / FAIL / WARNING / UNVERIFIED, uses fresh
CAD evidence and does not trust feature names or model judgment. The supported
single-L-profile alternative and verification revocation/restoration remain intact.
Results are memory-only in the panel, separate from learner-marked completion.
The user confirms final validation and merge at `81199ea`; the original
[Phase 8 review](PHASE_8_REVIEW.md) is retained unchanged, including its earlier
provisional wording, which this confirmation supersedes.

## Phase 9B safe-write controls

[Runtime review and threat boundary](PHASE_9_REVIEW.md): implemented and automated
tested, with Gate A human-proven and Gate B provider-audit confirmation deferred. Only
`suppress_terminal_fillet_v1` is allowed. Backend flag defaults OFF. Live OAuth app
permissions remain unchanged; known read/write consent is required before execution.
Unknown scope/bitmask fails closed; refresh cannot imply expanded consent.

Strict opaque candidates and immutable 120-second proposals bind user/session/grant,
context/feature, baseline microversion and digest. Same-origin JSON, exact Origin or
Referer fallback, session CSRF, bounded parsing and closed schemas protect all Modify
actions. Browser/AI cannot provide target IDs, payloads, hosts, FeatureScript or tokens.
PostgreSQL atomic claims and persistent fences commit before dispatch; shared user →
session → grant locking coordinates auth lifecycle and dispatch. Stale approvals
reject; the original provider microversion guard is mandatory. One POST only, no retry.
Fresh deterministic verification is required for success. Post-dispatch ambiguity
retains the fence; reconciliation is read-only and manual recovery remains deliberate.

The explicitly revised terminal-suppression policy distinguishes complete exact-key
state evidence from a present, exactly empty map. Empty means unavailable, with no
fabricated OK status or inactive Boolean; every hard suppression/structural/body/version
check remains mandatory. Missing, partial, extra-key or malformed maps reject.
The accepted mode is digest-bound; a fresh pre-dispatch change invalidates approval.
A nonempty after-map is strict, and an empty after-map never implies inactive=true.
Provider atomic stale rejection, one-use approval, fences and no-retry remain intact.
This narrower supported-result proof does not establish whole-model feature health.

Auxiliary suppression state has a separate explicit policy: exactly null contributes
no evidence and does not veto other operation-specific proof. It is never converted
to false, inactivity or an ordinary object. Suppressed must remain explicit.
Optional parent/configured flags are either explicit false or independently proven
through the complete restricted top-level structure and separate pinned empty
configuration response respectively. True/null/wrong-type values reject, and
missing is never rewritten as false. The per-feature modes are immutable/digest-
bound and checked again before/after dispatch. Unsafe proof changes retain fences.
Missing auxiliary property, malformed/base-invalid, specialized configured/expression/
parent or unknown objects reject. Modes and raw definitions remain bound; unexpected
post-write auxiliary changes retain uncertainty/fences. Omitted-field acceptance
does not expand permission or broader write authority and asserts no model health.

The body marker has a required explicit evidence mode, bound to the proposal digest
and fresh baseline. Both flags must be explicitly false (`EXPLICIT_CLEAN_FLAGS`)
or both absent (`EXACT_PINNED_ID_FLAGS_UNAVAILABLE`). The latter requires the fixed
client's exact microversion-pinned request, a matching explicit returned `theId`
and successful head bracketing. It does not assert either flag is false. Missing
ID, mismatched ID, null/true/wrong-type flags and mixed shapes reject. Exactly one
SOLID and `NO_ERROR` remain mandatory. Post-write evidence must identify the exact
new acknowledged microversion and re-prove an accepted mode; unsafe evidence
retains the fence and execution uncertainty with no retry. Older policy/missing-mode
records cannot execute. No mutation transport or OAuth permission changes.

The review specifies exact stored fields, 120-second approval/15-minute operational
retention, 60-second cleanup, persistent deny fences, safe audits and backup/restore
implications. No prompts, raw provider CAD payloads, tokens, hidden reasoning, history
or analytics are added. This is not a security certification. Real suppression and
atomic stale rejection remain separately evaluated human conformance gates. Gate A
is human-proven; Gate B showed the expected absence of stale suppression, with
provider-side rejection audit confirmation deferred. Writes returned OFF.

The first real write entered uncertainty correctly; see the current runtime
review for reconstructed evidence and limits. Policy 6 captures full returned
Sketch definitions for write verification within unchanged byte/structure/time
bounds. No additional field is normalized away. Fixed verification failure stages
and all failed final comparisons use the existing audit table without arbitrary
metadata, provider responses, private identities/markers or exception text. DEV
fixed-code logs and a writes-OFF internal GET-only helper add no public debug
endpoint, CAD write authority or fence-release capability. Gate A is now human-proven;
Gate B provider-audit confirmation remains deferred. Normal operational-row expiry
still never releases a fence.

Separately authorized operator recovery uses the internal `cad_edits/dev_recovery.py`
helper, outside browser/AI/API authority. It requires development mode, writes OFF,
an exact trusted private reference and an operator attestation of independently
established settlement. Under the shared user → original session → grant → fence
lock order, it requires one precise orphan, elapsed retention, no operational
records and a unique ordered claim/dispatch/acknowledgement/uncertainty audit window.
It deletes only the exact user/workspace/record match and atomically records fixed
`write_operator_recovery` / `local_only`; audit failure rolls back deletion.
An expired original session establishes identity only and is never revived.
There is no public endpoint, user control, bulk clearing, provider transport or
production-mode recovery. Normal fence semantics remain unchanged. The first
separately authorized recovery cleared one orphan with ZERO Onshape contact and
writes OFF; neither conformance gate was proven by that administration. The later
Gate A proof is a separate human-approved CAD trial, not a recovery outcome.

The separate retained-record V1 helper supports only a valid, aged A2 explicitly
uncertain single terminal Fillet suppression operation with independent preserved
operation evidence. It never changes the orphan helper's eligibility or transfers
old session/grant authority. Current credentials are cache-only, and the dedicated
five-GET reader is discarded before provider-free release. Exact transaction/object
provenance, deterministic current-state comparison, scoped row/advisory locks and
conditional mutations atomically produce a redacted `operator_recovered` tombstone
and fixed `write_retained_operator_recovery` / `local_only` audit. Independent
settlement and globally drained writers remain human prerequisites; DB locks and
receipt models cannot establish either. No public invocation or automatic recovery;
implementation verification is synthetic. See
[eligibility, trust assumptions and failure semantics](RETAINED_RECORD_OPERATOR_RECOVERY.md).

The one-time October 20 exception is CLOSED and its executable recovery surface
has been removed. Existing historical audit/result labels remain interpretable
without an incident-specific audit emitter, enrollment or invocation path. Normal
V1 provenance, authorization and strict CAD evidence checks remain unchanged. See
the [closed incident record](LEGACY_RETAINED_RETIREMENT.md).

## Phase 11 tutor

Explicit authenticated POST with exact Origin and session-bound CSRF; closed ≤16 KiB schema; errors never echo the
question. The browser cannot author check results: the tutor accepts them only through an HMAC evidence token keyed
by the caller's session credential (forged, altered, foreign-session, wrong-step, unknown-requirement and future
tokens are rejected; expired ones are ignored). No identifier, token, cookie, CSRF value, evidence token or learner
prediction is sent to the provider. The only tool is read-only `inspect_current_cad`. One in-flight request per user
plus a 30/hour in-memory cap. No persistence and no write path.

## Hackathon Modify A1 authority extension

A1 accepts only closed semantic operations and opaque catalog-owned targets;
provider identity, parameter selection, request construction and execution remain
server-only. Human approval binds the exact immutable ordered plan. Each operation
rechecks authority, expiry, the persistent fence and the previous verified revision.
A durable per-operation journal precedes the single guarded dispatch. Failures stop
later operations; dispatched uncertainty retains the fence without retry/rollback.
No route, AI execution tool, OAuth permission, secret, table or migration is added.
Private plan bindings behind a live fence remain until safe resolution; the
closed schema and one-fence-per-user invariant bound unresolved storage. Safe
terminal journals retain only statuses under the 15-minute purge policy. Raw CAD stays request-local. See [A1](HACKATHON_MODIFY_A1.md) for exact
shape/quantity limits, privacy boundaries and required future HTTP/CSRF controls.
CAD writes remain OFF and new-operation live conformance remains unverified.

## Modify planner (B1)

The planner route reuses the Modify guard (session, same-origin, CSRF, closed JSON,
8 KiB cap) plus a per-user hourly cap and one-in-flight gate. The model receives only
opaque handles, display labels, feature types, positions and supported operations, and
its output is validated by the server before A1 `prepare()`. Prompts, CAD names, catalogs
and model output are never logged. The route stops at the preview; approval stays a
separate human action. CAD writes remain OFF by default. See
[HACKATHON_MODIFY_B1.md](HACKATHON_MODIFY_B1.md).

## Generalized approval API (A2)

Only authenticated human POST `/api/modify/plans/{handle}/approve` reaches A1's
approval authority. It reuses the original Modify origin/session/CSRF/body guard
and accepts exactly the preview digest. Pending-only PostgreSQL cancellation races
atomically with claim and persists a queryable cancelled/skipped journal; cancel
and status call neither AI, approval nor CAD. The bounded, closed NDJSON stream
exposes no private identities or revisions. Disconnects never replay writes;
application-owned execution continues and status preserves A1's truthful partial
completion/uncertainty and persistent fences. No OAuth or default write-flag change.
See [A2 authority and privacy](HACKATHON_MODIFY_A2.md).

B2's live browser flow strictly parses previews/events/results, keeps authority in
component memory, consumes local approval before dispatch and never retries it.
Context changes abort consumers and clear authority. Names render as ordinary text;
uncertain outcomes use authenticated GET status only. See [B2](HACKATHON_MODIFY_B2.md).

## Modify recovery and deterministic planning

[Phase 16 preparation](PHASE_16_MODIFY_LIVE_CONFORMANCE.md) preserves all existing
write, approval, claim/fence, uncertainty and recovery controls. Real writes stay OFF
through implementation and synthetic verification; no production/OAuth changes.
The later human stage requires the passing automated gate, privately confirmed
disposable owned target, current representation review and explicit approval of each
exact preview. No live validation is claimed. Graph/model facts cannot authorize
payload construction, approval or dispatch. Quantity/rename eligibility remains
separate from the existing parameter-opaque terminal-suppression policy.

The subsequent DEV representation diagnostic reuses existing bounded pinned feature
responses; no additional provider request or mutation is introduced. Startup and
probe admission require DEV/diagnostics-ON/writes-OFF; the new hook rechecks before
projection and emission. Only strict frozen/extra-forbidden fixed categories,
known adapter vocabulary and capped counts can reach local logs after matching-head
checks. No names, CAD/geometry/node IDs, expressions, query contents, arbitrary
provider strings, tokens, URLs or raw JSON are emitted. The registry's pure parameter
validator supplies only a shape-match Boolean; summaries grant no target, proposal,
approval, payload or execution authority. No public payload/header/route, model input,
analytics or persistence is added. The human writes-OFF observation subsequently
confirmed structural eligibility but failed current-UI replacement conformance.
The additional `safe_edit_standard_parameter_coverage` log uses only a finite
public-source vocabulary and closed type/value categories under the same guards
and matching-head checks. It preserves the original report, read budget and caps;
recognition never authorizes an edit. Quantity bookkeeping is reduced to
presence/type/zero/empty classes, never raw values or import markers. Adapter
acceptance was unchanged during that evidence-gathering follow-up.

After the second human writes-OFF checkpoint, the registry adds closed standard
Extrude/Fillet replacement profiles. Expanded shapes require explicit simple-mode
guards and validate every unique ID, exact btType, allowed value, quantity field
and query/array envelope. The 50/38-input map cardinalities bound only this new
profile; the original minimal profile and global feature/read/transport/quantity
limits remain unchanged. Unknown fields, nonempty imports, configured/tolerant
quantities and active richer modes reject. Empty/zero bookkeeping is preserved
without normalization. Complete fresh definitions are copied; only the approved
name or depth/radius expression changes. Full fresh exact-effect verification is
unchanged. Source diagnostics and graph facts still provide no approval or write
authority. Actual current-fixture recheck and human live-write conformance remain
pending; real writes remain OFF during implementation and automated verification.

The subsequent human writes-OFF recheck still failed both replacements. Extrude's
confirmed scope correction changes only defaultScope to the observed explicit
false under NEW/SOLID/BLIND with empty scope; Fillet acceptance is not broadened.
The shared production predicate now raises its generic EditError subtype with an
internal strict frozen failure object limited to known parameter/sentinel and
reason literals. It never includes raw field names, values or CAD/credential data.
The DEV first-failure diagnostic calls that exact predicate, reuses complete
source-matched pinned responses and logs only those closed labels after matching
head and per-record flag guards. No new GET, public route/payload/header, AI input,
persistence, proposal, approval or mutation exists. Production errors remain generic;
the closed detail does not alter claims, fences, stale rejection, microversion
protection, post-write verification, uncertainty, recovery or global bounds.

The common-metadata follow-up accepts only absent/empty-string `parameterName`
and `valueString` on the closed current-UI parameter profiles, as documented
serialization defaults. It does not accept arbitrary provider text. Nonempty text,
wrong primitive types and every nondefault `libraryRelationType` reject. A later
human ordinary-fixture checkpoint established the exact string DEFAULT, matching
the current official schema. Only absence or this exact preserved string is now
accepted; the field is never configuration/import or write authority. Schema
and public standard source do not prove universal provider-internal behavior.
Nonempty imports, configured wrappers and unknown fields still reject. The
production exception may carry a strict frozen
`CommonMetadataFailure` with only one of the three documented field names,
presence=true and a closed primitive/enum-state label. DEV logs that projection
under the existing guards, never values, object keys or unknown strings. There
is no public/browser/model/analytics/persistent projection and no extra GET.
Accepted placeholders remain in the complete copied definition; omission or any
unrelated post-write delta still fails exact verification, including adding,
removing or changing DEFAULT on any feature. No authority or fence control changes.
The human targeted recheck remains NO-GO until rechecked.

The subsequent query-list investigation adds no filter acceptance. A documented
filter field remains unsupported for every current-UI query role, including empty
selections. Its shared production failure may contain a strict frozen summary of
fixed SDK categories, binary/unary operand counts, visited depth/nodes and closed
flags. Traversal stops at depth 8 or 64 nodes, examines only fixed operand slots,
and never reads leaf values, IDs, query strings or unknown payloads. Unknown type
strings map to unknown; other known opaque types map to other_known. No raw field
name or value can escape. Public errors remain generic unsupported_target. DEV
emission retains diagnostics-ON/writes-OFF, complete/source-matched evidence,
matching-head and per-record guards, with zero extra GETs. The same production
predicate supplies the failure; no second permissive parser or graph authority
exists. All approval, fence, stale, microversion, uncertainty and recovery controls
remain unchanged. Whole-inventory exact verification still rejects filter effects.

A final pre-commit review found that the legacy subset-ID path ignored extra
nested query fields. The Phase 16 safety repair requires complete historical
parameter-ID multisets and exact closed parameter/query envelopes, including
required Fillet tangentPropagation. Failed historical validation cannot fall
through; all other features undergo whole current-UI validation. No unknown nested
field is silently preserved into a replacement. Suppression still transmits only
feature identity/type and the desired suppression attribute, under its existing
independent terminal-Fillet contract. The finding preceded any real proposal,
approval or mutation, with writes OFF. The current real fixture still lacks a
proven filter contract; bounded diagnostic recognition is never write authority.

The exact-signature continuation permits only finite subtype, topology-token
and enum/Boolean-state projections in the same guarded DEV log. Arbitrary strings
map to unknown / unknown_value, never pass through. Local preorder numbers 1–64
are counters, not identities. Missing/null/wrong types are explicit; no defaults
are inferred. Iterative raw traversal caps remain depth 8 / visits 64. Signature
schema/emitter cap at 4,096 characters; schema-maximum log size stays below 16,384.
Unknown/opaque family payloads and unknown fields remain untraversed. Every filter
still rejects; legacy profile, suppression transport and all authority controls
are unchanged. Real topology/leaf semantics require another writes-OFF checkpoint.

The flat-sheet-metal continuation adds only a closed `allows` field projection:
`model_only`, `flattened_only`, `model_and_flattened`, `unknown_value`, `missing`,
`null` or `wrong_type`. Official UNKNOWN and arbitrary strings both become
`unknown_value`; no provider text is logged. Its diagnostic envelope permits only
`btType` and `allows`; extra keys trigger existing unexpected/uninspected flags
without reading their values. This is diagnostic inspection, never acceptance.
Existing log guards, bounds, four GETs, filter rejection and all CAD authority
remain unchanged. No real writes or private fixture reads accompany the patch.

[Recovery controls](MODIFY_RECOVERY_HOTFIX.md) use the existing authenticated
same-origin CSRF guard. Recovery returns only same-session consumed status handles
and safe previews, never approval digests or provider bindings. Reconciliation
performs fresh authorized reads only and closes exactly one matching fence after
strict terminal-suppression baseline agreement and a final authority/head check.
Rename, quantity and batch uncertainty remain fenced for manual recovery.

Cleanup cannot orphan live fences or erase their reconciliation evidence.
Unresolved records remain bounded by the existing one-fence-per-user invariant
and the fixed plan schema; closed status records expire normally. No new persistence of client
authority, scope, model tool or mutation route is introduced. Development-only A2
verification logs contain fixed stage/result categories only.

## Deployment hosting foundation

**DEPLOYMENT FOUNDATION IMPLEMENTED — NOT YET HOSTED.**
The image uses one non-root worker and one Railway replica, with private-only
PostgreSQL planned. Production static roots must be explicit, absolute and built,
without symlinks; routes expose only SPA entrypoints and asset directories.
No API/auth fallback, extra frame ancestor, X-Frame-Options conflict, CORS wildcard
or postMessage relaxation is introduced. Production docs remain disabled.

The canonical security origin stays validated APP_BASE_URL. Uvicorn ignores proxy
headers; internal HTTP does not remove Secure cookies or alter OAuth/CSRF origins.
Exact PostgreSQL URLs are parsed and standard PostgreSQL schemes normalized to the
existing psycopg driver without logging URL material. Production configuration
still rejects incomplete OAuth, missing encryption/database/static setup or HTTP.

The deny-by-default Docker context, nested exclusion canaries and final filesystem
inspection guard against env/certificates/Git/local data entering the build/image.
Backend-only keys are supplied at runtime. Alembic runs separately before deploy;
startup only checks schema. No live migration, OAuth/AI/CAD call, recovery change
or CAD write is part of this phase. Ingress callback-log redaction, private-network
configuration, backup restore verification and actual embedded cookie validation
remain operational gates. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Phase 12 internal graph boundary

The deterministic model graph is private, read-only and request-local. It consumes
existing normalized evidence with an explicit expected context; it never acquires
CAD, reads raw provider documents, persists data or exposes a new endpoint/model
tool. Strict frozen schemas and semantic checks reject malformed, mixed-context,
stale or revision-conflicting inputs; every fact retains bounded provenance and
availability. Browser selection references remain unverified observations without
feature/part/body ownership or inferred topology continuity.

Graph JSON contains private opaque CAD references and sanitized display metadata;
it must not be logged or treated as access/approval evidence. No credentials, raw
provider payloads or model reasoning are included. Future consumers must preserve
existing owner/session/lifecycle controls and further minimize AI context. This
phase changes no deployment, OAuth, CSRF, write flag, safe-write predicate or recovery
behavior. See [the graph contract](PHASE_12_FORGE_MODEL_GRAPH.md).

## Phase 13 Inspector adoption

The direct Inspector route supplies the independently request-validated workspace
reference to graph construction after the unchanged final session/grant check.
Full graph/Snapshot feature correspondence is checked before display truncation;
rich evidence joins by same-Snapshot opaque provider ID only. Graph rejection returns
fixed `invalid_response` unavailable evidence without logs, graph bytes or exception
inputs. Authorization stops discard partial evidence with their existing fixed code.
Other Inspector consumers retain their prior path. No acquisition, persistence,
public graph API, frontend data, OAuth scope or write/recovery authority is added.
See [Phase 13](PHASE_13_INSPECTOR_GRAPH_ADOPTION.md) for failure semantics and limits.

## Phase 14 Ask Forge adoption

Ask Forge constructs a graph only after its existing authorized acquisition returns,
from the accepted normalized Snapshot and independently validated request context.
Snapshot context cannot validate itself. The shared private pure projection checks
full graph/Snapshot identity and order correspondence before caps, using exact opaque
provider IDs for rich evidence. No additional provider read or authority is added.
Authorization stops bypass graph construction; final session/grant checks and request
cancellation continue to prevent use of discarded evidence.

The model sees bounded quoted canonical statements, never graph serialization,
node/edge/provider/context IDs, provenance or session/OAuth data. Only AVAILABLE
PRECEDES edges yield order facts. UNKNOWN/missing relationships prove nothing;
returned order is not dependency or ownership, and only completeness/end rollback
can prove a terminal. The semantics caveat is fixed server text and part of the
existing 65,536-byte bound. CAD names cannot change policy or create verified claims.
Overflow or graph/correspondence rejection fails closed without legacy fallback or
private errors. Existing authorization-specific failures remain distinct.

Selected FACE/EDGE ownership stays UNKNOWN even with singleton inventory and a
terminal feature. Recognized writes retain authorized inspection, zero model calls,
zero CAD writes and no proposal/Modify invocation. Direct Inspector remains Phase 13;
Tutor/Learn/Check my step/Modify remain unmigrated. No persistence, schema/migration,
OAuth scope, public graph API, topology continuity, engineering correctness or new
CAD authority is introduced. Reads remain sequential/non-atomic. Writes remain OFF;
Railway remains unhosted. See [Phase 14](PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md).

The authorized UX polish adds deterministic display formatting only. Exact fact
IDs/statuses and server statement grammar are required; duplicate/conflicting
identities or unmatched wording retain the original response. CAD names stay DOM
text, never HTML or policy. No model prose becomes a verified fact. Contextual
Limits change prominence only: the full uncertainty array, canonical evidence,
original answer and capture time remain accessible in Evidence. Selection UNKNOWN
and read-only capability authority are unchanged; no CAD write path is added.

## Phase 15 Tutor graph adoption

Only explicit learner-requested Tutor CAD inspection adopts the Phase 14 shared
grounding path. The same accepted Snapshot is constrained by independent validated
`TutorRequest.context`, after existing acquisition lifecycle checks. No extra
provider request, graph persistence, selected FACE/EDGE grounding or public graph
data is added. Invalid graph/correspondence evidence fails closed, with no legacy
interpretation or private validation details. Admission/provider throttle stops
are forwarded distinctly before graph construction. Final session/grant checks
and cancellation still prevent discarded evidence reaching the answer provider.

Canonical AVAILABLE adjacent PRECEDES facts establish order only, not dependency
or ownership. Missing/UNKNOWN relationships prove nothing; terminal facts require
the existing completeness/end rollback proof. A fixed semantics caveat survives
model selection. Server presentation distinguishes explicit relationship intent
and unsupported model-specific prose from ordinary educational use/input questions
and general CAD teaching. A general prefix or unknown word cannot exempt a named/
current-model claim. Already-projected names are escaped literal data, never proof
or policy. Only explicit learner relationship intent selects server-owned teaching;
incidental unsafe model fields are discarded without changing the question's
topic. Simple structural primary answers use the canonical count/feature/AVAILABLE
adjacent order catalog, never new model claims, inferred missing links or names
as identities. Closed grammar rejects unmatched facts; partial evidence remains
partial, duplicate-label lookup stays ambiguous, and zero inventory requires a
verified zero count. Proven terminal text or existing unknown copy remains server-
owned. Closed two-name dependency questions can additionally surface their exact
verified adjacent order without model-selected IDs. Every candidate name pair is
checked; duplicate names, ambiguous quoting/delimiters, unmatched fact grammar or
missing/UNKNOWN order retain the conservative fallback. No graph internals, index-
only ordering or transitive order is used. Canonical direction stays the same for
reverse dependency questions, with dependency explicitly unconfirmed. Ownership
questions retain the existing safety response. Reply/evidence bounds and all
check/CAD source separation remain unchanged.
CAD strings stay JSON-quoted untrusted data; graph/provider/context IDs and
provenance never reach Tutor model/browser payloads. Combined application/check
context and CAD evidence must fit the existing evidence byte bound or fail closed.

Check my step remains deterministic and unchanged, including the signed session-
bound token, tamper/step rejection and authentic expiry behavior. Check findings
and current CAD observations keep separate sources and capture times; a new CAD
read never changes a historical verdict. No correctness, completion or investigation
authority is granted to the Tutor. Existing explicit-send, auth/CSRF, quotas,
provider, strict output, no-conversation-persistence and read-only controls remain.
No new scope, CAD write, FeatureScript, Modify invocation, migration or deployment.
Direct Inspector = Phase 13, Design Ask Forge = Phase 14, Learn Tutor = Phase 15;
Modify remains unmigrated. No topology continuity, engineering correctness or new
CAD authority; reads remain sequential/non-atomic. Full UI overhaul remains future
work; Railway remains unhosted. See [Phase 15](PHASE_15_TUTOR_GRAPH_GROUNDING.md).
