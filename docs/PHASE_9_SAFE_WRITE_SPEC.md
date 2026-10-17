# Phase 9A — first safe CAD edit specification

> Historical Phase 9A design/preparation checkpoint. Its “9B not started” and
> future-tense statements describe that checkpoint. Subsequent explicit Phase 9B
> authorization produced the [runtime implementation review](PHASE_9_REVIEW.md),
> which governs current implementation status, operational deviations and pending
> human conformance gates. The historical mandatory-complete-state-map prerequisite
> is superseded by the explicitly authorized terminal-suppression evidence policy
> in that runtime review:
> exactly empty means unavailable, never OK/inactive; complete maps remain strict.
> Its mandatory ordinary auxiliary-suppression object is also superseded by the
> explicitly authorized null-unavailable mode. Optional parent/configured flags now
> use explicit independent evidence modes rather than false defaults; suppressed
> remains an explicit hard Boolean. See the current runtime policy for exact checks.
> All other structural/body/version and approval/write safeguards remain required.
> Phase 9A remains PREPARATION COMPLETE; Phase 8 remains
> COMPLETE, HUMAN VALIDATED, and MERGED. No real OAuth app change or CAD-write
> validation is claimed. Phase 10 remains NOT STARTED.

Status: **PREPARATION COMPLETE; runtime implementation NOT STARTED.** Research date:
2026-10-17. This is a future Phase 9B design, not an implemented capability or
permission to change CAD. Phase 8 is now **COMPLETE, HUMAN VALIDATED, and MERGED**
into main at `81199ea95df04b34e6065441cad87d60b637dcf2`, as confirmed by the user.
Merge `4f168423ce917014312c6946015f9659be0e8e0e` integrates it into this preparation
branch. **Phase 9B: NOT STARTED.** The original Phase 9A preparation remains `b95e866`.

## 1. Executive summary and authorization boundary

Select exactly one operation: **suppress one currently active, ordinary standard
Fillet that is the final user feature in an unconfigured workspace Part Studio**.
Operation identifier: `suppress_terminal_fillet_v1`. Only `false → true` is allowed.
This skips that fillet during regeneration; it is a real geometry-affecting edit.
It is neither Hide nor Delete, and is not a general suppression toggle.

Use Onshape's official partial `updateFeatures` mechanism with a one-entry list,
server-authored suppression attributes and microversion-skew rejection. A complete
feature replacement is unnecessary and would increase the fields at risk.
No measurement input or FeatureScript evaluation is needed.

Phase 9A changes documentation only. No pure domain implementation is added:
the required write evidence must be reconciled with the now-merged Phase 8
contracts during explicitly authorized 9B work; preparation does not implement it.
No routes, tools, UI controls, scopes, app settings, dependencies, database models
or migrations change. The existing read-only refusal remains operational.

The API schema provides the required revision guard, but its inherited description
uses addition terminology even on updates. The exact suppression payload and
provider-side stale rejection on this endpoint require controlled Phase 9B
conformance validation. **Failure of either gate rejects this mechanism and blocks
the first write; a check-then-write without a provider guard is never a fallback.**
No live write, OAuth grant inspection or provider write capability is claimed here.

## 2. Existing implementation audit

| Area                   | Actual merged behavior and consequence for Phase 9B                                                                                                                                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication         | `auth/routes.py` derives user from an opaque, hashed, revocable session; eight-hour absolute and one-hour idle defaults. `active_session` also binds configured stack/company.                                                                                                        |
| OAuth                  | `auth/provider.py:authorization_url` sends no runtime scope parameter. Onshape app registration owns permissions. Documented current permissions are `OAuth2ReadPII` + `OAuth2Read`; no new live-settings claim is made.                                                              |
| Credentials            | `auth/tokens.py` obtains backend-only access, coordinates refresh under a grant row lock, rotates generation and encrypts refresh tokens. A refresh itself changes generation; record proposal generation after acquiring the token, and conservatively invalidate on later rotation. |
| Provider transport     | `integrations/onshape/contracts.py` allows four fixed v17 GETs at `https://cad.onshape.com`; `client.py` rejects redirects, bounds JSON/bytes/time and never retries. Existing transport stays read-only.                                                                             |
| Evidence               | `models.py`, `normalize.py`, `inspector.py` project request-local provider data. Inspector exposes ordinals rather than provider feature IDs; quantities are unevaluated expressions and physical units unverified.                                                                   |
| Missing write evidence | Normalized features do not retain feature-state diagnostics, suppression configuration/expression/parent state or subfeatures. `ProviderDocument.raw` is request-local, not a public authorization contract. No client ordinal can become a write target.                             |
| Freshness              | Snapshot retains document source microversions server-side. Four separate workspace reads remain non-atomic/unverified even if markers match. Capture timestamp and browser launch microversion cannot establish write freshness.                                                     |
| Selection              | Validated single FACE/EDGE category and opaque reference; no proven feature ownership. Never use it to target this operation.                                                                                                                                                         |
| AI                     | `ai/service.py` allows one `inspect_current_cad({})`; explicit recognized write requests get server-owned refusal after authorized inspection with zero AI calls. Every other AI path also has read tools only.                                                                       |
| Routes/CSRF            | CAD GETs require session CSRF and same-origin checks. `ai/routes.py` demonstrates bounded JSON POST handling. `require_mutation` protects account POSTs but also requires an empty body; it cannot be used unchanged for future JSON proposals.                                       |
| Admission              | `ReadGate` is process-local, per-user, one active request, five-second cooldown, 32 active / 1,024 tracked capacity. It is insufficient for write consumption across workers.                                                                                                         |
| Audit/errors           | Existing `AuditKind`/`AuditOutcome` allowlists contain authentication codes only. Fixed public errors and no raw HTTP/SQL payload logs; request-validation defaults that echo data must remain suppressed.                                                                            |
| Persistence            | Six authentication tables plus Alembic revision table; only `0001_authentication`. No proposals, execution journal or history today.                                                                                                                                                  |
| Learn/UI               | Phase 7 authored, memory-only fundamentals without CAD/AI calls. Shared Button/Dialog/StatusBadge/GlassSurface and frozen solid reading layer remain canonical. Old DEV-only Modify examples are synthetic and cannot become write approval.                                          |

Read the historical phase reviews as evidence of their respective checkpoints.
Their old “next phase not started” wording does not override current authorization.
The original Phase 9A preparation did not copy unfinished Phase 8 work. The
completed Phase 8 implementation is now integrated by the normal merge above. Its
Mounting Bracket lesson/checker uses fresh authorized evidence, deterministic
PASS / FAIL / WARNING / UNVERIFIED, feature-name-independent requirements, the
single-L-profile alternative and verification revocation/restoration. It remains
read-only and does not supply write approval or atomic write freshness. The original
[Phase 8 review](PHASE_8_REVIEW.md) is unchanged; its provisional status wording
is superseded by the user's final validation/merge confirmation.

## 3. Official sources and reproducible research

Only official Onshape sources inform provider claims. Forge policy choices below
are explicitly design decisions, not promised Onshape guarantees.

