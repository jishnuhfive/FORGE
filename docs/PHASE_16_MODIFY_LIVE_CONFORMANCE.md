# Phase 16 — controlled real Modify conformance

**IN PROGRESS — TARGETED RECHECK NO-GO; DEFAULT LIBRARY RECHECK READY**

Initial status: `IN PROGRESS — AUTOMATED CONFORMANCE PREPARATION`.

Starting main: `017f4ab7e556b2653661cbda77b7b6f22cdf1a1c`.
Branch: `phase16/modify-live-conformance`. On 2026-10-24, the starting working
tree was clean, branch was `main`, fetch succeeded, and HEAD and `origin/main`
both matched the required SHA. The audit below was completed before edits.

This is preparation for a human-controlled conformance gate. The human has now
reported the writes-OFF read checkpoint below. **No Phase 16 proposal, approval or
mutation has occurred.** The agent has not read the private fixture. Automated
fixtures are synthetic and do not prove current Onshape feature serialization.
The final question remains open: can the existing deterministic pipeline safely
and exactly perform its five claimed operations on real current Onshape CAD?

## Scope and authority

Only SET_SUPPRESSED, SET_UNSUPPRESSED, RENAME_FEATURE, SET_EXTRUDE_DEPTH and
SET_FILLET_RADIUS are in scope. No creation, deletion, reorder, sketch editing,
holes, new extrudes/fillets, chamfers, patterns, mirrors, shells, assemblies,
drawings, arbitrary FeatureScript, generic provider JSON or topology-driven edits.
Phase 17 creation work is not authorized by completion of this preparation.

AI/model ≠ CAD authority ≠ approval authority ≠ provider-payload authority.
The tool-free planner sees only opaque handles, display labels, feature types,
positions and semantic capabilities. It may propose semantic operations; it
receives no feature IDs, provider URLs/methods/payloads, parameter IDs,
microversions, FeatureScript execution or approval capability.

The server owns discovery, validation, fresh exact baseline, authoritative preview,
digest and 120-second expiry, session/grant/context binding, atomic one-use claim,
write fence, fresh pre-dispatch reads, fixed payload construction and
`rejectMicroversionSkew=true`. It rereads fresh pinned evidence after each single
dispatch and verifies the exact effect before success. Uncertainty retains the
fence and stops the suffix. No automatic retry, resume, rollback or undo write.
Human approval applies to the exact displayed proposal/digest, never a later plan.

CAD writes remain OFF in the real environment throughout preparation and automated
verification. Existing test harnesses enable the capability only on isolated test
Settings with synthetic credentials and MockTransport; their POST counts describe
mock requests, never real Onshape writes. No global flag or operator dotenv edit
is needed. No deployment, Railway action, OAuth/Action URL/domain change, production
secret change or public visibility change is included. Local HTTPS remains the
later human validation environment.

## Starting implementation audit

Read `cad_edits/` authority, storage, routes, sequential executor, verification and
recovery boundaries; `edit_registry.py`, `write_client.py`, `modify_evidence.py`
and Phase 9 `write_evidence.py`; all planner modules; the live Modify component and
strict API/stream parser; A1/A2/B1/B2, recovery and Phase 9 tests; the four hackathon
records and current architecture/security/development/Onshape/AI/roadmap docs.
Inspected Makefile, npm workspace configuration, package-lock, API pyproject/uv.lock,
Playwright configuration, Compose and opt-in PostgreSQL isolation.

The entire Part Studio must pass Phase 9's pinned evidence policy: unconfigured
workspace, complete 3–20 standard top-level Sketch/Extrude/Fillet definitions,
empty namespaces/subfeatures, rollback at end, explicit suppression, all
nonterminal features active, terminal Fillet, one supported SOLID and NO_ERROR.
Empty feature-state maps mean unavailable, never inferred OK; nonempty maps need
exact coverage and strict status/inactive entries. Null auxiliary suppression and
omitted parent/configured flags retain their existing distinct evidence modes.

| Operation         | Supported feature / required shape                                  | Adapter assumptions                                                                              | Provider mutation path                                                              | Exact changed field                  | Fresh verification                                                                                                       | Unproven live assumption                                                                                             |
| ----------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| SET_SUPPRESSED    | Explicitly active standard terminal Fillet in the restricted studio | Phase 9 structural/suppression policy; does not replace or interpret parameters                  | Fixed POST `features/updates`, one suppression entry                                | `suppressed`: false → true           | Fresh acknowledged revision, exact inventory/configuration comparison; only target inactive state may follow suppression | Phase 9 Gate A is historically human-proven; this generalized UI/plan path still needs an independent Phase 16 trial |
| SET_UNSUPPRESSED  | Explicitly suppressed standard terminal Fillet                      | Same policy, reverse explicit transition                                                         | Same fixed suppression endpoint                                                     | `suppressed`: true → false           | Same exact comparison, active target and supported body re-proven                                                        | Reverse transition and generalized acknowledgement/current evidence behavior                                         |
| RENAME_FEATURE    | Standard Extrude or Fillet passing its complete quantity adapter    | Valid old name and complete supported definition; never reconstruct missing parameters           | Fixed POST `features/featureid/{server-encoded-id}`, full fresh feature replacement | `name` only                          | Exact replacement acknowledgement, fresh same feature identity/order and every unrelated field unchanged                 | Current UI definitions meet the narrow adapter; replacement and reread preserve all unrelated fields                 |
| SET_EXTRUDE_DEPTH | Active standard simple NEW SOLID BLIND Extrude                      | Exactly bodyType, operationType, entities, endBound, depth; exact enums and quantity type        | Same full-definition replacement                                                    | `parameters[depth].expression` only  | Exact acknowledgement plus fresh whole-inventory/configuration comparison at new revision                                | Current depth identity/quantity encoding, query representation, omitted/default options, server normalization        |
| SET_FILLET_RADIUS | Active standard simple Fillet                                       | Required entities/radius, optional explicitly Boolean tangentPropagation; no other parameter IDs | Same full-definition replacement                                                    | `parameters[radius].expression` only | Same exact acknowledgement/reread comparison                                                                             | Current radius/query/tangent representation and normalization; no variable/asymmetric/width/richer shape             |

Suppression deliberately retains Phase 9's existing parameter-opaque eligibility;
it sends no feature replacement. A definition ineligible for rename or quantity
may still advertise terminal suppression. Tests explicitly distinguish these
capabilities. This is not evidence that a richer fillet supports radius/rename.
The first live fixture must match the simple representation for **all five** cases.
An unsupported replacement shape must never acquire replacement authority simply
because its name says Extrude/Fillet. A whole-studio structural failure rejects
every operation, including suppression.

## Representation assumptions and evidence gap

`tests/fixtures/modify_parameters.json` is unchanged and **synthetic**. Extrude
uses BTMParameterEnum-145 with ExtendedToolBodyType/SOLID,
NewBodyOperationType/NEW, BoundingType/BLIND, BTMParameterQueryList-148/entities
and BTMParameterQuantity-147/depth. Fillet uses the same query-list envelope,
BTMParameterQuantity-147/radius and optional BTMParameterBoolean-144/
tangentPropagation. Literal positive bounded `N mm` or `N in` expressions only;
no expression evaluation, inferred units, cached quantity value/units, tolerant
quantity subclass or aliases such as endDepth/distance.

The quantity field allows only btType, parameterId, expression, optional string
nodeId and optional explicit isInteger=false. Missing, malformed, duplicate or
unknown parameter IDs reject replacement. Second direction, thin, draft and richer
extrude/fillet options are not accepted as harmless defaults, even if false.
Parameter order, node IDs, queries, metadata and all unrelated fields are copied
exactly; no normalization or broad verification ignore list exists.

Current entities validation proves the query-list type and a nonempty list;
individual query contents are opaque preserved JSON, not a validated topology or
ownership contract. The synthetic example contains a sketch-region query for
Extrude and an individual query string for Fillet. It does **not** establish that
current UI-created queries have those shapes, are complete, or survive replacement
unchanged. Neither graph facts nor a model assertion can fill that gap.

