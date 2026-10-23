# Phase 13 — CAD Inspector graph adoption

**COMPLETE — HUMAN READ-ONLY VALIDATION PASSED — MERGED INTO MAIN**

Started from clean `main` at `6f7d147dc4239dbe7b52c775eef9c4e2a7f12039`,
matching fetched `origin/main`, on `phase13/inspector-graph-adoption`.
Implementation commit: `7696aa0e51002725811379123f498cb91da1e3ff`.
Human-validation documentation commit: `bef41d2e13cca67e7436f06e4c09564e232867e8`.
Phase 13 is complete: human read-only validation passed, and Phase 13 merged into
main at `c200f0af5695a3c603074bdf3e640965a8d84171`. The non-fast-forward merge
preserves both commits without squashing. Phase 12 remains complete.
Railway remains unhosted.

## Consumer inventory and selection

The existing browser path is `ReadCad` → `inspectCad` → authenticated bodyless
GET `/api/onshape/part-studio/inspector` → `acquire` → validated
`WorkspaceReference` → `acquire_bound` → four-read `capture` → normalized
`Snapshot` → `inspect` → `CadInspector` → strict browser parser → `InspectorView`.

| Consumer                                          | Phase 13 behavior                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Direct CAD Inspector route                        | Uses `inspect_graph` after authorized acquisition; graph owns feature inventory/order |
| Compact `/snapshot` route                         | Same acquisition/proof; no graph construction                                         |
| AI `read_bound` in `ai/routes.py`                 | Unchanged `acquire_bound` → `inspect`; no graph grounding                             |
| Tutor `read_bound` in `tutor/routes.py`           | Unchanged `acquire_bound` → `inspect`                                                 |
| Learning Check my step in `step_checks/routes.py` | Unchanged acquisition, stop handling, `inspect` and deterministic checks              |
| Existing tests using `inspect`                    | Keep their existing projection, including legacy stale-evidence assertions            |
| Modify, approval, recovery                        | No integration or changes                                                             |

The Inspector was selected because it already presents bounded read-only feature
inventory from the identity-preserving Snapshot. It can prove graph adoption without
introducing a new public contract, model tool, provider read or UI behavior.

## Independent context boundary

`acquire` now returns the same immutable, server-validated request reference beside
the acquired result and request correlation. Query parsing, session/CSRF/exact-origin
checks, workspace-only validation and quota admission remain in their existing code.
The compact route ignores the extra return value. `acquire_bound` is unchanged.

```text
authenticated request → validated WorkspaceReference ───────────────┐
                       ↓                                          │
                acquire_bound → four bounded reads                │
                       ↓                                          │
               final session/grant revalidation                    │
                       ↓                                          ↓
               normalized Snapshot → graph_from_snapshot(snapshot, reference)
                       ↓                         ↓
               rich display evidence ← GraphQuery.ordered_features()
                       ↓
               unchanged CadInspector public contract
```

The expected context comes from the request validation, never from `snapshot.context`.
Construction happens only after the existing post-read lifecycle check returns.
Discarded acquisition results bypass graph construction. No graph is shared,
cached, persisted or reused across requests, accounts or contexts.

## Graph and Snapshot responsibilities

The graph establishes represented feature IDs, returned order, ordinal/index spine,
basic structural metadata and feature-list completeness provenance. The production
projection consumes `GraphQuery.ordered_features()`. It validates full identity/order,
count, completeness and metadata correspondence before applying the 100-feature cap.
Rich evidence joins by exact opaque provider ID within that same Snapshot only.
Repeated names, opaque ID spelling and lexical ID order cannot affect the join.

The unchanged feature display policy retains exact normalized provider type and
namespace eligibility, recognized type mapping, missing-name fallback, optional
suppression and bounded parameter labels/values/omitted counts. In particular, a null
graph namespace remains unknown; it is not proof of a standard feature.

