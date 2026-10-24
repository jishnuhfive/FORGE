# Hackathon Modify A1 — typed operations and deterministic executor

Branch: `hackathon/a1-modify-executor`. Starting commit:
`56bf83b85eb33c6c2d6277b9a289ae1edab8b71c`. This is a backend integration boundary,
not completed general Modify. No AI planner, new HTTP route, UI, OAuth change,
dependency, table or migration is introduced. CAD writes remain OFF. Development
and tests perform **zero real Onshape writes** and zero model calls.

Phase 9's `suppress_terminal_fillet_v1` and its browser request “Suppress the final
fillet.” retain their original path. Shared admission, atomic claim, integrity,
fence and pinned transport primitives now also support A1. The existing evidence
projector and Phase 9 verifier are unchanged. Historical reviews are unchanged:
**Gate A is proven; Gate B observed expected stale-write behavior, with provider-side
rejection audit confirmation still deferred.**

This document records the original minimal A1 representation contract. Phase 16
adds separate closed current-UI parameter profiles after human writes-OFF evidence;
see [the exact contracts, automated results and pending human recheck](PHASE_16_MODIFY_LIVE_CONFORMANCE.md).
The five operations, semantic planner contract and all approval/execution authority
below remain unchanged. Current-UI live writes are not yet validated.

## Semantic contract for Team B

`forge_api.cad_edits.plans.SemanticPlan` is strict, frozen and extra-forbidden:

```text
SemanticPlan = {
  target_catalog: Handle,
  operations: [ModifyOperation, ...]  // minimum 1, maximum 5
}
Handle = string matching ^[A-Za-z0-9_-]{43}$

ModifyOperation =
  {type: "SET_SUPPRESSED", target: Handle}
  | {type: "SET_UNSUPPRESSED", target: Handle}
  | {type: "RENAME_FEATURE", target: Handle, new_name: Name}
  | {type: "SET_EXTRUDE_DEPTH", target: Handle, quantity: Quantity}
  | {type: "SET_FILLET_RADIUS", target: Handle, quantity: Quantity}
```

The discriminator fixes the suppression Boolean. Quantities are literal strings:
`[0-9]{1,6}(\.[0-9]{1,6})? (mm|in)`, maximum 32 characters, 0.001–10000 mm or
0.001–393 in inclusive. Exact spelling is preserved; no conversion, evaluation,
inferred units or normalization occurs. NaN, infinity, exponents, variables,
functions, missing units, negative/zero values and extra whitespace reject.
These are conservative input limits, not engineering safety certification.

Names trim outer whitespace, require 1–128 characters and at most 256 UTF-8 bytes,
and reject Unicode C categories (including controls/format/surrogates) before trim.
Names remain untrusted text and must be rendered as text, never HTML or code.
Names do not resolve identity. Operations and plans reject all extra properties,
including featureId, providerFeatureId, url, method, payload, featureDefinition,
microversion, parameterId and FeatureScript. Only discovery accepts the existing
validated workspace context contract.

Stable interfaces in `cad_edits/plan_service.py`:

1. `discover(request, auth, context) -> TargetPreview`: authorized pinned reads,
   session-owned expiring catalog, opaque handles and semantic capabilities.
2. `prepare(request, auth, SemanticPlan) -> PlanPreview`: rechecks catalog ownership,
   authority, expiry and exact baseline; resolves handles and stores the ordered
   preview. Repeated targets are allowed: rename then suppress previews the new
   label; suppress then unsuppress previews both transitions.
3. A **separate human approval handler**, never a planner tool, calls
   `approve(request, auth, proposal_id, digest) -> PlanResult`.
4. `status(request, auth, proposal_id) -> PlanResult` is owner/session-scoped.

Future HTTP handlers must reuse `cad_edits.routes.guard`, bounded JSON parsing,
closed schemas and same-origin/session-CSRF policy. No A1 route is registered.
The existing Phase 9 approval route cannot decode/execute an A1 record. Neither
planning nor preview generation authorizes execution. Team B must not register
the executor, write client, private records or provider registry as model tools.
`TargetPreview.targets[].supported_operations` supplies applicable semantic capabilities;
`edit_registry.supports_operation(type, feature_type)` answers the static support
question without returning provider details. Capabilities are not approval.

