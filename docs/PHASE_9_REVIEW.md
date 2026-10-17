# Phase 9B first safe CAD edit review

Status: **IMPLEMENTED / AUTOMATED TESTED / AWAITING CONTROLLED HUMAN CAD-WRITE VALIDATION**.
Phase 8 is **COMPLETE, HUMAN VALIDATED, and MERGED** at
`81199ea95df04b34e6065441cad87d60b637dcf2`, integrated by `4f168423` without
squashing. Phase 9A is **PREPARATION COMPLETE** at `b95e866`. Phase 10 is
**NOT STARTED**. This review describes runtime work authorized after the historical
[9A specification](PHASE_9_SAFE_WRITE_SPEC.md) and
[preparation review](PHASE_9_PREP_REVIEW.md).

No real Onshape mutation, OAuth developer-app change, or real write flag activation
was performed during implementation. Gate A and Gate B below are **NOT VALIDATED**.
The default flag is OFF. Automated synthetic provider behavior does not prove real
provider conformance, production readiness, or engineering safety.

## Read-only target-discovery investigation

Human validation subsequently reached authenticated Modify target discovery:
OAuth2Write was added **by the human**, explicit reauthorization succeeded, and
ReadPII / Read / Write were authorized while Delete / Share / Purchase stayed off.
The writes-disabled check and unsupported-delete refusal passed. With temporary
human-enabled writes, discovery returned generic `unsupported_target` despite the
disposable visible Sketch → Extrude → ordinary active terminal Fillet and the
inspector's three active features / one solid body. The Fillet settings were opened
and cancelled; **zero CAD writes occurred**. Gate A and Gate B remain **UNPROVEN**.

The investigation keeps writes OFF; the configured settings and running local API
were checked without exposing environment contents. No OAuth app permissions or
mutation transport were changed. The initial diagnostic-only checkpoint changed
no accepted eligibility states. The human has now supplied the first live rejection:

```text
safe_edit_reject reason=rollback_active position=None field=rollbackIndex expected=end_of_list actual_type=integer actual_boolean=None
```

This identifies the exact failing check: response `rollbackIndex == -1`. The line
reports integer type, not the numeric value; do not claim a captured live value of
3 or that the whole target is eligible. No private CAD payload was saved as a fixture.

### Rollback response contract correction