Snapshot retains all parameters, source proof, request correlation, capture time,
freshness and physical evidence. Parts and bodies retain provider-return order and
all existing display bounds, description, part number, state, mesh/topology and mass
caveats. Graph semantic sorting of parts/bodies never reaches their Inspector output.
No graph IDs, edge IDs, provenance, provider IDs or graph bytes reach the browser.

## Equivalence and failure behavior

`tests/inspector_reference.py` freezes the pre-adoption feature/public projection
from the required starting commit, using existing public models and unchanged
part/physical helpers. It is test-only. Production shares presentation helpers,
and the direct route has one graph inventory authority. The existing `inspect`
entry point remains solely for consumers outside this phase and fixed unavailable
responses; a rejected Snapshot is never projected through it.

Equivalence tests reuse existing Inspector and topology parameterized fixtures and
their assertions, adding byte-for-byte public JSON comparison. Additional cases cover
nonlexical/repeated-name feature order, rollback/completeness, unavailable sections,
unique inventories beyond display caps and reversed semantic part/body ordering.
A frozen public-schema fingerprint guards `forge-cad-inspector-v1`.

Graph construction/query validation or graph/Snapshot correspondence failure returns
the existing HTTP 200 `CadInspector` unavailable-evidence shape: all section statuses
`provider_failure`, fixed code `invalid_response`, null proof counts and unavailable
inventory. The existing correlation and no-store boundary remain. No exception text,
IDs, payloads or graph serialization is logged or returned. This is distinguishable
from a successful, explicitly complete empty model (success, count 0, complete).
As with existing failed acquisition, its failure timestamp is response time, not
a claim about the discarded capture's freshness.

This intentionally changes unsafe legacy presentation of duplicate identities,
known stale/skewed/conflicting revisions or mixed-context evidence into unavailability.
Authorization stops retain their existing fixed error code and discard earlier
partial evidence. Acquisition failures such as lifecycle loss or rate limiting retain
their existing unavailable response. Valid graph-compatible evidence preserves output.

## Acquisition and authority

Graph adoption adds **zero Onshape requests**. The existing acquisition performs at
most four bounded GETs (features, parts, bodies, mass); early stops can perform fewer.
Pre-existing opt-in development safe-edit diagnostics remain unchanged and are not
part of the normal four-read contract. Phase 13 adds no diagnostic acquisition.
Endpoint regression tests prove four GETs for graph success and failure, no AI request
and no database mutation with a valid cached grant. Existing token refresh may still
perform its existing authentication persistence; Phase 13 adds none.

Session ownership, grant checks, CSRF, exact origin, duplicate-query rejection,
bodyless GET, workspace-only context, correlation and no-store policy remain intact.
No CORS, OAuth scope, write/approval/recovery, deployment, Railway, secrets, AI provider
configuration, schema migration, model or frontend change is included.
`FORGE_CAD_WRITES_ENABLED` remains default false.

Only AVAILABLE edges are facts/traversable neighbors. UNKNOWN context containment
stays unknown. PRECEDES means returned order, never dependency; absent edges disprove
nothing. No ownership, topology continuity, design intent or engineering correctness
is inferred. Phase 12 graph contracts and query implementations are unchanged.

## Verification record

The focused graph/Inspector gate passed **276 tests**, including 100 new Phase 13
cases and all 127 existing graph cases. Byte equivalence reuses the broad existing
Inspector fixture set; AST comparison confirms the test-only feature/public reference
matches the pre-adoption functions. The public schema also matches the required
starting commit exactly.

Frozen installs passed with `npm ci` and `uv sync --locked`; dependency versions
and lockfiles are unchanged. The complete automated gate passed:

- `make format`, `make lint`, `make typecheck` (strict Python and TypeScript).
- `make test`: **827 frontend / 2,712 API tests**, including all PostgreSQL cases;
  no skipped tests.