## Supported scope and centralized registry

`integrations/onshape/edit_registry.py::SUPPORTED_EDITS` is the only support map.
The Part Studio must satisfy the existing Phase 9 scope: unconfigured workspace,
3–20 standard top-level Sketch/Extrude/Fillet features, final Fillet, no subfeatures
or rollback, strict ordinary/null auxiliary suppression policy, all nonterminal
features explicitly active, and exactly one supported SOLID with NO_ERROR at the
exact pinned revision. This is not universal Onshape feature support.

| Semantic operation | Supported target                                              | Only changed field           |
| ------------------ | ------------------------------------------------------------- | ---------------------------- |
| SET_SUPPRESSED     | Active terminal standard Fillet                               | suppressed false → true      |
| SET_UNSUPPRESSED   | Explicitly suppressed terminal standard Fillet                | suppressed true → false      |
| RENAME_FEATURE     | Extrude or Fillet matching the same narrow parameter adapters | name                         |
| SET_EXTRUDE_DEPTH  | Active simple solid NEW BLIND Extrude                         | Recognized depth expression  |
| SET_FILLET_RADIUS  | Active simple Fillet matching the fixture adapter             | Recognized radius expression |

Unknown suppression never becomes false. A1 invokes the unchanged Phase 9
projector with the observed terminal Boolean. Exactly empty state maps mean
unavailable; complete maps must cover every feature and strictly agree with
suppression/inactive states. Partial maps, missing Boolean, configured/parent
conflicts or unsupported bodies reject. Unavailable states imply no model health.

### Rename safety (full-definition replacement)

Onshape's partial update endpoint does not document rename, so rename is a
**full feature-definition replacement**: the server copies the entire fresh
definition and changes only `name`. It is therefore safe only when Forge holds a
complete, proven definition to copy. Rename is restricted to the same narrow
Extrude and Fillet shapes as the quantity edits and must pass the full supported
parameter-shape check (`quantity_parameter` over exactly the allowed parameter IDs,
the required explicit enum/query/Boolean parameters, and a valid supported
quantity expression) before a target is even offered for rename.

Rename rejects **before any plan exists, and before any dispatch**, when the
definition is incomplete or malformed: parameters missing, null, empty, malformed,
duplicated, unknown or wrongly typed; unsupported feature type; non-standard
`btType`; unknown suppression state; or a name that is empty, over-long or contains
control characters. Missing provider fields are never treated as harmless defaults.
If a definition degrades after a plan was prepared, the executor repeats the check
against fresh evidence and stops with zero provider writes. Tests assert this
end to end: provider write count zero, no dispatch audit event, no workspace fence,
and later operations skipped.

### Parameter evidence and explicit limits

Repository inspection found no reliable captured depth/radius write fixtures.
The Inspector's `endDepth` fixture tests display formatting across unrelated
parameter types; it is not a write identifier source. A1 does not accept endDepth,
distance, length or other aliases.

`apps/api/tests/fixtures/modify_parameters.json` is **synthetic, not a live CAD
capture**. Its narrow supported representations are:

