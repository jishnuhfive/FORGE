# Phase 12 — ForgeModelGraph foundation

**PHASE 12 COMPLETE — MERGED INTO MAIN.** Full automated gate passed. No live
Onshape validation was required or claimed for Phase 12. Deployment and Phase 9
recovery remain frozen.

## Final merge record

Phase 12 merged into main at `e6a14d32a1a95d92fe9d03cf4edce71ee22a4640` through
a clean, no-conflict, non-fast-forward merge. Both implementation commits remain
preserved in history:

- Foundation: `ee827e191dc8e9c85085363686b68990dcf2f442`.
- Query review fix: `ee5040fd54bf6deca03974298542b6da4ac05c9b`.

The merged tree was byte-equivalent to the validated `phase12/forge-model-graph`
branch. Final merged-tree `make lint`, `make typecheck`, `make build`, `make audit`
and all 127 focused graph tests passed. Main was pushed and verified clean and
synchronized with origin. No live Onshape validation is claimed and no deployment
was performed; Railway remains not hosted.

ForgeModelGraph remains an internal foundation without broad production consumer
adoption. There is no selection ownership inference, dependency DAG, topology
continuity guarantee or engineering-correctness claim. The merge adds no CAD
authority, OAuth scope or provider acquisition. **Phase 13 remains NOT STARTED**
and requires separate authorization.

## Existing evidence inventory (recorded before graph design)

| Existing subsystem                                                                 | Deterministically available                                                                                                                                                                            | Limits / unavailable information                                                                                                                                                                              |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browser launch and bridge (`onshape/context.ts`, `bridge.ts`)                      | Validated document/workspace/element references, exact standard-stack server, workspace/version distinction; origin/parent-checked messages                                                            | Browser references do not authorize server access; launch metadata does not prove element type or current microversion                                                                                        |
| Four-read capture (`integrations/onshape/service.py`, `client.py`, `contracts.py`) | One request-local workspace Part Studio context; independent feature/part/body/mass outcomes; completion timestamp; reported source microversions; mismatch/skew detection                             | Reads are sequential and unpinned; even matching markers do not prove an atomic/current snapshot. Documents have only the capture envelope's context/time, not independently echoed context or timestamps     |
| Normalized features (`models.py`, `normalize.py`)                                  | Opaque feature IDs, returned order, provider type/name, optional explicit suppression, custom namespace flag, bounded allowlisted parameter summaries; isComplete/rollback/serialization/skew evidence | No complete dependency DAG, exact query resolution, face creation map, generic feature health or geometric intent. Unknown/missing flags remain unknown                                                       |
| Normalized parts and bodies                                                        | Opaque part/body IDs, provider names/types/mesh flags; returned topology counts only when nonempty arrays support them; per-part and body revision observations                                        | Equal part/body IDs are not an implemented ownership join. Empty export arrays do not establish zero topology; no face/edge identity inventory survives normalization                                         |
| Mass summaries                                                                     | Bounded aggregate physical estimates, explicit missing/hasMass evidence, source marker                                                                                                                 | Provider-native units remain unverified; aggregate mass establishes no individual part ownership or engineering correctness                                                                                   |
| Inspector (`inspector.py`)                                                         | Sanitized bounded display/evidence projection, section outcomes/counts, capture freshness, recognized feature categories                                                                               | Removes provider IDs; caps features at 100, parts/bodies at 200 and parameters at 16. It cannot be the identity-preserving graph input                                                                        |
| Selection (`onshape/selection.ts`, `ai/models.py`, `ai/selection.py`)              | Browser accepts at most one FACE/EDGE reference (opaque, 1–1024 characters, no C0/DEL controls), or explicit clear; backend AI receives only FACE/EDGE/none/unknown                                    | No server reference-ingestion endpoint today. A browser observation proves neither entity membership in acquired geometry nor owning feature/part/body, dimensions, surface/curve type or topology continuity |
| Modify discovery and safe-write evidence                                           | Separate narrow pinned microversion reads; strict immutable baseline, exact definition digests and evidence modes; owner/session/expiry-bound opaque target handles                                    | Requires existing write gate, approval and narrow supported shapes. Those records are authority-bearing, not general read-only graph evidence; no graph may synthesize or replace them                        |
| Learning checks and tutor                                                          | Deterministic requirements over Inspector; PASS/FAIL/WARNING/UNVERIFIED; session-bound signed check result evidence                                                                                    | Lesson-specific observations are not a generic dependency model or engineering certification; incomplete lists cannot establish arbitrary absence                                                             |

