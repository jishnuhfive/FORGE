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

### Feature-state coverage investigation

The next human read-only probe passed the corrected rollback predicate and rejected
at feature position 1:

```text
safe_edit_reject reason=feature_state_missing_or_invalid position=1 field=featureState expected=object actual_type=missing actual_boolean=None
```

The human's disposable inventory is Sketch → Extrude → Fillet, all visibly active,
with one solid body. This rejection proves an object-shaped top-level state map
and no exact match for position 1. It does not establish coverage at positions 2/3,
state validity, or eligibility of the full stack.

The [current official OpenAPI](https://cad.onshape.com/api/openapi) was rechecked;
its current server is `/api/v17`, version `1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`BTFeatureListResponse-2457.featureStates` maps keys to `BTFeatureState-1688`.
That state schema exposes `featureStatus` and Boolean `inactive`; neither field's
optionality establishes safe meaning for a missing entry. The feature-list query
supports immutable microversions and describes `noSketchGeometry` as controlling
simple sketch information without geometry. It does not document an exception
for Sketch state coverage. The [official feature guide](https://onshape-public.github.io/docs/api-adv/featureaccess/)
includes a Sketch state but explicitly labels its examples v9. Its omitted-default
discussion cannot establish that missing states mean OK or active in v17.

No documented individual-feature GET returning `BTFeatureState` was found in the
current public OpenAPI. The Part Studio feature-ID path offers POST/DELETE only;
neither is used. The existing list GET accepts a `featureId` query filter, but still
returns the same list-response state map, with no stronger completeness or missing
state guarantee. No supplemental provider endpoint or FeatureScript was added.

The opt-in development probe now compares `noSketchGeometry=true` then `false`,
both with `includeGeometryIds=false&rollbackBarIndex=-1`, using one server-resolved
microversion and checking the workspace head afterward. Only closed sanitized
metadata escapes: completeness Boolean/null, feature/state counts, position,
allowlisted category, exact-key-presence Boolean, unmatched-state count, source
microversion equality Boolean and exact response byte count. A match means key
presence only, including if its value is invalid. It never establishes state OK.

Both reads reuse the fixed host, v17 transport, no redirects, identity encoding,
2 MiB per-response cap, bounded JSON structure, per-call timeouts and shared
30-second deadline. The `false` comparison temporarily receives sketch geometry
in backend memory within these bounds; raw maps, definitions, geometry, identifiers
and tokens are neither logged nor persisted. Only minimized reports survive each
comparison read. At this investigation checkpoint the write-critical read mode,
definition fingerprints and before/after verification were unchanged. The then-current
policy required an actual state object, explicit OK status and explicit expected
inactive Boolean for every feature. The explicitly authorized revision below
supersedes that completeness prerequisite; no missing state is interpreted as OK.

The human selected the disposable target in Chrome. An explicitly authorized
backend probe used the sole matching existing connected OAuth grant; no app scope
or permissions were changed. The initial attempt required a non-idle local web
session and stopped before any CAD request. The completed manual read used the
existing OAuth connection independently of that idle browser session. Private
context stayed in process memory. A GET-only transport hook rejected any other
CAD method before network dispatch. The completed probe made nine CAD GETs,
including the comparison and unchanged evidence projection; no mutation occurred.

| Sanitized observation                      | `noSketchGeometry=true` | `noSketchGeometry=false` |
| ------------------------------------------ | ----------------------- | ------------------------ |
| `isComplete`                               | true                    | true                     |
| Returned features                          | 3                       | 3                        |
| State entries                              | 0                       | 0                        |
| Position 1 / sketch / exact state match    | false                   | false                    |
| Position 2 / extrude / exact state match   | false                   | false                    |
| Position 3 / fillet / exact state match    | false                   | false                    |
| Unmatched state entries                    | 0                       | 0                        |
| Source equals the same pinned microversion | true                    | true                     |
| Exact response bytes                       | 50,263                  | 67,158                   |

The workspace head remained unchanged across both reads. The subsequent unchanged
evidence projection reproduced the position-1 missing-state rejection. This is an
**empty map for the entire stack**, not an isolated Sketch key mismatch. For this
snapshot, `noSketchGeometry=false` did not restore any state, so changing that
production query would add geometry exposure and response size without fixing the
evidence gap. No raw provider response, key or private identifier was persisted.

Root cause at the rejection boundary is established: the provider returned zero
state entries for three features. The cause of that provider behavior remains
unresolved. Current public v17 schema/guide review found no authoritative statement
that an omitted state establishes both OK and active, and no individual-state GET
with stronger documented evidence. This observation alone proves neither a Forge
defect nor a provider defect, intentional API variation or a document problem.
That observation did not justify changing a query or inferring missing states.
The investigation checkpoint left its instrumentation, tests and review uncommitted.
The subsequent explicit operation-specific decision below authorizes the current
policy correction and inclusion of that investigation work in its scoped commit.

Twenty-eight new synthetic cases cover complete coverage, each missing position,
unmatched extras that cannot substitute for missing matches, invalid state objects,
missing status/inactive, error status, inactive upstream features, exact pinned GET
variants/byte counts, privacy, response caps, redirects and head changes. The full
gate passed **1,062 backend tests**, including all ten real PostgreSQL cases (seven
safe-edit cases), and **642 frontend tests** including Phase 8 regressions. Format,
lint, TypeScript, strict mypy (92 files), production build, dependency audits and
whitespace/local Markdown links passed. No frontend/public contract changed.

The initial recommendation was to seek clarification of the omitted states. The
human instead explicitly authorized the narrower suppression-specific policy below.
No provider health/default interpretation was established by that decision.
**ZERO real CAD writes; writes OFF; Gate A UNPROVEN; Gate B UNPROVEN.**

### Current policy: explicit unavailable feature-state evidence

The current [v17 OpenAPI](https://cad.onshape.com/api/openapi) was fetched again for
this revision with the same version and SHA-256 above. `featureStates` is a property
of `BTFeatureListResponse-2457`, with no required complete-coverage constraint.
`BTMFeature-134.suppressed` explicitly means skipping regeneration when true.
`updateFeatures` describes updating supplied top-level fields and optional feature
suppression attributes. These contracts and the live empty map support the human's
explicitly revised **single-operation** evidence policy; they do not prove missing
states mean OK or active, provider atomic stale rejection, or whole-model health.

| Evidence classification | Behavior                                                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `COMPLETE`              | Nonempty map with exactly the unique inventory IDs, no extras. Every value must be an object, status exactly OK and inactive explicitly false before dispatch; after suppression only the target must have inactive explicitly true. |
| `UNAVAILABLE_EMPTY`     | The field is present and exactly `{}`. State evidence is unavailable. Do not synthesize status/inactive or reject solely on this map; require every structural and model-output invariant below.                                     |
| Invalid evidence        | Missing/null/array/nonobject map, partial/wrong/extra coverage, duplicate JSON keys, invalid entry objects or missing/invalid status/inactive reject. No invalid mode can become a baseline or proposal.                             |

`Baseline.feature_state_evidence` records one of the two accepted modes with no
default. Inventory fingerprints still include the entire returned feature response
and configuration; the proposal digest also binds this mode. The policy is now
`terminal-fillet-2` at that checkpoint; the auxiliary-suppression revision below
advanced it to `terminal-fillet-3`. The guard-evidence revision advanced to
`terminal-fillet-4`; the current body revision below advances to `terminal-fillet-5`
without changing this feature-state policy.
Old policy records or records missing the explicit mode cannot
decode for execution. A mode/map change during discovery, proposal preparation or
fresh pre-dispatch capture invalidates the old baseline even at the same marker.
No migration or new authority is introduced; old previews must be prepared again.

Both accepted modes require a real workspace Part Studio, unconfigured configuration,
complete pinned inventory, matching source and no skew, exact documented rollback
end, 3–20 features, unique bounded IDs, only supported standard classes/types and
namespace, a Sketch and Extrude, no subfeatures or unexpected return, explicit false
or independently proven parent/configured suppression evidence and an accepted auxiliary suppression mode (strict
ordinary object or exactly null, as detailed below). Every explicit
`suppressed` field must be present and false before the write; the final feature
must be the ordinary unsuppressed Fillet. Serialization/library remain bounded.
The body contract requires exactly one SOLID, NO_ERROR, matching pinned
microversion and an accepted body-revision mode, detailed below. Configuration must be
empty and match the same microversion. Every captured feature definition, including
IDs/order/types and parameters, is fingerprinted; only terminal suppression is
excluded from the before/after definition digest. The existing geometry-minimizing
query is unchanged. This proves a supported solid-body result and explicit terminal
suppression state; **it does not establish whole-model feature health**.

Approval still requires a server-resolved opaque candidate, exact digest, 120-second
expiry, explicit human **Approve change**, user/session/grant/context binding,
committed one-use claim and workspace fence. Fresh evidence must match the approved
inventory, target, mode, suppression, configuration and original microversion.
Final locked authorization/head checks precede the sole fixed one-feature POST with
the **original approved** marker, `rejectMicroversionSkew=true` and
`updateSuppressionAttributes=true`. No name/parameter body, arbitrary HTTP,
FeatureScript, AI/browser authority, retry or newer-baseline substitution is added.

Verification requires an advanced acknowledgement microversion, fresh pinned
reads, the same terminal target now explicitly `suppressed=true`, all upstream
features explicitly unsuppressed, unchanged captured definitions/identity/order/
types, acceptable unchanged serialization/library, unconfigured evidence and one
matching supported SOLID with the existing body safeguards. A complete after-map
is validated strictly; an exactly empty after-map remains unavailable and does not
imply `inactive=true`. Either accepted after-mode is permitted independently of
the before-mode, since suppression necessarily advances the approved snapshot.
Partial/invalid after-evidence remains uncertain, retains the fence and never
retries. Success remains “Change verified. Forge confirmed that the selected
Fillet is now suppressed.” The preview explains the solid-body/suppression evidence
and that overall feature health is not established. No engineering PASS is claimed.

The current observed-v17 synthetic provider and PostgreSQL proposal fixtures use
`featureStates={}`. Populated-map projection/security cases and all four before/
after mode combinations remain covered. Regression cases prove missing fields
cannot turn into OK/false; incomplete/extra maps reject, duplicate JSON keys reject,
all structural/body/version predicates still reject independently in empty mode,
fresh changes prevent dispatch, and post-write changes retain uncertainty/fences.
The prior coverage diagnostic is preserved with its privacy and GET-only limits.

The feature-state revision added 77 dedicated empty-mode/policy regressions, alongside the 28
coverage cases from the preceding investigation. **451 focused evidence/provider
tests passed; 1,139 full backend tests passed**, including all ten real PostgreSQL
cases (seven safe-edit). **642 frontend tests and all 519 Playwright cases passed**
across Chromium, Firefox and WebKit, including 33 Modify and 24 Mounting Bracket
cases. Format, lint, TypeScript, strict mypy (93 files), production build, Alembic
check (no new operations), dependency audits, local Markdown links and whitespace
checks passed. The synthetic 320px proposal was visually reviewed. No dependency,
lockfile, migration, environment file or Phase 8 review changed. Secret/private-CAD
context checks passed. Configured settings and the running API write flag were
independently checked as OFF without exposing environment contents. No real CAD
request was needed for that feature-state revision; all mutation tests use synthetic transports.

**ZERO real CAD writes; writes OFF; Gate A UNPROVEN; Gate B UNPROVEN.** The next human read-only
step is to restart the local API with writes OFF and the opt-in diagnostic enabled,
then use CAD Inspector → Refresh CAD on the disposable Sketch → Extrude → Fillet.
Capture only the safe coverage/rejection or eligible outcome. A later rejection
requires its own exact contract review; it is not permission to relax another
predicate. Gate A and Gate B still require separate controlled human validation
before operational enablement. No CAD mutation is performed by Codex.

### Auxiliary suppression state: null is unavailable, not unsuppressed

The next human read-only rejection was
`unsupported_suppression_state`, position 1, `suppressionState`, expected object,
actual type null. The current [official v17 OpenAPI](https://cad.onshape.com/api/openapi)
was fetched **before editing**: same version `1.222.90730-c8d74e607a47` and SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`BTMFeature-134.suppressionState` references `BTMSuppressionState-1924` and is not
required. This does **not** document null semantics. The explicit `suppressed`
Boolean describes skipping regeneration; `suppressionConfigured` describes configured
suppression, and `parentSuppressed` is Boolean. The base auxiliary schema has
`suppressionConfigured` and inherits `BTMNode-19`; its discriminator lists configured,
expression and parent-suppressed subtypes. The existing strict ordinary base-object
representation remains supported. The human explicitly authorized null auxiliary
evidence independently of the required safe feature Booleans, without interpreting
provider omission/defaults.

Before changing eligibility, the development-only diagnostic was extended to emit
`safe_edit_suppression_coverage`: positions 1–3 only, allowlisted feature category,
shape null/object/missing/other, bounded btType category when object, and presence/
primitive type/Boolean-or-null value for the three hard fields. Arbitrary type names,
identities, parameters, maps, names, geometry, tokens and private URLs never enter
it. It projects the same existing pinned GET response; no endpoint or CAD read is
added. Existing GET-only guards, fixed host, byte/deadline caps and no redirects
remain. Reports are logged only after the final head check passes.

The human selected the current disposable target. The backend used its existing
connected OAuth grant, with writes OFF and diagnostics ON, under a GET-only CAD
transport guard. Both bounded sketch read modes produced the same observations:

| Position | Category | Auxiliary shape | btType category | `suppressed`              | `suppressionConfigured`      | `parentSuppressed`           |
| -------- | -------- | --------------- | --------------- | ------------------------- | ---------------------------- | ---------------------------- |
| 1        | sketch   | null            | not applicable  | present / Boolean / false | missing / missing / no value | missing / missing / no value |
| 2        | extrude  | null            | not applicable  | present / Boolean / false | missing / missing / no value | missing / missing / no value |
| 3        | fillet   | null            | not applicable  | present / Boolean / false | missing / missing / no value | missing / missing / no value |

These are sanitized live observations, not synthetic provider success. Complete
inventory/source equality and unchanged head passed; state entries remained zero.
The true/false sketch variants were 50,263 / 67,159 bytes in this probe. No raw CAD
response or private context was saved. A second probe after implementation confirmed:

```text
safe_edit_reject reason=parent_suppressed position=1 field=parentSuppressed expected=false actual_type=missing actual_boolean=None
```

At that auxiliary-only checkpoint the live target **remained ineligible**. Both
omissions required the separate contract review and explicit policy decision below;
neither field is inferred false. The two
manual probes made 18 CAD GETs total, zero CAD writes, and no permission changes.

That checkpoint required all three feature Booleans explicitly. The current
guard-evidence policy below replaces only the optional parent/configured prerequisites.
`suppressed` remains explicit before and after, and the auxiliary policy remains:

- Exactly null records `SuppressionAuxEvidence.NULL_UNAVAILABLE`. It contributes
  **no positive evidence** and supplies no inferred Boolean, inactivity or ordinary
  object. It simply does not veto otherwise valid operation-specific evidence.
- A base object records `ORDINARY_OBJECT` only with exact supported btType, explicit
  nested `suppressionConfigured=false` and the existing known-field restriction.
- Configured `-2598`, expression `-1811`, parent-suppressed `-5404`, unknown btTypes
  and malformed objects reject. Missing, array, string, numeric and Boolean values
  reject; missing is never converted to null. Rejections cannot become a baseline.

Per-position auxiliary modes are required in the immutable baseline, with no
default, and bound into the proposal digest. The raw auxiliary field remains in
both inventory and captured-definition fingerprints: no normalization or new
ignore-list was added. That checkpoint's policy `terminal-fillet-3` invalidated older previews and
records missing the modes; prepare fresh proposals. Feature-state COMPLETE /
UNAVAILABLE_EMPTY classification and partial-map rejection are unchanged.

After writing, null may remain null and the target's explicit suppression true,
advanced marker, same terminal identity/order/types, preserved definitions, one
matching supported SOLID, versions and every other invariant must still pass.
A supported ordinary after-object is validated; a change to a captured auxiliary
definition still fails the unchanged-definition invariant. Specialized/unknown
after-state rejects and stays execution-uncertain with the fence retained and no
retry. No inactivity, whole-model health or real provider conformance is inferred.

Verification for this revision: **128 new sanitized diagnostic/policy/security cases**;
**579 focused evidence/provider tests**, **1,267 full backend tests** including all
ten real PostgreSQL cases (seven safe-edit), **642 frontend tests**, and **57 browser
regressions** (33 Modify, 24 Mounting Bracket across Chromium/Firefox/WebKit) passed.
Format, lint, TypeScript, strict mypy (94 files), production build, Alembic check
(no new operations), dependency audits and whitespace/local Markdown links passed.
All mutation tests used synthetic provider transports. No dependency, lockfile,
migration, environment file, OAuth app permission or Phase 8 review changed.
Configured/running writes were verified OFF and running diagnostics ON without
printing environment contents. The live probes were reads only; no provider write
conformance or target eligibility success is claimed.
**ZERO real CAD writes; writes OFF; diagnostics ON; Gate A UNPROVEN; Gate B UNPROVEN.**
The next read-only step at that checkpoint was to inspect the optional-field
contract. The following section records the subsequent explicit decision. Writes
stay OFF and neither human provider conformance gate has been established.

### Current guard evidence: omitted values are not Boolean defaults

The current [official v17 OpenAPI](https://cad.onshape.com/api/openapi) was fetched
again before editing, with version `1.222.90730-c8d74e607a47` and SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`BTMFeature-134` exposes `parentSuppressed`, `suppressed`, `suppressionConfigured`
and `suppressionState` without a required-property declaration. This alone does
not make omission false. The [feature API guide](https://onshape-public.github.io/docs/api-adv/featureaccess/#json-encoding)
mentions omitted Boolean defaults, but labels those examples v9. That rule is
**not the sole justification** and is not implemented as provider-data defaulting.

The independent v17 `getConfiguration` supports microversion-pinned reads and
returns `BTConfigurationResponse-2019`, including configuration inputs/current
values, source marker and skew. The current operation still requires both arrays
explicitly empty, source equal to the feature snapshot and skew explicitly false.
The [configuration guide](https://onshape-public.github.io/docs/api-adv/configs/)
explains these inputs independently of any optional per-feature flag.

Live metadata supplied for this revision, consistent with the preceding direct
read-only capture, is null auxiliary state, explicit `suppressed=false`, and both
optional guards missing at each of Sketch / Extrude / terminal Fillet. State map
is exactly empty. The human reports the independent configuration arrays are both
empty and the complete inventory has only the three supported types. No raw CAD
payload, identifier or private URL is stored here.

| Field                   | Explicit false   | Missing                                                                                                                                   | True, null or wrong type |
| ----------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `parentSuppressed`      | `EXPLICIT_FALSE` | `STRUCTURALLY_NOT_APPLICABLE`, only after the complete pinned top-level supported structure passes                                        | Reject                   |
| `suppressionConfigured` | `EXPLICIT_FALSE` | `INDEPENDENTLY_PROVEN_UNCONFIGURED`, only after the separate pinned configuration response proves empty inputs/current values and no skew | Reject                   |

Parent evidence is conditional on the entire bounded 3–20-feature inventory being
complete and pinned, every top-level feature having the supported standard type,
btType and namespace, exactly empty subfeatures, accepted auxiliary state, explicit
safe suppression and the existing return/rollback checks. No unsupported folder,
container or custom feature is skipped or accepted. All features must finish
validation before a baseline can return. The [current feature-list help](https://cad.onshape.com/help/Content/PartStudio/features_and_parts_lists.htm)
documents that a suppressed folder can inactivate its contents; top-level display
alone therefore is not the proof. The complete restricted inventory and exclusion
of unsupported/container/custom structure are essential. No current provider
evidence was found contradicting that restricted condition. A contradictory live
case must stop validation and be reported, not accepted through this mode.

Configured evidence is conditional on the separate configuration proof above and
accepted null/ordinary auxiliary state. Configured/expression/parent-specialized
states still reject even when arrays are empty, as do explicit conflicting flags.
The target remains explicitly unsuppressed before dispatch; no omitted `suppressed`
value is accepted. Every existing body, revision, serialization/library, inventory,
approval/session/grant, claim/fence and original provider guard remains mandatory.
Feature-state COMPLETE / exactly-empty UNAVAILABLE_EMPTY policy is unchanged.

No provider dictionary gains false flags. Missing remains absent in captured
definitions and raw inventory/configuration fingerprints. Baseline/proposal now
retain per-feature parent/configured evidence-mode tuples, without defaults.
At that checkpoint policy `terminal-fillet-4` required fresh previews; old policy or missing-mode
records cannot execute. Fresh pre-dispatch comparison binds raw presence, modes,
identity, original approved marker and the entire baseline. Post-write fresh reads
re-prove both independent conditions and explicitly compare these modes. Target
suppression must now be true; missing optional flags need not appear. If they do
appear, they are checked strictly. Any true/invalid flag, unsafe configuration or
structure fails verification and retains uncertainty/fences without retry.
An appearing explicit false flag can pass its local check but still changes the
raw definition/mode, so unchanged-definition verification remains conservative.

Public/internal safe meaning is “No parent-suppression condition was observed in
the supported top-level structure” and “Forge verified the Part Studio has no
active configuration inputs.” No claim of explicit false is made for omissions,
and normal UI exposes no raw provider details or whole-model health claim.

The optional configured-control document must be created manually by the human,
outside Forge and separate from the plain disposable target. It is not a required
gate for this implementation under the explicit instruction. Its live comparison
status and current verification results are recorded after checks below. Codex
does not create or mutate any CAD document. The next human step remains a
diagnostics-only refresh with writes OFF, diagnostics ON and only sanitized output.
**ZERO real CAD writes; Gate A UNPROVEN; Gate B UNPROVEN.**

The additional plain-model probe was completed after the human selected the
disposable target. Existing backend OAuth authorization and a fixed GET-only CAD
transport were used. All three optional-field observations remained as above.
The independent configuration GET reported **0 configuration parameters, 0 current
configuration values, source equal to the pinned feature revision, skew false**.
Both feature-read variants were complete with matching source and unchanged head;
state entries remained zero. Nine CAD GETs were made, with no writes or permission
changes. The guard proof passed and the next unchanged predicate rejected:

```text
safe_edit_reject reason=body_microversion_ambiguous position=None field=ambiguous expected=false actual_type=missing actual_boolean=None
```

At that checkpoint this reported a missing required body marker flag; it did not
establish actual geometric ambiguity. The live target was not eligible and no
candidate, proposal, claim or CAD write was created by that probe. The separate
body-contract review below supersedes that marker policy.

No separate manually prepared configured-control target was provided during this
implementation. The optional live A/B configured-control comparison was not run;
configuration safety relies on the current v17 endpoint semantics, pinned empty
response and synthetic negative/transition tests, not the old v9 omission rule.
This optional evidence remains available for later human validation.

Verification: **105 new independent-guard evidence regressions**, **684 focused
safe-edit/provider tests**, **1,372 backend tests** including ten real PostgreSQL
cases (seven safe-edit), **642 frontend tests**, and **57 Modify/Phase 8 browser
cases** (33 Modify, 24 Mounting Bracket across Chromium/Firefox/WebKit) passed.
Format, lint, TypeScript, strict mypy (95 files), build, migration check (no new
operations), dependency audits and whitespace/local Markdown links passed.
Security regressions exercise absence preservation and reject False defaults on
critical guard reads. No dependencies, lockfiles, migrations, environment files,
OAuth app permissions or Phase 8 review changed. Secret/private-CAD-context scans
passed. The running API remained writes OFF / diagnostics ON. All mutation tests
used synthetic transports; the live probe performed GETs only.

The next human step at that checkpoint was CAD Inspector → Refresh CAD with writes OFF and diagnostics ON; collect only
the safe metadata and the body-flag rejection for its separate official-contract
review. Gate A and Gate B remain UNPROVEN; do not approve a mutation.

### Current body revision evidence: exact immutable identity, no inferred flags

The [current official OpenAPI](https://cad.onshape.com/api/openapi) was fetched
again before changing policy. It advertises `/api/v17`, build
`1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`BTMicroversionId-366` declares Boolean `ambiguous`, Boolean `deleted` and string
`theId`, with **no required-property declaration**. This does not give omitted
flags a false value. `getPartStudioBodyDetails` accepts `wvm=m` and returns
`BTExportModelBodiesResponse-734`, whose marker is that schema.
[Onshape architecture](https://onshape-public.github.io/docs/api-intro/architecture/)
establishes that document microversions cannot change; the
[REST introduction](https://onshape-public.github.io/docs/api-intro/)
documents the exact `m/{microversion}` reference form.

Before the policy edit, the human selected the disposable target and the extended
DEV diagnostic ran through the existing backend authorization with writes OFF and
diagnostics ON. CAD transport was additionally guarded to GET-only fixed v17
paths. Nine CAD GETs completed; the old policy still rejected the missing
`ambiguous` flag. The safe body report was:

```json
{
  "the_id": "present",
  "the_id_matches_requested": true,
  "ambiguous": "missing",
  "deleted": "missing",
  "body_count": 1,
  "body_type": "SOLID",
  "error_enum": "NO_ERROR"
}
```

Both optional flags were omitted. The complete three-feature inventory, empty
state map, null auxiliary suppression, explicit suppressed=false, omitted parent/
configured guards and independent empty configuration proof matched the preceding
capture. No private CAD IDs, names, URLs, raw body JSON, geometry or credentials
were logged, persisted or copied into fixtures. The diagnostic emits only the
fixed categories/count above after successful head bracketing, through the existing
DEV-only inspector probe; no public endpoint or response header was added.

The old body policy required both flags explicitly false and rejected their
absence. Policy `terminal-fillet-5` now requires `Baseline.body_revision_evidence`
without a default and accepts exactly two modes:

| Mode                                | Required proof                                                                                                                                                               |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EXPLICIT_CLEAN_FLAGS`              | Present marker object, explicit exact matching `theId`, `ambiguous is False` and `deleted is False`                                                                          |
| `EXACT_PINNED_ID_FLAGS_UNAVAILABLE` | Present marker object, explicit exact matching `theId`, both optional flags absent, and fixed-client transport proof of `m/{same}` after equal head-before/head-after checks |

Invalid evidence has no accepted mode. Missing/malformed marker or ID, mismatched
ID, either true, explicit null, wrong type, and mixed false/missing shapes reject.
Python integers 0/1 are not Booleans. Both absent flags remain absent; neither is
synthesized, stored as false or described as explicitly clean. The narrower proof
is that Onshape returned body output identifying the exact immutable revision
Forge requested. Optional explicit flags remain additional negative evidence.

The fixed client constructs feature/configuration/body paths from the same strict
head marker using `m/{same}`, checks the head again, then supplies internal pinned
read evidence to the projector. A matching response ID alone cannot authorize the
unavailable-flags mode. Exactly one body, type exactly SOLID, `NO_ERROR`, strict
body schema, complete bounded supported feature inventory, no skew, independent
empty configuration, terminal Fillet and explicit suppression remain mandatory.
No unrelated predicate, query, scope, approval, fence, retry or write boundary changes.

The new mode is included in closed baseline/proposal JSON and its digest. Full
fresh baseline equality rejects a mode change even at the same marker; feature/
configuration fingerprints and captured definition digests remain unchanged.
Older-policy or missing/invalid-mode records cannot decode for execution and need
fresh previews. No schema migration or raw body persistence is added.

Post-write verification uses the same pinned read path and requires the response
ID to match the exact new acknowledged marker, one SOLID and `NO_ERROR`. Either
accepted mode is independently re-proven at that new revision; it need not match
the before-mode. All other post-write invariants remain. True/null/wrong-type/
mixed flags, missing/mismatched IDs or invalid body output produce execution
uncertainty, retain the fence and never retry. Synthetic tests prove this behavior;
they do not establish real provider write conformance.

The follow-up probe used the same GET-only transport with writes OFF and diagnostics
ON. All nine CAD GETs completed, the same safe body metadata was observed, and the
read predicates passed with `EXACT_PINNED_ID_FLAGS_UNAVAILABLE`. This establishes
read-only target eligibility for that captured state, not either write-conformance
gate. Across the before/after probes, **18 CAD GETs and ZERO CAD writes** occurred.
No live candidate, proposal, claim, fence or approval was created.

Verification: **172 new body/diagnostic regressions**, **807 focused safe-edit/
provider tests passed** (seven PostgreSQL cases skipped there, then passed in the
full gate). The full gate passed **1,544 backend tests**, including all ten real
PostgreSQL cases (seven safe-edit), **642 frontend tests**, and **57 Modify/Phase 8
browser cases** (33 Modify, 24 Mounting Bracket across Chromium/Firefox/WebKit).
Coverage includes both body modes before/after, strict invalid/mixed flag and
marker shapes, missing transport proof, unchanged body safeguards, mode/digest
binding, stale approval, old records, post-write uncertainty/fences/no retry, safe
diagnostic privacy and no inferred false defaults. Format, lint, TypeScript, strict
mypy (96 files), production build, Alembic migration check (no new operations),
dependency audits, whitespace and local Markdown link checks passed. No dependency,
lockfile, migration, environment file or Phase 8 review changed. All mutation tests
used synthetic provider transports. The running API remained writes OFF and
diagnostics ON; secret/private-CAD-context checks passed.

The exact next human step is to keep writes OFF and diagnostics ON, reload the
current local Forge panel, then use **CAD Inspector → Refresh CAD** on the same
disposable Sketch → Extrude → Fillet Part Studio. Collect only
`safe_edit_body_coverage` and the fixed probe outcome/rejection. Do not prepare or
approve a mutation. **ZERO real CAD writes; Gate A UNPROVEN; Gate B UNPROVEN.**
No OAuth app permissions were changed.

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
initial diagnostic checkpoint left `write_client.py` untouched. The subsequent
coverage investigation only factors its existing bounded exchange to also return
an internal byte count; the guard, transport bounds and write payload are unchanged.

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
3. Copy only the `safe_edit_state_coverage noSketchGeometry=...` and
   `safe_edit_suppression_coverage noSketchGeometry=...` lines and
   the `safe_edit_reject reason=...` line (or `safe_edit_probe outcome=...`).
   They contain no private CAD content. Do not paste other logs, URLs, cookies
   or provider payloads.
4. Compare that first condition with the official contract. Leave eligibility
   unchanged until a documented equivalent representation is established. Turn
   the optional diagnostic flag on for this controlled investigation as requested;
   writes stay OFF throughout.

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
explicit safe suppression, accepted parent/configured evidence, an accepted auxiliary mode
and rollback at the documented end. Exactly
one SOLID body and matching pinned marker with an accepted body-revision mode are required.
All features must be explicitly unsuppressed before the write. A complete state map
adds strict OK/inactive checks; an exactly empty map records unavailable evidence
under the operation-specific policy above. Partial/invalid maps and missing critical
structural evidence reject; no Boolean defaults are inferred. Duplicate identities
reject as ambiguous.
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
  feature-state schemas. The initial 9A reconciliation was later revised for the
  live empty-map behavior under the explicit current policy above.
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
suppression field presence/defaults, response marker semantics, and unchanged
definition behavior remain Gate A/B questions. Nonempty state evidence must still
meet strict inactive/status checks; empty-map verification makes no such claim.
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
must establish the intended same target now explicitly suppressed (and the strict
inactive/status checks when state evidence is complete), supported body output,
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
sanitized label, microversion, explicit body-revision and feature-state modes,
per-position auxiliary/parent/configured suppression evidence modes, fingerprints
and versions for binding/reconciliation;
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