The current [official OpenAPI](https://cad.onshape.com/api/openapi), fetched again
for this correction, retains version `1.222.90730-c8d74e607a47` and SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`getPartStudioFeatures` request `rollbackBarIndex` is an int32 with default -1,
meaning evaluate at the list end. The separate response field
`BTFeatureListResponse-2457.rollbackIndex` is also int32; its current description
**explicitly allows -1 as an end-of-list sentinel**. Therefore -1 is not an
undocumented negative value and remains accepted under that explicit contract.

The current [official feature-access example](https://onshape-public.github.io/docs/api-adv/featureaccess/#get-the-list-of-features-in-a-part-studio)
uses request `rollbackBarIndex=-1` yet returns response `rollbackIndex: 4` for
four user features. The guide labels its examples v9; the current v17 schema still
permits integer response indices and explicitly describes the sentinel. Together
these sources support an exact concrete list-end index and the documented sentinel;
they do not support arbitrary nonnegative indices. `defaultFeatures` are separate
from the returned user `features` array and are not added to this count.

Forge's old **-1-only** response check was too narrow: it rejected the officially
illustrated concrete end position. The correction validates a complete bounded
feature list first, then requires:

```python
type(rollback_index) is int and rollback_index in (-1, len(features))
```

The concrete accepted index is exactly the feature count (3 for three, 4 for four).
The sole negative exception is the explicit current OpenAPI -1 sentinel. Zero,
interior or beyond-end indices, other negatives, absent/null values, Boolean,
string and float values reject with the same safe `rollback_active` diagnostic.
Python Boolean subtyping cannot pass the strict integer test. Completeness and
all configuration, suppression, feature-state, body and version checks remain.
The request query, write transport, guard and mutation payload are unchanged.

Safe-edit synthetic helpers now report the concrete feature count. Dedicated
regressions cover both documented representations, three/four-feature inventories,
invalid indices/types, incomplete inventory and a later namespace rejection.
No later predicate was loosened. The correction adds 30 synthetic regressions;
163 focused evidence/domain/diagnostic tests passed. The full backend gate passed
1,034 tests including ten real PostgreSQL cases with no skips; 642 frontend tests,
format, lint, TypeScript, strict mypy (91 files), production build and dependency
audits also passed. No browser code or public error contract changed.
**Zero real CAD writes; writes OFF; Gate A UNPROVEN; Gate B UNPROVEN.** The next
human Inspector probe may correctly expose another predicate and must remain
read-only.

`eligibility.py` now defines closed fixed reasons and bounded diagnostic metadata.
Each deterministic rejection logs `safe_edit_reject` with reason, known field,
expected category, primitive type, optional Boolean and feature position (1–20).
There are no names, feature/CAD IDs, arbitrary keys, payload values, query content,
tokens or private URLs in the diagnostic. Public error details remain unchanged:
ordinary rejection is `unsupported_target`; duplicate identity retains the existing
`ambiguous_target`. No diagnostic endpoint or response header was added.

The optional backend `FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED` defaults false and is
valid only in development with writes OFF. An explicit authenticated, CSRF-checked
CAD Inspector refresh then runs the existing pinned safe-edit **read** path inside
the existing quota gate. It logs the first rejection (or fixed eligible/read-failure
outcome), creates no candidates/proposals/fences and never calls the mutation
method. Snapshot, AI and Learn requests do not invoke this opt-in probe. The
underlying `write_client.py`, guard and write payload remain untouched.

Current official OpenAPI was fetched again during investigation: version
`1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
Relevant definitions are `BTFeatureListResponse-2457`, `BTConfigurationResponse-2019`,
`BTMFeature-134`, `BTMSuppressionState-1924`, `BTMNode-19`, `BTFeatureState-1688`
and `GBTNodeStatusType`. [Official feature access](https://onshape-public.github.io/docs/api-adv/featureaccess/)
describes omitted encoded defaults, but labels its examples v9; schema optionality
alone does not prove every missing/null value is safe in the current v17 response.
The observed failing field must be compared with its specific contract before any
acceptance change. In particular, no blanket missing-Boolean→false rule was added.

If the live probe cannot be run directly, the exact human **read-only** repeat is:

1. Keep the disposable document active. Keep writes OFF. Restart only the local
   development API using:

   ```sh
   FORGE_CAD_WRITES_ENABLED=false FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true make dev-api
   ```

2. Open Forge's existing **CAD Inspector** and explicitly click **Refresh CAD**.
   Do not approve a change or enable writes. The usual inspector remains read-only.
3. Copy only the backend terminal line beginning `safe_edit_reject reason=...`
   (or `safe_edit_probe outcome=...`). It contains no private CAD content. Do not
   paste other logs, URLs, cookies or provider payloads.
4. Compare that first condition with the official contract. Leave eligibility
   unchanged until a documented equivalent representation is established. Turn
   the optional diagnostic flag back off afterward; writes stay OFF throughout.

Synthetic tests cover exact rejection reasons, missing/null distinctions, unchanged
fail-closed checks, log privacy, default/production guards and GET-only inspector
probing with no operational records or public diagnostic leakage. The focused gate
passed 133 tests (90 existing safe-edit and 43 diagnostic cases). The full gate
passed 1,004 backend tests including ten real PostgreSQL cases with no skips, plus
642 frontend tests including Phase 8 regressions. Format, lint, TypeScript, strict
mypy (90 files), production build, whitespace/local Markdown links and dependency
audits passed; no dependencies changed. No browser rerun was needed because no
frontend or public response contract changed. No real write or provider conformance
success is claimed. Those counts describe the diagnostic-only checkpoint. The
rollback contract correction above supersedes its formerly pending first-predicate
classification; later predicates and both real write conformance gates remain open.

## Implemented scope and authority

Exactly `suppress_terminal_fillet_v1`: one ordinary standard final active Fillet,
`suppressed: false` → `suppressed: true`. There is no unsuppress, toggle, rename,
parameter edit, creation, deletion, batch operation, automatic rollback or Undo.
Learn and Design retain their read-only CAD boundaries. The Mounting Bracket,
deterministic fresh Check my step, PASS / FAIL / WARNING / UNVERIFIED, feature-name
independence, single-L alternative, completion and verification revocation/restoration
remain in the existing Phase 8 implementation. Its review is unchanged.

Modify uses a deterministic closed intent grammar, including “suppress the final
fillet”, “turn off the last fillet”, and “temporarily remove the final edge fillet”.
Other intents are refused. No new hosted AI request or tool is needed. The existing
AI gets no approval, execution, provider ID, transport or payload authority. CAD
names are inert display strings rendered as text, never instructions or authority.
Current FACE/EDGE selection does not establish feature ownership.

Server eligibility requires a workspace Part Studio on the configured standard
`https://cad.onshape.com` v17 stack, unconfigured configuration, complete 3–20-feature
inventory, unique feature IDs, only standard `newSketch` / `extrude` / `fillet`, at
least a Sketch and Extrude, a final Fillet, no namespace/subfeatures/parent suppression,
known ordinary nonconfigured suppression, no rollback and known OK states. Exactly
one SOLID body and known matching nonambiguous, nondeleted microversion are required.
All other features must be active. Unknown or missing critical evidence rejects the
target; no Boolean defaults are inferred. Duplicate identities reject as ambiguous.
The narrow final-feature policy permits at most one eligible candidate. Even this
candidate requires a separate explicit human choice; name, ordinal and selection
do not authorize it. Unsupported earlier Fillets are not offered as alternatives.

Additional authoritative projection lives beside the existing bounded read client
and body model. No second inspector, context store, lesson engine or checker was
created. Existing read client contracts remain read-only.

## Current official contract research

Rechecked 2026-10-17 from official sources:

- [Current public OpenAPI](https://cad.onshape.com/api/openapi): API v17;
  `info.version=1.222.90730-c8d74e607a47`. Download SHA-256
  `d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
  `updateFeatures` accepts `BTUpdateFeaturesCall-1748`, OAuth2Write, optional
  suppression attributes, sourceMicroversion, rejectMicroversionSkew,
  serializationVersion and libraryVersion. Current microversion and pinned
  feature/configuration/body endpoints were inspected, including suppression and
  feature-state schemas. No critical discrepancy from 9A was found.
- [Feature access](https://onshape-public.github.io/docs/api-adv/featureaccess/):
  feature definitions, IDs and serialization considerations.
- [Architecture](https://onshape-public.github.io/docs/api-intro/architecture/):
  document/workspace/version/microversion identity and immutable microversions.
- [Developer app permissions](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm):
  explicit app permission choices and authorization boundary.
- [Provider errors](https://onshape-public.github.io/docs/api-adv/errors/) and
  [limits](https://onshape-public.github.io/docs/auth/limits/): failures and quotas
  are not permission inference or automatic retry authorization.

The shared `rejectMicroversionSkew` description refers to feature addition. Schema
presence alone does **not** establish atomic rejection for updates. Ordinary
suppression field presence/defaults, inactive state after suppression, response
marker semantics, and unchanged definition behavior remain Gate A/B questions.
If real evidence omits required fields, stop and review the official contract;
do not guess defaults or weaken policy to make a test succeed.

The sole mutation is:

`POST https://cad.onshape.com/api/v17/partstudios/d/{did}/w/{wid}/e/{eid}/features/updates`

```json
{
  "btType": "BTUpdateFeaturesCall-1748",
  "sourceMicroversion": "<approved baseline>",
  "rejectMicroversionSkew": true,
  "serializationVersion": "<captured version>",
  "libraryVersion": 0,
  "updateSuppressionAttributes": true,
  "features": [
    {
      "btType": "BTMFeature-134",
      "featureId": "<server-resolved target>",
      "suppressed": true
    }
  ]
}
```

`libraryVersion: 0` above illustrates the numeric field shape only; the actual
value is always the captured provider value, never a constant. There are no
parameters, generated FeatureScript, browser IDs or arbitrary JSON bags. The
private client fixes host, version, methods, endpoint families and payload;
rejects redirects, non-JSON/encoded/oversize responses; bounds request to 8 KiB,
response to 2 MiB and each call/deadline; and never retries a mutation. It is not
registered as an AI tool or exposed as a generic HTTP endpoint.

## Proposal, approval and execution

The flow is intent → fresh authorized candidate evidence → opaque candidate →
explicit target choice → fresh immutable proposal → preview → **Approve change** →
committed atomic claim/fence → fresh authorization/evidence → final head check →
provider guarded write → fresh pinned evidence → deterministic verification.
Cancel never calls the provider mutation. No automatic discovery or approval runs
on mounting the panel. A capability GET only reports enabled/permission states.

Random 256-bit URL-safe handles are not provider IDs. Strict frozen closed records
bind schema/policy/operation, user, hashed session, grant generation, exact context,
feature identity/state, baseline document microversion, inventory/configuration
fingerprint, complete captured definition digest, serialization/library versions,
creation and expiry. SHA-256 over canonical JSON protects proposal identity against
browser tampering; the database is trusted server state, not an adversarial store.
Unknown fields and changed digests reject. Candidates and proposals expire in
120 seconds. New preparation invalidates older pending records for that session.
The public preview contains only the opaque handle/digest, fixed operation, safe
label/position, Active, Suppressed and expiry; no provider tokens or raw snapshots.

Routes are authenticated, same-origin, CSRF-bound JSON with Origin or exact-origin
Referer fallback, cross-site rejection, no query fields and bounded parsing.
Approval accepts **only** digest. The action path permits only approve/cancel/
reconcile; no arbitrary provider path or command. Status is session-owner scoped. Status, cancellation and read-only reconciliation
remain available while the write feature flag is OFF.
The API cannot observe browser focus; a navigation unmount removes the UI approval
and aborts its fetch, but a previously approved in-flight mutation continues safely
without retries. Late results do not populate a different context's UI.

An atomic conditional UPDATE pending→claimed and unique fence insert commit
**before** provider dispatch. Claim remains consumed on failure, disconnect or crash.
The client is refreshed before final authorization locks; token generation rotation
invalidates pending proposals. PostgreSQL transaction user advisory lock (before optional user-row locks) → session
row → grant row → operational state is the deterministic shared order. Logout,
disconnect, grant replacement/refresh and dispatch use this coordination. The final
locked check revalidates session, grant, proposal expiry, exact baseline/digest and
current document head. A logout committed before this boundary prevents dispatch;
a logout arriving while dispatch holds the lock serializes after that dispatch.
Collaborator changes are guarded by the **original approved** sourceMicroversion,
never a newly substituted head. Database locking cannot replace provider protection.

One unresolved operation per user and workspace is enforced across workers.
Preparation admits at most six reads per user/minute durably, plus the existing
process read gate/cooldown. Closely spaced discovery/preview clicks may return
“wait before trying again”; explicit retry after the cooldown performs fresh reads.
No write retry is possible. Reads bracket a single pinned document microversion:
head → features/configuration/body at `m/{mid}` → head. Any mismatch rejects.

HTTP acknowledgement is not success. Acknowledgement must identify the target,
explicit suppression and a newer marker without skew. Fresh post-write evidence
must establish the intended same target now suppressed/inactive, supported state,
exact acknowledgement marker, unchanged serialization/library versions and all
captured feature definitions except the intended suppression flag. A 30-second
evidence/dispatch/verification budget prevents late verified success or a new
dispatch after the deadline. An outstanding synchronous read can end later at its
per-call timeout; possible mutation outcomes remain uncertain, never retried. Captured
feature definitions exclude sketch geometry by provider query; this is **not**
full geometry equivalence, downstream reference safety, or engineering validation.
Any unexpected bookkeeping change also fails closed pending contract review.

All ambiguous post-dispatch failures, including timeout, access failure, bad
acknowledgement or verification mismatch, become execution_uncertain. There is no
second POST. Read-only reconciliation deliberately retains the fence and requests
operator recovery; it does not attribute a collaborator's suppression to Forge.
Success text is only “Change verified. Forge confirmed that the selected Fillet is
now suppressed.” Manual re-enabling remains a human Onshape action.

## Persistence, privacy, audit and recovery

Additive Alembic `0002_safe_edit` follows `0001_authentication`. It creates only
`write_records` and `write_fences`, preserves existing auth data and disallows
accidental destructive downgrade. Application startup requires the new schema;
run `make migrate` explicitly before starting the upgraded backend.

Operational records contain random handle, user FK, hashed session, fixed state,
digest, closed proposal JSON, timestamps. JSON contains the necessary CAD identities,
sanitized label, microversion, fingerprints and versions for binding/reconciliation;
no prompt, token, raw feature/configuration/body payload or model reasoning. Pending
payload is cleared on cancel/expiry/invalidation/safe finish. Consumed minimal
records remain tombstones until creation+15 minutes. Uncertain proposal binding may
remain for read-only inspection until that same purge. Cleanup runs every 60 seconds
and on admission/status. Expired claims become uncertain; no resumption or redispatch.
Admission counters have 60-second retention. Cleanup removes operational rows only.

Fences contain stable workspace digest, user FK, proposal handle;
no CAD payload. They have **no TTL** and intentionally no cascading reference to the
operational row. Stable SHA-256 over a domain separator + stack/document/workspace
replaces 9A's proposed token-key HMAC: rotating an encryption key must not erase a
denial. This is a pseudonymous digest of high-entropy IDs, not encryption or a grant
of authority. User uniqueness is an additional conservative denial across workspaces.

Fixed audit events cover creation, invalidation, expiry, cancellation, claim, stale
rejection, dispatch, acknowledgement, verified/failed/uncertain and reconciliation
required. They use existing minimized auth audit storage. No private metadata or
exception contents are attached. Audit retention remains the existing operator
policy; it is not shortened by proposal cleanup. No user history or analytics UI.

Database backups can retain sensitive operational bindings beyond live TTL. Operators
must include them in existing access/encryption/backup retention policy. Restoring
an older database can lose recently created fences: keep writes OFF after restore
until every potentially in-flight operation is reconciled. Loss of operational
state must never be treated as proof no upstream mutation occurred.

Operator recovery is deliberate, outside the application write API: keep writes OFF;
use the opaque recovery reference to inspect the exact record/fence with authorized
DB access; establish that no old request can still execute; inspect disposable CAD
feature state and provider history; record a minimized operational recovery decision.
If upstream settlement or intended state cannot be established, keep the fence.
Only after establishing a safe settled state may an operator remove that **exact**
fence by matching record_id inside a transaction while holding the same user lock.
Never restore a consumed proposal or use expiry/key rotation/database restore to
unblock. New work requires a new proposal and fresh approval. No operator fence was
cleared during implementation. After proposal purge there is no automated context
reconstruction; manual inspection is required.

## UI, accessibility and automated evidence

Modify uses existing auth/context providers, design-system controls, quiet reading
layer and one panel application. It offers intent, separate target choice, semantic
current/proposed summary, limitations, expiry, Cancel, Approve change, real checking/
executing/verifying announcements, explicit errors, uncertainty, status/inspection
and manual recovery. Disabled and permission-required states have no executable
preview. A preview fixture remains DEV-only product rehearsal. The shell reports
Approval required only when Modify's backend capability is available; other modes
retain Read-only. No fake runtime success or generic Undo is presented.

Automated coverage includes strict intent/eligibility/schema/bindings/expiry/digest;
fixed provider boundary and exact payload; stale race, zero pre-approval writes,
no retries, corrupt/oversize/redirect/timeout responses; CSRF/Origin/session/permission;
verification mismatch and persistent uncertainty; real PostgreSQL upgrade, schema
check, claims, cross-user fences, cleanup and logout interaction; UI cancel/double
approval/stale/uncertain; and Chromium/Firefox/WebKit synthetic browser flows with
320px, keyboard, Axe, forced colors and reduced motion. Safari/WebKit keyboard
coverage uses native Option-Tab for button traversal, consistent with
[Apple keyboard guidance](https://support.apple.com/guide/safari/cpsh003/mac). Existing Phase 8 browser
and unit suites remain included. No browser test mutates real Onshape.

Final gates: frozen npm/uv installs; format, lint, TypeScript and strict mypy
(87 files); 642 frontend tests; 961 backend tests including ten real PostgreSQL
cases with no skips; production build; Compose validation/healthy database; local
additive migration and Alembic check preserving auth row counts; dependency audits
with no known vulnerabilities; documentation links, whitespace and secret review.
The complete Playwright gate passed **519 tests** across Chromium, Firefox and
WebKit, including 33 Modify cases and 24 Mounting Bracket cases. Earlier harness
failures were corrected by draining iframe navigation and separating Axe scans
from native keyboard traversal; no assertion or retry policy was weakened.
No dependency was added. Synthetic layout screenshots live under ignored `.cache`;
none is committed.

## Exact human permission transition

1. Keep `FORGE_CAD_WRITES_ENABLED` unset/false while reviewing this change. Do not
   change Action URL or redirects. Use the existing development app only.
2. Human app owner opens Onshape developer-app permissions. Retain OAuth2ReadPII
   and OAuth2Read; add **OAuth2Write only**. Keep Delete, Share, Purchase and
   Internal disabled. Record no secret screenshots.
3. Explicitly disconnect/reconnect and complete new authorization/consent. Refresh
   is not consent expansion. Forge must observe known textual OAuth2Read and
   OAuth2Write in the grant. Unknown/bitmask authorization fails closed. If Onshape
   supplies only a bitmask, stop for official scope-contract review; do not edit DB
   scopes to bypass the check or infer permission from a successful read.
4. Use disposable CAD only. Human operator may then explicitly enable the backend
   `FORGE_CAD_WRITES_ENABLED=true` for controlled validation and restart. Browser
   and AI cannot change it. Keep conformance pause at zero for normal Gate A.
5. Any missing critical evidence, inconclusive gate or unexpected mutation: stop,
   set writes OFF, retain uncertainty fences, investigate. This is not release
   authorization. Return flag OFF after the controlled exercise.

## Exact controlled CAD validation and Gate A

1. Create a disposable document and workspace Part Studio: one simple rectangular
   Sketch, one solid Extrude and one ordinary terminal Fillet. No configurations,
   custom features, other bodies, rollback or important school/project geometry.
2. Confirm Fillet is active. Open Forge Modify in that current workspace. Ask
   “Suppress the final fillet.” Wait for fresh inventory; explicitly select target.
   Preview must identify it and show **Active → Suppressed**, effect and limits.
3. Cancel. Inspect Onshape: unchanged geometry/feature state; **zero mutation**.
4. Request/select a new proposal (wait for cooldown if necessary). Before approval,
   establish a safe local comparison of feature definitions in disposable CAD;
   do not commit raw captures. Approve once. Confirm one updateFeatures POST using
   the exact body above, no parameters, original baseline marker and guard true.
5. Observe executing → verifying → verified success only after fresh reads prove
   suppression. Inspect feature tree: same Fillet present and suppressed. Compare
   unrelated and target definitions/parameters: only target suppression changed.
   Inspect geometry and downstream effects manually. This proves **Gate A** only
   if all checks pass. Missing fields or unexpected changes mean stop, not PASS.
6. Human manually re-enables Fillet in Onshape for each new case. Prepare a new
   proposal, then manually change CAD **before approval**. Approve old preview:
   local stale rejection, zero POST. This tests local protection, not Gate B.
7. Prepare again; rapidly double approve: at most one mutation. Test unsupported
   requests, no terminal Fillet, already suppressed target, missing write permission,
   revoked connection, context navigation and 320px keyboard flow. Re-run Mounting
   Bracket Check my step and its PASS/FAIL/WARNING/UNVERIFIED/name-independent/
   single-L/revocation/restoration/completion regressions; students still edit CAD.

## Exact provider conformance Gate B

1. Use only disposable CAD with active eligible Fillet. Human enables the development
   setting `FORGE_CAD_WRITE_CONFORMANCE_PAUSE_SECONDS=10`, restarts backend; this
   bounded hook is rejected outside development. Writes remain controlled by the
   independent feature flag. Do not use the pause in normal operation.
2. Prepare at document microversion M0 and click Approve change. Wait for the real
   **Controlled validation pause** announcement. This occurs **after** the final
   local head check, while the original approval binding is held.
3. During that ten-second pause, manually change the disposable CAD to M1. The
   request must still send sourceMicroversion=M0 and rejectMicroversionSkew=true;
   no local head replacement occurs after the pause. Establish that the provider
   rejects that exact stale request and the Fillet remains unsuppressed.
4. Inspect the single attempted POST, provider rejection and final CAD state using
   private local instrumentation; never commit network captures/tokens. Forge may
   report uncertainty conservatively and retain a fence; it must not retry.
   A local rejection with zero POST is insufficient evidence for this gate.
5. Repeat with a change to another element in the same document/workspace, checking
   the document-level marker behavior against the official contract. Use deliberate
   operator recovery between cases only after upstream settlement is established.
6. If provider applies stale suppression, or atomic rejection cannot be established,
   **Gate B fails/inconclusive: writes OFF; do not release**. Local checks are not a
   substitute. Return conformance pause to zero and writes OFF after testing.

## Human screenshot plan

A request; B eligible target; C preview; D Active → Suppressed; E Cancel;
F unchanged CAD; G new preview; H Approve change; I executing; J verifying;
K verified success; L suppressed Fillet in tree; M stale rejection; N unsupported;
O permission required; P uncertainty/recovery only if safely testable; Q 320px.
Keep captures local and review/redact before sharing. Do not capture `.env`, tokens,
OAuth codes, Network tab, cookies, unrelated private CAD, HAR or database dumps.
No human screenshots or real CAD validation are claimed by this implementation.

## Changed-file map

- Configuration/commands: `.env.example`, `Makefile`, `README.md`.
- Backend authority: `cad_edits/{__init__,domain,storage,service,routes}.py`.
- Provider: `integrations/onshape/{write_client,write_evidence}.py`; the existing
  `client.py` and Phase 8 checker/evidence flow remain unchanged.
- Auth coordination: `auth/{routes,security,tokens}.py`, `db/coordination.py`.
- Persistence/lifecycle: `db/{models,database}.py`, `main.py`, migration
  `0002_safe_edit.py`.
- Backend tests: `test_safe_edit.py`, `test_safe_edit_postgres.py`,
  `test_postgres.py`, `test_client_context_boundary.py`.
- Web: `App.tsx`, `App.test.tsx`, `components/Shell.tsx`, `features/Modify.tsx`,
  `modify/{api.ts,Modify.test.tsx}`, `preview/ModifyPreview.tsx`, `styles.css`.
- Browser tests: `modify.spec.ts`, `foundation.spec.ts`; `ai.spec.ts` drains
  navigation and waits for the new iframe rather than racing an old response.
- Documentation: README plus architecture, security, UI, agent, roadmap,
  development, authentication, extension, this runtime review and historical 9A
  checkpoint annotations. `PHASE_8_REVIEW.md` is unchanged.