The normalized read snapshot is the least invasive identity-preserving input. Its
raw request-local provider documents must not be copied into the graph. Existing
transport bounds are 2 MiB per response, JSON depth 32 / 100,000 values, at most
2,000 features/parts/bodies and 20,000 returned topology entries per body; feature
parameters have separate limits. No additional acquisition is needed.

The following must remain unknown: feature-to-face/face-to-feature causal
ownership, selection ownership, part-to-body correspondence, unsupported parent /
child or geometric dependencies, geometric/design intent, topology correspondence
across edits, assemblies/mates, arbitrary feature health, inferred constraints,
manufacturability, stress/safety correctness and general engineering validity.
Feature order is evidence of ordering only, never dependency or creation.

## Purpose and integration boundary

The backend-only `forge_api.model_graph` package supplies a deterministic structural
projection beneath the ID-removing Inspector. It has no registered route, model
tool, provider transport, database, persistence, cache or UI. Existing Modify,
Learn, Inspector, AI, auth and recovery execution paths are unchanged.

```text
Existing authenticated acquisition -> normalized Snapshot
  -> evidence_from_snapshot(snapshot, expected_context, ...)
  -> immutable GraphEvidence -> build_graph -> ForgeModelGraphV1
  -> GraphQuery / explicit private deterministic serialization
```

`graph_from_snapshot` combines the adapter and builder. The caller must obtain
one already-authorized request-local snapshot and supply its independently expected
workspace context. The adapter does not fetch anything. An integration test runs
the existing synthetic authenticated four-read pipeline and proves graph creation
adds zero reads. `GraphEvidence` is an internal closed contract, not a browser
request or a new authorization capability.

## Versioned schema and nodes

The schema version is `forge-model-graph-v1`. Capture, provenance, nodes and edges
are frozen Pydantic models with strict types, forbidden extras and immutable tuples.
Validation also rechecks nested instances built with model_construct/model_copy.

| Node kind        | Identity and metadata                                                                                                   | Availability meaning                                                     |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| workspace        | Existing document/workspace provider references                                                                         | Unknown existence: the context is a validated request reference          |
| part_studio      | Existing element provider reference within that workspace                                                               | Unknown existence: no element name/type is invented from launch metadata |
| feature          | Opaque feature ID, returned index, safe name/provider type, optional suppression, positive custom-namespace observation | Available returned inventory entry; missing metadata remains null        |
| part             | Opaque part ID, safe name/body type, optional mesh flag and own reported microversion                                   | Available returned entry, not an inferred body mapping                   |
| body             | Opaque body ID/type; optional returned topology counts                                                                  | Available returned entry; absent/empty topology counts remain unknown    |
| selection        | Current observation slot; selected/clear/unknown/unavailable; FACE/EDGE category and separate reference availability    | Available describes a browser observation, not CAD ownership             |
| entity_reference | At most one bounded opaque FACE/EDGE selection reference                                                                | Browser-reported reference only, not an acquired face/edge topology node |

Node IDs are SHA-256 over canonical typed identity tuples, with an `fmg1` kind
prefix. Provider IDs remain opaque strings; names never resolve identity. Workspace
identity is scoped by provider/document/workspace; other inventory nodes also by
element. Selection-reference IDs additionally include capture time and entity type:
matching reference strings across captures do not establish topology continuity.
Part and body ID namespaces stay distinct even when their provider strings match.
The existing normalized namespace flag cannot distinguish an absent namespace from
an explicitly empty one. Its false value therefore projects to unknown, not a proven
standard feature; only a positive custom-namespace observation is retained as true.