| Ref | Official source                                                                                                                              | Finding / limit                                                                                                                                                                                                       |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | [Live OpenAPI](https://cad.onshape.com/api/openapi)                                                                                          | Downloaded public schema directly on 2026-10-17, without credentials. Current server `/api/v17`; `info.version=1.222.90730-c8d74e607a47`; SHA-256 `d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`. |
| S2  | [Explorer: updateFeatures](https://cad.onshape.com/glassworks/explorer/#/PartStudio/updateFeatures)                                          | Human-browsable operation reference. Text browser received a JS shell; S1 supplies the actual operation/schema evidence.                                                                                              |
| S3  | [Features guide](https://onshape-public.github.io/docs/api-adv/featureaccess/)                                                               | Feature read/add/update/delete workflows; IDs must come from inspection. Feature updates must preserve necessary fields. Examples explicitly describe v9 and do not override S1.                                      |
| S4  | [Onshape architecture](https://onshape-public.github.io/docs/api-intro/architecture/)                                                        | Workspaces advance, versions/microversions are immutable, geometry references have revision limits. Configuration omission is unsuitable for assuming the browser's active configuration.                             |
| S5  | [OAuth2](https://onshape-public.github.io/docs/auth/oauth/)                                                                                  | Delegated user access, consent/revocation and token lifecycle. Do not copy sample insecure transport or generic API forwarding.                                                                                       |
| S6  | [Developer settings and permission scopes](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm#Permission_scopes)            | Named profile/read/write/delete/share/purchase scopes; app permission management. Reviewed page dated 2026-10-09.                                                                                                     |
| S7  | [Evaluating FeatureScript](https://onshape-public.github.io/docs/api-adv/fs/)                                                                | Lambda evaluation endpoint is not a documented persistent-edit substitute. No FeatureScript needed for the selected edit.                                                                                             |
| S8  | [Feature and Part Lists](https://cad.onshape.com/help/Content/PartStudio/features_and_parts_lists.htm)                                       | Suppression skips a feature; dynamic/configured/parent effects and rollback differ from ordinary suppression.                                                                                                         |
| S9  | [Versions and history](https://cad.onshape.com/help/Content/Document/versions_and_history.htm)                                               | User-managed restoration exists; whole-workspace restoration has broader effect than reversing one feature state.                                                                                                     |
| S10 | [API limits](https://onshape-public.github.io/docs/auth/limits/) and [response codes](https://onshape-public.github.io/docs/api-adv/errors/) | Handle quota/rate failures; neither retries nor HTTP success proves CAD state.                                                                                                                                        |
| S11 | [Configuration guide](https://onshape-public.github.io/docs/api-adv/configs/)                                                                | Configuration must be treated explicitly. This operation excludes configured Part Studios.                                                                                                                            |

The downloaded public schema is outside Git in a temporary file. No private CAD
capture or SDK/dependency is added. Phase 9B must fetch S1 again and review relevant
contract changes rather than pinning an old example forever.

## 4. Candidate comparison and ranking

H/M/L mean relative suitability, not safety certification. All actual feature-edit
candidates require broad `OAuth2Write`; none has feature-scoped OAuth permission.

| Rank / candidate                            | Target / current visibility                                                  | Typed preview / units                                           | Verification / recovery                         | Blast radius / mechanism                                       | Decision                                                                   |
| ------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1. Suppress terminal standard Fillet        | H with full inventory, final-position and state checks                       | H, strict Boolean, no units                                     | H for suppression state; manual reactivation    | Lower within Part Studio; one partial update; no FS            | **Selected**, tightly restricted                                           |
| 2. Change literal blind Extrude depth       | H only for simple supported Extrude with exact parameter                     | H with explicit literal units; many enum/second-direction cases | H for stored parameter; geometric effect harder | Can affect all downstream geometry; replacement/partial update | Defer                                                                      |
| 3. Suppress arbitrary feature / unsuppress  | H ID, M activity semantics                                                   | H Boolean but parent/configuration state matters                | State readable; reactivation can fail           | Potentially removes a base body or regenerates descendants     | Reject broad toggle                                                        |
| 4. Change sketch dimension                  | M; constraints, driving/reference status and ownership complicate resolution | M; expressions/units/solver involved                            | M; stored value need not prove solved geometry  | Potential solver/downstream effects                            | Defer                                                                      |
| 5. Add bounded feature                      | M; geometric queries and new identity required                               | M; more fields and entity references                            | M; deletion/inversion not automatically safe    | New topology, retries can duplicate features                   | Defer                                                                      |
| 6. Static Forge-owned FeatureScript feature | M; still needs typed CAD queries                                             | M; code/version maintenance                                     | M; regeneration and result checks required      | Extra code authority unnecessary here                          | Reject for first write                                                     |
| 7. Rename feature                           | H; bounded string                                                            | H; no measurement units                                         | H label check / inverse label                   | Very low geometric effect                                      | Useful metadata but weaker demonstration of real CAD editing; not selected |
| 8. Model-generated FS or generic HTTP       | Unbounded                                                                    | Unbounded                                                       | Untrustworthy                                   | Arbitrary authority                                            | Prohibited                                                                 |

The chosen edit has useful teaching value: compare a finished edge to its preceding
shape while retaining the feature definition. It does not demonstrate dimensional
engineering validation. Suppression can affect consuming elements/documents and
remove functional edge treatment; terminal position is not proof of global safety.
First validation is confined to a disposable, unlinked, single-Part-Studio document.

## 5. Exact selected operation and eligibility

All checks are deterministic and fail closed. For the first supported release:

- Authorized standard-stack workspace Part Studio, never version/microversion,
  assembly, read-only shared document or linked-document-only access.
- Full bounded feature inventory with `isComplete=true`, unique feature IDs,
  explicit source document microversion and serialization/library versions.
- Target is an ordinary `BTMFeature-134`, `featureType=fillet`, empty standard
  namespace, last top-level user feature, with no subfeatures, parent suppression,
  configuration suppression or dynamic suppression expression. Unknown state fails.
- Target is explicitly `suppressed=false`; its provider feature status is OK and
  not inactive. All other feature states must be known OK. No implicit Boolean
  defaults from the existing read projection authorize a write.
- Configuration definition at the same pinned microversion must explicitly prove
  no configuration inputs; missing/unknown configuration evidence blocks editing.
  Reject folders/nested/custom features anywhere in the initial supported fixture.
- Entire initial feature list is restricted to standard Sketch/Extrude/Fillet,
  at most 20 top-level entries, with no derived/imported/custom features. One solid
  body, no surfaces/mesh/composite bodies in supported evidence. Unknown fails.
- User explicitly identifies/confirms the inventory target. A sole eligible target
  is still previewed; never reinterpret “remove selected face” as suppress Fillet.
  Multiple plausible named targets prompt clarification, even if only one is
  currently eligible. A nonterminal requested Fillet is unsupported, not retargeted.

Eligibility limits are Forge policy. The existing inspector does not prove these
conditions today. Phase 9B needs strict additional provider projections in the
existing integration layer, not a parallel evidence framework. External downstream
usage cannot be proven absent by terminal position or current inspection; retain
that limitation and the disposable-document validation restriction.

## 6. Official mechanism and transport boundary

S1 operation `updateFeatures`, production and nondeprecated:

```text
POST /api/v17/partstudios/d/{did}/w/{wid}/e/{eid}/features/updates
request: BTUpdateFeaturesCall-1748
response: BTUpdateFeaturesResponse-1333
scope: OAuth2Write
```

S1 describes partial parameter updates and optional suppression-attribute updates.
This is preferable to `updatePartStudioFeature` (full replacement at
`.../features/featureid/{fid}`). A list-shaped provider API does not authorize batch
edits: Forge's adapter must enforce **exactly one** target and no parameters.

Planned minimal body shape, **not a tested payload or executable recipe**:

```json
{
  "btType": "BTUpdateFeaturesCall-1748",
  "sourceMicroversion": "<server-owned approved document microversion>",
  "rejectMicroversionSkew": true,
  "serializationVersion": "<from pinned authoritative feature response>",
  "libraryVersion": 0,
  "updateSuppressionAttributes": true,
  "features": [
    {
      "btType": "BTMFeature-134",
      "featureId": "<server-resolved feature ID>",
      "suppressed": true
    }
  ]
}
```

Here `libraryVersion:0` is a schema-shape placeholder, not a value to send. Copy
the actual inspected library version unchanged. `updateSuppressionAttributes` has
no explanatory field text in S1; suppressionState's polymorphic variants also
exist. Do not guess extra attributes, copy complete unvalidated provider objects,
or fallback to full replacement. Phase 9B must establish, in its isolated
conformance harness, which ordinary-state fields are required and that omitted
parameters/name/type/queries remain unchanged. Freeze the proven exact request
schema before enabling a normal approval path. If it needs materially broader
payload authority, stop and amend this decision with review.

Future private adapter exposes only `suppress_terminal_fillet(authorized_context,
claimed_proposal)`. It privately fixes host, version, method, path, headers and
serialization. No public raw request method, no client token, no model-supplied
HTTP arguments, no redirects/proxy environment, no automatic write retries. Keep
the existing `OnshapeReadClient` four-GET restriction unchanged; add a separately
reviewed private write boundary in 9B only.

## 7. OAuth audit and future permission transition

Current documented app permissions: `OAuth2ReadPII` for identity and `OAuth2Read`
for four CAD reads. Additional minimum for S1 `updateFeatures`: **OAuth2Write**.
Keep read/profile permissions for supporting reads/authentication. No Delete,
Share, Purchase or Internal scope is required.

Write scope is broad document-write authority within the user's Onshape access,
not constrained to this feature, panel or disposable document. Forge's object and
operation gates must supply that narrower boundary; document ACLs still apply.
There is no claim that OAuth grants one-operation authority. Compromise of the
backend/token is a residual risk beyond prompt/tool restrictions.

Future registration permission change requires **explicit human authorization in
Phase 9B**. Existing users must obtain a newly consented write-capable grant before
using writes; Forge must never assume token refresh silently upgrades consent.
If old consent is reused, the future human procedure may revoke/regrant the dev
app. Exact provider re-consent behavior must be verified then. Logout alone does
not revoke the grant. Do not change Action URL, redirects, keys or app listing.

Known missing write scope produces `write_permission_required`; uninterpreted
bitmask/missing scope is not decoded by guesswork. Gate activation needs tested
proof of new grant capability. A 403 with unknown scope remains
`permission_or_access_required`, not falsely “write scope missing.” No Phase 9A
live application, token, consent or repository permission configuration changes.

## 8. Target resolution and selection

Fresh authorized inventory supplies provider feature identity on the server.
Return a random, short-lived candidate handle and safe label/type/position to the
browser; map it internally to the inspected identity and exact context. Candidate
handles are bound to session, inventory microversion and expiry. They are not
provider IDs. Check membership when handling the user's explicit target choice.
No public contract accepts a free-form feature ID from model output or browser.

If the user names a duplicate or uncertain feature, return `ambiguous_target` and
ask them to choose from the bounded inventory. Present unsupported requested
targets honestly. Ordinal/name alone never authorizes a write. Re-fetch exact
target before proposal and execution; removed/recreated same-name target fails.
Current face/edge selection is unusable for ownership and is not submitted to the
write path. User may confirm the named feature in Onshape's own feature list.

## 9. Unit semantics and bounds

No measurement input: the only transition is strict Boolean `false → true`.
Reject `1`, `0`, negative/zero values, floats, strings such as `"true"`, NaN,
infinity, quantity/expression/unit keys and all additional properties. No radius
or depth changes, conversion, unit default or floating-point comparison exists.
Unsupported-unit/invalid-value errors remain in the defensive test matrix.

Server-owned nonmeasurement limits: exactly one target; at most 20 features;
candidate handle/proposal ID 256 random bits; label at most 256 UTF-8 bytes without
controls (otherwise safe fallback); provider feature ID bounded to 256 characters
and URL-encoded privately if ever used in a path; document/workspace/element/
microversion follow reviewed CadId validation. No geometry ID is assumed to be
24-hex. Proposal body limit 8 KiB, body receive limit five seconds, preview expiry
120 seconds, claimed operation deadline 30 seconds. These are policy values to
implement/test in 9B, not current settings.

## 10. Typed proposal contract — design only

Use strict closed Pydantic records in 9B; all nested data must be immutable too.
Serialized schema version: `forge-write-proposal-v1`. No credentials, prompts,
reasoning, raw features or unrestricted JSON fields.

| Server-authoritative field                                | Type / invariant                                                                                                                  |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `proposal_id`                                             | Random 256-bit handle; unguessability supplements ownership checks                                                                |
| `schema_version`, `policy_version`                        | Exact reviewed literals                                                                                                           |
| `operation_type`                                          | Only `suppress_terminal_fillet_v1`                                                                                                |
| `owner_user_id`, `owner_session_hash`, `grant_generation` | Internal binding only; never credentials in public preview                                                                        |
| `context`                                                 | Fixed provider policy ID, document/workspace/element, revision kind workspace, configuration unconfigured, end-of-list evaluation |
| `target`                                                  | Internal feature ID, standard Fillet classification, position, safe display label and server-authored resolution explanation      |
| `expected_state`                                          | Suppressed false, noninactive OK, terminal and ordinary suppression facts, baseline inventory digest                              |
| `proposed_state`                                          | Suppressed true only                                                                                                              |
| `source_microversion`                                     | Authoritative document microversion, not browser timestamp                                                                        |
| `serialization_version`, `library_version`                | From pinned provider record, unchanged                                                                                            |
| `proposal_digest`                                         | SHA-256 over canonical complete immutable content, excluding mutable lifecycle fields and the digest itself                       |
| `created_at`, `expires_at`                                | Server UTC integer seconds; expiry exactly creation +120, never browser clock                                                     |
| `description`, `expected_effect`, `limitations`           | Bounded server-authored preview, with escaped safe label interpolation                                                            |

Public preview includes opaque proposal ID, digest, operation, safe context labels,
target explanation, current/proposed state, effect, limitations and expiry. It
does not expose internal owner/session/grant IDs, raw provider feature IDs or
microversions. Scope labels must not invent document/workspace names: acquire
authorized labels with a reviewed read or use neutral labels plus existing context
display. The proposal digest is not a signature or bearer authorization.

Lifecycle record separately holds state, claim ID/timestamps, fixed outcome and
optional post-write microversion for short-lived reconciliation. Integrity is
server-side storage plus canonical rehash on consumption; never trust a client
echo of content, expected state or new state. Schema/version mismatch fails closed.

## 11. Proposal creation: reads only

1. Validate session, connection, exact Forge Origin/Referer policy, CSRF and bounded
   JSON before quota/provider work. Derive owner and grant from the session.
2. Validate browser context as a request, then authorize each exact object with the
   owner's backend token. Establish real workspace, Part Studio and eligibility;
   an accessible version mislabeled workspace is unsupported, never remapped.
3. Acquire current document head M0, pinned features/configuration/body evidence,
   then head M1. Require M0=M1 and matching returned document source markers.
4. Resolve chosen candidate membership, reject ambiguity, unsupported/missing state
   or already-suppressed target. Validate the one Boolean transition.
5. Freeze proposal and canonical digest. Recheck session/connection/generation
   after reads, then store short-lived authoritative state and emit safe event.
6. Return minimized readable preview. No CAD write or reusable approval is created.

Creating a new proposal cancels earlier unclaimed proposals for that session.
Decline if an execution/reconciliation is unresolved for the workspace. Expired
or changed inventory requires a new explicit request; do not automatically refresh
a proposal into a differently approved model state.

## 12. Approval and future API contracts

Planned API surface only; **none of these routes exists in Phase 9A**:

| Future request                                     | Closed body / effect                                                                                                   |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `POST /api/modify/targets`                         | Validated context only; authorized bounded inventory read and candidate handles                                        |
| `POST /api/modify/proposals`                       | Context plus server-issued candidate handle and the sole operation literal; new suppression value is server-fixed true |
| `POST /api/modify/proposals/{proposal_id}/approve` | `proposal_digest` only; exact explicit approval and atomic claim, then execution                                       |
| `POST /api/modify/proposals/{proposal_id}/cancel`  | Empty body; cancels only an unclaimed proposal                                                                         |
| `GET /api/modify/proposals/{proposal_id}`          | Authenticated owner/session status; read-only reconciliation on explicit request under CSRF/quota protection           |

Proposal identifiers are opaque handles, never chosen provider URLs/paths. No
caller user, session, token, feature ID, arbitrary operation/value/unit, approval
flag or context override is accepted on approve. Unknown fields/query parameters,
duplicate JSON keys, invalid content type and oversized/slow bodies are rejected.
Use constant-time digest comparison. Foreign or missing handles share a fixed
unavailable response, avoiding cross-user existence disclosure.

The **Approve change** button alone initiates the approve request with the exact
displayed digest. No auto-approval, generic “edit this document” grant, chat “yes,”
model call or Enter in the composer constitutes approval. Intent interpretation
and proposal explanation cannot consume this endpoint on behalf of a user.

## 13. Approval binding and storage

Approval binds authenticated Forge user **and the exact session digest**, current
grant generation/provider policy, proposal ID/digest/policy, operation, document,
workspace, element, target feature, suppression attribute, current false/proposed
true, baseline document microversion, configuration/evaluation scope and expiry.
Same account in another session must create its own proposal. A different browser
context cannot substitute new IDs at approval.

Preferred 9B storage: short-lived server-side PostgreSQL operational records,
separate from a user-facing history. **No table or migration is added in 9A.**
9B must review its additive migration/retention design before implementation.
Store only the above minimal binding, baseline digests/states, fixed labels/copy
needed for preview, deadlines and execution outcome. Raw feature lists/bodies stay
request-local; reacquire baseline by pinned microversion for verification.

Unclaimed private proposal data expires at 120 seconds. Strip preview/target/
revision data on cancellation, expiry, logout, session invalidation or resolved
completion; retain only owner-scoped random handle, consumed flag and fixed outcome
tombstone for 15 minutes. Purge by a 60-second bounded cleanup task and lazily on
access. No indefinite proposal-content retention, history UI, prompts, model output
or analytics.
Pending ambiguous-execution binding may remain up to 15 minutes solely for
read-only reconciliation; it is never a live authorization after claim. Then
delete private binding and present manual-recovery guidance if state is lost.
An unresolved safety fence retains only a server-keyed HMAC of workspace identity
and a fixed blocked state until explicit human reconciliation. It contains no CAD
payload, target, values or authorization and cannot execute anything. This minimal
deny marker must survive proposal cleanup and restart; deleting expired proposals
must never silently unblock an uncertain workspace. Include this deliberately
longer-lived operational denial in the 9B privacy review. Restore/loss of fencing
state requires an operator write-disable and reconciliation gate before reopening.
Backups must exclude these short-lived operational tables or have an approved
retention policy; TTL alone does not remove historic backups. If that privacy gate
is not met, do not deploy the write feature.

## 14. Lifecycle and single use

```text
PENDING -> CANCELLED | EXPIRED | INVALIDATED
PENDING -> CLAIMED -> REJECTED_STALE | WRITE_FAILED
                    -> VERIFYING -> VERIFIED_SUCCESS | UNVERIFIED_RESULT
                    -> EXECUTION_UNCERTAIN -> reconciliation only
                                             -> UNVERIFIED_RESULT | RECOVERY_REQUIRED
```

Approve consumes PENDING via one conditional database update, checking owner,
session, digest and expiry using server time. Claim is committed **before** any
provider mutation. An approved-but-unclaimed reusable state is deliberately absent.
Duplicate approval returns the same minimized status/used state with zero writes;
never changes it back to pending. All failures after claim consume the approval,
including auth loss, stale state and failures known not to have applied.

Expiry and context/session/grant changes invalidate unclaimed proposals; context
change in the UI sends best-effort cancellation and removes preview. Backend binds
to the stored context regardless of that best effort. Browser navigation is not
an authenticated provider-side event: Forge cannot prove the physical active tab
has not switched. The approved target remains the displayed bound workspace, and
9B must test late-navigation suppression. Never claim UI focus provides security.

Logout/disconnect must invalidate pending proposals in the same local transaction.
Invalidation after an already dispatched write cannot recall the external request;
return no private CAD to the ended session, retain safe consumed outcome and
require reauthentication/manual inspection. No further write follows cancellation.

## 15. Version, microversion and freshness strategy

S1 supports these official reads (future additions, not current allowlist):

```text
GET /api/v17/documents/d/{did}/w/{wid}/currentmicroversion
GET /api/v17/partstudios/d/{did}/m/{mid}/e/{eid}/features
GET /api/v17/elements/d/{did}/m/{mid}/e/{eid}/configuration
```

`getCurrentMicroversion` returns `BTMicroversionInfo.microversion` for a workspace
head. Features' `sourceMicroversion` identifies the document revision read;
`serializationVersion` describes encoding compatibility, **not** edit freshness;
`libraryVersion` is not a revision counter. Workspace ID identifies a mutable
branch, version ID a named immutable snapshot, microversion ID immutable state.
Do not conflate document microversion with `elementMicroversionId`, body export
markers, feature ordinals or browser launch metadata. No fabricated “feature list
version” counter or ETag/If-Match support is assumed.

Pin authorized feature/configuration/body reads to M, explicitly require supported
configuration/evaluation semantics, and bracket acquisition with head reads.
Current read snapshots are useful research/projection infrastructure but cannot
replace this stronger gate. Pinning proves the baseline, not that head stays still.

Immediately after consuming approval and before dispatch: reacquire backend token,
session and grant; require exact bindings, unexpired proposal and claim deadlines,
head M, pinned
target and baseline digest match. Any document change, even unrelated or edit-then-
undo with same visible value, invalidates approval. Return:

> The model changed since this proposal was created. Review the updated model and create a new proposal.

Never silently rebase. A missing marker, malformed state, unsupported provider
schema/library or failed read means no write, not “probably current.”

## 16. Race analysis and provider rejection

Send the **approved** source microversion and `rejectMicroversionSkew=true` on the
one provider request; never replace it with a new head after approval. Shared S1
schema documentation says a mismatch rejects rather than attempts reinterpretation.
The presence of the flag on `BTUpdateFeaturesCall-1748` is verified; the inherited
text refers to additions, so update behavior is a hard 9B conformance gate.

Required proof: change the document after final Forge freshness check but before
dispatch, then issue the old-marker update in disposable CAD; provider must reject
without modifying suppression. Repeat concurrent competing updates and a change
to another element. Record actual safe status class/outcome, not guessed conflict
code. If the provider does not atomically guard this update, **reject the mechanism**
and stop; a local mutex, matching timestamps or immediate reread cannot fix this
race against collaborators. No alternative write is silently enabled.

Forge database transactions do not encompass Onshape. No rollback, exactly-once
delivery, cancellation-after-dispatch or linearizable browser-focus guarantee is
claimed. Provider rejection plus local single dispatch supplies the intended
bounded safety; it must be established by both contracts and real tests.

## 17. Concurrency and idempotency

9B uses PostgreSQL atomic conditional claims across processes and a workspace-scoped
execution fence shared across users, plus a per-user admission record. Lock/fence
keys derive from server-authorized context; raw CAD IDs stay out of logs. Acquire
fences in a fixed order; commit claim and fencing ownership before dispatch.
Hold a dedicated connection's advisory lock through final check/write/verification;
persist a short-lived in-progress marker so connection/process loss does not let a
second worker replay the proposal. Lock loss forbids dispatch; orphaned CLAIMED
becomes uncertain, never requeued. No lease expiry may redispatch a write.

Acquire/refresh the token before taking final authorization row locks; then lock
the bound session and grant, revalidate generation, expiry and ownership, and
retain those locks through the dispatch decision. Logout/disconnect must use a
compatible fixed lock order, so revocation committed before that decision wins.
Revocation ordered after dispatch cannot cancel a provider operation. Never hold
a grant lock while recursively invoking TokenManager's separate refresh transaction.
Specify and race-test the exact lock order in 9B before connecting its adapter.

One pending proposal/session, one active execution/user and one unresolved
execution/workspace. Admission conflicts return status safely; they do not take
over another user's proposal. Provider microversion guard remains mandatory even
with locks. An unresolved fence expires only into **manual recovery required**,
not automatic permission to overwrite; re-enabling that workspace after orphaned
execution needs explicit user inspection and a new proposal after uncertainty is
resolved. If coordination state is lost, writes stay disabled until reconciliation.

Proposal ID is the Forge idempotency key. No provider idempotency-key contract was
established in S1. Do not send an invented header or equate setting a Boolean with
safe network retry. A second identical target state is `already_suppressed` with
no request, never a second successful edit. Browser retry/status retrieval can
return the existing consumed result but cannot dispatch. Worker crash recovery
runs reads only. New proposal after a definitive failure requires explicit user
action and fresh evidence.

## 18. Execution architecture and budgets

```text
User intent -> authorized fresh inventory -> target clarification
 -> immutable proposal -> deliberate preview approval
 -> atomic claim + workspace/user fences -> session/object reauthorization
 -> exact baseline + provider revision guard -> ONE suppression request
 -> fresh authorized reads -> deterministic result -> truthful UI
```

The private executor consumes a server-created validated claimed object; it is not
registered as an AI-callable tool. AI can request a high-level proposal, never
approve or execute. Adapter rejects any internal payload drift too: extra target,
parameter modification, arbitrary JSON/URL/verb/token or FeatureScript fails.
No client context override after claim. No automatic refresh-and-replay on 401,
rate error, timeout or redirect. Refresh before dispatch is allowed under existing
auth controls, but grant rotation invalidates an older proposal conservatively.

Future per-user limits: proposals/target reads at most six/minute with five-second
cooldown and bounded global admission; execution at most one/ten seconds. Approval
claims are atomic independent of UI disabling. Existing read gate remains intact;
private execution verification must have a bounded reserved read budget rather
than being accidentally blocked by a shared five-second UI cooldown. Reconciliation
is explicit, max one/ten seconds, at most two read batches within the retention
window. Respect provider 402/429/Retry-After; no cross-user global mutable approval.

30-second overall execution/verification deadline; connect/read/write/pool
3/8/3/2 seconds, response cap 2 MiB and existing bounded JSON. Proposal acquisition
max six provider reads; execution max one write plus eleven reads: five for final
head/features/configuration/body/head checks, five for the equivalent verification
batch, and one pinned baseline feature read for definition comparison. Exact request
inventory must be enforced by tests; exceed
budget => no dispatch or unverified outcome as appropriate. No polling/spend loop.

## 19. Post-write verification

Only deterministic server code can produce `VERIFIED_SUCCESS`. HTTP 2xx is an
acknowledgement, not CAD verification. Require all of:

1. Parse bounded response, correct target, no reported microversion skew, expected
   suppression attributes, valid post-operation document marker M2 different from
   baseline M, and no provider feature errors. Missing marker is unverified.
2. Fetch fresh authorized feature/configuration/body evidence pinned at M2 and
   bracket with workspace head reads. Require stable head M2 throughout; later
   concurrent edit produces `UNVERIFIED_RESULT`, not a claim about current CAD.
3. Exact target still same standard Fillet at same position, now suppressed true
   with ordinary suppression state. Preceding features remain OK. Target inactive
   status must match the **conformance-tested** provider suppression behavior;
   never interpret inactive alone as success or demand ordinary active status.
4. Compare baseline and after definitions using a reviewed semantic projection:
   exact feature IDs/order, names/types/namespace, all parameters/query definitions,
   subfeatures and suppression fields. Only target suppression/equivalent ordinary
   suppression metadata may change. Provider-derived node bookkeeping needs a
   proven explicit normalization, not a broad ignore-list. Unknown drift fails.
5. Verify one solid remains and no new body/type error or lost original feature.
   Topology IDs/counts may legitimately change when rounding is removed; never
   require old geometry IDs to stay equal. Missing evidence is unverified.

Verification establishes the supported feature-state transition and preserved
definitions, not exact geometry equivalence, manufacturing safety, mass or engineering
PASS. The 9B human test inspects intended edge changes and unrelated geometry.
Do not invent a numerical geometric validator or Phase 8 checker result.

Success copy: “Fillet 1 is now suppressed. Forge verified the updated feature
state.” Add “Geometry and engineering suitability have not been validated.”
Only show safe target label, no private IDs. Record verified capture time; do not
promise the workspace cannot change afterward.

## 20. Failure, timeout and crash outcomes

| Event                                                                             | Outcome / action                                                                                              |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Bad context/value, unsupported/ambiguous target, auth/access failure before claim | Fixed rejection, no provider write; no approval created                                                       |
| Expired/tampered/foreign/used approval                                            | Reject, zero writes; do not disclose foreign proposal                                                         |
| Stale final evidence/provider stale rejection                                     | `REJECTED_STALE`, consumed; new proposal required                                                             |
| Definitive provider refusal proven not applied                                    | `WRITE_FAILED`, consumed; sanitized reason and explicit fresh-proposal option                                 |
| Network timeout/disconnect/5xx, malformed success, crash after claim              | `EXECUTION_UNCERTAIN`; may have applied, zero automatic replay                                                |
| Upstream acknowledgement but verification fails/unavailable                       | `UNVERIFIED_RESULT`; never success; read-only reconciliation                                                  |
| Response lost but read shows desired state                                        | Observed suppressed state can be reported, attribution remains unverified without matching execution evidence |
| Target mismatch, other definition drift, damaged model or unresolved ambiguity    | `RECOVERY_REQUIRED`; block further writes in workspace pending human inspection                               |
| Session revoked/logout during dispatch                                            | Cannot recall upstream; suppress private result and further requests; reauthenticate for inspection           |
| Crash after verification before local result commit                               | Orphaned claim stays uncertain; future read may reconcile, never reexecute                                    |

Do not classify every 4xx as definitely not applied without provider-specific
evidence. Partial success remains possible until inspection. A read failure after
2xx does not imply a rollback. A final read showing unchanged state after timeout
does not prove a delayed provider request will never apply; keep fence/recovery.

## 21. Recovery and truthful Undo

No automatic rollback or Undo endpoint/button. `true → false` is outside the sole
Forge operation; reversal would be another write requiring fresh authorization
and evidence. Reusing the consumed approval or blind inverse state is forbidden.

After verification the user can inspect the feature in Onshape and use its own
suppression controls to reactivate it; confirm ordinary context-menu behavior in
the disposable 9B test. Provider-native history restoration is an alternative under
user control (S9), with explicit warning that it can restore a broader workspace
state and affect intervening edits. S1 `restoreFromHistory` exists and requires
write scope, but Forge must not call it for this phase. Do not promise that an API
edit appears in the browser's immediate Undo stack; that was not established.

For uncertain writes: “The change may have occurred. Inspect the feature in
Onshape before trying another change.” For verified suppression: “To reactivate
the feature, review it in Onshape and use its suppression controls.” No automatic
undo, rescue script or fabricated restored-success state.

## 22. Audit and privacy

Future safe codes: `write_proposal_created`, `write_proposal_approved`,
`write_proposal_cancelled`, `write_proposal_expired`, `write_proposal_invalidated`,
`write_rejected_stale`, `write_execution_started`, `write_execution_acknowledged`,
`write_execution_failed`, `write_execution_uncertain`,
`write_verification_succeeded`, `write_verification_failed`,
`write_recovery_required`. Acknowledged is intentionally distinct from verified.

Extend existing fixed audit-code literals in 9B, not free-form metadata. Existing
safe audit table may store fixed kind/outcome, Forge user and UTC time only, under
existing approved security retention. Proposal/CAD IDs, digests, labels, prompts,
raw errors, URLs, values, cookies and tokens are excluded. Operational logs may
use only a random correlation, fixed stage/outcome/status class, bounded duration
and dispatch count. Failure to commit the execution-start/claim state means no
dispatch. A crash between provider action and later audit is an honest missing
outcome, not proof of failure or success.

No persistent CAD edit history, usage analytics, prompts/responses, model reasoning
or provider payloads. Short-lived proposal privacy/cleanup/backup policy is in
section 13. Ingress/APM must suppress path proposal handles and all private CAD
queries, headers and bodies as well as normal auth/AI suppression. No screenshots
or debug captures are committed. Minimized proposal explanations need no new AI
transfer; CAD names remain untrusted escaped text.

## 23. AI and deterministic authority

| AI may request/explain                                                              | Deterministic Forge owns                                                                        |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Interpret suppression intent, ask clarification                                     | Session, CSRF, exact object authorization and provider host                                     |
| Request the sole high-level proposal operation using server-issued candidate handle | Inventory membership, feature identity/type/state, all eligibility checks                       |
| Explain a server-created preview using its fixed facts                              | Closed schemas, limits, units prohibition, canonical immutable proposal                         |
| Describe a server-returned result without upgrading status                          | Approval binding/consumption, expiry, freshness, locks, dispatch, verification, recovery, audit |

The model cannot select arbitrary document/workspace/element/feature IDs, URL,
HTTP verb, token or FS, create approval, change policy, retry a used proposal,
invoke the executor, or assert success. No generic Onshape request function in any
tool schema. CAD names such as instructions to bypass approval remain inert data.

## 24. CSRF, session and object authorization

Reuse existing authenticated session, generation checks, secure cookie, HMAC CSRF,
no-store/no-referrer/nosniff, exact Forge origin and revoked-grant controls. The
parent Onshape origin is not Forge's mutation origin. SameSite=None/embedded status
never exempts CSRF. Reject duplicate Origin/CSRF, null/foreign Origin and cross-site
Fetch Metadata. If Origin is absent, permit only the existing exact-origin Referer
fallback plus valid token; do not accept absent/null evidence as origin proof.

Implement a small reviewed JSON-mutation guard in 9B using the existing security
primitives and bounded request handling. Do not loosen account empty-body routes
or copy the CAD GET's missing-Origin allowance into approvals. Recheck session,
owner, provider stack/company, grant generation/status and object access before
dispatch and before publishing private verification. Read access alone does not
prove edit permission; provider ACL enforcement on the exact write is final.
Revoked or expired authorization does not produce a mock success or automatic retry.

## 25. Focused threat model

| Threat                                                                  | Required mitigation / remaining limit                                                                                         |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Wrong user / cross-account                                              | Session-derived owner; foreign handle yields generic unavailable; provider uses only owner grant                              |
| Wrong session / stolen proposal handle                                  | Exact session hash plus CSRF/origin and digest; handle alone has no authority                                                 |
| Wrong document / workspace / element                                    | Frozen authorized tuple, server workspace/type checks, no approval override, fresh provider ACL                               |
| Wrong feature / invented IDs                                            | Server inventory handle membership and exact ID; duplicates/unknowns ask or fail; no ordinal or FACE ownership join           |
| Stale model or approval                                                 | Baseline document microversion, final read, guard on write, all-document changes invalidate                                   |
| Proposal modified after approval                                        | Closed request, immutable server state/canonical digest, fixed true, tamper rejection                                         |
| Reused / double execution / browser retry                               | Committed atomic claim, shared fences, consumed terminal state, status-only replay                                            |
| Simultaneous different users in workspace                               | Shared workspace fence plus provider revision guard; user records isolated                                                    |
| Forged client request / CSRF                                            | Authentication, exact Forge origin/Referer and secret token; bounded JSON/headers                                             |
| AI arbitrary URL/HTTP/operation/token/FS                                | No such tool fields, fixed adapter, strict enum and one-target payload; executor not model-callable                           |
| Malicious CAD names / prompt injection                                  | Escaped display data, no privileged interpolation, no authorization from model text                                           |
| Unexpected unit / NaN / infinity / overflow / extreme / negative / zero | No measurement input; strict Boolean literals only; reject all extra keys/types and bounded body                              |
| Configured/expression/parent suppression                                | Inspect strict ordinary-state evidence and no config inputs; unknown blocked                                                  |
| Check/write race / collaborator edit                                    | Provider guard conformance gate; local lock alone is insufficient                                                             |
| Timeout / response loss / ambiguous error / partial success             | Consume, uncertain result, read-only reconciliation, no write retry or blind inverse                                          |
| Upstream success / local verification failure                           | Unverified result, never green success; workspace fence and manual recovery as needed                                         |
| Process crash / DB disconnect / lost fence                              | Commit before dispatch, orphaned claims never replay; no takeover on lease expiry                                             |
| Session expiry / logout / revoked grant                                 | Atomic pending invalidation and pre/post checks; dispatched work cannot be recalled                                           |
| Quota / proposal spam / duplicate click                                 | Per-user limits and global admission; independent shared atomic consumption                                                   |
| Logging private payload / error leakage                                 | Fixed audit/error codes, no raw exceptions, default validation echo suppressed; ingress/APM review                            |
| Broad OAuth token compromise                                            | Backend-only credential containment; scope remains broad, not eliminated by tool safety                                       |
| External consumers / unexpected geometry                                | Terminal feature restriction lowers local impact only; no global dependency/safety claim; disposable validation               |
| Browser context changes without server notice                           | Bound preview target, frontend cancellation/late-result suppression; physical active tab is not authoritative server evidence |

## 26. Fixed public error contract

| Code / HTTP category                                              | User-facing meaning / next action                                                             |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `unsupported_edit` / 422                                          | This edit is not supported. Explain the supported suppression only.                           |
| `ambiguous_target` / 409                                          | Choose which listed feature you mean; no proposal yet.                                        |
| `target_unavailable` / 409                                        | Target is missing, unsupported or no longer eligible; inspect again.                          |
| `already_suppressed` / 409                                        | This feature is already suppressed; no change was made by this request.                       |
| `session_expired` / 401                                           | Sign in again; old approval is invalid.                                                       |
| `permission_or_access_required` / 403                             | Access could not be established; do not conflate unknown scope with document ACL.             |
| `write_permission_required` / 403                                 | Write authorization is missing when known; future reconsent only after human permission gate. |
| `csrf_failed` / 403                                               | Request could not be authorized; reopen/retry safely.                                         |
| `proposal_unavailable` / 404                                      | Unavailable/foreign handle without existence leak.                                            |
| `proposal_expired` / 409                                          | Review a new proposal.                                                                        |
| `proposal_used` / 409                                             | This approval was already used; existing status may be shown.                                 |
| `proposal_tampered` / 409                                         | Preview no longer matches; discard and create a new one.                                      |
| `context_changed`, `model_changed` / 409                          | Bound context/model changed; no rebase, create new proposal.                                  |
| `invalid_value`, `unit_unsupported` / 400                         | Only the supported suppression state is accepted; measurements unsupported.                   |
| `request_in_progress`, `rate_limited` / 409 or 429                | Wait/use existing status; never resend execution automatically.                               |
| `onshape_unavailable` / 503                                       | Before dispatch: no write; after dispatch: uncertain result instead.                          |
| `execution_failed`                                                | Consumed definitive failure, fresh proposal only if safe.                                     |
| `execution_uncertain`, `verification_failed`, `recovery_required` | May have changed; inspect/reconcile without replay.                                           |

Execution outcomes are typed response data when available; a transport status is
not sufficient to decide success. Fixed copy only, no stack traces/provider payloads.

## 27. Proposal UX and accessibility

Future Modify view uses the existing workspace scroll region and solid reading
layer. No phase numbers/provider jargon, new cards, sparkle, giant glow, alarm-red
ordinary proposal or nested modals. Existing functional glass Button treatment is
appropriate; design-system business logic stays in backend.

Textual preview, design only:

```text
Suppress Fillet 1
Active → Suppressed

Target: Fillet 1, final feature in this Part Studio
Why this target: you chose this feature from the inspected list.
Expected effect: regenerate the model without this fillet.
Limits: geometry and engineering suitability are not validated.
Other models that use this part may be affected.

Cancel       Approve change
```

Display immutable context summary with meaningful authorized labels or neutral
scope wording; support inspection through existing CAD Context. Never abbreviate
away current/proposed states. State change buttons are absent in Phase 9A.

Keyboard order: summary/target and optional limitations disclosure, Cancel,
Approve change. No autofocus on Approve, no automatic submit on content/target
selection, no keyboard trap outside a genuine existing Dialog if one is needed.
Accessible heading and description announce full operation/current/proposed values.
Approval semantics are explicit in button name/description. Disable duplicate
dispatch and preserve readable preview while executing. Separate real status
announcements: Checking model, Applying change, Verifying result, then outcome.
An executing operation cannot be advertised as cancellable/undoable after dispatch.

Use polite status announcements; fixed errors use appropriate alert with focus
on recoverable message. Colors always accompany words/symbols. Respect reduced
motion/transparency, high contrast/forced colors; do not add indefinite animation.
At 320px, states and buttons wrap without horizontal scrolling and remain in the
single vertical reading plane. Test keyboard/focus restoration, screen readers,
zoom, long hostile names, disabled/executing status and result navigation.

## 28. Synthetic fixture specifications

Specifications only, not another CAD evidence schema or runnable fake integration.
Build actual fixtures in 9B against merged Phase 8 and the reviewed provider types.
Use symbolic document/workspace/element M0/M1 labels in documentation; generate
invented valid-shaped IDs in tests. Never use private identifiers or captures.

| Fixture                                              | State / required assertion                                                                                           |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `ordinary_terminal_fillet`                           | Sketch → simple Extrude → ordinary active Fillet, all OK, one solid, complete/unconfigured at M0; preview false→true |
| `ambiguous_label`                                    | Two same-label Fillets or ambiguous user reference; clarification before eligibility/approval                        |
| `missing_target`                                     | Handle not in authorized inventory or target removed; zero writes                                                    |
| `nonterminal_or_custom`                              | Later feature/custom namespace/subfeatures/folder; unsupported                                                       |
| `configured_or_dynamic`                              | Configuration input, expression or parent suppression; unsupported                                                   |
| `missing_evidence`                                   | Missing flags/state/source/version/completeness; no optimistic defaults                                              |
| `stale_target`                                       | Target recreated with same label/new ID at M1; reject                                                                |
| `changed_current`                                    | Target already suppressed at M1; stale/used request cannot write                                                     |
| `wrong_workspace`, `wrong_element`, `wrong_document` | Single binding field changed, no object read/write through foreign grant                                             |
| `tampered_proposal`                                  | Changed digest/type/target/value/unit/owner/session/expiry; rejected                                                 |
| `provider_success`                                   | One suppression acknowledgement at M2; fresh pinned read required                                                    |
| `provider_failure`                                   | Proven rejection with unchanged model; consumed failure, no retry                                                    |
| `provider_timeout`                                   | Apply then lose response, do not apply then timeout, delayed apply after timeout; uncertain and no replay            |
| `verification_success`                               | Target true, other definitions intact, expected states, one solid, stable M2                                         |
| `verification_mismatch`                              | Wrong target/false state/changed parameters/missing solid/new head; no verified success                              |
| `recovery_case`                                      | Uncertain or bad result, manual inspection/reactivation; no automatic inverse                                        |
| `crash_and_duplicate`                                | Concurrent workers/users, lost response/connection after claim, repeated approval; at most one dispatch              |
| `hostile_label`                                      | CAD name requests arbitrary HTTP/approval bypass; escaped inert preview, no privilege change                         |

## 29. Phase 9B automated test matrix

All default tests use invented fixtures and injected transports; no real AI, OAuth
or Onshape writes. A mock proves Forge behavior, never provider atomicity.

| Suite                  | Required cases / assertion                                                                                                                                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Auth and context       | Proposal/targets/status require auth and valid context; wrong user/session/document/workspace/element rejected; expired session, logout and revoked grant before/after reads/dispatch; version mislabeled workspace rejected                           |
| CSRF                   | All proposal/approve/cancel mutations require correct token and exact Origin or authorized Referer fallback; duplicate/missing/null/foreign headers/cross-site rejected; iframe offers no exemption                                                    |
| Targets                | Exact server inventory membership; wrong feature/missing/recreated/custom/nonterminal/duplicate IDs; ambiguous names ask; no FACE/EDGE-to-feature inference; model inventing arbitrary feature ID cannot enter adapter                                 |
| Closed schemas         | Invalid operation, extra URL/HTTP verb/OAuth token/FS fields, raw JSON, extra targets/parameters, invalid units, value `false`, integers/zero/negative/extremes, strings, NaN/infinity and overflow tokens rejected                                    |
| Integrity              | Valid immutable nested proposal; canonical hash stable, every security-relevant field tamper changes digest/rejects; client current/new state/expiry not trusted                                                                                       |
| Lifecycle              | Pending/cancel/expiry/invalidation/claim/failure/success; exact-boundary expiry; used approval never restored; UI cancel races with claim have one winner                                                                                              |
| Staleness              | Different document head even same value, edit-undo, workspace/version change, serialization/library/policy mismatch, target/parameter digest drift; no automatic rebase; final head-check/write race sends original M and rejection flag               |
| PostgreSQL concurrency | Two workers same approval, different approvals same workspace, different users same workspace, same user different workspace, browser retry/double click; one dispatch, owner isolation, fencing, lock loss, orphaned claim/no lease replay            |
| Provider adapter       | Exact standard HTTPS host, fixed POST path, one-entry suppression body, actual library/version, approved source M, reject skew true; no generic transport exposure, redirects/proxy/retries; no widening of existing read client                       |
| Failure reconciliation | 401/403/402/429/5xx/timeouts, partial/ambiguous/malformed response, crash before/after dispatch/local commit, delayed success, response lost; never optimistic success or replay                                                                       |
| Verification           | Fresh reads required despite HTTP 2xx; wrong feature/suppression/definition/state/body/head causes unverified/recovery; successful state proof distinct from engineering validation; no false geometry equivalence                                     |
| Privacy/audit          | Correct fixed event/outcome, no secrets/CAD payload/name/digest/ID/prompt/provider errors in logs/errors; no history/browser storage; cleanup/backup policy; state expiry never reauthorizes                                                           |
| UI/Playwright          | Exact current→proposed hierarchy, deliberate approve, Cancel zero writes, duplicates disabled, context loss/late results, uncertain execution copy, no fake Undo; 320/360/380/400/480/640px, three engines, keyboard/axe/reduced effects/high contrast |
| Retained regressions   | Read-only Design refusal and zero provider calls, inspector four GETs, fundamentals sample no AI/CAD requests, bracket checks explicit read-only CAD with no AI, auth/scopes unchanged unless explicitly reviewed 9B change, no new history/analytics  |

Minimum malicious tool cases explicitly inject feature ID, provider host/URL,
verb, bearer token and FeatureScript both as arguments and CAD strings. Test
outgoing captured requests, not just an error message. Parameterized table-driven
cases must assert zero write calls for every rejected input.

## 30. Real Onshape validation plan — 9B only

Prerequisites: all six phase gates in section 33; human-approved permission
transition; safe local logging disabled for payloads; complete automated gates.
Use **only a disposable Forge development document**, single unlinked Part Studio,
no important personal/school CAD, no collaborators during ordinary success test.
The human creates a simple block and one terminal standard Fillet using Onshape.
No live write test runs in 9A.

1. Record browser/version/platform and safe symbolic fixture description; keep
   IDs, URLs and numeric CAD payloads private. Confirm fresh workspace and full
   rollback evaluation, no configuration, ordinary active final Fillet/one solid.
2. Complete the isolated provider conformance tests: ordinary suppression payload,
   all other definitions unchanged, resulting inactive/status semantics and exact
   revision markers. A qualified human approves each deliberate harness write.
3. Prove stale rejection using a deliberately old document microversion, including
   a manual change after the final read/before dispatch and another-element edit.
   Use a test-controlled barrier in the dedicated development harness, never an
   arbitrary production API proxy. Confirm provider does not apply suppression.
4. Ask “Suppress Fillet 1.” Verify interpreted target comes from inventory, exact
   Active→Suppressed preview and clear limitations. Check target in Onshape list.
5. Cancel; inspect Onshape feature state, geometry and history: no Forge write.
6. Request again, review then Approve change. Observe actual checking/applying/
   verifying stages. Verify one provider edit, fresh evidence, target suppressed,
   intended edge treatment gone, other feature definitions and unrelated geometry
   unchanged. Success appears only after deterministic verification.
7. Reactivate manually in Onshape for the next case. Request proposal; change CAD
   manually before approving. Expect model-changed rejection and zero Forge edit.
8. Repeat with two approvals/double click/browser retry and simultaneous worker
   requests; verify exactly one dispatch for a claimed proposal, status-only retry.
9. Submit invalid Boolean/numeric/out-of-range/NaN/infinity/unit fields through
   synthetic harness tests. UI requests for dimension changes are unsupported;
   they never become suppression edits. Do not send malformed writes to live CAD.
10. Create ambiguous label/request and nonterminal target; ask clarification or
    reject rather than choosing a convenient feature. Delete/recreate target and
    verify stale ID rejection even if name is unchanged.
11. Let proposal expire; test logout, session loss/rotation, disconnect/revoked
    authorization and read-only document access. No stale approval survives.
12. Use mock/injected transport only for apply-then-timeout, lost response,
    upstream rejection, post-write read failure and crash cases. No success without
    evidence; inspect/reconcile safely, no repeated write or automatic rollback.
13. Test recovery on disposable CAD: inspect state, manually reactivate ordinary
    Fillet via Onshape; verify original intended geometry. Review history restore
    guidance separately, never automatically restore the whole workspace.
14. Reconfirm original/current/proposed/fresh-state evidence and no unintended
    geometry/feature changes. Inspect 320px, keyboard, screen-reader summary,
    status/focus/reduced-motion/high-contrast states. Record honest limitations.
15. Stop only harness/services started for validation; preserve existing services
    and database volumes. Commit final sanitized validation documentation before
    describing the implementation as human-validated.

## 31. Future screenshot plan

Private human review only, **never Git**. Crop to the panel/disposable geometry;
exclude address bar, private IDs, accounts, OAuth codes/tokens, Network tabs, HARs
and unrelated personal CAD. Screenshots do not prove provider atomicity.

| Ref | Required 9B capture                                                           |
| --- | ----------------------------------------------------------------------------- |
| A   | Supported Modify suppression request                                          |
| B   | Interpreted inventory target and why it was selected                          |
| C   | Complete proposal preview                                                     |
| D   | Active → Suppressed state hierarchy (no measurement value for this operation) |
| E   | Cancel and unchanged CAD/state                                                |
| F   | Deliberate approval state                                                     |
| G   | Real executing/verification status                                            |
| H   | Verified successful suppression                                               |
| I   | Fresh evidence result with capture metadata and limitations                   |
| J   | Stale proposal rejection                                                      |
| K   | Invalid value / unsupported measurement request rejection                     |
| L   | Ambiguous target clarification                                                |
| M   | Synthetic execution failure/uncertain result                                  |
| N   | Honest manual recovery guidance/result                                        |
| O   | 320px proposal, continuation/actions and no horizontal overflow               |

## 32. Architecture decision record

Decision: one typed, bounded feature-state change, exact-state approval, one
dispatch and fresh verification. Provider OAuth scope is broader than this policy.

- Generic Onshape API access would let untrusted model/CAD text choose targets,
  methods and payloads outside validated intent; expose no such capability.
- One operation keeps target eligibility, preview, revision behavior and failure
  proof reviewable before expanding authority. No CAD tool library/general Modify.
- Exact model-state binding prevents old consent being applied to a different
  object/version/feature meaning. Workspace ID alone cannot bind moving state.
- HTTP success cannot prove regeneration, target state, unchanged definitions or
  fresh authorized evidence. Verified CAD state requires deterministic reads.
- Automatic rebase changes what was approved; reject stale proposals and ask for
  a new review. A visually identical value at a newer revision is still stale.

Consequences: broader intent is refused, configured/nested models excluded,
ambiguous timeouts require inspection, and occasional conservative invalidation
is preferable to unapproved changes. No certification or production readiness.

## 33. Phase 8 integrated; remaining hard start gate

Phase 8 is **COMPLETE, HUMAN VALIDATED, and MERGED** into main at `81199ea` and
integrated into this branch by merge `4f16842`. Reuse its actual lesson/checker and
authorized evidence infrastructure; do not create a second Check My Step system,
lesson engine or evidence framework. Review the merged checker/evidence/freshness
contracts before any future write integration. Never scrape lesson presentation,
interpret PASS as write approval or reuse read-only freshness as write authorization.

Start-gate status:

1. Phase 8B implementation: complete.
2. Real human Onshape validation: complete, confirmed by the user.
3. Phase 8 documentation: preserved from incoming main. Its original provisional
   wording is unchanged by instruction; current completion is recorded here and in
   the roadmap from the user's final confirmation.
4. Phase 8 merge to main: complete at `81199ea`.
5. Normal main integration into this branch: complete at `4f16842`; both histories
   retained with intentional documentation reconciliation.
6. **Explicit Phase 9B authorization: still required.** Separately obtain human
   approval before any write-scope/app-permission transition.

No runtime Phase 9B work is authorized by integration alone.

## 34. Known blockers and residual limits

- Phase 8 is complete and integrated. Explicit Phase 9B authorization and future
  permission-transition approval remain outstanding.
- S1 schema is authoritative structural evidence, not real-write validation.
  Suppression payload, dynamic/omitted-default exclusions, returned inactive/status
  behavior and atomic reject-on-skew for `updateFeatures` are mandatory live gates.
  If no sufficiently strong update guard can be proven, reject this mechanism.
- Existing inspector omits write-critical state; no broadening by inferred defaults.
  Add only the necessary projections/allowlisted reads after reviewing the merged
  Phase 8 contracts under explicit Phase 9B authorization.
- Future short-lived operational storage/fencing needs reviewed migration,
  cleanup/backup and PostgreSQL concurrency tests; none implemented in 9A.
- Broad OAuth privilege, other-document consumers and eventual external operations
  remain real risks. No universal rollback, exactly-once network delivery,
  engineering geometry validation or browser-focus attestation exists.
- Unknown provider scope reporting may need a documented capability-proof strategy
  in the new consent gate; never guess bitmask assignments or probe random writes.

## 35. Exact Phase 9B implementation order

After section 33, re-audit actual merged main/status/docs; retain Phase 7/8 behavior.
Refresh S1 research and resolve conformance gates in an isolated disposable-document
harness with the human, never by enabling a broad runtime route first. Freeze the
proved payload and verification projection; stop if atomic rejection is inadequate.

Then implement strict missing evidence projections in the existing integration
layer, pure closed proposal/lifecycle/domain tests, short-lived reviewed storage/
fences, CSRF-protected contracts and the private one-operation adapter. Establish
all zero-write rejection tests before connecting UI approval. Integrate the frozen
design primitives, enforce uncertain-result/recovery semantics, run full quality,
browser/PostgreSQL/security gates and the human plan/screenshots. Commit final
sanitized results; do not expand scope to a second write or Phase 10.

**Phase 9B: NOT STARTED.** Phase 9A ends with documentation, regression checks and
normal branch publication only. No write scope, endpoint, tool, executable
FeatureScript, active CAD approval or real model modification is authorized here.