The official [feature guide](https://onshape-public.github.io/docs/api-adv/featureaccess/)
was read on 2026-10-24. It describes internal feature encoding, older v9 examples
and checking UI-created definitions through a feature-list read. Public documentation
is not a live current-UI fixture. No provider API/version/schema contract is changed
or newly declared proven by this preparation.

**Mandatory writes-OFF representation checkpoint before any live write:** identify
the exact disposable user-owned workspace/Part Studio privately, read fresh complete
features/configuration/body evidence through the existing bounded pinned read
boundary, and review the actual Extrude/Fillet parameter IDs/types/enums/quantity
and query shapes. Also review full-definition completeness, disabled option
representations and expected acknowledgement semantics. No private CAD payload,
token, identity, query or microversion belongs in Git, model input or logs.
Record only redacted shape observations and provenance here. The generic Inspector
display and Phase 9 suppression diagnostic alone do not prove quantity eligibility.

If the ordinary UI fixture does not fit, stop before proposal/dispatch. Do not
rebuild an artificial feature to satisfy the parser, add aliases, drop fields,
infer omitted defaults, increase caps or relax exact verification. Any narrow repair
must be justified by the actual evidence, validated deterministically, preserve
unrelated fields exactly, add redacted/synthetic shape regressions and rerun the
automated gate with writes OFF. Review the repaired preview before human approval.

## Initial automated preparation changes and gate (63d79e8)

Production adapters, planner, routes, frontend, storage, recovery, flags, safety
bounds and dependencies remain unchanged. Added `test_modify_conformance.py` covers:

- Every required parameter independently missing, duplicated or wrongly typed;
  malformed collections/query-list envelopes; exact NEW/SOLID/BLIND enum values.
- Real-looking second-direction/thin/draft and variable/asymmetric/width/richer
  parameter IDs rejected for quantity/rename; typed unique optional tangent flags;
  names cannot disguise custom/namespaced/subfeature/unsupported features.
- Optional tangent variants, copied nested metadata, node IDs, isInteger=false,
  complete rename/quantity payload preservation and exact unrelated inventory
  preservation through each operation (both rename targets).
- Cancel before each independent operation, unchanged synthetic CAD, fresh proposal,
  single dispatch and consumed approval rejection.
- Each operation with missing/unchanged revision, missing skew flag, wrong identity,
  incomplete/missing fresh evidence or unrelated post-write changes: HTTP 200 cannot
  establish success; execution_uncertain, retained fence, skipped suffix, status-only
  lookup, rejected repeat approval and blocked new discovery.

Retained A1/A2/B1/B2 tests cover stale baselines before dispatch, context/session/
grant changes, expiry, concurrent/double approval with real isolated PostgreSQL,
cancel races, digest integrity, no planner execution authority, lost streams/status,
and Phase 9/recovery/fence guarantees. Existing assertions and timeouts stay intact.

Required gate: frozen npm/uv installs; focused Modify/Phase 9/retained-recovery
tests and frontend Modify tests; `make format`, `make lint`, `make typecheck`,
`make build`, `make test`, `make migration-check`, `make compose-check`, `make audit`;
Modify Playwright cases in Chromium/Firefox/WebKit. No shared runtime behavior is
changed, so the complete browser matrix is not required for this test/doc-only work.
Use a separately disposable PostgreSQL service and random schemas; never application
data/fences. Stop/remove only the test service created for this gate; retain existing
services/volumes.

Final automated results, 2026-10-24:

| Check                                                               | Result                                                                                                  |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Frozen installs                                                     | `npm ci` and `uv sync --frozen` passed; both lockfiles unchanged                                        |
| New Phase 16 conformance suite                                      | **129 passed**                                                                                          |
| Focused Modify + Phase 9 + retained recovery + AI write regressions | **1,585 passed**, including the 129 new cases and opt-in PostgreSQL families                            |
| Focused frontend Modify                                             | **108 passed** in 2 files                                                                               |
| Full `make test` frontend                                           | **869 passed** in 35 files                                                                              |
| Full `make test` backend                                            | **3,147 passed**, including all **42 PostgreSQL cases**; zero failures/skips                            |
| Modify browser matrix                                               | **45 passed**, 15 each in Chromium/Firefox/WebKit, normal 4 workers, zero retries/skips                 |
| `make format` / `make lint`                                         | Passed; no existing assertions, thresholds or timeouts weakened                                         |
| `make typecheck`                                                    | Passed; TypeScript and strict mypy, 177 source files                                                    |
| `make build`                                                        | Passed; existing nonblocking >500 kB chunk warning retained                                             |
| Isolated migration upgrade / `make migration-check`                 | Passed; no new upgrade operations, no migration changes                                                 |
| `make compose-check` / real test database health                    | Passed; isolated PostgreSQL accepting connections                                                       |
| `make audit`                                                        | npm: 0 vulnerabilities; pip-audit: no known vulnerabilities (local editable API excluded as configured) |
| Diff / secret / privacy / documentation links                       | Passed; no credentials, raw CAD, private IDs or provider captures added                                 |

The focused suites are subsets of the full suites; counts must not be added together.
The full browser matrix was not rerun: this branch changes tests/documentation only,
and all Modify browser cases passed in all three engines. No runtime/backend/frontend,
configuration, lockfile, database schema or dependency change was made.

Verification used the separate `forge-phase16-check` disposable PostgreSQL container,
loopback random port and synthetic-only credentials, with each PostgreSQL test owning
and deleting its random schema. Only this created container and its anonymous test
volume were removed after verification. Existing application service/data/volumes
were untouched. The ignored `.cache/phase16` runner supplied only the isolated DB
to migration checks and disabled operator dotenv/credential inheritance for pytest;
no operator file or test assertion was changed. Temporary browser servers stopped
after Playwright. Configured real CAD writes were checked OFF before and after the
gate. Private Onshape reads/writes/model calls: **0 / 0 / 0**. Live conformance:
**NOT RUN / UNVERIFIED**.

Pre-live automated verdict:
`PHASE 16 AUTOMATED GATE PASS — READY FOR CONTROLLED HUMAN LIVE VALIDATION`.
This authorizes no automatic live action and does not complete Phase 16.

## Writes-OFF representation probe preparation

The initial safe-edit diagnostic reported structural/suppression/body eligibility
but insufficient parameter detail to establish quantity/rename adapter shape
conformance. This follow-up adds a request-local typed sanitizer in
`dev/modify_representation.py` and extends the existing `dev/safe_edit.py` probe.
It is **diagnostic only, DEV only, writes OFF only**, with no write authority.
Actual human observation remains **PENDING**; no live CAD read or write was made
to implement or test this addition.

Startup validation still requires `ENVIRONMENT=development`,
`FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true`, `FORGE_CAD_WRITES_ENABLED=false`.
The existing probe checks those conditions before credentials/provider access.
The representation hook independently checks them before projection and again
before logging, including mutable-settings/direct-internal-call defense. Disabled,
test/production or writes-ON settings cannot execute the representation projector
through the probe/hook. Raw data are never logged on rejection or exception.

`safe_edit_representation_coverage noSketchGeometry=true|false metadata=...`
is local development logging only. Both reports reuse the **exact existing bounded
feature-list responses** in `CoverageClient.compare()`, discard raw data, and emit
only after its final matching-head check. No additional GET is introduced:
comparison still uses four GETs (head, two feature variants, head), and the existing
Inspector/probe integration still uses **13 GETs total** in its synthetic test.
No provider POST/mutation, route, query option, response payload/header, AI input,
analytics, persistence, database write, target, proposal, approval, write record,
fence or OAuth scope is added. Existing auth/reads/response behavior is unchanged.

All emitted models are strict, frozen and extra-forbidden, including nested data.
Allowed output is limited to:

- Positions 1–20; fixed sketch/extrude/fillet/unsupported and definition-type
  categories; ordinary-top-level/identity/name-usability and source-match Booleans,
  never identities, names or revision values.
- Parameter collection presence/type; counts capped at 20 with explicit cap flags;
  malformed/duplicate-known indicators. Unknown string IDs contribute only
  `unknown_present` and a capped count, never their text. Non-string/missing IDs
  and non-object items produce a malformed indicator.
- Only the feature's five Extrude or three Fillet vocabulary IDs, including explicit
  presence/missing, capped occurrences, duplicate indicator and fixed type category.
- Only SOLID/NEW/BLIND/other enum categories and expected-enum-name match Booleans.
  Quantity expressions become supported-bounds positive mm/in literal categories,
  other/missing/wrong_type; nodeId becomes missing/string_present/wrong_type;
  isInteger becomes missing/false/true/wrong_type. Unknown quantity fields yield
  only a supported-fields Boolean.
- Query envelope/type/empty-state categories, counts capped at 2000 with cap flags,
  and unique closed item-type categories from the first 2000 items. No query is
  evaluated. Tangent propagation reports presence, Boolean validity and only a
  valid true/false value.
- Per-feature `replacement` and `rename` summaries: exact_match,
  unsupported_shape or unavailable. Missing/null definitions/parameter collections
  or incomplete/source-mismatched inventories or unusable identities remain
  unavailable; malformed/duplicate/unknown/richer
  replacement shapes fail closed. Rename additionally requires a usable old name.

The private pure `quantity_parameter()` registry validator supplies only the
parameter-shape match Boolean; it is called without target resolution, payload
construction or mutation. Sanitized definition flags and this Boolean determine
the summary. A diagnostic exact_match describes the **current registry's shape**,
not runtime target eligibility, body/model health, query semantics, permission,
feature ownership, full transport preflight or proven provider write behavior.
The current registry still treats individual query contents as opaque preserved
JSON; item categories and clipped counts do not expand or tighten that contract.
Only the existing runtime registry/fresh full evidence can decide later planning.
Graph facts remain irrelevant to write authorization.

Never emitted: feature/document/workspace/element/microversion/entity/geometry IDs,
feature names, coordinates, quantity expressions, node IDs, raw query strings or
objects, arbitrary enum/btType/parameter strings, provider JSON, tokens or URLs.
Hostile synthetic values exercise these fields, including newline/URL-like content.

Follow-up automated results, 2026-10-24:

| Check                                                         | Result                                                                                                                                                                                                |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New representation tests                                      | **98 passed** within the focused gate                                                                                                                                                                 |
| Focused diagnostic/adapter/conformance gate                   | **807 passed**, zero failures/skips; includes safe-edit diagnostics, state/suppression/body coverage, 129 Phase 16 cases, 166 Modify adapter cases, Modify diagnostics and configuration tests        |
| `make format` / `make lint`                                   | Passed                                                                                                                                                                                                |
| `make typecheck`                                              | Passed; TypeScript and strict mypy over 179 source files                                                                                                                                              |
| `make audit`                                                  | npm: zero vulnerabilities; pip-audit: no known vulnerabilities (editable API excluded as configured)                                                                                                  |
| Privacy/authority/read-count review                           | Passed; hostile synthetic values cannot escape; guarded projection/credential/provider access and post-read flag changes tested; comparison remains 4 GETs and Inspector integration 13 GETs, no POST |
| Diff / configured-sensitive-value / documentation-link review | Passed; real write flag remains OFF                                                                                                                                                                   |

Tests use frozen uv execution, synthetic CAD/credentials and MockTransport only;
operator dotenv/settings overrides are isolated in the pytest child. No real
provider, proposal, approval or write was invoked. No database service or browser
server was started for this follow-up. Full backend/frontend/browser/migration
gates were not rerun: only the opt-in DEV diagnostic path changes, its Inspector
integration is covered, and shared authority/product contracts remain unchanged.
Earlier full-suite counts above are historical and are not represented as reruns
of this follow-up. Existing assertions, timeouts and safety behavior were preserved.

`PHASE 16 REPRESENTATION PROBE PASS — READY FOR WRITES-OFF HUMAN CHECKPOINT`

This subsection's results supersede no earlier live limitation or historical
automated count. No adapter, planner, approval, execution,
stale check, fence, microversion guard, post-write verifier, recovery or A1/A2/B1/B2
contract changed. No browser change, deployment, operator dotenv edit or live
diagnostic invocation is included.

### Original human representation checkpoint — completed; failed replacement conformance

1. Privately confirm the ordinary disposable owned workspace/Part Studio fixture
   below and the correct connected account. Keep the exact identifiers private.
2. Restart the existing local HTTPS/API workflow with exactly
   `ENVIRONMENT=development`, `FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true`,
   `FORGE_CAD_WRITES_ENABLED=false`. Preserve URLs, OAuth configuration, credentials,
   local certificates and all other settings. Startup must reject writes ON.
3. In the embedded Forge **CAD Inspector**, click **Refresh CAD** once. Do not open
   a Modify proposal or send any approval. Allow the existing bounded reads to finish.
4. Inspect only local `safe_edit_representation_coverage` metadata lines for both
   read variants, especially `noSketchGeometry=false`. Confirm expected positions,
   standard categories, complete inventory, no malformed/duplicate/unknown parameters,
   correct enums, supported literal quantity/type/bookkeeping and nonempty query
   envelopes. Both Extrude and Fillet must report replacement/rename exact_match;
   present tangent propagation must be explicitly Boolean. Review any query-item
   `other`/malformed category rather than inferring query conformance from the summary.
5. If unsupported_shape/unavailable, count-capped, mismatched variants or unexpected
   categories appear, stop and report only the fixed sanitized metadata. Do not
   paste raw logs, provider JSON, identifiers, names, quantities, query strings,
   network captures or tokens; do not reshape the ordinary fixture to fit a parser.
6. Record actual human shape observations separately before claiming representation
   confirmation. Even exact_match proves no live mutation conformance and authorizes
   no proposal or approval under this read-only task.
7. Return diagnostics OFF after capture and keep writes OFF. Any later write trial
   requires a separate explicitly authorized human stage and exact fresh preview.

## First real UI shape investigation — historical repair NO-GO

This follow-up started from clean, fetched/synchronized
`8aaf65c6c1b47447944e5a82977ee0dfd1fb432f` on the existing Phase 16 branch.
The human checkpoint is recorded as:

**STRUCTURAL ELIGIBILITY PASS**

**REPLACEMENT CONFORMANCE FAIL — ADAPTER TOO NARROW**

The human reports an ordinary owned disposable UI-created Sketch → NEW/SOLID/BLIND
Extrude → terminal constant-radius Fillet, one SOLID body, NO_ERROR, complete
inventory and matched source. Both standard features have usable identities/names
and ordinary top-level structure. The probe returned
`eligible_no_proposal_no_write`. There was no proposal, approval or mutation, and
CAD writes remained OFF. These are human-reported observations, not an agent
replay or a successful live Modify trial.

For both replacement features, parameter count and unknown count exceeded the
diagnostic cap of 20; malformed and duplicate-known flags were false. All existing
required fields appeared once with the expected enum/query envelopes. Depth and
radius were positive mm literals with string node IDs and explicit false
isInteger, but `supported_fields_only=false`. Fillet tangent propagation was
explicit Boolean true. Both registry shape checks, replacement and rename failed.
The adapter correctly failed closed. Structural eligibility and a valid body do
not establish complete replacement conformance.

### Authoritative research and its limits

Read-only research used the official public standard-library document linked by
[FeatureScript documentation](https://cad.onshape.com/FsDoc/index.html), selecting
the current public 3095 workspace. No private fixture, credentials, provider write
or FeatureScript execution was used. Input declarations were inspected in:

- [extrude.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/aff9bec3150a48098a8184ac)
  and [extrudeCommon.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/779e4e2168dfbdd421cdf6ed):
  body/domain/operation, bounds, direction, draft, second direction, thin, offset
  and query predicates.
- [boolean.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/4eea9f271b60454e84089e38):
  NEW excludes the solid merge-scope precondition; separate surface-scope inputs
  must not be confused with solid controls.
- [fillet.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/841b26d2621a46bf98eda1d5)
  and [edgeBlendCommon.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/ecf7740dba703fd61ba84038):
  EDGE/FULL_ROUND, RADIUS/WIDTH, cross-section, asymmetry, partial/variable modes,
  overflow and smoothing predicates. Tangent propagation and edge overflow have
  UI defaults true; function-call defaults are not interchangeable with UI defaults.
- [Official feature access guide](https://onshape-public.github.io/docs/api-adv/featureaccess/),
  [Extrude help](https://cad.onshape.com/help/Content/PartStudio/extrude.htm) and
  [Fillet help](https://cad.onshape.com/help/Content/PartStudio/fillet.htm).
- The official published Python SDK's
  [quantity schema](https://github.com/onshape-public/onshape-clients/blob/master/python/onshape_client/oas/models/btm_parameter_quantity147.py)
  names `value`, `units` and `importMicroversion` in addition to the existing
  quantity fields. This older generated SDK is vocabulary evidence only, not
  proof of the current fixture's encoding or harmless replacement semantics.

These sources establish semantic predicates and a finite discovery vocabulary.
They do **not** establish the fixture's exact serialized inactive parameters,
btTypes/envelopes, quantity extra fields or configuration/tolerance state. The
official [defineFeature documentation](https://cad.onshape.com/FsDoc/library.html#defineFeature-function-map)
explicitly distinguishes function-call defaults from UI defaults. Remembered UI
values and disabled branches cannot be inferred from the presence of a source
default. Anonymous access to a public feature-definition API was unauthorized;
no authentication workaround or raw private capture was attempted.

### Changes delivered and deliberately unresolved repair

No optional parameter has been newly accepted by the write registry. No adapter,
quantity bound, 20-parameter limit, 8 KiB write cap, query policy, planner, preview,
approval, digest/expiry, claim/fence, stale check, provider guard, post-write exact
verifier, uncertainty or recovery behavior changed. Full-definition copying and
single-field mutation guarantees remain unchanged for previously supported shapes.
All additional/richer shapes remain unsupported for rename and quantity replacement.
This follow-up does not claim to have repaired current-UI replacement eligibility.

The read-only diagnostic now emits a separate
`safe_edit_standard_parameter_coverage` record from the same fresh responses,
after matching-head and DEV/diagnostics-ON/writes-OFF guards. Its fixed purpose is
`source_vocabulary_only_no_edit_authority`. Its closed source-input vocabulary
classifies enum comparisons, Boolean values, query envelopes, array emptiness and
quantity bookkeeping presence/type. Numeric values, unit strings, expressions,
node/import IDs, query/array contents, unknown IDs/field names and arbitrary
provider strings never escape. Existing representation reports and count caps are
unchanged; registry-unknown parameters remain unknown in those reports even when
the separate source catalog recognizes them. Recognition never supplies approval,
eligibility or write authority. Non-source internal computed FS fields are excluded.

Synthetic tests cover each diagnostic identifier, feature-specific vocabulary,
wrong types, missing values, duplicate/unknown fields, count caps, quantity
bookkeeping privacy, arrays, guarded logging and zero added requests. Inputs are
invented source-classification cases, **not** fixtures claimed to match real UI
serialization. Tests expressly retain rejection of every extra input. Existing
assertions are preserved; two existing tests gain additional privacy/guard checks.

An evidence-backed optional-parameter contract still requires the next sanitized
read. Only after that can exact closed btTypes, disabled states, parameter envelopes
and quantity bookkeeping be validated without guessing. The current >20 parameter
evidence also conflicts with the existing adapter limit. This task does not silently
increase it or transport/verification bounds merely to obtain a pass. A future
repair must explicitly resolve that constraint within the authorized safety policy.

### Automated verification of this diagnostic follow-up

All commands passed on this follow-up. No adapter repair or live-conformance pass
is implied by passing diagnostic regressions. Counts overlap.

| Check                                                                          | Result                                                                                                                |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| New standard-parameter diagnostic cases                                        | 292 passed                                                                                                            |
| New diagnostic + existing representation diagnostic                            | 390 passed                                                                                                            |
| Focused Modify/planner/plan/write-client/diagnostic/recovery/fence regressions | 1,975 passed                                                                                                          |
| `npm ci`; `uv sync --locked`                                                   | Passed; lockfiles unchanged                                                                                           |
| `make format`; `make lint`                                                     | Passed                                                                                                                |
| `make typecheck`                                                               | Passed; Python checked 181 source files; strict TypeScript passed                                                     |
| `make build`                                                                   | Passed; existing bundle-size warning, no thresholds changed                                                           |
| `make test`                                                                    | 869 frontend tests in 35 files; 3,537 API tests, including all 42 PostgreSQL cases; no skips                          |
| Isolated PostgreSQL health, upgrade; `make migration-check`                    | Passed; no schema drift                                                                                               |
| `make compose-check`                                                           | Passed                                                                                                                |
| `make audit`                                                                   | No known JavaScript/Python dependency vulnerabilities; editable application distribution excluded by existing command |
| Modify browser matrix                                                          | 45 passed across Chromium/Firefox/WebKit, four workers, zero retries                                                  |

The test child disables operator dotenv loading, strips provider credentials and
keeps real CAD writes OFF. Provider mutations in existing tests use only synthetic
mock transports. PostgreSQL used a new named disposable tmpfs-backed container
with synthetic credentials and a random loopback port; the existing application
container/database were untouched. The task container was removed after checks.
No real diagnostic invocation, private CAD read, proposal, approval, deployment,
OAuth/URL/domain change, dependency change, timeout adjustment or weakened assertion
was used. Diff/privacy review found only public-source vocabulary and synthetic
canaries; all write-authority implementation files remain unchanged.

### Second human writes-OFF checkpoint — now completed

1. Keep the SAME ordinary disposable owned fixture. Do not modify its feature
   definitions to fit the adapter. Keep local HTTPS/OAuth/URLs unchanged.
2. Run the updated local API with `ENVIRONMENT=development`,
   `FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true`, `FORGE_CAD_WRITES_ENABLED=false`.
   Restart as needed to load this code; startup must reject writes ON.
3. In CAD Inspector click **Refresh CAD exactly once**. Do not open a proposal,
   approve, run a write script or request any mutation.
4. Privately inspect both `safe_edit_representation_coverage` and the new
   `safe_edit_standard_parameter_coverage` for both variants, especially
   `noSketchGeometry=false`. Share only those minimized metadata objects. They
   contain fixed source IDs and categories, never raw CAD. Do not paste full logs,
   tokens, names, IDs, expressions, quantities, queries, network traces or JSON
   feature definitions.
5. The current adapter is expected to remain `unsupported_shape`. Stop there.
   This is an evidence checkpoint, not the successful repair recheck requested
   as the eventual gate. Record recognized input types/values, remaining
   unrecognized/malformed/duplicate states and quantity bookkeeping categories.
6. Return diagnostics OFF after capture; keep CAD writes OFF. No write can follow
   until a narrow evidence-backed repair passes automation and a subsequent
   writes-OFF recheck reports replacement AND rename exact_match for both features,
   with no unknown, malformed or duplicate unsupported state.

**PHASE 16 REAL-SHAPE REPAIR NO-GO**

## Narrow current-UI adapter repair after the second human checkpoint

This continuation began from clean synchronized branch HEAD
`81d5045a55373cf6819c15134663dd1675ff90e3`. The human explicitly authorized the
narrow repair using the larger recognized vocabulary, with writes still OFF and
without requesting raw CAD or identifiers. This section supersedes the preceding
NO-GO and its pending evidence request; it does not establish live write conformance.

### Human evidence received

The second writes-OFF checkpoint reports complete/source-matched inventory,
Sketch → Extrude → Fillet, one SOLID body, NO_ERROR, structural eligibility,
zero proposals and zero mutations. Both ordinary top-level standard replacement
features have no malformed or duplicate input and zero unrecognized source IDs
(including uncapped zero unknown counts). Extrude explicitly has custom direction
OFF with an empty query, start offset OFF with its simple bound/quantity and empty
query, false offset direction, true default solid/surface scopes and empty scope
queries. Fillet explicitly has variable mode OFF, empty settings arrays, smooth
transition OFF, edge overflow ON with empty keep-edge query, corner smoothing OFF
with empty exceptions, and false second-bound trimming. Earlier required
SOLID/NEW/BLIND, nonempty recognized queries, literal quantities, usable identities
and names, and Boolean tangent propagation true remain human-confirmed.

Other source-defined mode states are explicit requirements of the contract below;
they are not inferred from an omitted value or claimed to have passed a real
mutation. The next human read must confirm the entire contract on the same fixture.
No new raw CAD, identifiers or private payloads were requested, read or committed.

### Closed contracts

`standard_edit_shapes.py` validates each input before the registry can permit a
replacement. Every parameter ID is unique and belongs to one of two finite maps:
50 Extrude inputs or 38 Fillet inputs. The original minimal A1 profile and its
20-parameter rejection bound remain separate and unchanged. The newly authorized
current-UI profile uses its exact finite vocabulary cardinality as its bound;
there is no generic parameter acceptance or unbounded limit increase. The
20-feature limit, read/query limits, 8 KiB write cap, units/numeric bounds for
authorized changes, deadlines and approval limits remain unchanged.

An expanded shape requires these explicit mode guards, even if other inactive
inputs are absent. A lone added optional parameter cannot upgrade a legacy shape.

- Extrude: core bodyType/operationType/entities/endBound/depth, domain,
  oppositeDirection, symmetric, hasDraft, hasSecondDirection,
  hasSecondDirectionDraft, hasOffset, hasSecondDirectionOffset,
  hasExtrudeDirection, startOffset, defaultScope and defaultSurfaceScope.
- Fillet: entities/radius/tangentPropagation, filletType, blendControlType,
  crossSection, isAsymmetric, isPartial, isVariable, smoothTransition,
  allowEdgeOverflow, keepEdges, smoothCorners, smoothCornerExceptions,
  vertexSettings and pointOnEdgeSettings.

Other inputs may be absent only because an explicit guard excludes their source
predicate/geometry branch. When present, every one must satisfy its rule. No
default value is inserted, reconstructed or normalized. Common metadata permits
only an optional 1–256 character string nodeId and absent/empty importMicroversion;
nonempty imports and configuration/tolerance metadata reject. Enum namespace may
only be absent/empty. All other parameter-level fields reject.

| Kind     | Exact btType                | Allowed representation                                                                                                                                                                                                                  |
| -------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Enum     | `BTMParameterEnum-145`      | Exact enumName/value below; optional empty namespace.                                                                                                                                                                                   |
| Boolean  | `BTMParameterBoolean-144`   | Actual Boolean, with the closed allowed value(s) below. No coercion or omitted value.                                                                                                                                                   |
| Quantity | `BTMParameterQuantity-147`  | Explicit bounded literal expression; optional isInteger=false, numeric value=0 (excluding Boolean), units="". These bookkeeping defaults may be omitted as documented by the official feature encoding; nonzero/nonempty caches reject. |
| Query    | `BTMParameterQueryList-148` | Explicit queries array. Inactive query arrays must be empty. Entities must be nonempty with recognized ordinary individual-query envelopes.                                                                                             |
| Array    | `BTMParameterArray-2025`    | Explicit empty items array only. No variable settings are accepted.                                                                                                                                                                     |

The exact optional IDs and states are:

| Extrude IDs                                                                                                                                                                                                                                                                                                                          | Kind / allowed state                          | Semantics                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| bodyType                                                                                                                                                                                                                                                                                                                             | Enum ExtendedToolBodyType / SOLID             | Excludes surface/thin geometry.                                                                            |
| operationType                                                                                                                                                                                                                                                                                                                        | Enum NewBodyOperationType / NEW               | Excludes Boolean merge/removal.                                                                            |
| endBound                                                                                                                                                                                                                                                                                                                             | Enum BoundingType / BLIND                     | Excludes richer end bounds.                                                                                |
| domain                                                                                                                                                                                                                                                                                                                               | Enum OperationDomain / MODEL                  | Excludes flat/sheet-metal operation domain.                                                                |
| surfaceOperationType                                                                                                                                                                                                                                                                                                                 | Enum NewSurfaceOperationType / NEW            | Inactive surface input; surface geometry excluded.                                                         |
| flatOperationType                                                                                                                                                                                                                                                                                                                    | Enum FlatOperationType / REMOVE               | Inactive flat input; MODEL domain required.                                                                |
| secondDirectionBound                                                                                                                                                                                                                                                                                                                 | Enum BoundingType / BLIND                     | Inactive second direction; no richer latent bound.                                                         |
| startOffsetBound                                                                                                                                                                                                                                                                                                                     | Enum StartOffsetType / BLIND                  | Inactive offset; no entity-offset mode.                                                                    |
| oppositeDirection, symmetric, hasDraft, draftPullDirection, hasSecondDirection, hasSecondDirectionDraft, secondDirectionDraftPullDirection, hasOffset, offsetOppositeDirection, hasSecondDirectionOffset, secondDirectionOffsetOppositeDirection, hasExtrudeDirection, startOffset, startOffsetOppositeDirection, midplane, flipWall | Boolean false                                 | Ordinary first direction only; richer modes disabled and inactive direction controls preserved.            |
| secondDirectionOppositeDirection                                                                                                                                                                                                                                                                                                     | Boolean true                                  | Source/UI default of an inactive second direction; not a second end.                                       |
| defaultScope                                                                                                                                                                                                                                                                                                                         | Boolean false                                 | Corrected by the final human recheck below; NEW excludes solid merge scope and booleanScope remains empty. |
| defaultSurfaceScope                                                                                                                                                                                                                                                                                                                  | Boolean true                                  | Inactive surface scope; SOLID plus empty queries excludes surface merge behavior.                          |
| entities                                                                                                                                                                                                                                                                                                                             | Nonempty Query                                | Existing ordinary profile selection, copied unchanged.                                                     |
| surfaceEntities, wallShape, endBoundEntityFace, endBoundEntityBody, endBoundEntityVertex, secondDirectionBoundEntityFace, secondDirectionBoundEntityBody, secondDirectionBoundEntityVertex, extrudeDirection, startOffsetEntity, booleanScope, booleanSurfaceScope                                                                   | Empty Query                                   | No inactive geometry, custom direction, offset/bound reference or merge scope.                             |
| depth                                                                                                                                                                                                                                                                                                                                | Positive length Quantity                      | Only this expression may be changed by SET_EXTRUDE_DEPTH.                                                  |
| thickness, thickness1, thickness2, secondDirectionDepth                                                                                                                                                                                                                                                                              | Positive length Quantity                      | Inactive because SOLID and no second direction are explicit.                                               |
| draftAngle, secondDirectionDraftAngle                                                                                                                                                                                                                                                                                                | Angle Quantity, literal `deg`, 0 < angle < 90 | Bounded dormant draft values; draft guards must be false.                                                  |
| offsetDistance, secondDirectionOffsetDistance, startOffsetDistance                                                                                                                                                                                                                                                                   | Nonnegative length Quantity                   | Positive supported length or exactly `0 mm` / `0 in`; offset guards must be false.                         |

| Fillet IDs                                                                                                                                     | Kind / allowed state                    | Semantics                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| filletType                                                                                                                                     | Enum FilletType / EDGE                  | Excludes full-round fillets.                                                                                   |
| blendControlType                                                                                                                               | Enum BlendControlType / RADIUS          | Excludes width-controlled fillets.                                                                             |
| crossSection                                                                                                                                   | Enum FilletCrossSection / CIRCULAR      | Excludes conic/curvature cross sections.                                                                       |
| startPartialType, endPartialType                                                                                                               | Enum EndTypePartialFillet / PERCENTAGE  | Inactive partial bounds only.                                                                                  |
| isAsymmetric, flipAsymmetric, isPartial, useTrimmedFirstBound, secondBound, useTrimmedSecondBound, isVariable, smoothTransition, smoothCorners | Boolean false                           | Excludes asymmetric, partial, variable and smoothing behavior.                                                 |
| partialOppositeParameter                                                                                                                       | Boolean true                            | Preserved ordinary inactive partial-bound direction.                                                           |
| allowEdgeOverflow                                                                                                                              | Boolean true                            | Human-confirmed normal UI mode; keepEdges must be empty. False is unsupported here.                            |
| tangentPropagation                                                                                                                             | Boolean false or true                   | Existing supported option, explicitly typed and preserved.                                                     |
| defaultsChanged                                                                                                                                | Boolean false or true                   | Source uses it only for informational NO_EFFECT status handling, not geometry; preserve either explicit value. |
| entities                                                                                                                                       | Nonempty Query                          | Existing ordinary edge selection, copied unchanged.                                                            |
| side1Face, side2Face, centerFaces, startPartialEntity, endPartialEntity, keepEdges, smoothCornerExceptions                                     | Empty Query                             | No full-round, partial, kept-edge or corner-exception selections.                                              |
| vertexSettings, pointOnEdgeSettings                                                                                                            | Empty Array                             | No variable settings.                                                                                          |
| radius                                                                                                                                         | Positive length Quantity                | Only this expression may be changed by SET_FILLET_RADIUS.                                                      |
| nonCircularRadius, width, otherRadius                                                                                                          | Positive length Quantity                | Inactive because circular/radius/symmetric mode is explicit.                                                   |
| rho, magnitude                                                                                                                                 | Dimensionless Quantity, 0 < value < 1   | Dormant cross-section values only.                                                                             |
| partialFirstEdgeTotalParameter, partialSecondEdgeTotalParameter                                                                                | Dimensionless Quantity, 0 <= value <= 1 | Dormant partial fractions only.                                                                                |
| startPartialOffset, endPartialOffset                                                                                                           | Nonnegative length Quantity             | Dormant partial offsets only.                                                                                  |

Positive lengths retain the existing exact `mm`/`in` grammar and bounds
(0.001–10000 mm or 0.001–393 in, at most six integer and six fractional digits).
Angle/fraction literals use the same bounded digit grammar, without expressions,
variables, scientific notation, signs, alternative units or tolerant subclasses.
They are inactive inputs, not new semantic edit operations.

Entities accept `BTMIndividualQuery-138` with a nonempty query string or bounded
nonempty deterministic-ID list. Extrude also accepts the existing
`BTMIndividualSketchRegionQuery-140` with usable feature identity and explicitly
Boolean filterInnerLoops when present; Fillet rejects sketch-region selections.
Unknown query fields/types and non-null dynamic/persistent query objects reject.
Known optional null query wrappers may be preserved. Query strings and identities
remain private provider-owned evidence; they are never generated or passed to the
planner. Official SDK schema names justify only these finite envelopes; the human
recheck still decides whether this fixture satisfies them.

### Preservation, diagnostic and authority review

The existing `change()` still deep-copies the complete fresh feature and changes
only name, depth.expression or radius.expression (or the existing separate
suppression field). It preserves every parameter, parameter order, query,
node ID, metadata field and feature identity. No definition is rebuilt from a
subset. The unchanged verifier compares the entire expected inventory and
configuration after the fresh post-write read. Even a structurally valid unrelated
value, ordering, query or metadata change prevents verified success.

The representation summary calls this same registry validation before reporting
exact_match. A valid expanded contract has zero registry-unknown inputs and valid
quantity bookkeeping; invalid expanded shapes remain unsupported. Source-vocabulary
recognition alone still confers no authority. Duplicate detection now covers all
closed standard input IDs; array btTypes have a fixed sanitized category. Count
clipping at 20 remains informational: the validator inspects every raw input, and
the separate source report lists the fixed recognized IDs. The next checkpoint may
therefore have parameter_count_capped=true while both replacement/rename pass;
unknown_count must still be zero and uncapped, with no malformed/duplicate state.

Planner contract, target identity resolution, preview, digest, expiry, explicit
approval, session/grant/context binding, atomic claim, write fence, stale rejection,
provider payload construction, rejectMicroversionSkew, post-write reread and exact
verification, no-retry uncertainty handling and recovery are unchanged. Graph
facts remain non-authoritative. No frontend behavior, production flag, secret,
OAuth/URL/domain, dependency or deployment configuration changed.

### Automated repair gate

All required checks passed on the final implementation. Counts overlap.

| Check                                                                          | Result                                                                                              |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| New full-shape conformance cases                                               | 1,024 passed                                                                                        |
| Focused Modify/planner/plan/write-client/diagnostic/recovery/fence regressions | 2,999 passed                                                                                        |
| `npm ci`; `uv sync --locked`                                                   | Passed; lockfiles unchanged                                                                         |
| `make format`; `make lint`                                                     | Passed                                                                                              |
| `make typecheck`                                                               | Strict TypeScript passed; Python checked 183 source files                                           |
| `make build`                                                                   | Passed; existing bundle-size warning; no threshold changes                                          |
| `make test`                                                                    | 869 frontend tests in 35 files; 4,561 API tests including all 42 PostgreSQL cases; no skips         |
| Isolated PostgreSQL health/upgrade; `make migration-check`                     | Passed; no schema drift                                                                             |
| `make compose-check`                                                           | Passed                                                                                              |
| `make audit`                                                                   | No known JavaScript/Python dependency vulnerabilities; existing editable application exclusion only |
| Modify browser matrix                                                          | 45 passed across Chromium/Firefox/WebKit, four workers and zero retries                             |

Tests cover every fixture input's exact btType, missing required value, duplicate,
configured/unknown fields, missing guards, non-supported modes, malformed
quantities/queries, empty inactive arrays, node/metadata/order/query preservation,
stale optional values, zero-write cancel, one-use approval, payload cap, valid ack
and fresh evidence, uncertainty, stopped suffix and no retry. Existing assertions,
timeouts, authority behavior and thresholds were not weakened. Final review also
restricts sketch-region queries to Extrude and tests unknown IDs within the finite
cardinality limit, so the limit cannot hide a missing whitelist check.

The synthetic full-shape fixture contains invented identities, queries, metadata
and dormant literal values, with no private CAD capture. It tests explicit
contracts rather than asserting that these invented values are the exact private
fixture. Provider mutations occur only in mock transports. Pytest disables operator
dotenv loading and strips provider credentials; the real write flag stays OFF.
All PostgreSQL cases ran against a new pinned-image, tmpfs-backed disposable test
container with synthetic credentials and a random loopback port. It was removed
after verification; the existing application container/database was untouched.
Diff/privacy review found no secrets, private captures, new operation or changed
planner/approval/executor/verifier/recovery implementation. No real CAD read,
proposal, approval, mutation, deployment, dependency or production-setting change
occurred during this continuation.

**PHASE 16 REAL-SHAPE REPAIR PASS — READY FOR WRITES-OFF RECHECK**

Actual five-operation write conformance remains UNVERIFIED.

### Previous writes-OFF recheck — completed, still NO-GO

1. Keep the SAME ordinary disposable owned Sketch → Extrude → Fillet fixture.
   Do not change its definitions to fit the parser.
2. Load the updated local API in development with diagnostics ON and CAD writes
   OFF. Preserve local HTTPS, OAuth, URLs and credentials.
3. In CAD Inspector click **Refresh CAD exactly once**. Do not prepare or approve
   any Modify operation and do not run any mutation script.
4. Inspect minimized representation and standard-parameter coverage for both read
   variants, especially noSketchGeometry=false. Both Extrude and Fillet must report
   replacement=exact_match AND rename=exact_match, with no malformed, duplicate or
   unsupported/unknown parameter state. Clipped total parameter counts alone are
   expected for this larger validated vocabulary; unknown counts must be zero and
   uncapped. These summaries prove only the replacement representation contract.
5. If either feature is unsupported/unavailable, stop again. Keep writes OFF and
   report only the existing minimized metadata, never raw CAD or identifiers.
6. Even a successful read recheck authorizes no write. Controlled live validation
   still requires the separate human stage, exact disposable target, fresh exact
   preview and explicit approval for each operation, one at a time.

## Targeted validator diagnosis after the final writes-OFF recheck

Starting branch HEAD was clean and synchronized at
`87051c1d7b4ef82b2b952f2246fb6e51547ca400`.

**FINAL WRITES-OFF RECHECK — STILL NO-GO**

The human refreshed CAD Inspector once on the same disposable ordinary fixture
with development/diagnostics ON and CAD writes OFF. Inventory was complete and
source-matched, one SOLID body had NO_ERROR, and the structural probe returned
eligible_no_proposal_no_write. Both replacements and renames nevertheless remained
unsupported_shape. Structural eligibility PASS does not override the adapter.
Zero proposal, approval or mutation occurred. No live conformance is claimed.

### Confirmed Extrude correction; Fillet remains unresolved

The final minimized evidence explicitly reports defaultScope=false. The previous
validator and synthetic fixture incorrectly required true. This latest observation
supersedes the earlier reported scope state, without changing any CAD fixture.
The current official public
[boolean.fs](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/4eea9f271b60454e84089e38)
was reread through its read-only UI at FeatureScript 3095. Its
booleanStepScopePredicate enters the merge-scope controls only for an operation
other than NEW; the Merge with all UI annotation defaults false. False is therefore
legitimate for this ordinary NEW feature. The contract now conservatively accepts
only the observed explicit Boolean false, retaining NEW/SOLID/BLIND and empty
booleanScope requirements. It does not permit both Boolean states or enable merge
behavior. defaultSurfaceScope remains explicitly true. The synthetic fixture was
corrected accordingly; tests still reject the opposite state and richer modes.

Fillet's high-level metadata appears compatible, including defaultsChanged=true,
variable/partial/asymmetry OFF, empty arrays/selections and ordinary overflow=true.
That does not identify the exact failing predicate. No Fillet value, quantity,
metadata, query or array acceptance rule has been broadened. The next human read
must identify its first closed failure; no raw CAD or identifiers are needed.

### One shared predicate and closed first-failure detail

Production ui_quantity_parameter still raises EditError(code=unsupported_target,
status=422) on rejection. Its internal ShapeValidationError subtype carries only a
frozen, strict, extra-forbidden ShapeFailure: a fixed known UI parameter ID (or
feature/parameters/unknown_parameter/duplicate_parameter/required_parameter) and a
fixed reason code. Arbitrary provider IDs, field names and values cannot enter it.
The canonical known catalog key is selected before validation; malformed/unknown
IDs use a fixed sentinel. The shared StandardId literal vocabulary moved to an
internal contract module and is reused by the existing source diagnostic.

Existing Boolean predicates were split into explicit rejection sites without
changing acceptance, other than the confirmed defaultScope correction. Query
validation now raises the first fixed reason instead of returning an unlabelled
false. The DEV diagnostic calls that exact production function and catches its
closed failure; it contains no second validator and cannot authorize an edit.
First failure follows original parameter order, then the existing predicate order.
Missing required inputs are reported deterministically after present inputs are
validated. Production exception text, public responses and operation support stay
generic and unchanged; the new detail is not persisted or passed to AI.

Only fixed reason codes escape: wrong_bt_type, unexpected_field,
bookkeeping_node_id, bookkeeping_import_microversion, wrong_boolean,
wrong_enum_namespace, wrong_enum_name, wrong_enum_value, wrong_quantity_expression,
wrong_quantity_value, wrong_quantity_units, wrong_is_integer, query_wrong_envelope,
query_empty, query_nonempty, query_item_wrong_type, query_item_unexpected_field,
query_item_bookkeeping, query_item_identity, array_not_empty, missing_required,
unknown_parameter, duplicate_parameter and too_many_parameters. No raw value or
expression, query, identifier, node, name, coordinate, enum text, token, URL,
microversion or raw JSON is logged.

After complete/source-matched pinned evidence and the unchanged head bracket,
local logs add only one of these fixed forms per recognized feature/read variant:

```text
safe_edit_standard_shape_failure category=fillet parameter=radius reason=wrong_quantity_units
safe_edit_standard_shape_validation category=extrude outcome=exact_match
```

These are examples, not observations of the private fixture's failure. Only the
closed category, parameter and reason (or category/outcome on pass) appear. Group
each line with the preceding existing coverage lines to identify the read variant;
the new line carries no extra context. An exact_match here means only the current-UI
parameter predicate, not complete target eligibility, approval or write conformance.
The separate original minimal A1 profile may pass its representation summary while
failing the stricter current-UI predicate; that is not a grant of new authority.

Projection and every individual log emission recheck development, diagnostics ON
and writes OFF. Incomplete/source-mismatched or changed-head evidence cannot emit
these new lines. They reuse the existing response with zero extra provider GETs:
four reads in compare and the same 13-read Inspector probe budget. No public route,
browser payload/header, proposal, approval, model input, persistent record or CAD
mutation is added. No planner/approval/claim/fence/stale/microversion/post-write
verification/uncertainty/recovery implementation or bounds change.

### Targeted automated verification

All checks passed on this continuation. Counts overlap.

| Check                                                                            | Result                                                                                              |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| New shared failure/guard/privacy tests                                           | 84 passed                                                                                           |
| New failure tests + UI/representation/source diagnostics                         | 1,498 passed                                                                                        |
| Focused Modify/planner/plan/write-client/diagnostic/recovery/fence regressions   | 3,083 passed                                                                                        |
| Frozen `npm ci`; `uv sync --locked`                                              | Passed; lockfiles unchanged                                                                         |
| `make format`; `make lint`                                                       | Passed                                                                                              |
| `make typecheck`                                                                 | Strict TypeScript passed; Python checked 186 source files                                           |
| `make audit`                                                                     | No known JavaScript/Python dependency vulnerabilities; existing editable application exclusion only |
| Broader `make test` after production-validator refactor                          | 869 frontend tests in 35 files; 4,645 API tests including all 42 PostgreSQL cases; no skips         |
| `make build`                                                                     | Passed; existing bundle-size warning, no threshold changes                                          |
| Isolated PostgreSQL health/upgrade; `make migration-check`; `make compose-check` | Passed; no schema drift                                                                             |
| Modify browser regression matrix                                                 | 45 passed across Chromium/Firefox/WebKit, four workers, zero retries                                |

A static failure matrix exercises every rejection site and all 24 closed reasons,
production/diagnostic parity, hostile-value log privacy, fixed first-failure
ordering, defaultScope=false, unchanged richer-mode rejection, all flag/head/
evidence guards and zero added GETs. Existing tests gain additional privacy,
no-authority and read-budget assertions; none are weakened. Fillet's rule table is
unchanged. Full-definition preservation, stale/fence/claim/recovery guarantees and
no-retry uncertainty behavior pass their existing broader suites.

Pytest disabled operator dotenv loading and stripped provider credentials; all
provider mutations used mock transports and real CAD writes stayed OFF. PostgreSQL
used a new pinned-image tmpfs-backed disposable task container with synthetic
credentials and a random loopback port. It was removed after checks; application
data/container were untouched. No real fixture read, proposal, approval, mutation,
deployment, dependency or production-setting change was performed by this task.
Diff/privacy review found only source vocabulary and synthetic test canaries.

**PHASE 16 TARGETED SHAPE DIAGNOSTIC PASS — READY FOR WRITES-OFF RECHECK**

This is an automated diagnostic pass. The human conformance result remains NO-GO.

### Exact next targeted writes-OFF recheck

1. Keep the SAME ordinary owned disposable fixture and existing local HTTPS/OAuth
   configuration. Load this updated local API with ENVIRONMENT=development,
   FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and FORGE_CAD_WRITES_ENABLED=false.
2. Click CAD Inspector → **Refresh CAD exactly once**. Do not prepare a Modify
   proposal, approve, enable writes or run a mutation script.
3. Privately inspect the new fixed standard_shape_failure/standard_shape_validation
   lines, grouped with existing coverage for both variants, especially
   noSketchGeometry=false. Record only category + known parameter + fixed reason,
   or category + exact_match. Do not share full logs, raw CAD, identifiers, values,
   payloads, expressions, query strings or tokens.
4. If a feature fails, stop and report only its first minimized tuple. Do not
   change the fixture or relax the parser to pass. The corrected Extrude may expose
   another first failure; Fillet remains unresolved until this evidence arrives.
5. Even if both current-UI predicates pass, require the existing replacement AND
   rename summaries to be exact_match with no unsupported/unknown/malformed/
   duplicate state. Keep CAD writes OFF. The separate human write stage still
   requires exact fresh preview and explicit approval for each operation.

## Graph boundary

ForgeModelGraph may later aid structural understanding, natural-language grounding
and target/reference reasoning. Phase 16 does not graph-migrate Modify. Graph facts
must not authorize writes. Authority remains fresh provider evidence + supported
edit registry + exact baseline + authoritative preview + explicit human approval +
fresh pre-dispatch evidence + provider microversion guard + fresh post-write exact
verification. Graph/read-only Tutor/Check my step authority is unchanged.

## Smallest disposable fixture for later human validation

Human creates a new, clearly disposable document owned by the connected user, with
one unconfigured mutable workspace Part Studio. Record exact identity privately;
no production, school/project, shared other-user, assembly, drawing or version target.
Use ordinary Onshape UI defaults, without export/import, API creation or FeatureScript:

1. `Sketch Phase16`: fully constrained 40 mm × 30 mm rectangle on a default plane.
2. `Extrude Phase16`: NEW, SOLID, one direction, BLIND, 20 mm; no draft/thin/second
   direction or additional options. Exactly one solid.
3. `Fillet Phase16`: terminal ordinary constant-radius edge fillet, 2 mm, one
   ordinary vertical edge, supported tangent propagation if present; no variable,
   asymmetric, width, conic or other richer settings. No downstream feature.

These names are display labels only. The real writes-OFF evidence checkpoint must
confirm both feature representations before activation; ordinary UI defaults may
serialize more fields than the current adapters accept. In that event keep the
ordinary fixture and investigate the adapter, not the other way around.

## Exact later human live-validation sequence — NOT EXECUTED

Only after the automated gate passes, the writes-OFF representation checkpoint
passes, and the human confirms the exact disposable target, the human operator may
temporarily enable the existing flag in the local HTTPS validation environment.
No global/production enablement or OAuth scope change is part of this record.
If required consent/credentials are unavailable, stop. Each dispatch additionally
requires the human's explicit approval of that exact fresh UI proposal. The agent
must not click approval, send an approval request or run an automatic write script.
Return the local flag OFF and confirm it after the controlled session.

Run one independent operation at a time, with the fixture manually restored between
cases if necessary. Do not start multi-operation live plans before all individual
cases pass. For unsuppress, the human first manually suppresses the terminal fillet
and confirms its exact state. Suggested exact requests and expected previews:

| Case                   | Modify request                                      | Required current → proposed                     |
| ---------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Depth                  | `Set the depth of Extrude Phase16 to 25 mm`         | Depth: exact observed 20 mm literal → 25 mm     |
| Radius                 | `Set the radius of Fillet Phase16 to 3 mm`          | Radius: exact observed 2 mm literal → 3 mm      |
| Extrude rename         | `Rename Extrude Phase16 to Extrude Phase16 Checked` | Name: Extrude Phase16 → Extrude Phase16 Checked |
| Optional Fillet rename | `Rename Fillet Phase16 to Fillet Phase16 Checked`   | Name: Fillet Phase16 → Fillet Phase16 Checked   |
| Suppress               | `Suppress Fillet Phase16`                           | Suppression: Active → Suppressed                |
| Unsuppress             | `Unsuppress Fillet Phase16`                         | Suppression: Suppressed → Active                |

For **every** row:

1. Explicitly read fresh model evidence. Confirm private document/workspace/element,
   user ownership/disposability, exact target/type/position and supported definition.
2. Submit the natural-language request through the real Modify tab. Verify one
   operation, intended feature and field, exact observed current → proposed value.
   If the literal differs from the table, investigate and review that exact value;
   never silently normalize or substitute approval.
3. **Cancel first.** Confirm cancelled status, zero provider mutations, unchanged
   Onshape CAD/tree and fresh reread of the unchanged baseline.
4. Generate a fresh proposal. Review its exact target/current/proposed value and
   approve **exactly once** within expiry. Preserve only private review evidence.
5. Confirm Checking → Applying → Verifying, with no success based on HTTP/ack alone.
   Confirm success appears only after fresh deterministic post-write verification.
6. Confirm exactly one provider mutation using private local observation and the
   fixed dispatch/ack/verification audit sequence; audit alone is not a provider-side
   transaction count. Never export tokens, request bodies or private network traces.
7. Reread and compare: same intended feature identity and tree membership/order;
   only approved name/expression/suppressed field changed (and corresponding inactive
   state where available); all unrelated definitions, parameters, queries and
   features unchanged. Check one valid solid remains. Parameter verification alone
   does not certify final dimensions, topology, model health or engineering suitability.
8. Record PASS/FAIL/UNVERIFIED and redacted observations; manually restore baseline
   if necessary before the next case. A verified prefix is not whole-plan success.

Prepared failure/authority cases, after individual success cases and still using
only disposable CAD:

- Stale proposal: prepare, manually change the disposable CAD, then approve the
  old proposal. Local context reset or server fresh-baseline rejection must stop it
  before provider dispatch. Zero Forge mutations; no provider-race experiment.
- Rapid double approval: one exact single-operation proposal, human rapid click;
  exactly one effective approval/provider mutation. No replay or scripted extra write.
- Cancel: pending proposal cancelled; zero mutations and later approval unavailable.
- Unsupported request (for example delete a feature): clarification/refusal, zero writes.
- Unsupported shape: human creates a richer option in a separate disposable copy,
  and requests its unsupported quantity/rename. No replacement proposal or write;
  valid independent terminal-suppression capability is not replacement support.
- No eligible target: empty disposable Part Studio; safe closed state, zero writes.
- Context switch: prepare in fixture, switch to another disposable Part Studio;
  local proposal authority clears, late responses cannot restore it. The server
  binds the captured context/baseline; it does not independently observe browser
  tab navigation. Never approve an old context through a private/manual request.

Do not intentionally cause uncertainty, corrupt network traffic or force a provider
race in the first live gate. Stop immediately for a non-disposable target, wrong
feature, unrelated change, ambiguous/unverifiable post-state, accepted unsupported
capability, duplicate mutation, stale dispatch, pre-approval write or regression of
Phase 9/recovery/fence guarantees. Keep uncertainty/fences intact; no retry or recovery
administration is authorized here. Return writes OFF and investigate with evidence.

## Live observations, repairs and final limitations

Actual Phase 16 live write observations: **NONE — human write stage not started**.
Human writes-OFF structural/representation observations are recorded above.
Representation-confirmed fixture: **NONE**. The human reports a disposable owned
fixture; its exact private identifiers are not recorded here. Five-operation live
verdict: **UNVERIFIED**.
Adapter state: **the human writes-OFF recheck remained NO-GO; confirmed Extrude
scope correction implemented; Fillet awaits the shared first-failure diagnostic**.
No live write pass is claimed.

Known limits remain the restricted studio/terminal-suppression policy, literal
quantity bounds, closed replacement profiles awaiting the real fixture recheck,
opaque provider-owned query contents, 8 KiB write
cap / 2 MiB response cap, 25-second pre-dispatch and 30-second whole-plan budget,
conservative exact comparisons that may reject benign provider normalization, and
manual recovery for quantity/rename/batch uncertainty. No topology continuity,
physical geometry equivalence, engineering certification or production readiness.
Phase 9 Gate B provider-side rejection audit remains deferred; this preparation
does not close it. Phase 16 remains incomplete until controlled human evidence
answers the conformance question. Phase 17 must wait for that separate decision.

## Common parameter metadata repair after the targeted recheck

**TARGETED RECHECK — NO-GO.** This is the latest human result, superseding any
prior preparation verdict. On the same disposable ordinary UI fixture, with
writes OFF and diagnostics ON, the shared validator reported:

- `category=extrude parameter=domain reason=unexpected_field`
- `category=fillet parameter=filletType reason=unexpected_field`

Structural/source/body evidence remained good. Zero proposals, approvals or
mutations occurred. These labels do not identify the extra field or its value.
The agent has neither requested nor read private CAD, identifiers or credentials.
Repair starting HEAD was clean and synchronized with the remote branch at
`4365437a7b4247f425cae981b1be735536685341`. Branch remains
`phase16/modify-live-conformance`; initial Phase 16 main is recorded above.

### Current official schema research

Read-only anonymous GET of the current
[official OpenAPI specification](https://cad.onshape.com/api/openapi), discovered
from the [official explorer](https://cad.onshape.com/glassworks/explorer/), returned
OpenAPI 3.0.1, info.version `1.222.91980-dcee49ea4d64`, on 2026-10-24.
The downloaded public schema SHA-256 was
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
The public download stays in ignored local cache; no CAD API was called.

`components.schemas.BTMParameter-1.properties` lists exactly btType,
importMicroversion, libraryRelationType, nodeId, parameterId, parameterName and
valueString. The last two have string types but no semantic descriptions.
`BTMParameterEnum-145.allOf` references that base and adds enumName, namespace,
value and an importMicroversion override. The import field is a writeOnly string
with import-microversion semantics, not a display placeholder.
`GBTParameterLibraryRelationType` lists DEFAULT, IGNORE_LIBRARY_VALUES and UNKNOWN;
it supplies no explanation proving any state harmless for this fixture.
Boolean, quantity, query-list and array parameter schemas also inherit the base.
Query items are a different schema and gain none of these parameter-only fields.

The [official feature API guide](https://onshape-public.github.io/docs/api-adv/featureaccess/)
documents omitted string defaults as empty strings, typed enumName/value and
quantity expression semantics. It warns its examples are v9 and actual encoding
can change. Therefore it supports the narrow empty-placeholder interpretation,
not arbitrary nonempty text or a library default. The current schema establishes
field names/types/inheritance; it does not prove the real fixture's values.
The official generated Go base/enum documentation corroborates the schema but
is not substituted for the current live OpenAPI response.

### Common metadata classification and closed acceptance

| Additional base field | Classification                                                          | Exact accepted state           | Rejected state / reason                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| parameterName         | A only for an empty serialization placeholder; C for nonempty semantics | absent or string exactly empty | nonempty strings, including whitespace; null, Boolean, number, array or object                                                            |
| valueString           | A only for an empty serialization placeholder; C for nonempty semantics | absent or string exactly empty | every nonempty string and wrong primitive; never interpreted as an expression or alternate value                                          |
| libraryRelationType   | B: potentially library-controlled; fixture state/harmlessness unproven  | absent only                    | every present state, including documented DEFAULT, IGNORE_LIBRARY_VALUES, UNKNOWN, legacy-looking NONE, empty, unknown or wrong primitive |

This is a deliberately narrow repair, not acceptance of all documented metadata.
No aliases, arbitrary fields, configured wrappers, external references, nonempty
imports, enum namespaces or richer modes gain authority. Existing node validation,
all 50/38 known-ID rules and mandatory guards are unchanged. Original minimal A1
profiles are unchanged. Unknown fields/IDs still fail closed.

The shared production validator validates these placeholders without modifying
input. It copies no metadata into its failure detail: unsupported common metadata
raises the existing generic unsupported_target error and unexpected_field reason
plus a separate strict frozen known-field/presence/closed-state object. DEV uses
that very exception, not a second parser or eligibility path. It appends only:

`common_field=parameterName|valueString|libraryRelationType present=true state=...`

Text classifications are nonempty_string or null/boolean/number/array/object.
Library classifications are default, ignore_library_values, unknown_library_value,
empty_string, unrecognized_string or those wrong-primitive classes. No value,
object key, arbitrary identifier or unknown field name can enter the projection.
There are no additional documented common fields in this base schema, so no
speculative other_documented_common acceptance or diagnostic is introduced.
Existing first-failure ordering is retained; the first rejected common field
uses fixed field order, then later checks remain unreachable until it validates.

All old DEV/diagnostics-ON/writes-OFF, complete/source-matched evidence,
matching-head and per-record emission guards remain. No extra GET: compare still
uses four, and the complete Inspector probe thirteen. No model, public/browser,
analytics, database, proposal or approval metadata is added. Real local writes
remain OFF; no live validation, deployment, merge or OAuth/domain change occurs.

### Preservation and automated coverage

Complete fresh definitions are deep-copied by the existing registry; only name,
depth.expression or radius.expression changes. No value is regenerated, normalized
or dropped. Field/parameter order, query contents, node IDs, metadata presence and
all unrelated fields remain exact. Existing transport serialization and its 8 KiB
bound remain unchanged. Fresh exact-effect verification still compares the whole
expected result; even removing an eligible empty metadata field fails verification.
No planner/approval/claim/fence/staleness/microversion/recovery code changes.
Graph facts and model suggestions still cannot authorize a write.

The updated synthetic fixture adds only invented empty metadata on representative
enums, quantities, Booleans, query lists and arrays. It adds no library state and
contains no private capture. A new test module covers the placeholders on all 88
known parameter occurrences, every wrong primitive/nonempty text, all present
library categories, aliases/config/import/unknown-field rejection, shared failure
parity, exact rename/depth/radius deltas, fresh post-write rejection of metadata
omission, closed schema and log privacy. All old assertions and bounds remain.

### Common metadata repair gate — PASS (writes OFF)

| Verification                                                                     | Result                                                                                     |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| New metadata module                                                              | **405 passed**, included below                                                             |
| Initial metadata + UI + shared-failure subset                                    | **1,513 passed**                                                                           |
| Focused Modify / planner / registry / diagnostics / recovery / fence regressions | **3,488 passed**                                                                           |
| Full API suite                                                                   | **5,050 passed**, including all **42 PostgreSQL** cases, no skips                          |
| Full frontend suite                                                              | **869 passed** in **35 files**, no skips                                                   |
| Modify browser matrix                                                            | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                     |
| Frozen installs                                                                  | npm ci and uv sync --locked passed; no dependency/lockfile changes                         |
| Required quality commands                                                        | make format, lint, typecheck, build, test, migration-check, compose-check and audit passed |

Strict Python checking passed across 187 source files; TypeScript checking passed.
The existing build bundle-size warning remains; no threshold, assertion, timeout,
safety bound or approval behavior was changed. npm audit found zero vulnerabilities;
pip-audit reported none among audited dependencies (editable forge-api excluded).
Migration checking found no new upgrade operations.

All CAD transport in tests was mocked. Credentials/local application settings were
excluded from test settings; the real local write flag was checked false before
and after verification. PostgreSQL 18.6 ran on a fresh loopback-only random port
with synthetic credentials and tmpfs storage; that temporary container was removed.
Existing application PostgreSQL was left running and untouched. No app database
reset, private CAD capture, deployment, proposal, approval or real mutation occurred.

Diff/privacy review found only the twelve files listed below. No secrets, local
environment files, provider authority code or production settings are included.
The current human conformance result remains **TARGETED RECHECK — NO-GO**.

### Common metadata repair files

- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/src/forge_api/integrations/onshape/standard_shape_contract.py
- apps/api/src/forge_api/integrations/onshape/dev/standard_shape_failure.py
- apps/api/src/forge_api/integrations/onshape/dev/safe_edit.py
- apps/api/tests/test_modify_common_metadata.py
- apps/api/tests/fixtures/modify_ui_parameters.json
- apps/api/tests/fixtures/README.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md

### Exact next human writes-OFF checkpoint

Keep ENVIRONMENT=development, diagnostics ON and CAD writes OFF. Use the SAME
privately confirmed disposable Sketch → Extrude → Fillet fixture. Perform one
CAD Inspector → Refresh CAD. Do not generate a proposal, approve or mutate CAD.
For **each** Extrude and Fillet, require all three:

- `safe_edit_standard_shape_validation ... outcome=exact_match`
- representation replacement `exact_match`
- representation rename `exact_match`

If either feature fails, STOP. If a common metadata failure remains, only its
known field/presence/state labels are needed; do not share raw values or CAD.
In particular, a library state remains rejected even if named DEFAULT, until its
harmless semantics and the fixture's closed state are proven. Automated repair
PASS means ready for this writes-OFF recheck only. It is not live conformance,
permission to enable writes, or permission for Phase 17.

## DEFAULT library metadata repair after the common-metadata recheck

**LATEST HUMAN WRITES-OFF RESULT — NO-GO, FIRST FAILURE IS NOW IDENTIFIED.**
This supersedes the earlier checkpoint descriptions above. The same disposable
ordinary UI Sketch → Extrude → Fillet fixture was refreshed exactly once with
DEV, diagnostics ON and writes OFF. Structural/source/body checks remained good.
The shared production predicate reported:

- Extrude: `category=extrude parameter=domain reason=unexpected_field common_field=libraryRelationType present=true state=default`
- Fillet: `category=fillet parameter=filletType reason=unexpected_field common_field=libraryRelationType present=true state=default`

No subsequent predicate was reached for those features. Zero proposals, approvals
or mutations occurred. The human has now confirmed the exact DEFAULT state on
ordinary parameters; the prior repair correctly withheld acceptance before this
fixture evidence existed. The agent has not read the private fixture or requested
raw CAD/identifiers. Starting branch was clean and synchronized with origin at
`cedb266f0aeb66a434da7e027c45111120173d5f` on
`phase16/modify-live-conformance`. Real CAD writes stay OFF throughout this repair.

### Authoritative library metadata research and its limits

A new anonymous read of the current
[official OpenAPI](https://cad.onshape.com/api/openapi) returned the same
OpenAPI 3.0.1 / `1.222.91980-dcee49ea4d64` schema as the prior repair, SHA-256
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
`BTMParameter-1.libraryRelationType` references the string enum
`GBTParameterLibraryRelationType`: exactly DEFAULT, IGNORE_LIBRARY_VALUES, UNKNOWN.
The standard enum, quantity, Boolean, query-list and array parameter schemas inherit
that base. There is no additional field or object wrapper to accept.
The [official generated enum documentation](https://github.com/onshape-public/go-client/blob/master/onshape/docs/GBTParameterLibraryRelationType.md)
and [generated Go enum definition](https://github.com/onshape-public/go-client/blob/master/onshape/model_gbt_parameter_library_relation_type.go)
corroborate those three string values and reject other strings in decoding.
Neither the live schema nor these generated files provides prose defining DEFAULT
or saying it disables every possible provider library behavior. There is no
OpenAPI default annotation proving absence semantically equivalent to presence.
Existing acceptance of absence is retained, not newly inferred from the enum name.

The current official public standard source was re-read through its view-only
Feature Studio, at FeatureScript 3095:
[Extrude source](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/aff9bec3150a48098a8184ac),
[Fillet source](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/841b26d2621a46bf98eda1d5).
Their feature predicates use semantic definition fields, including domain,
bodyType, filletType and entities; neither source contains libraryRelationType.
The [official Feature UI guide](https://cad.onshape.com/FsDoc/uispec.html) describes
these definition/precondition inputs. This supports keeping REST base metadata
separate from those semantic parameters. Absence in FeatureScript does **not**
prove provider-internal behavior. The API's configured/reference parameter wrappers
remain separate unsupported types; the library relation enum itself is not proof
that a feature is unconfigured or unimported.

The bounded conclusion combines schema type/inheritance, unchanged standard
semantic predicates, the independently checked simple/unconfigured baseline and
new real ordinary-fixture evidence: DEFAULT is the ordinary serialization state
observed here, and can be carried through unchanged. It is inert **to Forge's
semantic edit selection**, never interpreted, synthesized or used as authority.
This is not a universal claim about every Onshape feature or provider internals.
The other two enum values are distinct library-relation states, with no evidence
supporting equivalence to this observed state; both remain unsupported. No claim
that their exact configuration behavior is documented is made.

### Narrow contract and preservation

The only production change adds libraryRelationType to the finite shared current-UI
base field set and accepts it only when the primitive is string and the value is
exactly DEFAULT. Absence remains accepted under the old contract. No trimming,
case folding, aliases or conversion; DEFAULT with whitespace, default, NONE,
IGNORE_LIBRARY_VALUES, UNKNOWN, empty, null, Boolean, number, object, array and
arbitrary strings all reject. Unknown library-related fields still reject.
ParameterName/valueString remain absent or exactly empty string; importMicroversion
remains absent/empty only. Nonempty imports, configured wrappers, nonempty feature
namespace, richer modes and unknown fields/IDs retain all existing rejection.
Original minimal A1 profiles and query-item schemas are unchanged.

No diagnostic code or authority path changes. The existing shared predicate now
continues beyond a valid DEFAULT to every remaining field/guard. A later failure
still emits its fixed first-failure labels; exact_match derives only from complete
production validation. Existing representation projection derives
parameter_shape_matches_registry=true, replacement=exact_match and rename=exact_match
from that same predicate. No hardcoded success, extra GET, raw metadata log,
public/browser/model field, analytics or persistence is introduced.

Existing full-definition copying changes only name, depth.expression or
radius.expression. DEFAULT presence, value, key/parameter order, queries, node IDs
and all unrelated fields are preserved exactly. Nothing regenerates, normalizes
or removes library metadata. Fresh exact-effect comparison still covers the whole
inventory/configuration: removing DEFAULT, changing it, adding an otherwise valid
DEFAULT, or altering another feature's metadata cannot verify successfully.
The planner, digest, approval, one-use claim, fences, stale-state/context/expiry
checks, microversion guard, post-write reread, uncertainty/no-retry behavior,
recovery and graph boundary remain unchanged. Metadata never grants write authority.

### DEFAULT repair tests and gate

The synthetic fixture adds only the two schema-defined constants actually reported
by the human: Extrude domain and Fillet filletType DEFAULT. Other fields/identities
remain invented. New tests independently apply absent/present DEFAULT across all
88 known parameter occurrences, covering all five parameter families; reject all
other metadata/library states; prove imports/configuration remain closed; exercise
full copied provider payloads for both renames and both quantity edits; reject
unapproved library metadata effects; and verify success versus a genuine later
failure using the guarded four-GET diagnostic. Query items do not gain these fields.
Existing nondefault rejection assertions remain; the previously intentional
DEFAULT rejection is replaced by positive coverage and additional case/whitespace
rejections. Richer-mode, recovery/fence and uncertainty regressions are unchanged.

**DEFAULT library metadata repair automated gate — PASS, writes OFF.**

| Verification                                                                                    | Result                                                                                  |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New DEFAULT module                                                                              | **251 passed**                                                                          |
| Additional strict malformed/case/whitespace rejection variants                                  | **18** (269 added cases total)                                                          |
| Metadata + standard-shape + UI conformance subset                                               | **1,782 passed**                                                                        |
| Focused Modify / registry / planner / diagnostics / preservation / recovery / fence regressions | **3,757 passed**                                                                        |
| Full API suite                                                                                  | **5,319 passed**, including all **42 PostgreSQL** cases, no skips                       |
| Full frontend suite                                                                             | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                                           | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                                                 | npm ci, uv sync --locked passed; no dependency/lockfile changes                         |
| Full commands                                                                                   | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

Strict Python checking passed across 188 source files; TypeScript checking passed.
Audits found zero known vulnerabilities among audited dependencies (editable
forge-api excluded by the existing audit command). Migration check found no new
upgrade operations. The pre-existing bundle-size warning remains. No assertion,
bound, timeout, retry count, threshold or authority control was weakened.

All test CAD traffic was mocked, without real credentials or local application
settings. The real local write flag was checked false. PostgreSQL ran in a fresh
loopback-only random-port container with synthetic credentials and tmpfs storage;
application PostgreSQL/data were untouched. That temporary container is removed
after verification. No environment, secret, deployment or production setting is
part of the diff. The latest human conformance result remains NO-GO, pending the
final same-fixture writes-OFF refresh below. Counts overlap.

### DEFAULT repair files

- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/tests/test_modify_common_metadata.py
- apps/api/tests/test_modify_default_library_metadata.py
- apps/api/tests/fixtures/modify_ui_parameters.json
- apps/api/tests/fixtures/README.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md

### Exact final human writes-OFF checkpoint

Use this repair in ENVIRONMENT=development, diagnostics ON and CAD writes OFF.
Use the SAME privately confirmed disposable fixture. Perform exactly one
CAD Inspector → Refresh CAD; generate no proposal, approval or mutation.
For **both** Extrude and Fillet require:

- `safe_edit_standard_shape_validation ... outcome=exact_match`
- `parameter_shape_matches_registry=true`
- `replacement=exact_match`
- `rename=exact_match`

Also require `safe_edit_probe outcome=eligible_no_proposal_no_write`.
If any new closed failure appears, STOP and report only the sanitized labels.
Do not enable writes automatically. Even all these read checks passing does not
prove a live write; a separately authorized controlled human stage still follows.
No deployment, merge, production/OAuth/domain change or Phase 17 work is included.