Feature parameters, descriptions, part numbers, raw definitions, mass/units,
FeatureScript, provider state maps and approval-bearing Modify records are not
copied into V1. This is intentionally a structural foundation, not a replacement
for their existing evidence or authority contracts. Unsafe/oversized display text
is omitted whole using the existing display policy; identifiers and malformed
structural evidence reject rather than being repaired. No fallback name is invented.

## Edges and unknown relationships

Each edge has a stable typed ID, source/target node IDs, provenance reference and
explicit availability. The supported relationships are only:

| Relationship | Allowed endpoints                         | Meaning                                                                                                                            |
| ------------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| CONTAINS     | workspace -> Part Studio                  | Requested context association, explicitly UNKNOWN; not proof the requested object exists                                           |
| CONTAINS     | Part Studio -> returned feature/part/body | Membership observed in that normalized read                                                                                        |
| PRECEDES     | feature -> feature                        | Relative provider ordering between consecutive returned entries; not immediate tree adjacency when incomplete and never dependency |
| REFERENCES   | selection -> entity_reference             | Current browser observation references that opaque provider value                                                                  |

The canonical graph contains only those edges. It has no feature-created-face,
OWNED_BY, part-to-body, feature-health, constraint, assembly, mate, design-intent or
geometric dependency edge. Unavailable ownership is represented by absent ownership
relationships, not a fabricated false or a singleton-count inference. The requested
workspace/Part Studio association remains explicitly unknown even if some reads
succeed; no server-side element metadata lookup has been added.

## Provenance and context/freshness

Five fixed provenance records cover context, features, parts, bodies and selection.
Every node and edge references the applicable record. Records bind:

- exact standard-stack provider origin and document/workspace/element context;
- capture completion timestamp, provider API/schema version and default configuration;
- request-scope, normalized-workspace-read or browser-observation evidence mode;
- complete / partial / unavailable / unknown state, section status/code and returned count;
- reported microversions only where present; feature completeness, rollback,
  serialization and skew observations remain explicit, including missing versus false.

For parts/bodies, complete means the bounded returned collection was projected
without truncation, not a new provider completeness/absence guarantee. For features,
provider isComplete is preserved directly. Suppression null is never coerced to false.
Mass contributes a revision-conflict check in the snapshot adapter only; its marker
never fills missing structural-section markers and no mass facts enter V1.

Cross-context evidence, conflicting markers, known skew/mismatch, stale selection or
stale capture flags, and differing per-source capture bindings reject. The optional
expected capture timestamp lets an owner reject an older request result. Terminal
feature is known only for an explicitly complete feature list with an explicit
end rollback marker (or its concrete end index); otherwise the query returns None.

Even matching microversions do not make sequential workspace reads atomic. Freshness
and consistency stay `captured_unverified` / `unverified`. No wall-clock TTL,
current-head check or invented per-section observation time is introduced. Context
and time on normalized documents come from the server capture envelope, not an
independent provider echo. The graph cannot detect trusted code forging/rebinding
an unversioned document into that envelope; it is not a cryptographic receipt.
Callers retain the existing final ownership/session checks and lifecycle invalidation.

## Selection boundary

`SelectionObservation` mirrors the existing at-most-one FACE/EDGE/clear contract;
unsupported entity kinds, occurrence paths, malformed/control-bearing references
and multi-selection reject. The observation is explicitly associated with the same
capture context/time and is never assigned a guessed provider microversion.

`selection_from_category` accepts the existing backend categories. FACE/EDGE
without a reference yields partial selection evidence and no entity-reference node;
clear, unknown and unavailable stay distinct. An internal caller can represent an
already-normalized bounded browser reference, but this phase adds no reference
transport endpoint or browser message handling. No production path starts sending
or logging those references, and postMessage checks are unchanged.

No selection reference is resolved against parts, bodies or features. Equal strings,
a single feature/body/part or a recognized feature type cannot establish ownership,
measurements, surface/curve type, dependency or geometry correspondence.

