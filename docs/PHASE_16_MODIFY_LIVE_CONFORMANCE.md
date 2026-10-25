# Phase 16 — controlled real Modify conformance

**IN PROGRESS — EXTRUDE QUANTITY CONTRACT REPAIRED; FINAL WRITES-OFF EXACT-MATCH REFRESH REQUIRED**

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

## Current query-list filter evidence investigation

**FINAL WRITES-OFF RECHECK — STILL NO-GO.** This is the latest human result,
superseding previous checkpoint descriptions. On the SAME disposable ordinary UI
Sketch → Extrude → Fillet fixture, with DEV, diagnostics ON and writes OFF:

- DEFAULT library metadata failures are gone.
- Extrude: `category=extrude parameter=entities reason=unexpected_field`.
- Fillet: `category=fillet parameter=entities reason=unexpected_field`.
- Structural/source evidence remains good; zero proposals, approvals or mutations.

Starting branch was clean and synchronized with origin at required HEAD
`8fd3847e8b45479f94419eeadb4a2196c26c2530`, on
`phase16/modify-live-conformance`. Local CAD writes were verified OFF. No private
CAD/identifiers were requested or read by the agent. These first-failure labels
alone do not prove which extra field is present or reveal a filter tree.

### Official schema and concrete filter families

The current [official OpenAPI](https://cad.onshape.com/api/openapi) still returns
OpenAPI 3.0.1 / `1.222.91980-dcee49ea4d64`, SHA-256
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
`BTMParameterQueryList-148` inherits BTMParameter-1 and adds optional filter,
referencing BTQueryFilter-183, and optional queries, an array of
BTMIndividualQueryBase-139. The [official generated query-list model](https://github.com/onshape-public/go-client/blob/master/onshape/docs/BTMParameterQueryList148.md)
corroborates these fields. The base filter discriminator lists **37 concrete
subtypes**, not one generic safe object. The evidence vocabulary is checked against
that exact current list plus the abstract base; it is not a write allowlist.

Relevant schema facts:

| Concrete type                    | Declared subtype fields beyond btType              |
| -------------------------------- | -------------------------------------------------- |
| BTAndFilter-110 / BTOrFilter-167 | operand1, operand2, each another BTQueryFilter-183 |
| BTNotFilter-165                  | operand, another BTQueryFilter-183                 |
| BTEntityTypeFilter-124           | entityType                                         |
| BTGeometryFilter-130             | geometryType                                       |
| BTBodyTypeFilter-112             | bodyType                                           |
| BTEdgeTopologyFilter-122         | edgeTopology, isInternalEdge                       |
| BTConstructionObjectFilter-113   | isConstruction                                     |

The [official AND](https://github.com/onshape-public/go-client/blob/master/onshape/docs/BTAndFilter110.md),
[OR](https://github.com/onshape-public/go-client/blob/master/onshape/docs/BTOrFilter167.md)
and [NOT](https://github.com/onshape-public/go-client/blob/master/onshape/docs/BTNotFilter165.md)
models confirm fixed binary/unary operand slots, not arbitrary child arrays.
Other concrete families include sketch, active-sheet-metal, modifiable-entity,
reference and annotation filters. The SDK/schema does not establish which actual
concrete tree the current UI fixture serialized, its leaf values, omitted fields,
association order or whether otherwise equivalent Boolean forms are preserved.

### FeatureScript 3095 selection intent

The current public source captured in the prior source read was inspected for its
actual query annotations, with the recorded FeatureScript 3095 headers:
[Extrude](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/aff9bec3150a48098a8184ac),
[Fillet](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/841b26d2621a46bf98eda1d5).
The source establishes UI selection intent, not REST serialization evidence:

- Ordinary solid Extrude entities: either sketch faces with flattened geometry
  allowed, or planar faces with flattened geometry disallowed; both exclude
  construction objects. It is not an unrestricted generic face query.
- EDGE Fillet entities: inactive-sheet-metal two-sided edges or faces, or edges
  corresponding to sheet-metal definition vertices; construction and sketch
  objects are excluded and modifiability required. There is also a separate
  edge-only additional box-selection annotation.
- Extrude surfaceEntities selects sketch edges with modifiability/construction
  restrictions; wallShape has separate planar-face versus sketch-edge branches.
- Fillet side1Face/side2Face/centerFaces use face restrictions in FULL_ROUND;
  keepEdges uses two-sided edge restrictions; smoothCornerExceptions uses vertices.
  These cannot inherit an active entities filter by assumption.

The [official Feature UI guide](https://cad.onshape.com/FsDoc/uispec.html) explains
that annotations specify selection filters and that features must not rely on
those filters alone to prove query results. Therefore UI filter metadata is not
Forge target identity, engineering validation, AI permission or write authority.
The optional schema field may also occur on an empty query list: the schema does
not condition it on nonempty queries. Actual presence/tree shape for inactive
roles remains unproven. No active or inactive filter profile is accepted here.

### Closed production failure and DEV evidence only

The task's evidence-needed path is followed. **No adapter acceptance is broadened.**
Filter remains outside the accepted query-list envelope. When it is the only extra
field on an otherwise recognized current-UI query parameter, the same production
predicate raises generic unsupported_target / 422 with internal reason
query_filter_unproven and a strict frozen QueryFilterSummary. Unknown sibling
fields retain unexpected_field, and filter on quantities, arrays or query items
retains their existing rejection. All present filter values, including null and
malformed objects, still reject. Filter absence follows the unchanged old profile.

The DEV first-failure projection consumes that exact production exception; no
second filter-eligibility parser exists. It emits only:

- filter_root / categories: entity_type, geometry, body_type, edge_topology,
  construction, and, or, not, other_known or unknown.
- root_state: object, null or wrong_type.
- child_count: present recognized root operand slots, at most two.
- max_depth: maximum visited level, root=1, capped at eight.
- node_count: at most 64 visits, using an iterative bounded walk.
- malformed, missing_operand, unexpected_fields, uninspected and truncated flags.

Only SDK operand1/operand2/operand slots are traversed. No arrays, arbitrary keys
or unknown/other-known payloads are recursively walked. Wide objects are flagged
by bounded key checks; their values are not inspected. Leaf enum/geometry/Boolean
values are never read. uninspected marks opaque families, not an assertion that
other leaf values were validated. Clipped/opaque summaries are not exact trees.
Raw SDK type strings, arbitrary enums, names, IDs, node/deterministic IDs, query
strings, coordinates, tokens, URLs and provider JSON never enter the log model.
Known-looking names do not imply a supported filter or successful validation.

All existing DEV/diagnostics-ON/writes-OFF, completeness/source match, head bracket
and per-record guards remain. No extra GET: compare stays four, the full probe
thirteen. No public/browser/model payload, route, analytics or persistence changes.
Approval, digest, claims, fences, stale/context/expiry checks, microversion guard,
post-write reread, exact-effect comparison, uncertainty/no retry, recovery and the
graph authority boundary are unchanged. Existing parameter-opaque terminal
suppression remains separate from replacement/rename conformance.

### Preservation and test scope

The canonical synthetic fixture is not changed to invent a supposedly real tree.
SDK-shaped trees in tests are clearly labeled **unproven rejection cases**.
All filter-bearing replacement targets reject before proposal/dispatch or copying;
positive acceptance/preservation for actual target filter trees is deferred until
real sanitized evidence proves each exact role. No unsupported target is enabled
merely to manufacture a passing preservation test.

Existing full-definition copying and exact full-inventory verification are
unchanged. Tests cover both renames and depth/radius edits while an unrelated
feature's opaque filter remains exact, then prove removing/modifying that filter
or adding a filter to the edited target cannot verify. This proves inventory
preservation without granting replacement authority to an unproven filter target.
Existing richer-mode, library/import, uncertainty, recovery and fence assertions
are retained; the exhaustive failure matrix adds the new fixed rejection reason.

### Query-filter evidence automated gate — PASS, writes OFF

| Verification                                                                                    | Result                                                                                  |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New filter evidence module tests                                                                | **411 passed**                                                                          |
| Exhaustive shared-failure matrix                                                                | **85 passed**, including one added filter reason case                                   |
| Initial filter/shape/UI conformance subset                                                      | **1,520 passed**                                                                        |
| Focused Modify / registry / planner / diagnostics / preservation / recovery / fence regressions | **4,169 passed**                                                                        |
| Full API suite                                                                                  | **5,731 passed**, including all **42 PostgreSQL** cases, no skips                       |
| Full frontend suite                                                                             | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                                           | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                                                 | npm ci and uv sync --locked passed; no dependency/lockfile changes                      |
| Required commands                                                                               | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

There are 412 added cases total, counted within the overlapping suites above.
Strict Python checking passed across 190 source files; TypeScript checking passed.
The existing bundle-size warning remains. Audits found no known vulnerabilities
among audited dependencies (editable forge-api excluded by the unchanged command).
Migration check found no new upgrade operations. No assertion, timeout, threshold,
retry count, transport bound or authority control was weakened.

CAD test traffic was mocked, without real credentials/local application settings.
The real local write flag remained false. PostgreSQL used a fresh loopback-only
random-port container with synthetic credentials and tmpfs storage, removed after
verification; application PostgreSQL/data were untouched. Diff/privacy review
found only the files below, with no secret, environment, deployment, dependency or
production authority changes. This passing automated gate does not establish any
actual filter contract or live write conformance: **QUERY FILTER EVIDENCE NEEDED**.

### Query-filter evidence files

- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py
- apps/api/src/forge_api/integrations/onshape/standard_shape_contract.py
- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/src/forge_api/integrations/onshape/dev/standard_shape_failure.py
- apps/api/src/forge_api/integrations/onshape/dev/safe_edit.py
- apps/api/tests/test_modify_query_filter_evidence.py
- apps/api/tests/test_modify_shape_failure.py
- apps/api/tests/fixtures/README.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md

### Exact next query-filter evidence checkpoint

Using this commit, retain ENVIRONMENT=development,
FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and FORGE_CAD_WRITES_ENABLED=false.
Use the SAME privately confirmed disposable fixture. Perform **ONE CAD Inspector
→ Refresh CAD**. Generate no proposal, approval or mutation. Report only the new
safe_edit_standard_shape_failure lines for Extrude and Fillet, including their
closed root/count/category/flag fields, alongside the existing structural/source
and safe_edit_probe summaries. Do not provide raw filters, JSON, IDs, leaf values
or query strings. Group records by the existing noSketchGeometry variant.

Expected evidence if filter is the sole extra field is reason=query_filter_unproven
plus the closed summary; it is a deliberate continued rejection, not exact_match.
If unexpected_field remains, filter was not established as the sole cause: STOP
and report that fixed failure. If any other closed failure appears, STOP and
report it. Do not enable writes. Active/empty-role filter contracts and all real
write conformance remain unproven; this diagnostic gate grants no live-write or
Phase 17 creation authority, deployment or merge.

## QUERY FILTER REPAIR SAFETY REVIEW — LEGACY BYPASS FOUND

The final pre-commit safety review of the diagnostic preparation found a separate
fail-open historical representation path. No diagnostic work was committed at
that point; all 13 uncommitted files were preserved for this authorized repair.
Starting committed HEAD remained `8fd3847e8b45479f94419eeadb4a2196c26c2530` on
`phase16/modify-live-conformance`, matching origin. `git diff --check` passed.

The old registry selected its minimal path when parameter IDs were a subset of
the historical vocabulary. Its entities check required only a nonempty queries
list, ignoring additional envelope/query-item fields such as entities.filter.
Thus quantity replacement and full-definition rename could bypass the stricter
current-UI predicate. **This was found before enabling writes: zero real proposals,
approvals or mutations occurred.** The prior passing diagnostic tests did not
cover this bypass; the preparation was correctly stopped without commit/push.

### Complete, separate representation profiles

Profile selection now examines the entire parameter-ID multiset. Exactly five
unique Extrude IDs (bodyType, operationType, entities, endBound, depth), or exactly
three unique Fillet IDs (entities, radius, tangentPropagation), select the strict
historical validator. Every other collection goes whole to the existing closed
current-UI validator. A failed historical validation rejects immediately, never
falls through, strips a field, normalizes data or combines the two profiles.
The registry also requires the exact BTMFeature-134 and supported featureType.
Existing global fresh evidence still proves the ordinary top-level scope.

The historical parameter contract is closed at every level:

| Role               | Exact representation                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------- |
| Extrude enums      | BTMParameterEnum-145, enumName/value: ExtendedToolBodyType/SOLID, NewBodyOperationType/NEW, BoundingType/BLIND |
| entities           | BTMParameterQueryList-148, queries, no filter or unknown field                                                 |
| Extrude query item | Exactly btType=BTMIndividualSketchRegionQuery-140 and a nonempty string featureId                              |
| Fillet query item  | Exactly btType=BTMIndividualQuery-138 and a nonempty string queryString                                        |
| depth/radius       | BTMParameterQuantity-147, expression in the unchanged bounded literal mm/in grammar; optional isInteger=false  |
| tangentPropagation | Required BTMParameterBoolean-144 with actual Boolean value, either true or false                               |

Each parameter has its exact parameterId and may preserve a string nodeId, as
exercised by the existing A1 metadata-preservation tests. No current-UI common
metadata, quantity value/units, query node/deterministic IDs or unknown nested
fields are imported into this historical contract. Query lists are nonempty and
capped at 2,000 (the existing current-UI bound); opaque query strings/reference
strings are nonempty and capped at 8,192 characters, also subject to the unchanged
8 KiB request limit. No query is evaluated or sent to the planner. Original
feature/parameter/query data and order remain intact; the executor deep-copies
the fresh definition and changes only the approved expression or name.

Current-UI features retain their whole-feature validation. A filter-bearing UI
feature reaches the shared closed query_filter_unproven rejection, not the legacy
path. **No current-UI filter conformance is claimed.** The real fixture still needs
filter evidence. The bounded diagnostic is preserved unchanged: depth <=8,
visits <=64, fixed categories/counts/flags, no leaf values, IDs, queries or extra
provider GET. The next checkpoint deliberately remains a rejection when a filter
is encountered; the diagnostic does not prove its semantic contract.

### Suppression remains independent

Inspection of every write-client path confirms SET_SUPPRESSED/SET_UNSUPPRESSED use
/features/updates and only BTMFeature-134, featureId and suppressed in the feature
entry. They never transmit a parameter/query/filter tree. Replacement profiles do
not gate this independent attribute transport. Existing terminal-Fillet, explicit
Boolean state, supported scope, approval, fence and exact-effect rules remain.
Regression tests verify both directions with a filter-bearing parameter definition
that cannot be renamed or quantity-replaced, and reject nonterminal suppression.
The original Phase 9 suppression entry point retains the same minimal payload.

### Safety invariants before commit

1. Full-definition rename/depth/radius dispatch without one complete recognized
   parameter representation profile: **NO**. Discovery, planning, local transport
   preflight, dispatch construction and exact-effect verification share change /
   quantity_parameter; no alternate full-definition transport was found.
2. Unknown nested parameter/query/filter fields ignored by the minimal profile:
   **NO**. Every envelope has a finite exact field contract.
3. Suppression sends full feature parameters: **NO**.
4. CAD writes remain OFF: **YES**. Only isolated in-process synthetic mock clients
   enable their test-only flag; real local settings remain false.

Planner, approval, grant/session/context binding, expiry, one-use claims, stale
rejection, pre-dispatch rereads, rejectMicroversionSkew, fresh post-write rereads,
whole-inventory exact-effect comparison, fences, recovery, uncertainty, suffix
stopping and no-retry behavior are unchanged. Graph facts authorize no writes.
No live CAD access, real proposal/approval/mutation, deployment, merge, OAuth,
domain, secret, dependency or lockfile change is part of this repair.

### Profile safety repair verification

**Automated profile-safety repair gate passed; current real filter conformance
remains unproven.**

| Check                                                                            | Result                                                                                  |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New minimal-profile regression module                                            | **162 passed**                                                                          |
| Preserved query-filter diagnostic module                                         | **411 passed**                                                                          |
| Shared first-failure module                                                      | **85 passed**, including the added filter case                                          |
| All focused Modify / safe-edit / retained / AI-write / standard-diagnostic cases | **4,331 passed**                                                                        |
| Full API suite                                                                   | **5,893 passed**, including all **42 PostgreSQL cases**, no skips                       |
| Frontend suite                                                                   | **869 passed** in **35 files**, no skips                                                |
| Focused Modify browser matrix                                                    | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                                  | npm ci and uv sync --locked passed; no dependency or lockfile changes                   |
| Required commands                                                                | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

Counts overlap. There are **574 added cases** relative to the starting commit:
162 safety cases plus the preserved 412 diagnostic cases. Strict Python checking
passed across 191 source files, and TypeScript checking passed. Migration drift
check reported no new upgrade operations. Both dependency audits reported no
known vulnerabilities among audited packages; the unchanged Python audit excludes
the editable forge-api distribution. The pre-existing bundle-size warning remains.

Tests used synthetic fixtures, in-process mock CAD transport and isolated local
settings. PostgreSQL used a fresh healthy loopback-only random-port tmpfs container
with synthetic credentials; only that container was removed afterward. Existing
application PostgreSQL and data were untouched. Privacy/diff review found no
secret, raw CAD, environment, dependency, production configuration or unrelated
file changes. The real local Settings flag was confirmed false again after the
gate. All four security-review answers above were confirmed before commit.

The old positive expectation for absent tangentPropagation is tightened to reject;
its explicit true/false preservation assertions are retained. No safety assertion,
transport limit, retry setting, timeout or test threshold is weakened. The
historical JSON fixture is unchanged. New regression cases cover all historical
parameters, nested unknown/filter fields, missing/duplicate/extra parameters,
rename/quantity bypass, whole current-UI routing, direct transport preflight and
both suppression payload directions. The preserved diagnostic tests cover privacy,
bounds, guards, no extra GET and exact post-write effects.

### Combined repair files

Runtime:

- apps/api/src/forge_api/integrations/onshape/edit_registry.py
- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py
- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/src/forge_api/integrations/onshape/standard_shape_contract.py
- apps/api/src/forge_api/integrations/onshape/dev/standard_shape_failure.py
- apps/api/src/forge_api/integrations/onshape/dev/safe_edit.py

Tests / fixture provenance:

- apps/api/tests/test_modify_minimal_profile.py
- apps/api/tests/test_modify_query_filter_evidence.py
- apps/api/tests/test_modify_conformance.py
- apps/api/tests/test_modify_representation.py
- apps/api/tests/test_modify_shape_failure.py
- apps/api/tests/fixtures/README.md

Documentation:

- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md
- docs/HACKATHON_MODIFY_A1.md

### Exact next human checkpoint after this repair

Keep ENVIRONMENT=development, FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and
FORGE_CAD_WRITES_ENABLED=false. On the SAME privately confirmed disposable
Sketch → Extrude → Fillet fixture, perform **ONE CAD Inspector → Refresh CAD**.
Generate no proposal, approval or mutation. Report only the bounded
safe_edit_standard_shape_failure lines for Extrude and Fillet, grouped by the
existing noSketchGeometry variant, plus structural/source and safe_edit_probe
summaries. Do not supply raw filters, provider JSON, IDs, leaf values or queries.

A present filter is still expected to reject as query_filter_unproven and reveal
only its closed structural summary. Unexpected_field means filter was not proven
to be the sole extra envelope field; stop and report it. Any other new closed
failure also stops advancement. This code does not add a filter acceptance
contract; exact_match cannot be inferred from category recognition. No writes
until exact_match and a separately authorized human-controlled preview/approval
stage. Phase 17 creation remains future work.

## Exact closed filter signature diagnostic

Starting clean synchronized branch: phase16/modify-live-conformance, HEAD
`ffdac547df3a553f029da310e73ca1b3e35e6d8e`. Local Settings confirmed CAD writes
OFF before implementation. This continuation adds evidence only; no live CAD
read, proposal, approval or mutation is performed by the agent.

### Latest human checkpoint

One same-fixture writes-OFF Inspector refresh on ordinary Sketch → Extrude →
Fillet reached query_filter_unproven for both entities parameters:

| Feature | Root / children | Depth / visits | Categories                                                     |
| ------- | --------------- | -------------- | -------------------------------------------------------------- |
| Extrude | and / 2         | 5 / 13         | entity_type, geometry, construction, and, or, other_known      |
| Fillet  | and / 2         | 8 / 17         | entity_type, edge_topology, construction, and, or, other_known |

Both reported malformed=false, missing_operand=false, unexpected_fields=false,
uninspected=true and truncated=false. safe_edit_probe remained
eligible_no_proposal_no_write. The human reported zero proposals/approvals/mutations.
These are the actual observations; no exact subtype positions or leaf values
were supplied. The unordered category set and other_known cannot prove a tree.

### Current primary-source research

The public [current OpenAPI](https://cad.onshape.com/api/openapi) was fetched again
with TLS verification. It remains OpenAPI 3.0.1 / 1.222.91980-dcee49ea4d64,
SHA-256 6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb.
Its BTQueryFilter-183 discriminator still lists 37 concrete subclasses. Exact
subtype mappings, leaf field names/types and every finite enum value used below
were checked against that schema. No runtime schema fetch or dependency is added.

Official generated models corroborate [flattened geometry](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/docs/BTAllowFlattenedGeometryFilter2140.md),
[active sheet metal](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/docs/BTActiveSheetMetalFilter2944.md),
[sketch object](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/docs/BTSketchObjectFilter184.md),
[sheet-metal definition entity type](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/docs/BTSMDefinitionEntityTypeFilter1651.md)
and [modifiable entity](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/docs/BTModifiableEntityOnlyFilter1593.md).
All model properties are schema-optional: absence is diagnosed as missing, never
converted into an assumed Boolean/default or evidence of semantic equivalence.

### FeatureScript 3095 expected selection intent

The previously captured public [Extrude source](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/aff9bec3150a48098a8184ac)
and [Fillet source](https://cad.onshape.com/documents/12312312345abcabcabcdeff/w/a855e4161c814f2e9ab3698a/e/841b26d2621a46bf98eda1d5)
were re-inspected, including both FeatureScript 3095 headers and the actual entities
annotations. Expected intent, expressed with neutral semantic labels:

- Extrude: union of sketch faces with flattened geometry allowed, and planar
  faces with flattened geometry disallowed; construction objects excluded.
- Fillet: union of inactive-sheet-metal two-sided edges/faces, and edges whose
  sheet-metal definition entity is a vertex; exclude construction/sketch objects
  and require modifiable entities. The separate additional box-select filter
  selects edges; it must not be silently folded into the REST tree.

The source-derived synthetic candidates use binary left-associated conjunctions:

```text
Extrude:
and(or(and(and(allow_flattened_geometry,sketch_object),entity_type),and(and(geometry,allow_flattened_geometry),entity_type)),construction)

Fillet:
and(and(and(or(and(active_sheet_metal,or(and(entity_type,edge_topology),entity_type)),and(entity_type,sheet_metal_definition_entity_type)),construction),sketch_object),modifiable_entity_only)
```

These candidates produce exactly 13 visits/depth 5 and 17 visits/depth 8, matching
the observed counts. **That is consistency, not proof of serialization.** The
real operand grouping/order, exact subclasses, Boolean/enum values and optional
isInternalEdge/objectType fields remain unknown. The invented SDK-shaped fixture
omits those two optional fields and explicitly expects missing diagnostic states.
It is not a real capture or an acceptance fixture. The [Feature UI guide](https://cad.onshape.com/FsDoc/uispec.html)
also distinguishes UI selection filters from validating actual query results.

### Closed subtype vocabulary

other_known is replaced by exact normalized labels for all 29 formerly collapsed
concrete families: active_sheet_metal, allow_edge_point, allow_flattened_geometry,
allow_mesh_geometry, annotation, center_of_mass, closed_composite_constituent,
closed_curve, curved_text, feature, feature_type, flat_sheet_metal, image,
in_context_object, mate_connector, mate, modifiable_entity_only, occurrence,
plane_orientation, sheet_metal_application_type, sheet_metal_definition_entity_type,
section_geometry, sketch_object, sketch_solve_status, spline_control_polygon,
spline_handle, spline_internal_point, text_object and text_stroke. The original
eight concrete labels remain. The abstract base maps to query_filter and every
unrecognized discriminator maps to unknown. Thus 39 closed labels total, never
raw btType strings or prefix matches. Opaque families remain uninspected leaves;
recognizing a class does not validate its payload or grant edit authority.

### Closed topology and leaf states

The shared production rejection now carries a frozen, extra-forbidden projection:

- signature: a tuple of finite category/punctuation tokens, logged as a compact
  tree. Only documented operand1/operand2 and operand slots are traversed. Order
  follows those slots, never category sorting or Boolean normalization.
- signature_truncated: true on depth/node clipping, missing/extra operator slots
  or signature length clipping. The signature is then empty and logged unavailable;
  a partial tree is never presented as complete.
- leaf_states: ordered preorder visit numbers with fixed field/state labels. Visit
  numbers are local counters 1–64, never provider identities. Null/wrong-type
  children appear only as unknown with malformed=true. Missing fields remain
  missing; unknown enum strings become unknown_value. The official enum UNKNOWN
  maps separately to unknown_enum. Neither outputs any input text.

Only these schema-defined identity-free fields are projected:

| Category                           | Provider field → closed diagnostic field                        | Type                         |
| ---------------------------------- | --------------------------------------------------------------- | ---------------------------- |
| entity_type                        | entityType → entity_type                                        | GBTEntityType                |
| geometry                           | geometryType → geometry                                         | GBTGeometryType              |
| body_type                          | bodyType → body_type                                            | GBTBodyType                  |
| edge_topology                      | edgeTopology → edge_topology; isInternalEdge → internal_edge    | GBTEdgeTopology; Boolean     |
| construction                       | isConstruction → construction                                   | Boolean                      |
| allow_flattened_geometry           | allowsFlattenedGeometry → allow_flattened_geometry              | Boolean                      |
| active_sheet_metal                 | isFromActiveSheetMetal → active_sheet_metal                     | Boolean                      |
| sheet_metal_definition_entity_type | smDefinitionEntityType → sheet_metal_definition_entity_type     | GBTEntityType                |
| sketch_object                      | isSketchObject → sketch_object; objectType → sketch_object_type | Boolean; GBTSketchObjectType |
| modifiable_entity_only             | modifiableOnly → modifiable_entity_only                         | Boolean                      |

All five enums use compile-time exact finite dictionaries, not runtime lowercasing
or string formatting. Booleans require actual bool; 0/1 and strings do not coerce.
There are 12 field labels and 44 state labels, including missing/null/wrong_type/
unknown_value. No string-valued identity-bearing field is inspected. All other
known SDK families remain category-only opaque leaves. Unknown fields set closed
flags without walking their values. This is deliberately not a generic validator.

Bounds remain depth <=8 and raw visits <=64, with an iterative walk even for
cyclic/deep synthetic inputs. Signature length is <=4,096 characters, enforced
both by emission and the strict projection schema, with <=192 finite tokens.
Each leaf has at most two states and there are at most 64 leaf records. The whole
filter log record is bounded below 16,384 characters, including fixed metadata;
tests check actual candidates and the worst schema-permitted labels/counts.
Clipped leaf-state records describe only visited nodes; flags must accompany them.

### Privacy and authority proof

DEV emission still requires development, diagnostics ON, writes OFF, complete /
source-matched evidence, matching head bracketing and the per-record guard. It
uses the same production exception and the existing four comparison GETs; the
Inspector flow adds no new request. Raw provider JSON/types, IDs, queries, node /
deterministic IDs, names, coordinates, expressions, credentials and arbitrary text
cannot enter the literal-only projection. Public errors remain generic
unsupported_target. No browser/model/API payload, analytics, database or graph
projection is added. No new read or write authority exists.

The repaired historical profile is untouched: exact parameter sets, closed nested
envelopes, every filter rejected, no fallback. Current-UI filter rejection is also
unchanged, including every inactive role. Suppression remains the independent
attribute-only transport. Planner/approval, one-use claims, binding, stale checks,
microversion guards, fences, fresh post-write exact verification, uncertainty and
no-retry/suffix-stopping behavior remain unchanged. No adapter accepts a filter.

### Acceptance decision

**PHASE 16 EXACT FILTER SIGNATURE EVIDENCE NEEDED.** No role-specific acceptance
contract is justified yet. Source intent, SDK types and observed counts align
provisionally; real closed topology and leaf-state evidence are still missing.
The new fixture is explicitly source-derived synthetic data. Even a future exact
entities match must not authorize inactive roles such as surfaceEntities,
wallShape, booleanScope, side1Face, centerFaces or keepEdges.

Tests preserve an unedited feature's source-shaped filter and reject removal,
addition to the target, subtype changes, operand swaps and leaf semantic changes
for all four replacement operations. The edited target remains filter-free: this
does not claim preservation/acceptance of a target's filter. That write-validation
obligation remains deferred until an exact role-specific contract is proven.

### Automated signature gate

All automated gates passed with real CAD writes OFF. Counts overlap:

| Check                                                                            | Result                                                                                  |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New signature diagnostic module                                                  | **217 passed**                                                                          |
| Preserved query-filter evidence module                                           | **411 passed**                                                                          |
| Targeted signature / filter / minimal-profile / first-failure suites             | **875 passed**                                                                          |
| All focused Modify / safe-edit / retained / AI-write / standard-diagnostic cases | **4,548 passed**                                                                        |
| Full API suite                                                                   | **6,110 passed**, including all **42 PostgreSQL cases**, no skips                       |
| Frontend suite                                                                   | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                            | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                                  | npm ci and uv sync --locked passed; dependencies/lockfiles unchanged                    |
| Required commands                                                                | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

There are 217 added cases. Strict Python checking passed across 192 source files;
TypeScript checking passed. Audits reported no known vulnerabilities among audited
packages; the existing pip-audit command excludes the editable application. No
migration drift. The pre-existing bundle-size warning remains. No assertion,
timeout, retry setting, threshold, depth/node limit or authority control weakened.
The projection schema was tightened to enforce the signature character limit.

All CAD traffic was synthetic and mocked, isolated from operator dotenv and
credentials. PostgreSQL used a fresh healthy loopback-only random-port tmpfs
container with synthetic credentials; only that container was removed afterward.
Application PostgreSQL and data remained untouched. Local Settings confirmed
writes false after the gate. Final diff/privacy review found only the 11 files
below, with no environment, private CAD, credential, dependency, deployment or
production configuration change. The closed historical profile, current-UI
acceptance rules, write client, exact-effect verifier, planner and approval/fence
implementation are byte-for-byte unchanged from starting HEAD. Only diagnostic
vocabulary/projection/logging, tests and documentation change.

Automated success prepares the next evidence refresh. It does not prove actual
filter conformance, target-filter preservation or any live write.

### Signature diagnostic files

- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py
- apps/api/src/forge_api/integrations/onshape/dev/safe_edit.py
- apps/api/tests/test_modify_filter_signature.py
- apps/api/tests/test_modify_query_filter_evidence.py
- apps/api/tests/fixtures/modify_source_filters.json
- apps/api/tests/fixtures/README.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md

### Exact next writes-OFF checkpoint

Use this branch/commit with ENVIRONMENT=development,
FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true, FORGE_CAD_WRITES_ENABLED=false. On the
SAME privately confirmed disposable fixture, perform **ONE CAD Inspector → Refresh
CAD**. Generate no proposal, approval or mutation. Report only Extrude and Fillet
safe_edit_standard_shape_failure lines, grouped by the existing noSketchGeometry
variant, containing category/parameter/reason, root, closed signature,
signature_truncated, leaf_states, bounded counts and flags, plus the existing
structural/source and safe_edit_probe summaries. Do not provide provider JSON,
raw types, IDs, leaf input text or query contents.

Expected reason remains query_filter_unproven. A complete signature and finite
states enable comparison; they do not establish exact_match or authorize a write.
If truncated/uninspected/unexpected/malformed/missing flags or missing/unknown
states remain, stop advancement and report only those closed results. No extra
read, live write, merge, deployment, domain/OAuth/secret change or Phase 17 work.

## Flat sheet metal leaf evidence continuation

Starting clean synchronized branch: `phase16/modify-live-conformance`, HEAD and
fetched `origin/phase16/modify-live-conformance` both
`61cba7a25755dc63f8b20412fce1d752bd1097b8`
(`test: expose closed Onshape filter signatures`). No operator dotenv was present;
the inherited write flag was OFF/unset. CAD writes remain OFF. This patch makes no
private CAD read, proposal, approval or mutation.

### Latest human writes-OFF checkpoint

The human reported one same-fixture Sketch 1 → Extrude 1 → Fillet 1 Inspector
refresh. Both entities filters still rejected as `query_filter_unproven`.
Extrude's signature was:

```text
and(or(and(and(flat_sheet_metal,sketch_object),entity_type),and(and(geometry,flat_sheet_metal),entity_type)),construction)
```

Extrude had root=and, child_count=2, depth=5, nodes=13, malformed=false,
missing_operand=false, unexpected_fields=false, signature_truncated=false and
uninspected=true. The only recognized opaque family was flat_sheet_metal. Its
other closed leaf states were sketch_object=true,
sketch_object_type=any_sketch_object, entity_type=face twice, geometry=plane and
construction=false. Real `allows` presence/values were not supplied or inferred.

Fillet's signature was unchanged, depth=8/nodes=17, all structural flags false,
signature_truncated=false and uninspected=false. Its fully projected leaf states
included active_sheet_metal=false, entity_type=edge/face/edge,
edge_topology=two_sided, internal_edge=true,
sheet_metal_definition_entity_type=vertex, construction=false,
sketch_object=false, sketch_object_type=not_sketch_object and
modifiable_entity_only=true. The human reported
`safe_edit_probe outcome=eligible_no_proposal_no_write` and no proposal, approval
or mutation. These human observations are distinct from automated fixtures.

### Independently verified official schema

Before code changes, the current public [OpenAPI](https://cad.onshape.com/api/openapi)
was fetched with TLS verification: OpenAPI 3.0.1, API version
`1.222.91980-dcee49ea4d64`, SHA-256
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
`BTFlatSheetMetalFilter-3018` inherits `BTQueryFilter-183`, which contributes only
`btType`, and adds optional `allows: GBTFilterFlattenedGeometryOptions`. The subtype
has no other schema-backed fields. The enum is exactly MODEL_ONLY, FLATTENED_ONLY,
MODEL_AND_FLATTENED and UNKNOWN.

The official Go SDK [model](https://raw.githubusercontent.com/onshape-public/go-client/386ba6fdf60a7de469253857e227064c7df33273/onshape/model_bt_flat_sheet_metal_filter_3018.go)
and [enum](https://raw.githubusercontent.com/onshape-public/go-client/386ba6fdf60a7de469253857e227064c7df33273/onshape/model_gbt_filter_flattened_geometry_options.go)
independently corroborate both fields, optionality and all four values. The
official master SHA was checked during this continuation. No runtime schema
request, dependency or additional provider GET is introduced.

### Diagnostic mapping and privacy

| Input state         | Closed `allows` state |
| ------------------- | --------------------- |
| MODEL_ONLY          | model_only            |
| FLATTENED_ONLY      | flattened_only        |
| MODEL_AND_FLATTENED | model_and_flattened   |
| UNKNOWN             | unknown_value         |
| absent              | missing               |
| null                | null                  |
| wrong primitive     | wrong_type            |
| arbitrary string    | unknown_value         |

One compile-time Literal field and three Literal states are added to the existing
finite vocabulary (now 13 fields/47 states). The exact enum dictionary performs
no runtime lowercasing or provider-text formatting. UNKNOWN deliberately maps to
unknown_value for this subtype; mappings for every existing leaf are unchanged.
Null/wrong types also retain malformed=true. Missing is distinct from a default.

Only `btType` and `allows` form this subtype's diagnostic envelope. Any extra key
sets unexpected_fields=true and uninspected=true through the existing shared
logic; extra values, including trees/cycles, are not traversed. This envelope is
diagnostic inspection only. Every present filter still rejects, including known,
missing, malformed, unknown and extra-field cases. No raw type/enum string, ID,
query, provider JSON, field name or arbitrary value is projected or logged.

Depth <=8, visits <=64, signature <=4,096 characters, <=192 finite tokens,
<=64 leaf records with <=2 fields each and whole filter logs <16,384 characters
remain unchanged. Existing DEV/diagnostics-ON/writes-OFF, complete/source-matched,
matching-head and per-record guards are untouched. Tests require exactly the
same four GETs, zero writes and an unchanged input fingerprint.

The source-derived synthetic Extrude/Fillet fixture remains unchanged. Separate
synthetic candidates reproduce the human-reported Extrude topology but invent
`allows` inputs for coverage; they are not real captures or semantic equivalence
proof. Existing Fillet signature and leaf text are asserted unchanged. Legacy
profiles, edit registry, suppression, approval, stale checks, claims, microversion
guards, exact-effect verification, fences, recovery, uncertainty and retries are
untouched. No final filter acceptance contract is implemented.

### Verification

All automated gates passed with real CAD writes OFF; counts overlap:

| Check                                                          | Result                                                                 |
| -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| New flat-sheet-metal suite                                     | **42 passed**                                                          |
| Signature suite / preserved query-filter suite                 | **225 passed / 411 passed**                                            |
| Focused filter / shape / Modify diagnostics                    | **1,319 passed**                                                       |
| Full API suite                                                 | **6,160 passed**, including all **42 PostgreSQL cases**, no skips      |
| Frontend suite                                                 | **869 passed** in **35 files**, no skips                               |
| Modify browser matrix                                          | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries |
| Frozen installs                                                | npm ci / uv sync --locked passed; lockfiles unchanged                  |
| Format / lint / strict types / test / build / audits / Compose | Passed                                                                 |
| Disposable PostgreSQL migration / drift check                  | Passed; no new upgrade operations                                      |

There are 50 additional collected cases: 42 targeted, seven from extending the
existing closed-leaf matrix and one additional bounds case. All requested enum,
missing, null, wrong-type, unknown-string, extra-field and hostile-log cases are
covered. The bounds case exercises the new leaf at/over the unchanged depth/node
caps. The existing signature and schema-maximum log-length checks still pass.

Strict Python checking passed across 193 source files; TypeScript checking passed.
An initial test annotation mismatch was corrected before the successful strict
type gate. Audits found no known vulnerabilities among audited packages; the
existing Python audit excludes the editable application. The pre-existing bundle
size warning remains. No assertion, retry, timeout, threshold or safety bound was
weakened. No dependency, schema migration or deployment configuration changed.

Node 24/uv tools were obtained in a temporary directory because they were absent
from the normal PATH. Tests used no operator dotenv or inherited service
credentials. PostgreSQL used a fresh healthy loopback-only random-port tmpfs
container with synthetic credentials; only this verification container was
removed after the gate. Existing application data was not used or removed.
Local Settings confirmed writes=false. Final diff/privacy review and secret
pattern checks found no private CAD, credentials, keys or local environment data.
Only the diagnostic module, two test modules and five documentation files change.

Automated evidence is complete for this diagnostic patch. It does not establish
real `allows` values, semantic filter equivalence, target-filter preservation or
live write conformance. The next step remains the human writes-OFF refresh below.

### Files changed

- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py
- apps/api/tests/test_modify_filter_signature.py
- apps/api/tests/test_modify_flat_sheet_metal.py
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md
- docs/ROADMAP.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md

### Exact next human checkpoint

On this branch/commit, keep ENVIRONMENT=development,
FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and FORGE_CAD_WRITES_ENABLED=false. On the
same privately confirmed disposable Sketch 1 → Extrude 1 → Fillet 1 fixture,
perform **ONE CAD Inspector → Refresh CAD**. Generate no proposal, approval or
mutation. Report only existing closed structural/source/probe summaries and
Extrude/Fillet standard-shape failure lines grouped by the existing
noSketchGeometry variant. Include closed signatures, leaf states, counts and
flags; provide no private identifiers, raw enums/types, queries or provider JSON.

Extrude must still reject as query_filter_unproven and show uninspected=false,
signature_truncated=false, malformed=false, missing_operand=false,
unexpected_fields=false and explicit closed `allows=...` states at both
flat_sheet_metal visits. The signature/counts must remain the reported tree at
depth 5/nodes 13. Fillet must retain its already complete depth 8/nodes 17 tree.
The probe must remain eligible_no_proposal_no_write. Missing/null/wrong/unknown
leaf states or any structural flag leave evidence incomplete; report only those
closed results and stop advancement. Only after satisfactory human evidence may
a later authorized task construct exact role-specific acceptance. Do not accept
filters, enable writes, merge, deploy or begin Phase 17 in this continuation.

## Strict current-UI entities filter contracts

Starting clean synchronized branch: `phase16/modify-live-conformance`, local and
fetched origin HEAD `c415890a48e2357c1b6002d378df78f6f2f6be61`
(`test: close flat sheet metal filter evidence`). The operator dotenv was absent;
local Settings confirmed CAD writes OFF before implementation. No private fixture
read, real proposal, approval or mutation was performed by the agent.

### Complete human evidence

The human has now reported complete sanitized current-UI trees on the same
disposable Sketch 1 → Extrude 1 → Fillet 1 fixture. Both roots are and with two
children. Extrude has exactly 13 nodes/depth 5; Fillet exactly 17 nodes/depth 8.
Both reported malformed, missing_operand, unexpected_fields, uninspected,
truncated and signature_truncated all false. Body evidence was one SOLID with
NO_ERROR. The probe remained `eligible_no_proposal_no_write`; the human reported
no proposal, approval or mutation.

The exact human-observed Extrude entities topology is:

```text
and(or(and(and(flat_sheet_metal,sketch_object),entity_type),and(and(geometry,flat_sheet_metal),entity_type)),construction)
```

| Visit | Required closed leaf states                              |
| ----- | -------------------------------------------------------- |
| 5     | allows=model_and_flattened                               |
| 6     | sketch_object=true, sketch_object_type=any_sketch_object |
| 7     | entity_type=face                                         |
| 10    | geometry=plane                                           |
| 11    | allows=model_only                                        |
| 12    | entity_type=face                                         |
| 13    | construction=false                                       |

The exact human-observed Fillet entities topology is:

```text
and(and(and(or(and(active_sheet_metal,or(and(entity_type,edge_topology),entity_type)),and(entity_type,sheet_metal_definition_entity_type)),construction),sketch_object),modifiable_entity_only)
```

| Visit | Required closed leaf states                               |
| ----- | --------------------------------------------------------- |
| 6     | active_sheet_metal=false                                  |
| 9     | entity_type=edge                                          |
| 10    | edge_topology=two_sided, internal_edge=true               |
| 11    | entity_type=face                                          |
| 13    | entity_type=edge                                          |
| 14    | sheet_metal_definition_entity_type=vertex                 |
| 15    | construction=false                                        |
| 16    | sketch_object=false, sketch_object_type=not_sketch_object |
| 17    | modifiable_entity_only=true                               |

The current [official OpenAPI](https://cad.onshape.com/api/openapi) was independently
re-fetched before implementation: OpenAPI 3.0.1, API version
`1.222.91980-dcee49ea4d64`, SHA-256
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
All operator/leaf subtype field envelopes and enum/Boolean types were rechecked.
The schema supplies exact type/field mappings; the human evidence supplies the
specific role structure, optional-field presence and exact semantic states.
Schema recognition alone does not authorize any other tree.

### Acceptance and representation integration

`current_ui_filters.py` defines two private immutable typed shapes and two named
role predicates. The current-UI parameter validator selects the known feature
category before invoking the appropriate predicate for `entities`. It walks the
parsed provider objects directly, compares exact node types/key sets/operand
positions and type-checks every enum/Boolean value. Integers cannot stand in for
Booleans. No diagnostic signature, summary flag, rendered leaf text, string
normalization, tree sorting or Boolean-equivalence rewrite participates in
acceptance. The diagnostic module is not imported by the acceptance module.

The bounded iterative walk requires the exact role count/depth at completion.
Missing/extra nodes or fields, unknown/opaque subtypes, missing/null/wrong enum
values, UNKNOWN, alternative known values, operand swaps and equivalent-looking
reassociation reject. The fixed schema slots make partial/uninspected/truncated
trees impossible to accept. Depth <=8 / visits <=64 remain hard ceilings; the
actual accepted work is exactly 13 or 17 nodes. Extrude and Fillet trees cannot
substitute for each other. Other query roles, including empty inactive selections,
still reject every present filter with the existing `query_filter_unproven` detail.

Exact filters on the two proven entities roles proceed through all existing
query, quantity, mode, parameter, bookkeeping and whole-feature requirements.
Unknown/duplicate IDs, malformed inputs and richer modes still reject. The
50-input Extrude and 38-input Fillet fixtures with these exact reconstructed
filters reach standard-shape exact_match, parameter_shape_matches_registry=true,
replacement=exact_match and rename=exact_match. Previously supported filter-free
definitions retain their existing validation; no filter is removed to obtain a
match, and removal during execution fails exact-effect verification.

Historical minimal profiles remain byte-for-byte unchanged in the registry:
exactly bodyType/operationType/entities/endBound/depth for Extrude and exactly
entities/radius/tangentPropagation for Fillet. Their nested envelopes still reject
all filters, including the newly proven trees. A historical failure never falls
through to current UI. No hybrid profile, field stripping or default rebuilding
is introduced. Accepted full definitions, filters, parameter order and dormant
inputs are copied exactly; only the intended name or quantity expression changes.
The 8 KiB replacement limit is unchanged.

Suppression is independently eligible under its existing terminal-Fillet
contract, even when a replacement filter is invalid. SET_SUPPRESSED and
SET_UNSUPPRESSED retain dedicated `/features/updates` attribute-only transport;
no complete parameter/filter definition enters their mutation payload.

Human approval, authoritative preview/digest, session/context binding, expiry,
one-use claims, stale rejection, execution fences, pre-dispatch freshness,
rejectMicroversionSkew, fresh post-write reads, exact-effect verification,
uncertainty, no-retry/suffix stopping and recovery are unchanged. Model/AI and
ForgeModelGraph gain no provider-payload, approval or write authority. Only the
specific representation eligibility gap is closed. No live write is proven.

### Diagnostics and verification

Accepted roles now emit the existing guarded
`safe_edit_standard_shape_validation category=... outcome=exact_match` and
representation exact-match metadata. Rejected trees retain the same closed
failure/summary projection and generic public unsupported_target error. This adds
no raw provider types, enum strings, IDs, query text or arbitrary fields/values to
diagnostic logs, public/model payloads or persisted diagnostics. Existing DEV/diagnostics-ON/writes-OFF,
matching-head, complete/source-matched and per-record guards remain unchanged.
The mocked Inspector route still uses exactly 13 existing GETs, makes no proposal
or write, and adds no public diagnostic payload or header.

The new fixture reconstructs provider-shaped synthetic objects from sanitized
human evidence and official schema fields; it contains no private capture,
identity or query. The original historical, full-parameter and source-derived
filter fixtures remain unchanged. Source-derived incomplete candidates still
reject. Automated traffic uses only synthetic credentials and MockTransport;
isolated test Settings enable mock approval cases without changing the real flag.

Focused gate: **2,553 passed**, including **600 new strict-contract cases**.
Coverage mutates every node/type/key, every required leaf's presence/type/value,
every operator position/arity/order, both roles, inactive roles, historical
fallback, deep/wide/cyclic inputs and spoofed diagnostic summaries. Positive
cases cover full field/order preservation, four approved mock replacement kinds,
stale rejection before dispatch, one-use claims, unchanged size/microversion
guards, filter-aware fresh exact verification, independent suppression and the
human checkpoint's expected writes-OFF Inspector output. No safety test is skipped.

All full gates passed with real CAD writes OFF; counts overlap:

| Check                                        | Result                                                                 |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| New strict-contract suite                    | **600 passed**                                                         |
| Focused contract / filter / shape suites     | **2,553 passed**                                                       |
| Full API suite                               | **6,760 passed**, including all **42 PostgreSQL cases**, no skips      |
| Frontend suite                               | **869 passed** in **35 files**, no skips                               |
| Modify browser matrix                        | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries |
| Frozen installs                              | npm ci / uv sync --locked passed; lockfiles unchanged                  |
| Format / lint / strict typing / test / build | Passed                                                                 |
| Dependency audits / Compose validation       | Passed                                                                 |
| Isolated migrations / migration drift        | Passed; no new upgrade operations                                      |

Strict Python checking passed across 195 source files; TypeScript checking passed.
An empty-list test annotation was corrected before the successful strict type
gate. Audits found no known vulnerabilities among audited dependencies; the
existing Python command excludes the editable application. The pre-existing
bundle-size warning remains. No safety assertion, bound, retry, timeout or
threshold was weakened, and there are no dependency/schema migrations.

PostgreSQL used a fresh healthy loopback-only random-port tmpfs container with
synthetic credentials, isolated from operator dotenv and service credentials.
Only that verification container was stopped/removed; existing services/data were
retained. Local Settings confirmed writes OFF. Diff/privacy and secret-pattern
review passed. Registry/legacy profiles, write client, exact verifier, approval /
claims/fences/recovery, graph code, frontend and all original fixtures/lockfiles
remain unchanged. The diagnostic module has documentation-only changes.

**PHASE 16 STRICT FILTER CONTRACT PASS — READY FOR WRITES-OFF EXACT-MATCH CHECKPOINT**

### Strict-contract files changed

- apps/api/src/forge_api/integrations/onshape/current_ui_filters.py
- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py (docstrings only)
- apps/api/tests/test_modify_filter_contracts.py
- apps/api/tests/fixtures/modify_observed_filters.json
- apps/api/tests/fixtures/README.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md
- docs/ROADMAP.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md

### Exact next human writes-OFF checkpoint

On the original development Mac, pull `phase16/modify-live-conformance`. Keep
ENVIRONMENT=development, FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and
FORGE_CAD_WRITES_ENABLED=false. On the SAME disposable Sketch 1 → Extrude 1 →
Fillet 1 fixture, perform **exactly ONE Inspector → Refresh CAD**. Do not generate
a proposal, approval or mutation.

For each existing noSketchGeometry variant, both Extrude and Fillet must show:

- standard shape validation = exact_match;
- parameter_shape_matches_registry = true;
- replacement = exact_match;
- rename = exact_match.

The probe must remain `safe_edit_probe outcome=eligible_no_proposal_no_write`,
with the existing structural/body evidence intact. No query_filter_unproven may
remain for the accepted Extrude/Fillet entities roles. Report only these closed
states and any later closed first failure; provide no private identifiers, query
contents or provider JSON. Any failure stops advancement and requires separate
review. This human exact-match checkpoint is still mandatory before the first
separately authorized controlled mutation. Do not enable writes, merge, deploy,
run a live write trial or begin Phase 17 in this continuation.

## Inventory every current query role in one refresh

Starting clean synchronized branch: `phase16/modify-live-conformance`, local and
fetched origin HEAD `2f68b5f2478b030238d4dad1a8246f4e2f56b61c`
(`fix: accept exact current Onshape filter contracts`). Local Settings confirmed
CAD writes OFF; no operator dotenv was present. No private CAD read, real proposal,
approval or mutation is part of this continuation.

### Latest human writes-OFF result

The strict entities contracts no longer appeared as the first failure. Validation
advanced to Extrude `surfaceEntities` and Fillet `side1Face`, each still rejected
with `query_filter_unproven`. This confirms progress through the entities checks;
it does not establish whole-feature representation exact_match or live writes.

Extrude surfaceEntities:

```text
and(and(and(entity_type,sketch_object),modifiable_entity_only),construction)
```

The human reported two children, depth 4/nodes 7, entity_type=edge,
sketch_object=true, sketch_object_type=any_sketch_object,
modifiable_entity_only=true and construction=false.

Fillet side1Face:

```text
and(and(and(and(entity_type,construction),sketch_object),modifiable_entity_only),active_sheet_metal)
```

The human reported two children, depth 5/nodes 9, entity_type=face,
construction=false, sketch_object=false, sketch_object_type=not_sketch_object,
modifiable_entity_only=true and active_sheet_metal=false.

For both, malformed, missing_operand, unexpected_fields, uninspected, truncated
and signature_truncated were all false. Body evidence remained one SOLID with
NO_ERROR; the probe remained eligible_no_proposal_no_write. The human reported
no proposal, approval or mutation. Neither newly exposed role is accepted here.

### Independent complete-role diagnostic

`dev/query_roles.py` enumerates every present parameter whose source kind is query
or whose provider representation is query-bearing. It derives names/order from
the existing source vocabulary and the actual returned parameters, independently
of the first-failure production validator. Exact query-list types and malformed
envelopes containing queries/filter are included, even on a source non-query role;
that source/provider disagreement is flagged malformed. No hand-maintained role
allowlist or early stop at the first unsupported parameter is used. A missing
optional parameter is not invented. Every recognized discovered role appears
exactly once in source-catalog order, independent of returned parameter ordering.

Current complete synthetic feature fixtures yield the following sets. These are
catalog/fixture observations; the next refresh must establish actual human data.

- Extrude (13): entities, surfaceEntities, wallShape, endBoundEntityFace,
  endBoundEntityBody, endBoundEntityVertex, secondDirectionBoundEntityFace,
  secondDirectionBoundEntityBody, secondDirectionBoundEntityVertex,
  extrudeDirection, startOffsetEntity, booleanScope, booleanSurfaceScope.
- Fillet (8): entities, side1Face, side2Face, centerFaces, startPartialEntity,
  endPartialEntity, keepEdges, smoothCornerExceptions.

The two existing pinned feature GET variants are reused. After matching-head
bracketing, each emits `safe_edit_query_role` rows with noSketchGeometry, local
feature position/category, fixed role name, occurrences, query state/count/capping,
filter presence, root/child count/depth/nodes/categories, structural flags,
normalized signature/signature_truncated and closed leaf states. Empty lists are
inspected exactly like nonempty lists. Query item contents are never read by this
projection. Missing/null/wrong list states remain explicit; counts cap at 2,000.
Absent filters have filter_present=false with unavailable signature and zero
filter counters; a present null filter is separately projected as malformed.
No absent filter/default semantic value is invented.

Each feature also emits `safe_edit_query_role_summary` with position/category,
total_query_roles_discovered, total_query_roles_inspected, all_roles_inspected,
any_malformed, any_unexpected_fields, any_uninspected and any_truncated, plus
unrecognized_query_parameters and parameter_count_capped. Counts include every
recognized unique query role plus unidentified query-bearing parameters. Unknown
identities are counted but never printed; they prevent completeness. Counts are
lower bounds if scanning is clipped. A duplicate role emits one ambiguous record
with its occurrence count; no duplicate payload is selected as representative.
Its state is unavailable and its inspection is explicitly incomplete.

The inspected count excludes opaque, unknown-field, duplicate and clipped roles.
all_roles_inspected=true requires every discovered role to be accounted for with
no such inspection gap. A fully classified malformed primitive can still be
counted as inspected; any_malformed separately prevents treating it as clean
evidence. Completeness and all-false flags are diagnostic observations, never
acceptance. Closed unknown/missing semantic states still require human review.

### Privacy, bounds and authority

Only existing finite role/category/state vocabularies and bounded counters/flags
leave the projection. No raw provider JSON, btType/enum text, IDs, names, query
strings, node IDs, arbitrary field names/values or credentials are logged.
Unknown fields are flagged without walking their values. Frozen extra-forbidden
schemas carry already-closed filter summaries; provider mappings are not accepted
as nested projection instances or exposed in validation-error paths.

Bounds are 20 features, 100 scanned parameters per feature, at most the current
maximum source vocabulary size of 50 role rows, query counts <=2,000 and the
unchanged per-filter depth <=8/nodes <=64/signature <=4,096 characters/192 tokens.
Each new row is bounded below 17,408 characters including its fixed log header.
New inventory logs cap at 128 KiB per feature/variant including the summary, or
5 MiB over both variants at the 20-feature limit. Output-budget clipping preserves
each role's row, removes its filter payload explicitly, and marks uninspected /
truncated/incomplete; it never silently omits a role or claims full inspection.

Projection and every emitted row/summary retain development, diagnostics ON,
writes OFF, complete/source-matched and matching-head guards. A flag change stops
subsequent inventory records. Existing compare uses four GETs; the full Inspector
test retains 13 total GETs, with zero extra acquisition or mutation requests.
No public/browser/model metadata, API/header, persistence, background job or
mutation-capable entry point is added.

Strict Extrude/Fillet entities contracts, current-UI parameter rules, historical
profiles, registry, suppression transport, approval, authoritative preview/digest,
one-use claims, stale rejection, fences, microversion guards, freshness, post-write
exact-effect verification, uncertainty, no-retry and recovery remain unchanged.
The production first failures remain surfaceEntities and side1Face in the
reported-shape synthetic tests; representation remains unsupported_shape.
No inactive role is accepted and no fully inspected tree is presumed writable.
The pure evidence collector cannot grant eligibility. CAD writes remain OFF.

### Verification

Focused diagnostic/filter/contract/minimal-profile suites: **1,974 passed**,
including **55 new inventory cases** and all **600 unchanged strict-contract
cases**. Coverage includes complete derived role sets, once-only/catalog ordering,
empty lists, absent filters/parameters, source/provider disagreement, malformed
envelopes/operands, unknown identities/fields/subtypes, duplicates, cycles,
depth/node/count/output limits, strict projection privacy, runtime/source/head /
per-record guards, unchanged authority and a GET-only Inspector route with zero
proposal/fence records. Dormant filters on roles other than the two reported ones
are explicitly invented diagnostic fixtures, not new live evidence or contracts.

All full suites/checks passed with real CAD writes OFF; counts overlap:

| Check                                   | Result                                                                 |
| --------------------------------------- | ---------------------------------------------------------------------- |
| New query-role inventory suite          | **55 passed**                                                          |
| Focused diagnostic/filter/contract gate | **1,974 passed**                                                       |
| Preserved strict entities suite         | **600 passed**, unchanged                                              |
| Full API suite                          | **6,815 passed**, including all **42 PostgreSQL cases**, no skips      |
| Full frontend suite                     | **869 passed** in **35 files**, no skips                               |
| Modify browser matrix                   | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries |
| Frozen installs                         | npm ci / uv sync --locked passed; dependencies/lockfiles unchanged     |
| Format / lint / strict types / build    | Passed                                                                 |
| Dependency audits / Compose validation  | Passed                                                                 |
| Isolated migrations / migration drift   | Passed; no new upgrade operations                                      |

Two initial frontend runs at default parallelism reported timeout/DOM-wait
failures (84 and 31 cases). The complete unchanged `make test` command then passed
with the supported execution-only `VITEST_MAX_WORKERS=2` environment setting.
Every frontend case and API/PostgreSQL case ran. No test, assertion, timeout,
threshold, repository runner configuration or product retry rule was changed;
the browser matrix retained its normal four workers and zero retries.

Strict Python checking passed across 197 source files; TypeScript checking passed.
Audits reported no known vulnerabilities among audited dependencies; the existing
Python command excludes the editable application. The pre-existing bundle-size
warning remains. No dependency, environment file, migration or deployment setting
changed. A new projection test caught raw key text in nested validation-error
locations; the new role schema was tightened to require an already-closed filter
summary before the successful privacy/full gates. No raw provider mapping is
passed into that nested schema in the live projection.

PostgreSQL used a fresh healthy loopback-only random-port tmpfs container with
synthetic credentials and an isolated gate environment. Only that verification
container was stopped/removed; existing services/data were retained. Local
Settings confirmed writes OFF. Final scope/privacy/secret-pattern review passed.
The strict filter contracts, current-UI validator, registry/legacy profiles,
write client, exact verifier, approval/claims/fences/recovery, graph code, frontend,
all original tests/fixtures and lockfiles remain byte-for-byte unchanged. Shared
filter evidence has docstring-only changes; its vocabulary/traversal is unchanged.

**PHASE 16 QUERY ROLE INVENTORY PASS — READY FOR COMPLETE HUMAN FILTER EVIDENCE REFRESH**

### Query-role inventory files changed

- apps/api/src/forge_api/integrations/onshape/dev/query_roles.py
- apps/api/src/forge_api/integrations/onshape/dev/safe_edit.py
- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py (docstrings only)
- apps/api/tests/test_modify_query_role_inventory.py
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md
- docs/ROADMAP.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md

### Exact next human complete-evidence checkpoint

On the original development Mac, pull `phase16/modify-live-conformance`. Keep
ENVIRONMENT=development, FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and
FORGE_CAD_WRITES_ENABLED=false. On the SAME disposable Sketch 1 → Extrude 1 →
Fillet 1 fixture, perform **exactly ONE Inspector → Refresh CAD**. Generate no
proposal, approval or mutation.

Report every `safe_edit_query_role` row and both feature summaries for each
noSketchGeometry=true/false variant, including accepted entities and every empty
role. Report actual discovered/inspected totals, all_roles_inspected and every
aggregate flag, plus the existing closed first-failure/body/probe summaries.
Require discovered=inspected, all_roles_inspected=true, no unidentified/duplicate
roles, no count/output clipping and all malformed/unexpected/uninspected/truncated
flags false for complete evidence. Record explicit filter presence and all closed
leaf states. Missing/unknown states or any inspection gap stop advancement.

The probe must remain eligible_no_proposal_no_write, with one SOLID / NO_ERROR
body evidence. First-failure query_filter_unproven on dormant roles is expected;
full representation exact_match is not claimed. Share only these sanitized
records, never provider JSON or identifiers/query contents. A later separately
authorized task may assess exact role-specific inactive-filter contracts from
the complete evidence. No merge, deployment, real writes or Phase 17 work here.

## Close the remaining mesh/mate and diagnostic-depth evidence gaps

Starting clean synchronized branch: `phase16/modify-live-conformance`, local and
fetched origin HEAD `18493146f5cb5b220036603c089ab40f6eaf4ece`
(`test: inventory all current Onshape query roles`). Local Settings confirmed CAD
writes OFF. No private fixture read, real proposal, approval or mutation was made
by the agent. Dormant-role acceptance is not part of this continuation.

### Complete human inventory results, incomplete filter evidence

One same-fixture Sketch 1 → Extrude 1 → Fillet 1 refresh discovered all 13 Extrude
and 8 Fillet query-bearing roles, but reported:

| Feature | Discovered / inspected | All inspected | Malformed / unexpected | Uninspected | Truncated |
| ------- | ---------------------- | ------------- | ---------------------- | ----------- | --------- |
| Extrude | 13 / 4                 | false         | false / false          | true        | true      |
| Fillet  | 8 / 6                  | false         | false / false          | true        | false     |

The human reported eligible_no_proposal_no_write and no proposal, approval or
mutation. The already complete Extrude roles were entities, surfaceEntities,
wallShape and startOffsetEntity. The already complete Fillet roles were entities,
side1Face, side2Face, centerFaces, keepEdges and smoothCornerExceptions. Their
normalized behavior is preserved; the 600 strict entities cases remain unchanged.

The remaining shallow evidence classes were:

| Roles                                                   | Observed normalized topology                                                                       | Known semantic states; remaining gap                                            |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| endBoundEntityFace / secondDirectionBoundEntityFace     | or(and(and(entity_type,sketch_object),allow_mesh_geometry),body_type)                              | face; sketch=false/not_sketch_object; body=mate_connector; mesh opaque          |
| endBoundEntityBody / secondDirectionBoundEntityBody     | and(and(and(entity_type,or(body_type,body_type)),sketch_object),allow_mesh_geometry)               | body entity; solid/sheet bodies; sketch=false/not_sketch_object; mesh opaque    |
| endBoundEntityVertex / secondDirectionBoundEntityVertex | or(entity_type,mate_connector)                                                                     | vertex; mate connector opaque                                                   |
| booleanScope                                            | and(and(and(entity_type,body_type),modifiable_entity_only),allow_mesh_geometry)                    | body entity/solid; modifiable=true; mesh opaque                                 |
| booleanSurfaceScope                                     | and(and(and(and(entity_type,body_type),modifiable_entity_only),allow_mesh_geometry),sketch_object) | body entity/sheet; modifiable=true; sketch=false/not_sketch_object; mesh opaque |
| startPartialEntity / endPartialEntity                   | or(and(entity_type,allow_mesh_geometry),or(entity_type,mate_connector))                            | face/vertex; mesh and mate connector opaque                                     |

Extrude extrudeDirection reported root=or, child_count=2, depth=8/nodes=15,
malformed/missing_operand/unexpected_fields=false, uninspected/truncated=true and
signature_truncated=true with signature unavailable. Known leaves included line,
circle, arc, cylinder and plane geometry plus body_type=mate_connector. **Its
complete real topology was hidden and remains unknown.** No production contract,
real fixture capture or reconstructed complete topology is inferred from this.

### Official schema verification before implementation

The current public [OpenAPI](https://cad.onshape.com/api/openapi) was fetched with
TLS verification: OpenAPI 3.0.1, version `1.222.91980-dcee49ea4d64`, SHA-256
`6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb`.
BTQueryFilter-183 contributes only btType. The exact subtype envelopes are:

- BTAllowMeshGeometryFilter-1026: btType plus optional Boolean allowsMeshGeometry.
- BTMateConnectorFilter-163: btType plus optional Booleans
  allowImplicitMateConnector, isMateConnectorInferenceEnabledByDefault and
  requiresOccurrence.

The official generated SDK independently confirms the
[mesh model](https://raw.githubusercontent.com/onshape-public/go-client/386ba6fdf60a7de469253857e227064c7df33273/onshape/model_bt_allow_mesh_geometry_filter_1026.go)
and [mate connector model](https://raw.githubusercontent.com/onshape-public/go-client/386ba6fdf60a7de469253857e227064c7df33273/onshape/model_bt_mate_connector_filter_163.go).
Official master was checked at that exact SHA. Comments and independent tests
record this provenance; no runtime schema request or dependency is introduced.
SDK getter zero values are not evidence of a missing provider field's value.

### Closed leaf inspection and separate diagnostic depth

The finite diagnostic projection adds exactly these schema-backed mappings:

| Provider field                           | Closed diagnostic field          |
| ---------------------------------------- | -------------------------------- |
| allowsMeshGeometry                       | allow_mesh_geometry              |
| allowImplicitMateConnector               | allow_implicit_mate_connector    |
| isMateConnectorInferenceEnabledByDefault | mate_connector_inference_default |
| requiresOccurrence                       | requires_occurrence              |

Each independently emits only true, false, missing, null or wrong_type. Actual
Boolean type is required: integers, strings, arrays and objects never coerce or
echo. Null/wrong-type values flag malformed; missing stays explicit with no default
inference. Unknown fields still set unexpected_fields/uninspected without walking
their values. Exact discriminator matching is unchanged; unknown schema variants
remain opaque/uninspected. No new categories or state values are added, only four
compile-time field labels. The real Boolean values still require a human refresh.

The default `unproven_filter_summary` and its production rejection model retain
depth <=8. A separate `diagnostic_filter_summary` / sibling
`DiagnosticQueryFilterSummary` is used only by the DEV role inventory, with
depth <=16 and the unchanged node cap <=64. The models are separate: extended
evidence does not validate as the production rejection model. Strict production
acceptance remains byte-for-byte unchanged, including its independent depth-8 /
64-node ceilings and exact role shapes.

Depth 16 is a modest doubling of the clipped evidence allowance. The truncated
human result cannot establish the exact required height, so no guessed height or
topology is claimed. The iterative walker still follows only fixed SDK operands,
counts raw visits, terminates safely on cycles and clears signatures on any
depth/node/arity/length clipping. If the real tree exceeds 16 or 64 nodes, it must
remain incomplete. There is no recursive or arbitrary provider-value walk.

Mate connector has three Boolean fields, so the closed per-leaf field bound is
now three. The worst-schema filter-message budget is 20 KiB (previously 16 KiB),
with <=4,096 signature characters / 192 tokens / 64 leaf records unchanged. The
inventory row budget is correspondingly 21 KiB including its fixed header. Its
128 KiB per-feature/variant and 5 MiB whole-refresh ceilings are unchanged;
budget clipping remains explicit and preserves every role row. Schema-maximum
tests now exercise all three fields rather than the old two-field maximum.

No raw provider JSON/types/values, IDs, node IDs or query text escape. Frozen
projection models still require already-closed diagnostic summaries. DEV,
diagnostics-ON/writes-OFF, complete/source-matched, matching-head and per-record
guards remain; the Inspector still uses its existing 13 GETs (four for compare),
with no additional provider acquisition or mutation request.

### Authority and automated evidence

No dormant role gains acceptance. The exact entities predicates, full current-UI
parameter validator, registry/historical profiles, suppression transport,
approval/preview/digest, stale checks, one-use claims, execution fences,
rejectMicroversionSkew, pre-dispatch freshness, post-write fresh evidence,
exact-effect verification, uncertainty/no-retry, recovery and graph/model
boundaries are unchanged. Normal first failures remain Extrude surfaceEntities /
Fillet side1Face → query_filter_unproven. Diagnostic completeness cannot grant
write eligibility. CAD writes remain OFF; no real write success is claimed.

Focused gate: **2,104 passed**, including **102 new closure cases**, **28 additional
closed-leaf matrix cases**, and all **600 unchanged strict-contract cases**. Tests
cover every supported Boolean/state, hostile values, exact envelopes, unsupported
variants, separate model/depth bounds, cycles, node clipping and excessive depth.
Inventory tests achieve 13/13 and 8/8 with clean aggregate flags; existing complete
roles retain identical normalized projections and dormant replacements still
reject. A GET-only Inspector test verifies complete bounded signatures/states,
sanitized logs, an unchanged input fingerprint, no proposal/fence records and
eligible_no_proposal_no_write. Fault cases preserve truthful aggregate flags.

The deep direction test is an explicitly synthetic depth-12/17-node stress tree,
with the known root category and geometry/body leaf families. It is **not** the
real extrudeDirection topology or an accepted filter. New optional Boolean values
in test fixtures are invented schema coverage, not observed provider values.

All full suites/checks passed with real CAD writes OFF; counts overlap:

| Check                                  | Result                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------- |
| New evidence-closure suite             | **102 passed**                                                         |
| Extended shared leaf-state matrix      | **28 additional cases**, **253 signature cases passed**                |
| Focused evidence/contract/shape gate   | **2,104 passed**                                                       |
| Preserved strict entities suite        | **600 passed**, byte-for-byte unchanged                                |
| Full API suite                         | **6,945 passed**, including all **42 PostgreSQL cases**, no skips      |
| Full frontend suite                    | **869 passed** in **35 files**, no skips                               |
| Modify browser matrix                  | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries |
| Frozen installs                        | npm ci / uv sync --locked passed; dependencies/lockfiles unchanged     |
| Format / lint / strict types / build   | Passed                                                                 |
| Dependency audits / Compose validation | Passed                                                                 |
| Isolated migrations / migration drift  | Passed; no new upgrade operations                                      |

There are 130 added collected cases in total. The complete `make test` command
used the supported execution-only VITEST_MAX_WORKERS=2 setting for machine
capacity. No test was skipped and no assertion, timeout, product retry behavior,
threshold or repository runner configuration was weakened. Production depth/node
and 8 KiB replacement bounds remain unchanged; only explicit diagnostic bounds
and their maximum-output tests change. Python strict checking passed across
198 source files; TypeScript checking passed. Audits found no known vulnerabilities
among audited packages; the existing Python audit excludes the editable app.
The pre-existing bundle-size warning remains. No dependency, migration, environment
file or deployment configuration changed.

PostgreSQL used a fresh healthy loopback-only random-port tmpfs container with
synthetic credentials, isolated from operator dotenv and service credentials.
Only that verification container was stopped/removed, retaining existing services
and data. Final local Settings confirmed writes OFF. Scope/privacy and secret
pattern review passed. Strict entities acceptance, current-UI validation,
registry/legacy profiles, write transport, exact verifier, approval/claims/fences /
recovery, graph/model code, frontend and original fixtures remain unchanged.
Automated success proves diagnostic capability only; real optional-field values
and direction topology still require the human refresh below.

**PHASE 16 QUERY EVIDENCE CLOSURE PASS — READY FOR COMPLETE 13/13 + 8/8 REFRESH**

### Query-evidence closure files changed

- apps/api/src/forge_api/integrations/onshape/query_filter_evidence.py
- apps/api/src/forge_api/integrations/onshape/dev/query_roles.py
- apps/api/tests/test_modify_query_evidence_closure.py
- apps/api/tests/test_modify_filter_signature.py (three-field maximum proof)
- apps/api/tests/test_modify_query_role_inventory.py (diagnostic model/depth proofs)
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md
- docs/ROADMAP.md
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md

### Exact next human 13/13 + 8/8 evidence checkpoint

On the original development Mac, pull `phase16/modify-live-conformance`. Keep
ENVIRONMENT=development, FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and
FORGE_CAD_WRITES_ENABLED=false. On the SAME disposable Sketch 1 → Extrude 1 →
Fillet 1 fixture, perform **exactly ONE Inspector → Refresh CAD**. Generate no
proposal, approval or mutation.

For each noSketchGeometry variant, report every sanitized query-role row plus
both feature summaries. Required targets are Extrude discovered=13/inspected=13,
Fillet discovered=8/inspected=8, all_roles_inspected=true and all four aggregate
malformed/unexpected/uninspected/truncated flags false. Require complete real
extrudeDirection topology, signature_truncated=false and all bounded closed leaf
states, plus explicit mesh Boolean and all three mate-connector field states on
every applicable role. Preserve/report the already complete roles unchanged.

The probe must remain eligible_no_proposal_no_write. Continue reporting closed
first-failure/body summaries; surfaceEntities / side1Face query_filter_unproven
remains expected. Report optional missing fields explicitly as absence, without
inferring defaults; their meaning requires later contract review. Unknown states,
malformed values, unexpected fields or clipping stop advancement; never guess a
hidden tree/value. Only complete human evidence can
support a later separately authorized dormant-role acceptance task. No merge,
deployment, writes ON, live mutation trial or Phase 17 work is authorized here.

## Separately authorized bounded full-definition payload repair

Historical implementation/gate record: this repair incorrectly selected 32 KiB.
The human subsequently confirmed the authorized ceiling is **24 KiB / 24,576
bytes**. The correction and its fresh verification are recorded at the end of
this document; the prior sizes/counts below describe the original implementation.

Starting clean synchronized branch phase16/modify-live-conformance at
`8a8c9ccba37dfb1c45be246455fd6199204cfae7`. The latest human checkpoint reports
complete 13/13 Extrude and 8/8 Fillet query-role evidence in both Inspector variants,
with all completeness/error flags clean, one SOLID / NO_ERROR body, and
eligible_no_proposal_no_write. Zero proposals, approvals or mutations occurred.
All supplied dormant-role topologies and typed leaf states remain available for
the later production acceptance task; this separate repair does not accept them.

### Concrete blocker and explicit authorization

Before changing eligibility, synthetic complete definitions were reconstructed
from the supplied sanitized role evidence and the existing 50/38-parameter test
fixtures. No private provider JSON, identifiers or query content were requested.
Their full replacement envelopes measured:

| Feature | Existing json.dumps serialization | Compact serialization (comparison only) |
| ------- | --------------------------------- | --------------------------------------- |
| Extrude | 14,771 bytes                      | 13,723 bytes                            |
| Fillet  | 10,782 bytes                      | 10,009 bytes                            |

These are synthetic measured sizes, not claimed measurements of private live CAD.
Both exceed the inherited 8,192-byte preflight and transport fences, even with
compact formatting. In-process MockTransport probes proved rejection before any
transport call. No real provider request was made. Removing preserved fields or
filters would violate the full-definition contract, so the acceptance task stopped
with NO-GO before source changes. The human then explicitly selected:
**Authorize a separate payload-limit repair.** This authorization supersedes the
previous unchanged-8-KiB requirement only for the narrow replacement path below.

### Original two fixed server-owned byte budgets (superseded below)

- MAX_REQUEST_BYTES remains **8,192** for ordinary exchanges, suppression and the
  original Phase 9 suppression path. Public request-body limits are unchanged.
- MAX_FEATURE_REPLACEMENT_BYTES is **32,768**, only for the private validated
  RENAME_FEATURE / SET_EXTRUDE_DEPTH / SET_FILLET_RADIUS execution path. This
  bounded 32 KiB envelope contains both reconstructed full payloads with headroom
  for preserved serialization metadata. It is not an Onshape/provider size claim
  or permission to accept a larger/unknown feature representation.

Payload preflight reconstructs the complete feature through the unchanged change /
registry predicates and checks the exact preview before choosing its fixed budget.
Oversized replacements fail unsupported_target / 422 before write_dispatch_started
and provider dispatch; their plan fails without a live fence and its suffix stops.
The private replacement exchange checks writes-enabled again, serializes the
same body with the unchanged json.dumps/allow_nan=false/UTF-8 encoding, enforces
32 KiB independently and makes exactly one fixed POST. The ordinary exchange
checks 8 KiB before reaching the shared network implementation. A final absolute
32 KiB guard also protects that implementation before opening a stream.

No payload field, discriminator, URL pattern, external setting, user/model argument
or diagnostic selects the larger budget. There is no global request-cap increase,
configurable bypass, compacting workaround, feature reconstruction from defaults,
query/filter stripping, normalization or automatic retry. Only the closed executor
calls the private larger-body wrapper after fresh semantic/shape/preview checks.
No new model tool, route or provider-payload authority is exposed.

### Preserved safety and scope

The historical and current-UI validators, exact active entities contracts,
dormant-role rejection, planner, preview/digest, human approval, session/grant /
context binding, expiry, stale baseline checks, one-use claims, execution fence,
rejectMicroversionSkew, pre-dispatch freshness, fresh post-write reread, exact-effect
verification, uncertainty/no-retry/suffix stopping and recovery are unchanged.
Suppression still sends only BTMFeature-134 / featureId / suppressed. No parameter
or filter definition enters its request even when the feature snapshot is large.
Response limits remain 2 MiB; all network deadlines/timeouts and redirects remain
unchanged. ForgeModelGraph and models gain no write or approval authority.

The current observed dormant roles still fail closed as query_filter_unproven.
This repair creates byte capacity only after a representation has independently
passed. It does not grant current ordinary full-profile eligibility or establish
live-write conformance. Every fresh real definition must still fit the fixed cap;
actual live wire sizes have not been read or measured here. Larger definitions
fail closed and must never be trimmed to fit. CAD writes remain OFF.

### Payload-budget automated gate

All checks passed with real CAD writes OFF; counts overlap:

| Check                                                                   | Result                                                                                  |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New byte-budget suite                                                   | **43 passed**                                                                           |
| Focused Modify / safe-edit / retained / AI-write / standard diagnostics | **5,426 passed**                                                                        |
| Full API suite                                                          | **6,988 passed**, including all **42 PostgreSQL cases**, no skips                       |
| Frontend                                                                | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                   | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                         | npm ci and uv sync --locked passed; dependencies/lockfiles unchanged                    |
| Required gate                                                           | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

The initial targeted suite passed 1,232 cases before one final absolute-ceiling
case was added; the final focused/full suites include all 43 new cases. Strict
Python checking passed across 199 source files; TypeScript checking passed.
Audits reported no known vulnerabilities among audited packages; the unchanged
Python audit excludes the editable app. Migration check reported no new upgrade
operations. The pre-existing bundle-size warning remains. Frontend test execution
used VITEST_MAX_WORKERS=2 for machine capacity, without repository runner changes.

Verification used synthetic CAD, in-process MockTransport and isolated settings /
databases. PostgreSQL used a healthy loopback-only random-port tmpfs container
with synthetic credentials; only that container was removed after verification,
retaining application services/data. Final Settings confirmed real writes OFF.
No private CAD, secret, environment, dependency, deployment or unrelated changes.
Representation/registry/role validators, planner, approval/fence/recovery and exact
post-write verification source files remain unchanged from starting HEAD.

Files: write_client.py; test_modify_payload_budget.py; test_modify_plan.py;
test_modify_ui_conformance.py; docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md;
docs/ROADMAP.md; docs/ARCHITECTURE.md; docs/SECURITY.md; docs/DEVELOPMENT.md;
docs/HACKATHON_MODIFY_A1.md.

Boundary coverage includes all four rename/quantity target combinations at 8,192,
8,193, 14,771, 32,768 and 32,769 serialized bytes, Unicode escaping at the exact
32 KiB boundary, an independent transport ceiling and writes-OFF guard, and the
unchanged 8 KiB ordinary limit even with replacement-looking fields/paths.
Large snapshots still produce minimal suppression attributes. Larger bodies do
not bypass unsupported shape rejection, stale detection, cancel, one-use claims,
exact acknowledgement/fresh verification or uncertainty/fence/suffix behavior.

The existing over-cap replacement tests keep their failure/no-dispatch/no-fence
assertions and then exceeded the incorrectly implemented 32 KiB cap. Original public
8 KiB parsing and suppression regressions remain unchanged. No other bound,
assertion, timeout, retry, threshold, dependency or lockfile change is introduced.

### Next work and human checkpoint

Resume the separately requested exact current-UI query-role acceptance task using
the complete 13/13 and 8/8 evidence already provided. That task must keep explicit
role/category/query-count contracts and the narrow depth-9 extrudeDirection rule,
with full preservation and no diagnostic-string authority. This payload-only
commit does not implement or claim those contracts.

After that acceptance implementation and its complete gate pass, perform ONE
same-fixture writes-OFF Inspector refresh for exact_match on both complete
representations, rename and quantity replacement diagnostics, with the probe still
eligible_no_proposal_no_write. No additional live read is performed by this repair,
and no live write, deployment, merge, OAuth/domain/secret change or Phase 17 work
is authorized. Explicit approval of an exact preview remains mandatory later.

## Complete current ordinary query-role production contracts

Required initial HEAD was verified clean and synchronized at
8a8c9ccba37dfb1c45be246455fd6199204cfae7. A concrete payload-cap blocker was
resolved first under separate explicit human authorization and its own full gate:
99bc6f8022f81b91de400f3f596ff9e369ed0b4d (fixed 32 KiB replacement-only budget;
ordinary/suppression/public parsing remain 8 KiB). This acceptance change starts
from that clean pushed commit. CAD writes remain OFF throughout both stages.
No real fixture read, proposal, approval or mutation is performed by the agent.

### Complete human evidence incorporated

The human reports complete matching evidence in BOTH noSketchGeometry variants
from the same disposable ordinary Sketch → NEW SOLID BLIND Extrude → constant
Fillet fixture: Extrude discovered=inspected=13, Fillet discovered=inspected=8,
all_roles_inspected=true, unrecognized_query_parameters=0,
parameter_count_capped=false and all malformed/unexpected/uninspected/truncated
aggregate flags false. Body evidence remains one SOLID / NO_ERROR and the probe
eligible_no_proposal_no_write, with no proposal/approval/mutation.
The last remaining failures were surfaceEntities and side1Face /
query_filter_unproven. Complete role-specific topology and finite leaf semantics
were supplied with the acceptance request; no guessed hidden tree is used here.

### Exact category / role / query contracts

Production matches parsed provider structures against immutable typed shapes,
never a diagnostic signature, summary flag, hash or semantic-equivalence heuristic.
Every binary node requires exactly btType/operand1/operand2 with ordered children.
Every leaf requires exactly its listed official btType and fields, with actual
Boolean types and exact enum strings. Missing/null/unknown/additional fields,
opaque SDK families, wrong types, reassociation, reversed operands and extra nodes
reject. No tree normalization, synthesis, regeneration or stripping occurs.

Active entities retain their existing exact raw filter predicates: Extrude 13
nodes/depth 5, Fillet 17/depth 8. Their filter-bearing current profile requires
exactly one recognized query item. Every dormant role below requires the exact
provider parameterId matching the explicit caller role/category, queries=[] and
count zero. Shared immutable shapes for equal trees do not share caller identity;
each role has a separate mapping entry and mismatched provider identities reject.

The complete contracts are listed below. Local preorder numbers in leaf states
identify positions in the expected tree, never CAD identities. These diagnostic
forms are documentation/test expectations only; production validates typed fields.

| Category / role                            | Query items | Nodes / depth | Exact topology                                                                                                                                                                                  | Exact leaf states                                                                                                                                                                                                                                                                                 |
| ------------------------------------------ | ----------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extrude / entities                         | 1           | 13 / 5        | and(or(and(and(flat_sheet_metal,sketch_object),entity_type),and(and(geometry,flat_sheet_metal),entity_type)),construction)                                                                      | 5:allows=model_and_flattened;6:sketch_object=true,sketch_object_type=any_sketch_object;7:entity_type=face;10:geometry=plane;11:allows=model_only;12:entity_type=face;13:construction=false                                                                                                        |
| extrude / surfaceEntities                  | 0           | 7 / 4         | and(and(and(entity_type,sketch_object),modifiable_entity_only),construction)                                                                                                                    | 4:entity_type=edge;5:sketch_object=true,sketch_object_type=any_sketch_object;6:modifiable_entity_only=true;7:construction=false                                                                                                                                                                   |
| extrude / wallShape                        | 0           | 15 / 5        | or(and(and(and(entity_type,geometry),construction),modifiable_entity_only),and(and(and(entity_type,sketch_object),construction),modifiable_entity_only))                                        | 5:entity_type=face;6:geometry=plane;7:construction=false;8:modifiable_entity_only=false;12:entity_type=edge;13:sketch_object=true,sketch_object_type=any_sketch_object;14:construction=false;15:modifiable_entity_only=true                                                                       |
| extrude / endBoundEntityFace               | 0           | 7 / 4         | or(and(and(entity_type,sketch_object),allow_mesh_geometry),body_type)                                                                                                                           | 4:entity_type=face;5:sketch_object=false,sketch_object_type=not_sketch_object;6:allow_mesh_geometry=true;7:body_type=mate_connector                                                                                                                                                               |
| extrude / secondDirectionBoundEntityFace   | 0           | 7 / 4         | or(and(and(entity_type,sketch_object),allow_mesh_geometry),body_type)                                                                                                                           | 4:entity_type=face;5:sketch_object=false,sketch_object_type=not_sketch_object;6:allow_mesh_geometry=true;7:body_type=mate_connector                                                                                                                                                               |
| extrude / endBoundEntityBody               | 0           | 9 / 5         | and(and(and(entity_type,or(body_type,body_type)),sketch_object),allow_mesh_geometry)                                                                                                            | 4:entity_type=body;6:body_type=solid;7:body_type=sheet;8:sketch_object=false,sketch_object_type=not_sketch_object;9:allow_mesh_geometry=true                                                                                                                                                      |
| extrude / secondDirectionBoundEntityBody   | 0           | 9 / 5         | and(and(and(entity_type,or(body_type,body_type)),sketch_object),allow_mesh_geometry)                                                                                                            | 4:entity_type=body;6:body_type=solid;7:body_type=sheet;8:sketch_object=false,sketch_object_type=not_sketch_object;9:allow_mesh_geometry=true                                                                                                                                                      |
| extrude / endBoundEntityVertex             | 0           | 3 / 2         | or(entity_type,mate_connector)                                                                                                                                                                  | 2:entity_type=vertex;3:allow_implicit_mate_connector=false,mate_connector_inference_default=false,requires_occurrence=false                                                                                                                                                                       |
| extrude / secondDirectionBoundEntityVertex | 0           | 3 / 2         | or(entity_type,mate_connector)                                                                                                                                                                  | 2:entity_type=vertex;3:allow_implicit_mate_connector=false,mate_connector_inference_default=false,requires_occurrence=false                                                                                                                                                                       |
| extrude / extrudeDirection                 | 0           | 17 / 9        | or(or(or(or(geometry,or(geometry,or(geometry,or(geometry,or(geometry,geometry))))),mate_connector),geometry),body_type)                                                                         | 5:geometry=line;7:geometry=circle;9:geometry=arc;11:geometry=cylinder;13:geometry=cone;14:geometry=revolved;15:allow_implicit_mate_connector=false,mate_connector_inference_default=false,requires_occurrence=false;16:geometry=plane;17:body_type=mate_connector                                 |
| extrude / startOffsetEntity                | 0           | 9 / 5         | or(or(or(and(geometry,entity_type),entity_type),entity_type),body_type)                                                                                                                         | 5:geometry=plane;6:entity_type=face;7:entity_type=edge;8:entity_type=vertex;9:body_type=mate_connector                                                                                                                                                                                            |
| extrude / booleanScope                     | 0           | 7 / 4         | and(and(and(entity_type,body_type),modifiable_entity_only),allow_mesh_geometry)                                                                                                                 | 4:entity_type=body;5:body_type=solid;6:modifiable_entity_only=true;7:allow_mesh_geometry=true                                                                                                                                                                                                     |
| extrude / booleanSurfaceScope              | 0           | 9 / 5         | and(and(and(and(entity_type,body_type),modifiable_entity_only),allow_mesh_geometry),sketch_object)                                                                                              | 5:entity_type=body;6:body_type=sheet;7:modifiable_entity_only=true;8:allow_mesh_geometry=true;9:sketch_object=false,sketch_object_type=not_sketch_object                                                                                                                                          |
| fillet / entities                          | 1           | 17 / 8        | and(and(and(or(and(active_sheet_metal,or(and(entity_type,edge_topology),entity_type)),and(entity_type,sheet_metal_definition_entity_type)),construction),sketch_object),modifiable_entity_only) | 6:active_sheet_metal=false;9:entity_type=edge;10:edge_topology=two_sided,internal_edge=true;11:entity_type=face;13:entity_type=edge;14:sheet_metal_definition_entity_type=vertex;15:construction=false;16:sketch_object=false,sketch_object_type=not_sketch_object;17:modifiable_entity_only=true |
| fillet / side1Face                         | 0           | 9 / 5         | and(and(and(and(entity_type,construction),sketch_object),modifiable_entity_only),active_sheet_metal)                                                                                            | 5:entity_type=face;6:construction=false;7:sketch_object=false,sketch_object_type=not_sketch_object;8:modifiable_entity_only=true;9:active_sheet_metal=false                                                                                                                                       |
| fillet / side2Face                         | 0           | 9 / 5         | and(and(and(and(entity_type,construction),sketch_object),modifiable_entity_only),active_sheet_metal)                                                                                            | 5:entity_type=face;6:construction=false;7:sketch_object=false,sketch_object_type=not_sketch_object;8:modifiable_entity_only=true;9:active_sheet_metal=false                                                                                                                                       |
| fillet / centerFaces                       | 0           | 9 / 5         | and(and(and(and(entity_type,construction),sketch_object),modifiable_entity_only),active_sheet_metal)                                                                                            | 5:entity_type=face;6:construction=false;7:sketch_object=false,sketch_object_type=not_sketch_object;8:modifiable_entity_only=true;9:active_sheet_metal=false                                                                                                                                       |
| fillet / startPartialEntity                | 0           | 7 / 3         | or(and(entity_type,allow_mesh_geometry),or(entity_type,mate_connector))                                                                                                                         | 3:entity_type=face;4:allow_mesh_geometry=true;6:entity_type=vertex;7:allow_implicit_mate_connector=false,mate_connector_inference_default=false,requires_occurrence=false                                                                                                                         |
| fillet / endPartialEntity                  | 0           | 7 / 3         | or(and(entity_type,allow_mesh_geometry),or(entity_type,mate_connector))                                                                                                                         | 3:entity_type=face;4:allow_mesh_geometry=true;6:entity_type=vertex;7:allow_implicit_mate_connector=false,mate_connector_inference_default=false,requires_occurrence=false                                                                                                                         |
| fillet / keepEdges                         | 0           | 9 / 5         | and(and(and(and(entity_type,edge_topology),construction),sketch_object),modifiable_entity_only)                                                                                                 | 5:entity_type=edge;6:edge_topology=two_sided,internal_edge=true;7:construction=false;8:sketch_object=false,sketch_object_type=not_sketch_object;9:modifiable_entity_only=true                                                                                                                     |
| fillet / smoothCornerExceptions            | 0           | 7 / 4         | and(and(and(entity_type,construction),sketch_object),modifiable_entity_only)                                                                                                                    | 4:entity_type=vertex;5:construction=false;6:sketch_object=false,sketch_object_type=not_sketch_object;7:modifiable_entity_only=true                                                                                                                                                                |

All mesh leaves require allowsMeshGeometry=true. Every mate-connector leaf requires
allowImplicitMateConnector=false, isMateConnectorInferenceEnabledByDefault=false,
and requiresOccurrence=false, with no omitted defaults. Body enums remain exact
SOLID/SHEET/MATE_CONNECTOR in their observed slots. The first wallShape branch
requires modifiableOnly=false; its second branch requires true. keepEdges requires
TWO_SIDED and isInternalEdge=true. These exact distinctions cannot be generalized
from display names, shared classes or inactive feature modes.

### Narrow depth-nine direction handling

Only (extrude, extrudeDirection) selects the fixed 17-node/depth-9 shape and a
production depth ceiling of 9. Its nested OR geometry order is LINE, CIRCLE, ARC,
CYLINDER, CONE, REVOLVED, then the explicit mate connector, PLANE and body-type
MATE_CONNECTOR in the supplied exact topology. It must remain empty while
hasExtrudeDirection=false. No flattening or sorting of OR operands is accepted.
All other role ceilings remain 8 and their exact smaller shape depths/counts must
also match. The 64-node ceiling is unchanged. Generic production rejection
diagnostics retain depth 8; separate DEV inventory diagnostics retain their
existing depth-16 bound. Diagnostic completeness never authorizes acceptance.

### Whole representations and compatibility boundaries

The validator checks every supplied parameter against its exact closed type,
metadata, mode, quantity/query/array contract; nothing is ignored because it is
dormant. A current ordinary profile containing any dormant filter additionally
requires every serialized known parameter exactly once (50 Extrude / 38 Fillet)
and a filter on every query role. Dropping a dormant parameter/filter, or even an
unrelated serialized optional quantity, cannot create a hybrid partial profile.
Unknown IDs, duplicates, malformed collections and active richer modes reject.

Previously supported filter-free/current-UI serialization and the existing
entities-only representation remain explicit compatibility shapes, with their
existing validation. They are never constructed by projecting a fresh feature
down: the server copies and validates the actual complete provider definition.
A failed current filter check raises immediately, with no fallback. Historical
minimal ID sets and closed nested envelopes are byte-for-byte unchanged; every
filter still rejects in the historical path and cannot fall through to current UI.

### Preservation and authority review

Both renames, SET_EXTRUDE_DEPTH and SET_FILLET_RADIUS copy the complete fresh
feature definition. Only name or the approved quantity expression changes. All
21 query filters, dormant empty query lists, query items, parameter/list ordering,
node IDs and accepted serialization metadata remain exact. Request byte capacity
comes solely from the separately approved replacement budget; cap failures still
reject locally before dispatch. No field is removed to fit a request.

Fresh post-write exact-effect verification is unchanged and compares the entire
inventory/configuration. Tests reject dormant-filter removal/addition/subtype /
operand-order/leaf-state deltas for both rename and quantity paths. A synthetic
HTTP-200 acknowledgement followed by a changed dormant filter becomes
execution_uncertain, retains the fence, sends no retry and skips subsequent
operations. Success still requires a valid acknowledgement AND fresh exact proof.

Suppression remains independent: terminal-Fillet state policy and the dedicated
/features/updates featureId/type/suppressed transport are unchanged. It never
sends the full parameter/filter definition. Planner/model/ForgeModelGraph gain no
provider identifiers, parameter IDs, URLs, payload or approval authority. Preview,
digest, explicit human approval, session/grant/context binding, expiry, one-use
claim, stale rejection, fence, pre-dispatch freshness, rejectMicroversionSkew,
post-write reread, uncertainty/recovery and no-retry behavior are unchanged.

### Tests and full gate

All checks passed with real CAD writes OFF; counts overlap:

| Check                                                                   | Result                                                                                                      |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| New current-query contract suite                                        | **1,247 passed**                                                                                            |
| Targeted new contracts / original entities / inventory / closure suites | **2,004 passed**                                                                                            |
| Original strict active-entities suite                                   | **600 passed**, byte-for-byte unchanged                                                                     |
| Focused Modify / safe-edit / retained / AI-write / standard diagnostics | **6,673 passed**                                                                                            |
| Full API suite                                                          | **8,235 passed**, including all **42 PostgreSQL cases**, no skips                                           |
| Frontend suite                                                          | **869 passed** in **35 files**, no skips                                                                    |
| Modify browser matrix                                                   | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                                      |
| Frozen installs                                                         | npm ci and uv sync --locked verified in the preceding payload-repair gate; dependencies/lockfiles unchanged |
| Required gate                                                           | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed                     |

There are 1,247 added cases in this acceptance commit, plus 43 in the separate
payload repair (1,290 total beyond the required initial HEAD). Strict Python
checking passed across 200 source files; TypeScript checking passed. Audits found
no known vulnerabilities among audited packages; the unchanged Python audit
excludes the editable application. No migration drift. The existing bundle-size
warning remains. VITEST_MAX_WORKERS=2 was an execution-only resource choice;
repository runners, browser workers/retries, timeouts and thresholds are unchanged.

All CAD was synthetic and all provider transport in-process mocked, with isolated
settings. PostgreSQL used a fresh healthy loopback-only random-port tmpfs
container and synthetic credentials; only that container was removed afterward,
retaining application services/data. Final local Settings confirmed writes OFF.
Diff/privacy review found only the listed files, with no private CAD, credential,
environment, dependency, migration or production/deployment configuration change.
Registry/legacy profiles, write client (including the separate 32/8 KiB budgets),
planner, approval/fence/recovery and exact-effect verification remain unchanged
from the payload-repair commit. No new CAD capability or live mutation is claimed.

### Current-query acceptance files

- apps/api/src/forge_api/integrations/onshape/current_ui_filters.py
- apps/api/src/forge_api/integrations/onshape/standard_edit_shapes.py
- apps/api/tests/test_modify_current_query_contracts.py
- apps/api/tests/fixtures/modify_current_query_filters.json
- apps/api/tests/fixtures/README.md
- apps/api/tests/test_modify_query_role_inventory.py
- apps/api/tests/test_modify_query_evidence_closure.py
- docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/DEVELOPMENT.md

The new fixture reconstructs only public SDK-shaped structures from sanitized
human role evidence. It is not a raw private CAD capture; identities, query text,
node IDs and incidental quantities in complete feature tests remain invented.
Negative tests cover every dormant role and every required leaf field, empty
query counts, exact topology/order/arity, missing/extra/malformed/opaque/deep nodes,
role identity and cross-feature substitution. Equal endBound/secondDirection,
side1Face/side2Face/centerFaces and start/endPartial trees require explicit matching
caller identities. The direction exception is tested against every other role.

Whole-profile completeness tests remove each of all 88 parameters independently.
Positive tests cover all four replacements, reversed parameter ordering, full
payload preservation, cancel then single approval and one-use rejection. A real
Inspector route test with synthetic GET-only transport proves 13 unchanged reads,
exact_match for both variants/features, complete 13/13 and 8/8 summaries, the safe
probe and zero proposal/fence records. No diagnostic data enters its public body.

The original 600 strict active-entities cases remain unchanged. Older synthetic
inventory tests still reject their deliberately copied/mismatched later filters;
expected first failures advance to wallShape / startPartialEntity because their
surfaceEntities / side1Face rows now have exact accepted shapes. Their zero-write,
privacy, count/bound and whole-feature rejection assertions remain. No assertion,
timeout or bound is weakened to obtain a pass; the only new depth allowance is
the human-authorized exact direction role, and the byte repair is separate.

### Exact final human writes-OFF checkpoint

Pull this branch on the development Mac. Keep ENVIRONMENT=development,
FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true and FORGE_CAD_WRITES_ENABLED=false.
On the SAME privately confirmed disposable fixture, perform **ONE CAD Inspector
→ Refresh CAD**. Generate no proposal, approval or mutation.

For BOTH noSketchGeometry variants and BOTH Extrude/Fillet require:

- standard shape outcome=exact_match;
- parameter_shape_matches_registry=true;
- replacement=exact_match and rename=exact_match;
- no query_filter_unproven or any remaining standard-shape failure;
- complete 13/13 and 8/8 role summaries with clean flags, including direction
  depth=9 / nodes=17 without clipping;
- one SOLID / NO_ERROR and safe_edit_probe outcome=eligible_no_proposal_no_write.

Any different result stops advancement; report only the existing sanitized labels,
counts/flags and closed signatures/states. No raw provider JSON, IDs or query text
is needed. This automated gate does not claim actual live exact-match or write
success. Even a successful final read checkpoint does not enable writes or
approve a mutation: controlled human live preview/approval remains a separate
stage. No merge, deployment, OAuth/domain/secret change or Phase 17 work occurs.

## Authorized 24 KiB replacement-ceiling correction

Starting clean synchronized branch phase16/modify-live-conformance at
`109b91e21b6d72ec57326dea587bf382fd17f999`. Before the final human writes-OFF
checkpoint, the human confirmed the authorized full-definition replacement
ceiling is **24 KiB / 24,576 bytes**, correcting the prior implementation's
32 KiB value. Historical gate results above retain their original context.

The only runtime change is MAX_FEATURE_REPLACEMENT_BYTES = 24 * 1024.
Ordinary exchanges and both suppression paths remain independently capped at
**8 KiB / 8,192 bytes**. Only the existing validated full-definition replacement
path selects the larger budget. Preflight, private replacement transport and the
absolute shared transport guard all enforce the corrected ceiling. There is no
new setting, caller-selected limit, serialization change or payload trimming.

Boundary expectations use literal sizes so a future increase fails the tests:
all four rename/quantity target combinations cover 8,192, 8,193, 10,782, 14,771,
24,576 and 24,577 serialized bytes. The two observed-size examples remain
synthetic evidence-shaped payloads, not new measurements of private CAD.
Exactly 24,576 bytes succeeds in MockTransport; 24,577 rejects before dispatch,
without a dispatch audit or live fence. Unicode JSON escaping is tested at both
boundaries, as is the independent private transport ceiling. Ordinary exchanges
explicitly cover both replacement-looking and /features/updates paths at
8,192/8,193 bytes. Large snapshots still produce attribute-only suppression.
Existing over-cap regression fixtures now exceed 24 KiB; their no-dispatch and
failure assertions remain intact. The complete current-query test only tightens
its payload-size assertion to 24,576; query-role contract work is not redone.

All feature/query validators, payload construction, field preservation, planner,
preview/digest, approval/one-use claims, expiry/context/stale checks, fences,
microversion guards, fresh exact-effect verification, uncertainty/no-retry and
recovery behavior remain unchanged. Real CAD writes remain OFF. This correction
does not perform the pending human Inspector checkpoint or establish live-write
conformance. No real CAD read, proposal, approval, mutation, merge or deployment.

### Ceiling-correction automated gate

All checks passed with real CAD writes OFF; counts overlap:

| Check                                                                   | Result                                                                                  |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Affected payload / plan / UI conformance tests                          | **1,243 passed**                                                                        |
| Focused Modify / safe-edit / retained / AI-write / standard diagnostics | **6,683 passed**                                                                        |
| Full API suite                                                          | **8,245 passed**, including all **42 PostgreSQL cases**, no skips                       |
| Frontend                                                                | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                   | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                         | npm ci and uv sync --locked passed; dependencies/lockfiles unchanged                    |
| Required gate                                                           | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

Strict Python checking passed across 200 source files; TypeScript checking passed.
Migration check found no new upgrade operations. Dependency audits found zero
known vulnerabilities among audited packages; the unchanged Python audit excludes
the editable application. The existing bundle-size warning remains. Frontend
tests used execution-only VITEST_MAX_WORKERS=2; no runner, timeout, retry, approval,
safety assertion or other bound was relaxed.

Verification used synthetic CAD and in-process MockTransport, isolated settings,
and a fresh healthy loopback-only random-port tmpfs PostgreSQL container with
synthetic credentials. Only that temporary container was removed afterward;
existing application services and data were retained. Local Settings confirmed
real CAD writes OFF before and after verification. Diff review found no private
CAD, credentials, environment, dependency, migration or deployment changes.
Only the replacement ceiling and its explanatory comment changed at runtime;
all query-role and authority/verification implementation files are unchanged.

The final human writes-OFF checkpoint above remains the next step. It must not
generate proposals, approvals or mutations. This automated correction neither
performs that checkpoint nor authorizes any later live write.

## Complete Extrude quantity-role evidence checkpoint

Starting clean synchronized branch phase16/modify-live-conformance at
`2617729a9731727f054f23943073c57cc038af9f`. The latest human writes-OFF checkpoint
now proves Fillet exact_match for standard shape, registry, replacement and rename.
Both variants have complete clean 13/13 Extrude and 8/8 Fillet query-role evidence,
one SOLID / NO_ERROR body and eligible_no_proposal_no_write. The only current
standard-shape failure is Extrude thickness2 / wrong_quantity_expression. Zero
proposal, approval or provider mutation occurred; CAD writes remained OFF.

The first-failure result is insufficient to repair quantity acceptance safely.
It proves that earlier roles passed their current rules, but does not expose the
exact expression representations of thickness2 or any later Extrude quantity.
The repository fixture cannot supply that authority: it explicitly documents all
incidental dormant quantities as invented. Therefore this continuation changes
no acceptance rule and prepares one bounded diagnostic for all source-declared
Extrude quantity roles at once.

The source vocabulary yields exactly ten roles in order: depth, thickness,
thickness1, thickness2, draftAngle, secondDirectionDepth,
secondDirectionDraftAngle, offsetDistance, secondDirectionOffsetDistance and
startOffsetDistance. The diagnostic binds every row to that fixed role and source
kind and labels depth active while all other roles are dormant. It never stops at
the production validator's first failure and never treats a value class as generic
eligibility.

For each role it emits only closed classifications: occurrence/duplicate state;
provider quantity type; expression class, sign, numeric class/format and units;
whether literal units match the role's source dimension; cached numeric value and
units classes; node-ID and isInteger states; import/common metadata states; the
ordered presence of fixed schema fields; required-field and allowed-field-only
flags; and capped unexpected-field counts. Expressions are never logged. Unknown
parameter IDs are counted without names. Duplicates are not inspected by choosing
one payload. The complete record has ten rows and an independent 16 KiB bound.

Projection and emission require development, diagnostics ON, writes OFF, a
complete source-matched response and the existing matching-head bracket. The
diagnostic reuses both existing noSketchGeometry feature responses and adds no
provider request. It has no public/browser/model payload, persistence, proposal,
approval, target eligibility or mutation path. Fillet and query-filter logic are
untouched. Production standard-shape, registry, legacy, write-client, planner,
approval, freshness, digest, claims, fences, microversion, verification, recovery,
24 KiB replacement and 8 KiB ordinary/suppression implementations are unchanged.

### Quantity-diagnostic automated gate

All checks passed with real CAD writes OFF; counts overlap:

| Check                                                                   | Result                                                                                  |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| New complete quantity-role diagnostic                                   | **46 passed**                                                                           |
| Quantity/current-query/UI-shape/first-failure suite                     | **2,402 passed**                                                                        |
| Focused Modify / safe-edit / retained / AI-write / standard diagnostics | **6,729 passed**                                                                        |
| Full API suite                                                          | **8,291 passed**, including all **42 PostgreSQL cases**, no skips                       |
| Frontend                                                                | **869 passed** in **35 files**, no skips                                                |
| Modify browser matrix                                                   | **45 passed**, Chromium / Firefox / WebKit, four workers, zero retries                  |
| Frozen installs                                                         | npm ci and uv sync --locked passed; lockfiles unchanged                                 |
| Required gate                                                           | make format, lint, typecheck, build, test, migration-check, compose-check, audit passed |

Strict Python checking passed across 202 source files; TypeScript checking passed.
Migration check found no new upgrade operations. Dependency audits found no known
vulnerabilities among audited packages; the unchanged Python audit excludes the
editable application. The existing bundle-size warning remains. Tests used only
synthetic CAD, in-process MockTransport and a fresh isolated loopback-only tmpfs
PostgreSQL container with synthetic credentials. Only that temporary container
was removed afterward; existing application services and data were retained. No
provider mutation was issued.

### One required human writes-OFF refresh

On the same confirmed disposable ordinary fixture, keep development diagnostics
ON and FORGE_CAD_WRITES_ENABLED=false, then perform exactly one CAD Inspector →
Refresh CAD. Generate no Modify proposal or approval. For BOTH noSketchGeometry
variants, report the two `safe_edit_extrude_quantity_coverage` records only as
sanitized closed fields. Each must prove:

- summary expected_roles=10, roles_present=10 and roles_inspected=10;
- all_roles_inspected=true, unrecognized_quantity_parameters=0 and
  parameter_count_capped=false;
- all missing/duplicate/malformed/unexpected/uninspected flags=false;
- every role occurs once, has its fixed source_kind/activity, provider_type=quantity,
  non-null evidence and expression_dimension_matches_source=true;
- for each role, the exact expression_class, number_class, number_format, sign and
  units classifications;
- each role's cached value/units, node-ID, isInteger, import/common-metadata and
  ordered present_allowed_fields classifications;
- required_fields_present=true, allowed_fields_only=true and zero uncapped
  unexpected fields.

The refresh must also retain the already observed Fillet exact matches, clean
13/13 and 8/8 query summaries, one SOLID / NO_ERROR body and
eligible_no_proposal_no_write. Do not provide raw expressions, IDs, names, query
text or provider JSON. Any incomplete, nonliteral, dimension-mismatched, malformed,
unexpected or variant-disagreeing result stops the repair. This diagnostic commit
does not claim Extrude exact_match or live-write conformance.

## Exact current Extrude quantity-contract repair

Starting clean synchronized branch phase16/modify-live-conformance at
`44ee0e0f956508506c9f483dc3c8274e5028a3eb`, the requested writes-OFF refresh
completed the missing authority. Both noSketchGeometry variants agree: all ten
source-declared roles are present once and fully inspected; no role is malformed,
duplicated, unrecognized, clipped or carrying an unexpected field. Every role has
the exact nine-field quantity envelope: btType, parameterId, expression, nodeId,
isInteger, value, units, parameterName and libraryRelationType. The observed common
state is a nonempty string nodeId, isInteger=false, numeric cached value zero,
empty cached units/parameterName, DEFAULT library relation and absent import marker /
valueString. These are representation requirements, not reconstructed defaults.

The production contract remains keyed by Extrude plus the exact parameter role.
Depth keeps the existing positive supported length expression needed by
SET_EXTRUDE_DEPTH; its current observed integer-mm baseline does not narrow the
approved replacement quantity grammar. Dormant roles accept only their proven
classes:

| Role                                                               | Accepted current dormant expression class                         |
| ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| thickness, thickness1                                              | positive unsigned decimal inches                                  |
| thickness2                                                         | unsigned integer zero inches                                      |
| draftAngle, secondDirectionDraftAngle                              | positive unsigned integer degrees below 90                        |
| secondDirectionDepth                                               | positive unsigned integer inches within the existing length bound |
| offsetDistance, secondDirectionOffsetDistance, startOffsetDistance | positive unsigned integer inches within the existing length bound |

There is no general dormant-length or zero-quantity predicate. The explicit role
map chooses a closed expression class before validation. Zero-inch thickness2
cannot substitute into the positive decimal thickness roles, those roles cannot
substitute into thickness2, and angle literals cannot substitute into length roles.
Canonical unsigned literal forms are required; configured, arithmetic, scientific,
signed, wrong-format, wrong-unit and wrong-dimension forms reject. Current complete
query-filter profiles additionally require the exact observed field envelope and
common states. Older filter-free standard profiles retain their prior metadata
envelope, while their role-specific expressions use the same closed role map. The
separate A1 minimal adapters and all Fillet contracts are unchanged.

The synthetic full profile now uses invented magnitudes that match the ten proven
classes and the exact observed metadata presence; it contains no private capture,
provider identifier or query text. Tests prove both features report standard-shape
exact_match, parameter_shape_matches_registry=true, replacement=exact_match and
rename=exact_match. Query evidence remains complete and clean at 13/13 Extrude and
8/8 Fillet. Negative coverage includes positive/decimal/wrong-unit thickness2,
signed and nonliteral forms, cross-role substitution, angle/length mismatch, wrong
provider type, cached value/units, missing node/required fields, wrong isInteger,
unexpected fields, duplicates and malformed parameter entries. Full-copy mutation
and post-write verification tests continue to compare every unrelated field.

The resumed full regression run exposed six synthetic size failures after the
shared quantity fixture gained metadata: two older entities-only replacements
exceeded their 8 KiB fixture assertions, and four 8,192/8,193-byte boundary cases
could no longer be padded to their exact size. The older entities-only builder now
retains its compact dormant metadata, while the complete current builder restores
all observed fields. All size, approval, full-copy and no-dispatch assertions remain
intact. The 2,069-case fixture regression suite passed after that separation.

This repair changes no planner/model input, target discovery, preview/digest,
approval/one-use claim, context/expiry/stale checks, execution fence, fresh
pre-dispatch evidence, rejectMicroversionSkew, post-write exact-effect verification,
uncertainty/no-retry or recovery behavior. Query filters, Fillet and suppression
transport are unchanged. The 24 KiB full-replacement and independent 8 KiB ordinary /
suppression ceilings remain. CAD writes stayed OFF; no proposal, approval, provider
mutation, deployment or merge occurred.

The final human checkpoint remains one Inspector refresh on the same confirmed
disposable fixture with writes OFF. Both response variants must report Extrude and
Fillet standard-shape exact_match, registry=true, replacement/rename exact_match,
clean 13/13 and 8/8 query summaries, one SOLID / NO_ERROR and
eligible_no_proposal_no_write. This read-only checkpoint authorizes no live write.

### Quantity-contract repair automated gate

The complete resumed gate passed on 2026-10-25 with real CAD writes OFF. Counts
overlap; all full-suite tests ran without skips:

| Check                                                           | Result                                                                                     |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| New exact quantity-contract module                              | **169 cases**, included in affected/full runs                                              |
| Affected quantity/current-query/UI/common-metadata/shape suite  | **3,245 passed**                                                                           |
| Older/current fixture and exact payload-boundary regressions    | **2,069 passed**                                                                           |
| Focused Modify/safe-edit/retained/AI-write/standard diagnostics | **6,898 passed**                                                                           |
| Full API                                                        | **8,460 passed**, including all **42 PostgreSQL cases**                                    |
| Frontend                                                        | **869 passed** in **35 files**                                                             |
| Modify browser matrix                                           | **45 passed**, Chromium/Firefox/WebKit, four workers, zero retries                         |
| Required repository gate                                        | make format, lint, typecheck, build, test, migration-check, compose-check and audit passed |
| Frozen installs                                                 | npm ci and uv sync --locked passed; lockfiles unchanged                                    |

Strict typing passed for 203 Python source files and all TypeScript projects.
Migration drift reported no new upgrade operations; npm and Python audits found
no known vulnerabilities among audited dependencies (the editable API is excluded
by the unchanged audit command). The existing bundle-size warning remains.
Verification used synthetic CAD, MockTransport and an isolated loopback-only,
random-port tmpfs PostgreSQL 18.6 container matching the Compose image. Its schema
was migrated before the final full run; only this temporary container was removed
afterward. Existing database services/data were retained. VITEST_MAX_WORKERS=2 was
execution-only; no timeout, retry, threshold, assertion or safety bound was relaxed.

Final diff review confirms runtime changes are confined to the standard quantity
validator. Fillet fixture data, A1 minimal fixture, query-filter contracts, write
client, planner, approvals, exact-effect verification, recovery and lockfiles are
unchanged. Local Settings confirmed writes OFF before and after verification.
Full logs are retained locally in `/tmp/forge-phase16-quantity-gate`; no private
CAD, identifiers, secrets, environment files or provider capture was added.

**PHASE 16 EXTRUDE QUANTITY CONTRACT PASS — READY FOR FINAL WRITES-OFF EXACT-MATCH REFRESH**

## First controlled live depth write: execution uncertain

After the writes-OFF exact-match checkpoint, a human approved one depth change on
the disposable Extrude, 20 mm to 25 mm. Onshape later showed a 25.000 mm measured
edge; Forge reported `execution_uncertain`, zero verified operations and manual
recovery required. The write-enabled backend was stopped and restarted with CAD
writes OFF. The original record and protective fence remain intact. The measurement
does not establish an exact feature-definition change or authorize recovery.

The retained terminal excerpt contains startup messages but no request or
`a2_verify` messages. This does not identify the failed boundary: the development
launcher uses Uvicorn `--no-access-log`, and `a2_verify` begins only after the
provider response, acknowledgement checks and acknowledgement-journal transaction
commit. A dispatched POST can therefore become uncertain on a transport/response
error; a failed
`microversionSkew` predicate; returned feature envelope, identity or exact
fingerprint mismatch; invalid/non-advancing `sourceMicroversion`; or an audit,
journal or commit failure after acknowledgement. A worker interruption can also
leave a claimed/verifying record fenced and later reported uncertain by retention
cleanup. The available excerpt cannot distinguish these cases or prove which
process handled the approval.

A development-only, closed `a2_dispatch` trace now labels request preflight,
provider exchange, each acknowledgement predicate and acknowledgement-journal
commit as pass/fail. It records no exception text, response data, feature content,
identifiers or expressions. The prior `a2_verify` stages, dispatch, approval,
freshness, exact-effect verification, fence and recovery behavior are unchanged.
Synthetic response and journal failures verify stage attribution, retained
uncertainty and no success inference. No live CAD request or write was made during
this diagnosis. For any later separately authorized investigation, compare the
closed trace from the process that actually handled approval with the retained
audit/record state using read-only, privacy-preserving inspection; do not retry
the uncertain operation or release the fence based on the measured edge.

## Depth recovery prerequisite preparation (writes OFF)

The completed read-only database investigation found one uncertain fenced record
and one nearby same-user operational record. Relevant committed events were
write_dispatch_started at creation +3 seconds and write_uncertain at +4 seconds;
no provider-acknowledged or verified event committed. Audits have no operation ID.
This supports failure before durable acknowledgement, including response validation
or acknowledgement-transaction rollback, without proving a particular predicate.
No acknowledgement defect has been established; diagnostics and predicates remain.

`quantity_recovery_evidence.py` adds only a pure comparison prerequisite for a
single explicitly uncertain SET_EXTRUDE_DEPTH. It reprojects complete historical
and current captures through existing evidence validation, requires the historical
Baseline to equal the approved plan, and reuses unchanged verify_operation for
exact depth-only inventory/configuration/state comparison. It performs no I/O,
returns no authorization/result receipt, and has no route or fence-release path.
Offline negatives cover wrong depth, unrelated features, metadata/order/configuration,
revision mismatch, historical mismatch, malformed bodies/inventory and incompatible
journal/scope. No production caller consumes this component.

A complete quantity closure remains BLOCKED: the existing five-GET recovery reader
captures current state only, its independently preserved receipt contract describes
Fillet suppression, and its release policy requires a committed acknowledgement.
Depth recovery requires a separately reviewed historical immutable-microversion
capture path, independently preserved depth-operation provenance, and an atomic
quantity-specific coordinator with stale-evidence, identity/session/fence, replay,
concurrency and rollback tests. The pure comparison does not supply these controls.
Existing Fillet closure and orphan recovery remain unchanged and ineligible here.
Screenshots, measurements, current DB values and elapsed time cannot substitute for
independent provenance or upstream settlement. No recovery or real Onshape call was
performed in this task; the original record and fence were not accessed or changed.

Consolidated human sequence: keep all writers OFF and drained; review an independent
original approval receipt and independent upstream settlement evidence; arrange a
separately authorized read-only historical/current exact-definition comparison on
the disposable Part Studio. Stop if those sources are unavailable. Do not release
the fence until the missing quantity-specific administrative path is implemented,
reviewed, tested and separately authorized. After such closure, final live conformance
still requires separate exact-operation previews, cancel-first checks and explicit
human approval once per operation, using the dispatch diagnostics; uncertainty stops
that gate without retry. Phase 16 remains IN PROGRESS / live NO-GO.

Preparation gate: 13 new offline prerequisite cases; full API 8,482 passed, no
skips, including all 42 PostgreSQL cases; frontend 869 passed in 35 files; Modify
browser matrix 45 passed across Chromium/Firefox/WebKit. make format, lint,
typecheck (205 Python files and TypeScript projects), build, migration-check,
compose-check and audit passed. The existing bundle-size warning remains. Only a
new random-port, loopback-only tmpfs PostgreSQL 18.6 container was used for this
run and removed afterward; development data/volumes were not used. Logs are local
under /tmp/forge-depth-*. Existing recovery concurrency/replay/rollback tests passed;
these do not establish a quantity release implementation. No provider response
predicate, payload ceiling, adapter, approval, freshness, fence or recovery policy
was changed. This is prerequisite preparation, not a recovery or live-gate pass.

## Depth-specific administrative recovery implementation

The missing path is now implemented separately in depth_contracts.py,
depth_release.py, depth_recovery.py and integrations/onshape/depth_reader.py.
Existing Fillet modules, semantic prerequisite, write client, planner and public
routes are unchanged. The sole new audit kind is write_depth_operator_recovery
with local_only outcome. There is no route, CLI, browser action or model tool.

The private operator must supply independently preserved original approval evidence
(source, receipt digest, historical handle or approval digest, exact owner/context,
Extrude identity/position and approved quantity), an independent upstream-settlement
review with evidence digest and settled attestation, and explicit operator review of
stack/company/current grant generation, writer drain, provenance and authorization.
These typed attestations enforce consistency; they cannot authenticate an operator's
claims or cryptographically establish settlement. Database values relabeled as an
external receipt, screenshots and measurements are insufficient.

The depth-only coordinator follows the existing user/session/grant/fence/record
lock order and aged, explicitly uncertain single-operation eligibility. It requires
development with writes OFF, an inactive historical session, current same-user
connected read grant and an already cached credential valid through capture. It
never refreshes a token. Competing active records, mismatched references and audit
ambiguity reject. Required unique ordered audits are claim, dispatch and uncertainty;
a single acknowledgement is optional but, when present, must be ordered between
dispatch and uncertainty. Absence is never fabricated or treated as settlement.
This separate policy handles the established incident without changing Fillet policy.

Eight fixed GETs capture features/configuration/bodies at the approved immutable
microversion, followed by current head, pinned current features/configuration/bodies
and final head. Exact origin/path/query/body guards, response/JSON byte/structure
limits, timeouts, no retry and one-use readers apply. History must project to the
exact approved Baseline. check_depth_recovery_state remains the comparison authority
for exactly the approved depth change and all unrelated inventory/configuration and
relevant model state. Bad history stops before current reads. The raw captures stay
inside the private reader invocation and are never persisted or logged.

After closing the reader and discarding its credential, a transaction-local run
registers the exact sanitized evidence object. Object identity, reference pins,
transaction identity, consumed handoff, 30-second capture / 5-second handoff /
40-second transaction bounds, locked revalidation and conditional exact updates
protect release. One atomic transaction writes a redacted operator_recovered
tombstone retaining original_execution_outcome=execution_uncertain, deletes exactly
the matching fence, and adds the fixed audit. Any failure rolls back; a lost commit
reply never triggers retry or reports success. Closure does not prove write causality
or verified_success and never restores approval authority.

### Separately authorized real operator procedure (not executed)

1. Keep every effective writer OFF and drained, including in-flight work. Independently
   establish upstream settlement and review the preserved approval receipt against
   the original owner, exact disposable context, target and approved depth. Stop if
   provenance or settlement cannot be established. Review current configuration and
   connected read grant; the original session must be expired or revoked, never revived.
2. In one trusted private process, construct IndependentDepthApproval,
   IndependentSettlement and OperatorReview from the independently reviewed sources.
   Load the retained plan privately for consistency checking only; use
   build_depth_reference to pin it. Do not derive independent evidence from that row,
   export private values or log raw objects. Obtain separate explicit authorization
   for this exact administrative closure before invoking the coordinator.
3. Use recover_depth_record with the existing session factory, Settings, existing
   TokenManager cache and reference. Do not supply a live transport override. It
   performs exactly eight GETs on success and zero provider writes. Missing cached
   credentials, mismatches or stale evidence stop with the fence intact. On ambiguous
   completion inspect sanitized DB status/audit read-only; do not retry automatically.
4. Confirm the administrative tombstone and exact fence removal; historical outcome
   remains uncertain. Only then schedule a separately authorized live conformance
   gate: each of the five operations individually, fresh read/preview, cancel first,
   fresh proposal and approve once, verified exact effect and one mutation; additionally
   stale/double approval, cancel, unsupported/no-target and context-switch denial cases.
   Any uncertainty stops the gate. Do not infer Phase 16 completion from recovery.

This implementation task made ZERO real Onshape calls, did not access the live
retained record, did not execute administrative recovery, and kept CAD writes OFF.

### Depth administrative closure gate results

Full final API: **8,657 passed, zero skips**, including all 42 existing PostgreSQL
cases and 16 new depth PostgreSQL cases. The new depth matrices contribute 175
cases overall. Targeted semantic/evidence/recovery run passed 155 cases, and the
additional boundary matrix passed 17; counts overlap the full suite. Frontend:
869 tests in 35 files. Modify browsers: 45 passed across Chromium/Firefox/WebKit.
make format, lint, typecheck (214 Python files plus TypeScript), build,
migration-check, compose-check and audit passed. Existing bundle-size warning only.
All test CAD/transports were synthetic. PostgreSQL used new loopback random-port
tmpfs 18.6 containers matching the pinned Compose image; only those containers were
removed. Development database/volumes, credentials, domains, environment files,
lockfiles and provider contracts were not changed. Full logs remain local under
/tmp/depth-closure-*. Final diff review confirms Fillet retained modules, quantity
comparison prerequisite, normal Modify execution and payload ceilings are unchanged.
Implementation verification is not execution of the real recovery or live CAD
conformance; independent provenance/settlement availability remains a human gate.

## Server-attested disposable development incident policy

The external approval receipt search found none. This policy explicitly trusts
Forge's server database and code-enforced state transitions for the unique disposable
local incident; it does NOT treat the database as independent approval evidence.
It is separate from the stronger independent-receipt path and cannot run in
production (nor test environment). It does not defend against a privileged coherent
rewrite of database history. Suspected tampering or ambiguous history must stop
operator review; an unkeyed stored digest is integrity checking, not authentication.

Code-level approval proof and limits:

- plan_routes.approve applies the authenticated session, exact origin/CSRF and bounded
  strict body guard, handle grammar and write-enable fence. Its only executor call is
  plan_service.approve; no model/planner tool exposes this call.
- plan_service.approve identifies the active session and atomically claims through
  plan_storage.claim. Ownership/session, strict stored-plan integrity, exact immutable
  digest, pending/unexpired state, one-use conditional update, fence and claim audit
  commit together. A claim consumes the preview; it does not renew approval.
- Claim commits BEFORE current grant/context revalidation. Therefore claim alone
  cannot prove current CAD authority. A new synthetic route test removes write scope
  after preview: claim still commits, but dispatch never happens and CAD is untouched.
- Before durable dispatch, _current rechecks authenticated authority including current
  connected grant/write scope/generation and exact context binding, expiry and deadline;
  fresh evidence, semantic preview, payload preflight and head checks must pass.
  The typed retained uncertain row plus unique claim/dispatch/uncertain audit sequence
  supports server-attested approval/execution provenance under the trusted-server
  assumption. Audits themselves contain no operation IDs or digest and are not an
  independent or cryptographic receipt, nor proof of a physical human at the keyboard.
  The normal endpoint is human-approval-only by product contract, not a human-detection
  mechanism. Known human approval plus explicit operator review supplies that context.

ServerAttestedDevelopmentApproval and DevelopmentOperatorReview name this trust
claim honestly. IndependentDepthApproval and the independent result schema remain
unchanged. The server-only result additionally labels approval_provenance as
server_attested_development and audits write_depth_development_recovery/local_only.
Both results retain original_execution_outcome=execution_uncertain; neither is
verified_success or restored approval authority. Existing Fillet recovery is untouched.

recover_development_depth_incident accepts only the trusted in-process AuthRuntime
and DevelopmentIncidentReview. It chooses exactly one fenced incident globally,
serializes on the owner, derives private pins from strict stored-plan integrity and
the exact row, and uses the shared locked depth policy and eight-GET reader. The
operator supplies no opaque IDs/digests. Missing/duplicate/misordered audits, verified
or other conflicting execution audits, mismatched records/identities/fences, wrong
operation, unaged record, active old session, absent connected cached read credential,
non-disposable fixture, missing settlement or undrained writers all deny. Acknowledgement
is optional but never invented. Production and non-disposable denial is rechecked
at release. Evidence remains fresh, exact, one-use and bound to one transaction.
Atomic closure is followed by read-only confirmation of the exact tombstone, matching
fixed audit and absence of the related fence. Failure or ambiguous/lost completion
returns a fixed denial with no retry, even if commit actually completed. No browser,
HTTP/API/AI endpoint or provider-write path is added. A privileged local development
console launcher supplies the real in-process runtime; it is not a normal-user API.

### One trusted operator procedure for this incident (not executed)

1. Keep writes OFF. Stop/drain the old backend and all other effective writer processes;
   leave the existing local HTTPS frontend/configuration in place. Review the unique
   owned disposable incident, accept this server-attested trust policy, establish
   independent upstream settlement and authorize this administrative closure. The
   exact historical session must be inactive before recovery. The console now offers
   guarded revocation of only that retained incident session; signing out a different
   current browser session is neither required nor sufficient.
2. From the repository, run exactly this local operator launcher (no opaque pins):

   ```sh
   cd apps/api
   uv run --frozen python ../../scripts/depth_incident_operator.py
   ```

   It refuses non-development or writes-enabled settings before starting anything.
   It runs the normal backend on 127.0.0.1:8000 without reload, with no origin/domain/
   OAuth configuration changes and no new recovery route. If that port is occupied,
   stop and resolve the old backend; do not use a second competing instance.

3. In the existing Forge UI, establish normal authenticated read access in this
   launcher-owned backend. This populates the actual TokenManager cache through the
   normal supported auth/read flow; recovery itself never obtains or refreshes a token.
   A separate interpreter importing app cannot share another process's cache. Once
   normal read access exists, return to the console and type the exact review phrase
   DISPOSABLE SETTLED DRAINED AUTHORIZE only if each fact has been independently
   reviewed. Enter the private settlement facts when prompted (hidden input), the
   reviewed exact stack URL https://cad.onshape.com/api, and an empty company ID for
   this personal-stack fixture. No proposal handle, user/session/feature ID or digest
   is entered or printed. Cancellation/invalid review causes denial with no attempt.
   If the exact historical session is still active, the console prints the sanitized
   historical-session prompt. Type REVOKE HISTORICAL SESSION only to authorize that
   exact session's revocation. It commits and re-reads inactivity before continuing
   recovery with the same private incident pins. If already inactive, this step is
   skipped without another revocation/audit. A different current session, OAuth grant
   and cached read credential are preserved.
4. The console invokes the guarded entry once. It derives the unique server pins,
   validates all audits/relationships, performs at most eight bounded GETs, and closes
   only on exact agreement. It confirms the committed tombstone/audit/fence state
   read-only before printing PASS closure_confirmed with the original uncertain
   outcome. Any failure prints only a fixed DENIED category, never raw exceptions or
   private data. The launcher then stops its backend; retain the existing database.
   Do not retry an ambiguous/lost completion. Inspect sanitized status/audit read-only
   before any separately authorized next action. Missing cached credentials or missing
   operator evidence means stop; do not paste/export credentials or edit DB rows.

The launcher is private privileged local administration, with explicit console review;
it supplies no production switch, generic execution facility or normal-user recovery
mechanism. Starting normal read access does not authorize recovery or any CAD write.
No launcher or real recovery was executed during implementation/testing.

### Minimal remaining live gate after confirmed closure

Use the same disposable Sketch/Extrude/terminal-Fillet fixture. One case at a time:
depth, radius, rename, suppress, unsuppress. Each case uses the real Modify UI and
required fresh evidence/preview: cancel first and confirm unchanged, mint a fresh
proposal and approve once, wait for exact verified evidence and confirm one mutation
and unrelated definitions unchanged. Combine rapid double approval with one approved
case; exactly one mutation is permitted. Restore the fixture manually between cases
only when needed. Then test stale proposal (manually edit before approval), unsupported
request, no eligible target and context switch; all must deny CAD mutation. Cancel
coverage is already included in each operation. Do not add redundant Inspector polls
or disable any mandatory freshness/head/post-write read. Any uncertainty stops the
gate without retry. Recovery is not live conformance; Phase 16 remains incomplete.

This development task made ZERO real provider calls and did not access or modify
the original record/fence, enable writes, execute real recovery, merge or deploy.

### Server-attested policy final automated gate

Full final API: **8,843 passed, zero skips**, including all **74 PostgreSQL cases**
(42 original, 16 independent-depth and 16 server-attested-depth). The new server
policy/console matrices add 186 tests. Focused mixed new/existing recovery regression:
232 passed; console lifecycle/review tests: 10 passed. Counts overlap the full suite.
Frontend: 869 passed in 35 files. Modify browser matrix: 45 passed across all three
engines. make format, lint, typecheck (221 Python files plus TypeScript), build,
migration-check, compose-check and dependency audits passed. The existing bundle
size warning remains. PostgreSQL used newly isolated loopback random-port tmpfs 18.6
containers, removed afterward; development DB/volumes were never used for tests.
Logs remain local under /tmp/server-final-* and /tmp/server-gate-*. No lockfile,
secret, origin/OAuth configuration, planner, approval, payload ceiling, exact-effect
predicate or Fillet recovery implementation changed. Independent-depth reference
serialization/result schema remain unchanged. CAD writes remained OFF and no real
Onshape request, real closure, original-record/fence mutation, merge or deployment
occurred. This is implementation verification, not Phase 16 live conformance.

## Exact historical-session administrative preparation

The real operator denial historical_inactive_identity_required exposed a different
historical browser session still within its normal eight-hour lifetime. Recovery's
inactive-session requirement remains intact. A separate guarded preparation step now
uses the same complete incident validation and user/session/grant/fence/record locks.
The common validator returns the exact original session; _validate_locked still
requires it inactive before any recovery capture/release. No active-session bypass
or optional relaxation was added to recovery.

inspect_development_depth_session derives the exact session from the unique retained
fenced plan, validates the current disposable/operator/settlement/drain review and
all record integrity, single-depth, owner, grant, workspace, audit and age conditions,
and returns private frozen incident pins plus an active classification. The console
requires the exact extra phrase REVOKE HISTORICAL SESSION before invoking
revoke_development_depth_session. That helper rechecks the same pins/guards under
locks and conditionally sets only the exact Session.revoked_at=now(), with one
session_revoked/local_only audit in the same transaction. Already hard-expired or
revoked sessions are no-ops. It commits and re-reads the exact inactive identity and
unchanged incident relationships. Failure rolls back; ambiguous completion denies
without retry. Separate sessions, OAuth grant/generation, token cache, uncertain row
and fence are never mutated by preparation. It performs ZERO provider calls.

Console recovery then receives the same private incident pins; substituted or changed
incidents reject before capture. The operator enters no session ID/hash, need not log
out a different current browser session, and cannot revoke all sessions. There is no
new route, AI/browser capability, production mode or direct database-edit procedure.
The existing command/procedure above applies with this one conditional prompt.
The real historical session, retained record and fence were not accessed or modified
in this implementation task; real preparation/recovery was not executed.

Historical-session preparation gate: **8,874 API tests passed with no skips**, including
all **75 PostgreSQL cases** (the existing 74 plus the exact-session concurrent-revocation
case). The change adds 31 tests overall. Targeted mixed preparation/console/independent/
server-depth regression: 182 passed, one PostgreSQL case deselected for the targeted
non-PostgreSQL run; that race case passed separately and in the complete gate.
Frontend: 869 passed in 35 files. Modify browsers: 45 passed across all three engines.
make format, lint, typecheck (222 Python files and TypeScript), build, migration-check,
compose-check and audits passed. Existing bundle-size warning only. PostgreSQL used
only a newly isolated loopback/random-port tmpfs 18.6 container, removed afterward;
existing development data/volumes were untouched. Logs are local /tmp/session-gate-*.
No real provider call, real session revocation or recovery occurred. CAD writes stayed
OFF. Fillet recovery, independent-depth eligibility, exact-effect comparison, normal
approval/fence behavior, payload limits, grants and token handling remain unchanged.

### Closed development depth-read failure classification

The real operator advanced beyond historical-session inactivity and then denied
read_evidence_unavailable. That observation alone does not identify the failed
GET, projection or exact comparison. No cause or successful closure is inferred.

The existing eight-GET reader now reports fixed depth_recovery:stage:category
codes only for the private server-attested development incident path. Stages
identify historical features/configuration/body reads, historical projection,
current/final head, current features/configuration/body reads and projections,
and comparison. Categories distinguish unavailable projection, historical baseline
mismatch, invalid body evidence, changed final head, deadline, transport and rejected
provider response. Comparison categories distinguish inventory, configuration,
serialization, library, parent suppression, configured suppression, revision and
preview mismatch; an unclassifiable rejection remains unavailable. Where several
exact comparisons fail, the specific serialization/library/suppression predicate
precedes the encompassing inventory/configuration fingerprint mismatch.

Classification runs only after the unchanged authoritative prerequisite rejects.
It mirrors the existing depth verifier predicates independently, cannot authorize
recovery, and never includes provider values, opaque identifiers, expressions,
fingerprints, URLs, credentials, bodies or exception text. General Modify verification
and independent-depth/Fillet recovery remain unchanged. No session, grant, fence,
record, payload ceiling or recovery-release rule changes. Failure still closes the
reader, denies without retry and leaves the retained incident/fence intact.

Synthetic differential tests compare accepted/rejected states with the unchanged
verifier, isolate every comparison category, cover read/projection/provider/deadline
failures, check sanitized output and unchanged incident/fence, and prove even a
classifier returning no mismatch cannot override an authoritative rejection.
No real provider calls or real incident access occurred during implementation.
CAD writes remain OFF. The single next human evidence step is the existing operator
command, with the same disposable-fixture, drain and settlement review prerequisites:

```sh
cd /Users/jishnuhiremath/Developer/FORGE-retained-recovery/apps/api
uv run --frozen python ../../scripts/depth_incident_operator.py
```

Run once, record only its fixed denial category or sanitized closure result, and
stop on denial. This diagnostic does not establish live conformance or settle the
original uncertain operation. No automatic retry or fence release is introduced.

Diagnostic gate: **8,909 API tests passed, zero skips**, including all **75
PostgreSQL cases**. The diagnostic adds 35 synthetic tests; targeted reader,
comparison and session-preparation regressions passed 214 tests (one PostgreSQL
case awaited the full isolated-database run and then passed there). Frontend:
869 passed; Modify browsers: 45 passed across Chromium, Firefox and WebKit.
make format, lint, typecheck (223 Python files and TypeScript), test, build,
migration-check, compose-check and dependency audits passed. PostgreSQL ran only
in a newly created random-loopback-port tmpfs container, removed afterward;
existing development databases and volumes were untouched. Full logs remain local
under /tmp/depth-class-*. No live recovery or CAD write was attempted.

### Development inventory-mismatch explanation

The next real operator reported depth_recovery:comparison:inventory_mismatch.
This establishes an exact expected/current inventory disagreement; it does not
establish the specific structural difference or settle the original operation.

Only after the existing authoritative comparison rejects, the private development
reader now explains an inventory fingerprint mismatch using the already captured
historical/current inventories. It constructs the same expected approved depth
replacement and source revision as verify_operation, without changing that verifier.
No provider request, persisted CAD, new recovery mechanism, normalization or
verification exception is introduced. The closed diagnostic vocabulary does not
ignore any field for acceptance: the complete exact fingerprint remains authoritative.

The appended diagnostic set is deduplicated in this fixed order:

- feature_count_changed
- feature_order_or_identity_changed
- non_target_feature_changed
- target_name_changed
- target_suppression_changed
- target_definition_metadata_changed
- target_parameter_count_changed
- target_parameter_order_changed
- target_parameter_type_or_shape_changed
- target_depth_expression_unexpected
- target_depth_parameter_metadata_changed
- other_target_parameter_metadata_changed
- feature_states_changed
- source_revision_metadata_changed
- unknown_provider_metadata_changed

Features/parameters are aligned by identity for diagnostic attribution only.
Unknown fields (including nested additions/removals) collapse to the generic label;
no keys, values, identities, indexes, revisions, expressions, quantities, fingerprints,
queries or exception text appear in output. Multiple categories may overlap and are
reported together, without implying causality or authorizing a repair. A classifier
failure remains a denial with the generic label. Independent-depth and Fillet paths,
session revocation, grants, payload ceilings, record/fence and verification rules
remain unchanged. CAD writes stayed OFF; no real provider/incident was accessed.

The existing operator command above remains the next single human evidence step,
with the same disposable/drain/settlement review. Record the fixed denial suffix
and stop on denial. No live retry or recovery was run in this implementation task.

Inventory diagnostic verification: **8,963 API tests passed, zero skips**, including
all **75 PostgreSQL cases** in a newly isolated random-port tmpfs database container,
removed afterward. The change adds **54 synthetic tests**. Focused diagnostics,
readers, exact comparison and historical-session regressions: **268 passed**, with
one PostgreSQL case initially skipped locally and subsequently passed in the full
isolated-database run. Frontend: **869 passed**; Modify browsers: **45 passed** across
all three engines. make format, lint, typecheck (225 Python source/test files and
TypeScript), test, build, migration-check, compose-check and audits passed. Final
privacy boundary additions were followed by focused tests and full API/PostgreSQL
regressions. Full logs remain local under /tmp/inventory-diff-*. No real provider
calls or incident access occurred; CAD writes remain OFF. The exact verifier,
release procedure and operator console are unchanged.

### Consolidated development baseline/current diagnostics

The next human attempt reported historical_projection:baseline_mismatch instead of
the previously observed current inventory mismatch. The retained incident and pinned
historical revision are reported unchanged. This does not identify a cause or prove
that any difference is safe to normalize. No normalization or repair is introduced.

The private server-attested development reader now compares every typed Baseline
component with the saved approved baseline, emitting only the following fixed labels
in this order: context_mismatch, microversion_mismatch, terminal_identity_mismatch,
terminal_label_mismatch, position_mismatch, definitions_digest_mismatch,
full_evidence_digest_mismatch, serialization_mismatch, library_mismatch,
suppressed_state_mismatch, body_revision_evidence_mismatch,
feature_state_evidence_mismatch, suppression_aux_evidence_mismatch,
parent_suppression_evidence_mismatch, configured_suppression_evidence_mismatch.
No values, labels, counts, digests or revisions are emitted. An exhaustive field-map
test requires every Baseline field to have exactly one diagnostic category.

A mismatch latches an unconditional denial from the original model equality check,
independently of diagnostic labels. Only this already-denied development path may
continue the existing bounded eight-GET sequence, project current evidence, collect
all supported exact comparison failures and inventory-difference categories, and
check the final head. The combined output is a fixed historical_baseline_mismatch
section plus current_comparison and/or current_capture sections. Current read,
projection, deadline or final-head failures preserve the historical section. A
current_comparison:exact_match label describes only the diagnostic comparison;
the historical mismatch still forbids recovery. Even an empty diagnostic category
result cannot remove the denial. No VerifiedDepthRecoveryEvidence is constructed,
registered or handed to release_depth_record after a historical mismatch.

The existing single-category API is retained for matching-history behavior.
verify_operation, check_depth_recovery_state, saved-plan equality, exact inventory
fingerprints, locking, grants, session preparation, release and original uncertainty
remain unchanged. Independent recovery still aborts immediately on historical mismatch.
No new provider request, retry, route, recovery mechanism or raw CAD persistence is
added. CAD writes remain OFF. No real provider call, incident/session access or live
recovery occurred during implementation. The existing one-time operator command
above remains applicable with the same reviewed disposable/drain/settlement inputs.

Consolidation gate: **8,992 API tests passed, zero skips**, including all **75
PostgreSQL cases** in a newly isolated random-port tmpfs container, removed afterward.
The change adds **29 synthetic tests**. Focused baseline/current diagnostics,
comparison, readers and session preparation: **297 passed**, with one PostgreSQL
case initially skipped and then executed successfully in the full database gate.
Frontend: **869 passed**; Modify browsers: **45 passed** across three engines.
make format, lint, typecheck (227 Python source/test files and TypeScript), test,
build, migration-check, compose-check and dependency audits passed. Logs remain
local under /tmp/depth-consolidated-*. Existing development databases/volumes and
the real incident were untouched. No real provider calls or live recovery occurred;
CAD writes remain OFF. Phase 16 live conformance remains unproven.

### Schema-aware semantic node repair — human recovery pending

Controlled evidence now isolates the remaining mismatch to target parameter metadata;
all reported structural/semantic categories were absent. The strict ordinary profile
fixes the other metadata values, while nodeId is bounded provider-generated parameter
bookkeeping. Replacement responses may regenerate those nodes. Binding raw nodeIds
in semantic inventory equality therefore rejects otherwise exact approved changes.
This explains the conformance defect; it does not establish the original dispatch
failure stage or retroactively verify the original 20-to-25 mm execution.

semantic_inventory.py creates a copy and removes ONLY validated nodeId fields at:
standard top-level Sketch/Extrude/Fillet feature objects, their supported ordinary
suppressionState object, fully validated Extrude/Fillet parameter objects, and
supported individual query objects directly inside validated query-list parameters.
There is no arbitrary recursive deletion. Sketch internals, filter trees, unknown
containers/keys, featureStates and configuration retain node-named fields exactly.
Unknown/unsupported parameter profiles keep all raw parameter fields and gain no
eligibility. Every recognized node slot must remain a nonempty 1–256 character
string; malformed nodes reject before semantic evidence can be used.

Complete raw features remain available to change()/payload construction, including
nodeIds and parameter order. Existing complete legacy/current-UI adapter validators
run before parameter bookkeeping removal. Verification deliberately compares exact
canonical inventories; acknowledgement feature equality uses the same representation.
There is no permissive catch after a failed exact comparison. Every other field,
including quantity/query metadata, remains exact and fresh body/model proof remains
mandatory. New Modify baseline definitions/full-inventory digests use this semantic
representation with configuration untouched. Repeated reads differing only in
proven node bookkeeping are stable at the same immutable revision.

New plans use policy modify-semantic-nodes-2. Old pending modify-a1-1 plans cannot
execute under the new meaning; their claim rejects before creating a write fence.
For retained single-depth uncertainty, the explicit legacy helper first reprojects
fresh historical evidence using the ORIGINAL RAW baseline contract and requires
complete equality with the original approved baseline. Only then can historical and
current semantic inventories prove exactly the approved depth change. A mismatch in
that raw binding still unconditionally denies, even if the difference is a nodeId.
No stored plan, approval digest or database row is rewritten for compatibility.
Existing locked ownership, historical-session inactivity, settlement/drain review,
one-use evidence, final head bracket and release rules remain mandatory. Closure
still reports original_execution_outcome=execution_uncertain. Pre-repair Fillet
reconciliation continues using its original raw digests; Phase 9 is unchanged.

Synthetic tests cover each allowed location independently in history/current reads,
bounded node rejection, meaningful value/query/feature/unknown changes, raw payload
preservation, regenerated acknowledgement followed by fresh verification, uncertainty
on acknowledgement/post-read tampering, raw-bound legacy depth closure and denial,
unchanged legacy Fillet behavior, and rejection of old pending policy claims. The old
per-role node-rejection tests now require successful validated node-only verification
AND rejection of unknown nested node-named fields on every role. Diagnostic negatives
use non-node metadata so they continue testing meaningful mismatches.

CAD writes stayed OFF. No real Onshape calls, real incident access, live approval,
recovery, merge or deployment occurred during implementation. Remaining human step:
run the existing reviewed development operator ONCE with writes OFF. Expected closure:
PASS closure_confirmed original_execution_outcome=execution_uncertain. If the original
raw binding or exact semantic state cannot be proved, retain the denial/fence; do not
retry automatically. Phase 16 remains incomplete until controlled live conformance.

The semantic representation also binds the existing parameter validator's profile
classification. An unsupported raw envelope cannot compare equal to a validated,
node-cleaned envelope merely because required node fields were omitted. This
classification is comparison-only and never added to raw provider payloads. Tests
cover missing required node envelopes at acknowledgement and fresh verification.

Final repair gate: **9,073 API tests passed, zero skips**, including all **75
PostgreSQL cases**. The repair adds **81 synthetic tests**; final focused semantic,
current-UI and diagnostic checks passed **1,223 tests**. The broader Modify/Phase 16/
recovery suite was exercised; its obsolete raw-node rejection expectations were
replaced with positive validated-node and negative unknown-node/non-node metadata
checks, then the complete final API suite passed. Frontend: **869 passed**; Modify
browsers: **45 passed** across Chromium, Firefox and WebKit. make format, lint,
typecheck (229 Python source/test files and TypeScript), test, build, migration-check,
compose-check and audits passed. The final schema-classification guard was followed
by the full final gate. Only the authorized node-only equality expectation changed;
timeouts, numeric bounds, approval rules and test thresholds remain unchanged. Logs remain local under /tmp/semantic-node-final-*.
PostgreSQL used only newly isolated loopback/random-port tmpfs containers, removed
afterward; existing development databases/volumes and the retained real incident
were untouched. Real recovery and live conformance remain human checkpoints.

PHASE 16 REPAIR READY FOR REAL RECOVERY

### Controlled acknowledgement failure after semantic-node repair

The latest human-controlled disposable depth write reported this exact closed trace:
request_preflight pass, provider_exchange pass, ack_skew pass,
ack_feature_envelope pass, ack_target_identity pass, ack_fingerprint fail.
No a2_verify stages occurred. The operator reports the requested 25 mm state visible
in Onshape, zero verified operations, execution_uncertain and a protective fence.
Writes are now OFF. A visible measurement does not verify the acknowledged feature.
No recovery, retry or real provider/incident access occurred in this implementation.

The proven boundary is acknowledgement semantic-feature comparison before marker
validation, acknowledgement journaling and fresh post-write reads. The trace alone
does not distinguish an unequal semantic representation from rejection while
constructing that representation. It does not identify the differing field or
parameter-profile discriminator. No raw acknowledgement was supplied or retained
by this task; synthetic fixtures cannot establish the actual live field difference.
Consequently no additional bookkeeping exclusion or production conformance fix is
justified. The actual mismatch category remains unproven beyond ack_fingerprint.

The development-only a2_ack_difference warning now reports a deterministic deduplicated
closed set of schema-path classes and existing validator reason codes. Classes cover
feature/suppression envelopes, field presence, parameter inventory/order/type/profile,
quantity expression/cached value/units/integer flag, common parameter metadata,
enum/Boolean/array changes, query/filter/identity structure, unknown fields and malformed
node slots. It distinguishes invalid semantic projection from comparison inequality.
Unknown keys/containers collapse to fixed labels; no values, names, IDs, node IDs,
expressions, quantities, query contents, fingerprints, URLs, bodies or exception text
are emitted. There is no generic recursive dump. Schema-derived parameter limits and
the existing query-list bound cap detailed inspection; diagnostic_structure_limit
explicitly flags uninspected excess structure. Classifier failures emit only
fixed diagnostic_unavailable. Production performs no classification or logging.

The warning is emitted only at an already-failed full-definition acknowledgement.
The production semantic_feature representation, exact comparison, rejection and
exception propagation are unchanged; the diagnostic cannot authorize success.
Raw request/response data remains unchanged and is never persisted by this helper.
Identity checks, rejectMicroversionSkew, freshness/digest/claim/fence controls,
post-write exact verification, recovery and no-retry behavior, query contracts and
24 KiB/8 KiB limits are unchanged. Original records/fences remain untouched.

Synthetic cases demonstrate multiple distinct acknowledgement-only differences can
produce the same observed stage trace. They also cover already-proven valid node-only
variation, malformed/out-of-location nodes, meaningful field/query mutations, privacy,
production silence, classifier failure, uncertainty/fence retention, no retry and no
post-write read after a rejected acknowledgement. Existing semantic verification and
legacy recovery regressions remain required. These tests are not a replay of the real
incident and do not constitute new live evidence.

Remaining human evidence is a closed schema classification from an independently
preserved acknowledgement or a separately authorized future capture. This task does
not request or authorize another write, incident retry, recovery or fence release.
Phase 16 remains blocked on actual live acknowledgement conformance; do not infer a
new safe normalization rule from any diagnostic class without supporting evidence.

Acknowledgement diagnostic gate: **9,125 API tests passed, zero skips**, including
all **75 PostgreSQL cases**. The change adds **52 synthetic tests**; final focused
acknowledgement/stage/semantic-node checks passed **146 tests**. The relevant Modify,
current-UI, payload, depth/legacy recovery and session suites were exercised and are
included in the passing complete API gate. Frontend: **869 passed**; Modify browsers:
**45 passed** across Chromium, Firefox and WebKit. make format, lint, typecheck
(231 Python source/test files and TypeScript), test, build, migration-check,
compose-check and dependency audits passed. Logs remain local under
/tmp/ack-fingerprint-*. PostgreSQL used only a new isolated random-loopback-port
tmpfs container, removed afterward; existing development databases/volumes and
real incident records/fences were untouched. No real provider calls, writes,
recovery, retry, merge or deployment occurred. CAD writes remain OFF.

AUTOMATED ACK DIAGNOSTIC GATE PASS — ACTUAL LIVE MISMATCH CLASS UNPROVEN

### Explicit original-baseline-restored administrative disposition

Human sequencing evidence: after the second controlled depth write failed at
ack_fingerprint, CAD was manually restored from the observed 25 mm state to the
original approved 20 mm baseline before the recovery operator ran. The operator
then denied depth_recovery:comparison:inventory_mismatch:target_depth_expression_unexpected.
The historical session was explicitly revoked when prompted; writes remained OFF
and the protective fence remained. This expected denial does not establish a new
Modify conformance defect: the existing recovery predicate requires current CAD
to match the approved final state. The acknowledgement mismatch remains unresolved.

The private development console now offers a separately explicit reviewed choice:
RESTORED BASELINE SETTLED DRAINED AUTHORIZE. It requires the same owned disposable
fixture, independently reviewed upstream settlement, drained writers, writes OFF,
unique aged fenced uncertain depth incident, original binding/integrity/audits,
inactive historical session, current connected read grant and cached credential.
The reviewed choice is bound into the incident reference fingerprint, including
historical-session preparation and the one-use transaction-local evidence handoff.
Changing the choice after capture invalidates the handoff. There is no fallback
between baseline-restored and approved-final-state recovery.

The same eight bounded GETs reacquire immutable approved history and bracket fresh
current pinned feature/configuration/body reads. Legacy approvals must pass their
original RAW historical baseline binding first; semantic-policy approvals keep their
original semantic binding. The new pure comparison validates the exact retained
depth target and preview, then compares the complete projected original baseline
with current evidence. Only the already-supported sourceMicroversion substitution
and validated nodeId bookkeeping semantics apply. Inventory/order/identity, depth
expression and all other parameters/queries/metadata, independent configuration,
suppression evidence and projected model-health evidence must agree. No geometry
equivalence beyond the existing bounded body/model evidence contract is inferred.
Unknown, malformed or unsupported changes reject; no new normalization is added.
Final head movement/deadlines reject before release.

Atomic administrative release, exact conditional record/fence updates, fixed audit,
commit and read-only completion confirmation are reused. The redacted tombstone
records disposition=independently_settled_original_baseline_restored and preserves
original_execution_outcome=execution_uncertain. It never claims the original write
did or did not happen, fabricates execution success, edits CAD or rewrites approval
authority. The old independently_settled_current_state_matches disposition and its
exact approved-result verification remain unchanged, as do independent-depth and
legacy Fillet recovery. No public route, AI tool or production mode is added.
Failures before commit roll back and retain record/fence. An ambiguous commit result
must deny without retry; as with the existing path, a commit already completed can
only be assessed by independently inspecting committed state, never by assuming
rollback or reporting success.

Implementation/tests used synthetic provider evidence and isolated test databases
only. The real incident/fence, real Onshape document and CAD-write configuration
were not accessed or changed. No recovery attempt, live write, merge or deployment
was performed. Production Modify verification, ack comparison, approval/freshness,
claim/fence/microversion/no-retry behavior, query contracts and 24 KiB/8 KiB limits
remain unchanged. Phase 16 live conformance is still incomplete.

Separately authorized next operator checkpoint (do not run as an automated test):
stop other backends/writers; keep CAD writes OFF; start the existing local console
with `cd apps/api && uv run --frozen python ../../scripts/depth_incident_operator.py`.
Use normal read-only UI access to populate that runtime's cached credential. Review
settlement/drain and the disposable incident, choose exactly
RESTORED BASELINE SETTLED DRAINED AUTHORIZE, and provide the existing private review
and exact stack/company inputs. Revoke only the historical session if prompted.
Attempt once; on denial or unconfirmed completion retain the stop/no-retry posture.
A confirmed baseline-restored disposition proves current restoration only, never
original-write causality or successful Modify conformance.

The first complete automated gate exposed an existing development closure timestamp
race: the tombstone used now() at construction while its audit used a separate
insertion-time default; completion requires their timestamps to be exactly equal.
A deterministic synthetic clock-tick test reproduced completion_unconfirmed_no_retry.
Development closure now assigns the same atomic closure timestamp to its fixed audit
and tombstone. The exact confirmation predicate is unchanged. Independent-depth
and Fillet auditing remain unchanged; audit-failure rollback injection remains
covered. This is a local administrative-confirmation fix, not evidence about the
real ack_fingerprint failure. Full regressions are rerun after this proven repair.

Final baseline-restoration gate: **9,177 API tests passed, zero skips**, including
all **76 PostgreSQL cases** (75 existing and one added concurrent restored-closure
case). This change adds **52 synthetic cases**, including a deterministic clock-tick
regression. The initial relevant suite passed **3,109 tests**; after the clock fix,
focused recovery/session/semantic regressions passed **405 tests**. Each focused run
omitted its one isolated PostgreSQL case; that case executed in the final complete
passing gate. Frontend: **869 passed**; Modify browsers: **45 passed** across Chromium,
Firefox and WebKit. make format, lint, typecheck (232 Python files and TypeScript),
test, build, migration-check, compose-check and dependency audits all passed.
The first complete run's one timestamp-confirmation failure was reproduced and fixed
before the final full rerun; no assertion, timeout, bound or confirmation predicate
was weakened. Logs are local under /tmp/baseline-restored-* (the failed first run is
preserved separately). PostgreSQL used only new random-loopback-port tmpfs containers,
removed afterward; existing development databases/volumes and the real incident/fence
were untouched. Human recovery and actual acknowledgement conformance remain unrun.

AUTOMATED BASELINE-RESTORED ADMINISTRATIVE CLOSURE GATE PASS — LIVE CONFORMANCE PENDING