- `make build`: passed; only the existing unchanged frontend chunk-size advisory.
- `make test-e2e`: **594 Chromium/Firefox/WebKit tests**, no retries or weakened checks.
- `make migration-check`, `make compose-check`, `make audit`: passed; npm and Python
  audits found no known vulnerabilities.

The disposable synthetic PostgreSQL database was health-checked and migrated before
verification, then removed. Existing local data/services were left untouched.
Final scope/diff/secret-pattern review found only the three backend Inspector files,
three test/reference files and five documentation files. No deployment, scope,
write/recovery, migration/model, frontend, lockfile, AI or Modify integration changed.
There is no raw provider/graph exposure, credential change or additional provider call.
These are automated results, not a security certification or live Onshape validation.

## Known limitations and future boundaries

Sequential workspace reads remain non-atomic and captured-unverified. Graph V1 has
no wall-clock TTL or current-head check. Staleness here means existing explicit
mismatch/skew/context/revision rejection, not newly inferred elapsed-time freshness.
Graph-wide bounds and revision checks also cover parts/bodies/mass, even though their
Inspector presentation remains Snapshot-based; invalid structural evidence fails closed.
Automated fixtures do not establish real provider conformance or production readiness.

Future AI, Tutor, Learn, Modify, selection, dependencies, assemblies/mates, topology
or public graph API adoption requires separate authorization. There is no runtime
feature flag or retained second production implementation for the direct Inspector.

## Human read-only validation record

The human reported completing the authorized validation in a **real Onshape workspace
Part Studio**, using the **local HTTPS Forge development environment** on the
**Phase 13 branch**. Validation was read-only and **CAD writes remained OFF**.
The observations below are human-reported evidence, separate from the automated gate.
No browser/platform/version was supplied; no broader live browser coverage is claimed.

### Normal Part Studio

The Onshape model contained **Sketch Gate → Extrude 1 → Fillet 1** and **1 part**.
After **Refresh CAD**, Forge Inspector showed **3 modeled features**, in this exact
order, with these recognized types and suppression presentation:

| Order | Feature name | Recognized type | Presentation |
| ----- | ------------ | --------------- | ------------ |
| 1     | Sketch Gate  | Sketch          | Active       |
| 2     | Extrude 1    | Extrude         | Active       |
| 3     | Fillet 1     | Fillet          | Active       |

Feature parameter presentation remained normal when expanded. Inspector showed
**1 part** and **1 SOLID body**. Physical evidence remained conservative: mass was
unavailable, with no invented mass value. No ForgeModelGraph IDs, provider IDs,
provenance, graph bytes or other graph internals were exposed.

Onshape's larger visible **Features** count includes default geometry such as
Origin/planes. It does not contradict Forge reporting the **three modeled features**.

### Empty Part Studio

After **Refresh CAD**, Inspector showed **0 features, 0 parts and 0 bodies**.
Successful empty inventory was not presented as unavailable evidence. No previous
Sketch/Extrude/Fillet inventory remained.

### Context transitions

Switching back to the modeled Part Studio and refreshing restored **3 features,
1 part and 1 body**, with **Sketch Gate → Extrude 1 → Fillet 1** in order.
Switching again to the empty Part Studio and refreshing restored **0 features,
0 parts and 0 bodies**. No stale prior inventory persisted across these Part Studio
transitions. These observations do not establish untested account/session transitions.

### Read-only authority

The human observed:

- No CAD mutation.
- No feature suppression/unsuppression.
- No write proposal.
- No approval prompt.
- No additional Onshape consent prompt.
- No Phase 9 write validation was performed or required.

### Closeout scope

These observations validate the reported Inspector behavior in the tested read-only
workspaces. They do not establish atomic provider reads, general production readiness,
graph adoption in AI/Tutor/Learn/Modify, topology continuity, feature ownership,
dependency DAG correctness or engineering correctness. The known limitations above
remain in force. Railway remains unhosted. The human-validation documentation
closeout performed no deployment, merge or CAD write; the subsequent Phase 13 merge
is recorded above.