## Determinism, serialization and queries

Node collections use fixed type order; features preserve returned order; parts and
bodies sort by opaque provider ID. Edges use a fixed relation/source/target order.
No random IDs, current time, display-name identity, set iteration order, provider
call or model output contributes facts. Canonical private JSON uses sorted keys,
fixed separators, ASCII escaping and explicit schema version. Round-trip bytes and
outputs under different Python hash seeds are tested. Noncanonical deserialized
node/edge order rejects instead of being silently rearranged.

`GraphQuery` provides get_node, nodes_of_type, ordered_features, terminal_feature,
selection, selected_nodes, neighbors, has_fact and relationship_evidence. Query
order is deterministic; the view and its lookup map are immutable. `has_fact`
returns true only for a matching AVAILABLE edge, and `neighbors` traverses only
AVAILABLE edges in either direction. An AVAILABLE relationship may be treated as
a graph fact within its recorded provenance and relationship meaning; ordering
still does not prove dependency, nor a browser reference CAD ownership.

`relationship_evidence(relation, source, target)` explicitly returns matching Edge
objects, including availability and provenance. UNKNOWN is recorded evidence state,
not a proven CAD fact. The UNKNOWN workspace → Part Studio association remains in
the graph and is visible through this helper, but yields false from `has_fact`
and no default neighbor traversal. False, an empty query result or an absent edge
does not prove that the CAD relationship (or its inverse) is false.
Likewise an empty selected_nodes result does not conflate clear, unknown,
unavailable or category-only observations; inspect selection state/reference state.

Serialization intentionally preserves private internal provider references and
safe CAD display metadata. It contains no OAuth/session credentials, database URLs,
raw payloads or hidden reasoning, and is not automatically logged, persisted or
sent to a browser/model. Future AI consumers must apply their own minimized,
authorized, bounded context projection; these bytes are not a public AI prompt API.

## Validation, resource limits and security

Duplicate IDs within a provider namespace, conflicting context identities, invalid
capture times/IDs/types/Booleans/counts, outcome/data contradictions, dangling or
duplicate edges, impossible endpoints, missing/extra/speculative relationships and
mixed provenance fail closed. The graph validator recomputes typed identity and
structural edge coverage; serialization and queries revalidate bypass-constructed
instances. Fixed validation messages do not interpolate provider values.

Limits reuse the existing normalized read contracts:

| Resource                          | Maximum          |
| --------------------------------- | ---------------- |
| Features / parts / bodies         | 2,000 each       |
| Selections / selection references | 1 / 1            |
| Nodes                             | 6,004            |
| Edges                             | 8,001            |
| Feature/part/body provider ID     | 256 characters   |
| Opaque selection reference        | 1,024 characters |
| Safe display text                 | 256 UTF-8 bytes  |
| Returned per-body topology count  | 20,000           |
| Canonical serialized graph        | 8 MiB            |

Collections are checked before projection; extra-large evidence rejects without
truncating identity or order. Source records and all per-node fields are bounded;
raw provider trees and unbounded parameter collections are never traversed/copied.
Edge validation uses a node-ID set, avoiding a node-by-edge Cartesian scan.
The maximum supported graph is exercised by an automated test, not a performance
benchmark or a claim about arbitrary provider model sizes.

This package grants no access or write authority. It adds no scopes, FeatureScript,
new service/configuration, database migration, public inspection route, model tool,
CSRF exception, or approval/recovery mechanism. CAD writes remain default OFF.
Deployment files, production serving/launcher and existing subsystem code remain
unchanged. Tests use invented fixtures and mocked transports only; live Onshape
validation has not occurred.

## Future consumers and explicit non-goals

Phase 13 should adopt one read-only consumer behind the existing ownership/lifecycle
checks, using graph queries for inventory/order while retaining evidence and
selection uncertainty. Review graph equivalence with current Inspector outputs and
collect separately authorized real read-only validation before wider adoption.