- Extrude: one `BTMParameterQuantity-147`, `parameterId: depth`, string expression;
  explicit bodyType=SOLID/ExtendedToolBodyType, operationType=NEW/NewBodyOperationType,
  endBound=BLIND/BoundingType, and a nonempty entities query parameter. Only those
  five parameter IDs are accepted. This follows the official
  [Extrude REST example](https://onshape-public.github.io/docs/api-adv/featureaccess/).
- Fillet: one `BTMParameterQuantity-147`, `parameterId: radius`, string expression,
  a nonempty entities query, and optional explicit Boolean tangentPropagation.
  Only those three parameter IDs are accepted. The
  [official geometry documentation](https://cad.onshape.com/FsDoc/library.html#opFillet-Context-Id-map)
  establishes radius semantics; the feature guide documents REST quantity encoding.
  This synthetic adapter contract does **not** prove current UI-created Fillet
  serialization. Live representation/conformance validation is still required.

Target quantities allow only btType, parameterId, expression, optional nodeId and
optional explicit isInteger=false. Cached numeric value/units, tolerant subclasses,
extra target fields, missing/duplicate parameters, unsupported expressions and
other parameter IDs reject. Existing node IDs, ordering, queries, metadata and
unrelated feature fields are preserved exactly as JSON values. Unsupported second
directions, draft, thin, variable/asymmetric/width fillets and other richer shapes
reject. Never broaden support from a display name or planner assertion.

### Fixed provider transport

The public [Onshape OpenAPI](https://cad.onshape.com/api/openapi) was rechecked
without credentials on 2026-10-18: v17, version `1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
It matches Phase 9's research snapshot. Suppression uses the existing one-entry
`BTUpdateFeaturesCall-1748` with updateSuppressionAttributes=true. Rename/quantity
use `updatePartStudioFeature` / `BTFeatureDefinitionCall-1406`: copy the entire
fresh supported definition and change only name or the one expression. The partial
update endpoint does not document rename, so A1 does not assume it does.

All paths/methods/envelopes are private/server-built; feature IDs in the fixed
replacement path are URL-encoded. The original 8 KiB request and 2 MiB response
caps remain. Oversized definitions fail local preflight with zero POST; no partial
reconstruction occurs. Every mutation sets rejectMicroversionSkew=true using the
immediately preceding verified microversion and captured serialization/library.
Malformed/skewed acknowledgements, wrong identity, unchanged/missing revision or
nonexact replacement definitions become uncertain after dispatch. HTTP 200 is not
success. New-operation payload/guard conformance is not claimed live-proven.

## Identity, persistence and approval

`TargetCatalog` binds private feature ID/type/position and random handles to user,
hashed session, grant generation, exact context, baseline revision/fingerprints and
creation+120-second expiry. `ModifyPlan` holds the same authority, 1–5 ordered
resolved operations and previews, opaque proposal ID, schema `forge-modify-plan-a1`,
policy `modify-a1-1`, creation and expiry. Nested frozen records/tuples prevent
in-place mutation. Canonical SHA-256 binds the entire immutable plan to approval
and trusted database state; it is not a bearer credential or hostile-DB signature.

`WriteRecord.payload` holds `StoredPlan(plan, result)`. Mutable statuses are separate
from the digest and cannot authorize or resume work. Claim requires the initial
pending journal. Existing conditional UPDATE and unique workspace/user fences
produce one winner across workers. User → session → grant locks still coordinate
auth and dispatch. Both workflows share fences and admission budgets.

No tables, columns or Alembic revisions change. Pending invalidation, 120-second
expiry, 15-minute operational retention and nonexpiring denial fences are reused.
Safe completion retains only statuses until purge; uncertainty retains private
plan bindings until purge. Fences survive purge. Raw features/configuration/bodies
and write payloads stay in request memory; no raw CAD, prompts, tokens, model
reasoning, learner history or chat persistence is added. Existing backup/access
controls for short-lived operational metadata still apply.

Safe previews contain only opaque proposal ID, digest, expiry, operation type,
label/type/position, semantic field and current/proposed text. They contain no
provider identity, microversion, context IDs, token, raw payload or fence key.

## Sequential execution and failure behavior

Approval consumes the plan and commits the fence before provider reads. Each step:

1. Rechecks claim/fence, enable flag, session/grant/context, expiry and deadline.
2. Reads fresh head-bracketed features/configuration/body at one immutable revision
   and compares the complete baseline to the expected previously verified state.
3. Resolves the original private target, rechecks applicability/exact preview and
   preflights the fixed payload.
4. Commits the executing journal/dispatch audit, reacquires auth locks, rechecks
   head/authority/fence, and sends exactly one provider-guarded POST.
5. Records acknowledgement, reads fresh pinned evidence, verifies the exact effect
   and rechecks authority before durably recording verified success.
6. Advances expected baseline only to that verified evidence. M0 → op1 → M1 means
   op2 uses M1, never M0; every later operation performs another fresh read.

The whole plan retains the 30-second verification budget and 25-second pre-dispatch
bound. Steps do not renew this deadline or approval expiry. Five operations may
stop under provider latency. No automatic write retry, resume or rollback exists.

Per-operation states: pending, checking, executing, verifying, verified_success,
rejected_stale, write_failed (before dispatch), execution_uncertain, skipped.
All verified yields verified_success. A verified prefix followed by deterministic
failure/stale rejection yields partial_failure. A dispatched unverifiable step
yields execution_uncertain. Later steps are skipped, and prior verified effects
remain applied. First pre-dispatch failures yield rejected_stale or write_failed.

An abandoned claim becomes uncertain after the existing 150-second threshold;
status preserves the verified prefix and never resumes execution. Executing means
possible dispatch, not proof of provider success. Timeouts/lost acknowledgements,
unknown provider errors and incomplete evidence retain the fence. No automatic
provider-rejection-based fence release or operator recovery is added.

## Verification semantics

Fresh projection re-proves readability, pinned identity, supported body, ordinary
suppression/configuration and complete inventory policy. Type-sensitive hashes
compare the entire inventory/configuration after changing only the intended field,
revision markers and (for complete suppression state maps) the target's inactive
Boolean. Identity, feature membership/order, parameters/order, queries, metadata,
serialization/library versions and unrelated state otherwise match exactly.

Suppress proves explicit active→suppressed; unsuppress proves suppressed→active.
Rename proves same identity, exact new name and unchanged remaining definition.
Extrude/Fillet verify the recognized parameter expression and unchanged unrelated
structure. “Depth parameter verified” does not mean “the part is exactly this
thick.” No final edge geometry, geometry equivalence or engineering certification
is inferred. There is no broad ignore list or numeric tolerance hiding changes.

## Verification and remaining human work

Tests use synthetic fixtures/MockTransport only. PostgreSQL tests create/drop only
random test schemas, preserving application data and the existing healthy service.
They cover single-use concurrent claims, cross-workflow fences, mid-plan revocation,
abandoned claims and migration drift. Focused tests cover all operations, domain
bounds, identity, provider shape rejection, exact preservation, five-step execution,
revision chains, stop-on-failure, one-call timeout, no rollback, durable journals,
authority changes, privacy and injected extra properties.

Final automated gate:

- Frozen installs: npm ci and uv sync --frozen passed; lockfiles unchanged.
- 1,970 backend tests passed with real isolated PostgreSQL enabled. This includes
  145 A1 focused cases, four A1 PostgreSQL cases and all 809 Phase 9 regressions.
- All 15 PostgreSQL cases passed, including migration upgrade/drift verification.
- All 737 frontend tests passed with `--maxWorkers=2`. The initial unconstrained
  `make test` run hit worker-start and 5-second test timeouts; the complete frontend
  rerun passed with bounded concurrency, and the backend suite passed separately.
  No frontend code or test timeout was changed.
- make format, make lint, make typecheck (strict mypy: 123 files), make build and
  make migration-check passed. No new upgrade operations were detected.
- npm audit found zero vulnerabilities. Python pip-audit found no known
  vulnerabilities after retrying a PyPI timeout with a 60-second timeout.
- Whitespace, local documentation links, changed-file sensitive-pattern scan and
  manual sensitive-content review passed. No dependencies or secrets changed.
- Browser E2E was not rerun: no browser code, route or public HTTP contract changed.
  Existing Modify frontend regressions and the complete production build passed.

### Continuation validation of the final tree (Windows)

The checkpoint above predates the final rename-safety edit. A continuation agent
re-validated the exact final tree, reviewed the executor, evidence and storage code
against the A1 requirements, and added 18 end-to-end rename-safety tests.

- Focused A1: 166 passed (145 original + 18 rename-safety cases: rename of an
  incomplete or malformed Extrude/Fillet definition at prepare time, and a definition
  that degrades after preparation, all asserting zero provider writes, no dispatch
  audit and no fence; + 3 narrow additions: empty and `-Infinity` quantities, and an
  explicit M0 -> M1 -> M2 -> M3 chain assertion).
- Phase 9 safe-edit regression plus `test_ai_write`: 850 passed (non-PostgreSQL).
- PostgreSQL (isolated schemas): 15 passed, including four A1 cases.
- Full backend with PostgreSQL enabled: 1,989 passed. One failure and two collection
  errors are Windows-only and also occur on clean `main`: `test_dev_key` asserts POSIX
  file mode, and two `test_cad_read` parametrized ids are oversized for pytest.
- Frontend (normal `npm test --workspace @forge/web`): 737 of 737 passed. An
  earlier run on a loaded machine showed one timeout in the unrelated `InspectorView`
  test, which passed alone; A1 changes no frontend file.
- Phase 9 Modify browser tests (`modify.spec.ts`): 33 passed in Chromium, Firefox and
  WebKit.
- Platform notes (Windows, not A1 regressions): Prettier reports CRLF line endings on
  192 files repo-wide because `core.autocrlf=true`, and passes everywhere with
  `--end-of-line auto`; strict mypy over `scripts/` reports three POSIX-only
  `os.killpg`/`signal.SIGKILL` errors in `scripts/dev.py`, a file A1 does not touch.
- Ruff, formatting, strict mypy (`src tests migrations`, 119 source files), ESLint, TypeScript, production
  build, Compose config and `git diff --check`: pass. `alembic check`: no new upgrade
  operations, head `0002_safe_edit`; no migration file changed.
- `npm audit`: zero vulnerabilities. `pip-audit`: no known vulnerabilities.
- Real Onshape writes: zero. OAuth changes: zero. Writes remain default OFF.

### Known limitations for Team B

- Suppress and unsuppress apply only to the terminal standard Fillet, because the
  reused Phase 9 evidence policy requires every non-terminal feature to be active.
  Models must also have 3 to 20 standard Sketch/Extrude/Fillet features.
- Extrude and Fillet quantity shapes come from a synthetic fixture and official
  documentation, not from a live capture. Live conformance is unproven.
- The whole plan shares one 30-second verification budget, so a five-operation plan
  can stop as `execution_uncertain` under provider latency. That is fail-closed, not
  unsafe, but the fence then needs the existing recovery path.
- A planner may call `discover` and `prepare` only. `approve`, the write client, the
  private records and the registry must never be exposed as model tools.

Real new-operation representation/payload/guard validation remains required, along with the deferred
Phase 9 Gate B provider audit. No live mutation, OAuth redirect/permission/key
change, AI execution, merge or production-readiness claim belongs to A1.

## Changed-file map

- `apps/api/src/forge_api/cad_edits/plans.py`: closed semantic/public and private authority types.
- `apps/api/src/forge_api/cad_edits/plan_service.py`: target discovery, resolution, ordered executor and status.
- `apps/api/src/forge_api/cad_edits/plan_storage.py`: serialized plan/progress records on existing tables.
- `apps/api/src/forge_api/cad_edits/domain.py`: adds the partial_failure state.
- `apps/api/src/forge_api/cad_edits/service.py`: extracts shared preparation admission.
- `apps/api/src/forge_api/cad_edits/storage.py`: shares integrity/atomic claim primitives.
- `apps/api/src/forge_api/integrations/onshape/edit_registry.py`: sole operation/shape registry and exact definition changes.
- `apps/api/src/forge_api/integrations/onshape/modify_evidence.py`: request-local projection and complete structural verification.
- `apps/api/src/forge_api/integrations/onshape/write_client.py`: pinned-read reuse and closed guarded dispatch.
- `apps/api/tests/test_modify_plan.py`: 166 focused synthetic cases.
- `apps/api/tests/test_modify_plan_postgres.py`: four isolated PostgreSQL cases.
- `apps/api/tests/fixtures/modify_parameters.json` and its `README.md`: narrow synthetic shapes and provenance.
- `docs/HACKATHON_MODIFY_A1.md`, `ARCHITECTURE.md`, `SECURITY.md`, `DEVELOPMENT.md`, `ROADMAP.md`: integration, boundaries, validation and scope.