Do not expand into autonomous CAD, generic graph queries, graph persistence/public
inspection, whole-system migrations, selection ownership inference, a dependency
DAG, assemblies/mates, topology tracking, new geometry APIs or engineering
certification. Selection-aware Modify and all future writes require separate
acquisition/authority designs; this graph cannot replace a pinned approved baseline.

## Original automated gate and review — 2026-10-22 (historical)

Started from clean main and fetched origin/main at
`8d72cafc5cf94b79a7e38e15f17e4bc7b37817c1`; work is isolated on
`phase12/forge-model-graph`. At this historical gate, Phase 12 was not yet merged
and no live Onshape validation was claimed. Locked npm/uv installs passed without
dependency or lockfile changes.

| Gate                                           | Final result                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| Focused model-graph tests                      | 124 passed, including maximum graph and existing four-read capture integration        |
| `make format` / `make lint` / `make typecheck` | PASS                                                                                  |
| `make test`                                    | 827 frontend and 2,609 API tests passed; all 42 opt-in PostgreSQL cases ran, no skips |
| `make build`                                   | PASS; existing Vite bundle-size advisory, unchanged frontend output                   |
| `make test-e2e`                                | 594 passed across Chromium, Firefox and WebKit                                        |
| `make migration-check`                         | PASS against an independently disposable synthetic PostgreSQL database                |
| `make compose-check`                           | PASS; existing local database service untouched                                       |
| `make audit`                                   | PASS; no known dependency vulnerabilities reported                                    |

An earlier browser run encountered four synchronized WebKit Learning timeouts
(590 other tests passed), and an overlapping full-test command failed. Final
complete runs passed without changing browser/frontend source, timeouts, retries,
assertions or test selection. No failure was skipped or check weakened.

The disposable database was health-checked and migrated before the integration
gate, then removed in cleanup. No migration, test fixture or recovery operation
touched the pre-existing database. No real OAuth, AI or CAD call was performed.

Review confirms changes are limited to the new graph package/tests and architecture,
roadmap, security and Phase 12 documentation. Deployment configuration/serving,
OAuth/session/CSRF, frontend, provider acquisition, safe-write/recovery code,
lockfiles and migrations are unchanged. The temporary runner, logs and browser
artifacts are ignored and excluded from the commit. Source review found no raw
provider-document access, authority/I/O imports, model-selected graph facts or new
public endpoint. Secret-pattern review passed; this is not a security certification.

## Narrow query review fix — 2026-10-22 (historical, before final merge)

Started with a clean `phase12/forge-model-graph` at
`ee827e191dc8e9c85085363686b68990dcf2f442`, matching the fetched remote branch.
Fetched main remained `8d72cafc5cf94b79a7e38e15f17e4bc7b37817c1`.

The query boundary now treats only AVAILABLE relationships as graph facts and
traversable neighbors. Explicit `relationship_evidence` inspection preserves the
UNKNOWN context association and its provenance. Regression coverage checks both
traversal directions, available containment/order/selection references, and missing
or reversed evidence. No graph schema, identity, builder or serialized tree changed.

The focused suite passed **127 tests**. The complete review gate passed
`make format`, `make lint`, `make typecheck`, `make test` (**827 frontend / 2,612 API**),
`make build`, `make test-e2e` (**594 Chromium/Firefox/WebKit**),
`make migration-check`, `make compose-check` and `make audit`. All **42 PostgreSQL
cases** ran; no tests were skipped, retried or weakened in this review gate.
The only build advisory is the existing unchanged frontend bundle size.

The isolated synthetic PostgreSQL database was healthy, migrated and removed after
verification; the pre-existing local database was untouched. The review fix changes
only query behavior, graph tests, this document and factual roadmap status. No
deployment, OAuth, CAD-write, recovery, dependency or lockfile changes are included.
Phase 11's merge is established by PR #5's merge commit in main; real Onshape human
validation is not recorded as complete. The deployment foundation is merged but
has no live Railway provisioning, production secrets, OAuth cutover or hosted
validation. At this historical review, the Phase 12 branch was not yet merged and
no live Onshape validation was claimed.
