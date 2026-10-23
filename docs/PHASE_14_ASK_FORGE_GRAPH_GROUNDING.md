# Phase 14 — graph-grounded Ask Forge

Implementation and automated verification only. Human read-only validation is
pending. No live Onshape read/write validation, deployment or merge is performed.
CAD writes remain OFF. Railway remains unhosted.

**AUTOMATED GATE PASSED — READY FOR HUMAN READ-ONLY VALIDATION.** The earlier
browser-gate failure is resolved by a fresh complete run after the user confirmed
machine availability. Main remains unchanged; human validation is pending.

## Starting state and scope

Started from clean `main`, matching fetched `origin/main`, at the required
`204725ce141df6f2cccdaa7241f618b0989a7f62`. Work is isolated on
`phase14/ask-forge-graph-grounding`; do not merge automatically.

Before this phase, normal Ask Forge used `acquire_bound` → normalized Snapshot →
legacy `inspect` → minimized canonical facts → model fact-ID selection → server
answer. Direct Inspector already used the Phase 13 graph projection. Tutor,
Learn/Check my step, Modify, safe-write/recovery, OAuth, deployment and database
schema/migrations are outside this migration and remain unchanged.

## Architecture and lifecycle

```text
explicit send → authenticated/CSRF-checked strict Ask Forge request
  → one existing acquire_bound(validated request WorkspaceReference)
  → at most four sequential GET reads → normalized Snapshot
  → final acquisition session/grant check
  → private pure _inspect_graph(Snapshot, independent request reference)
      → one ForgeModelGraph + GraphQuery
      → graph-backed Inspector feature projection + same-Snapshot rich evidence
      → bounded human-readable structural facts
  → existing minimized evidence/canonical catalog (65,536-byte total bound)
  → final agent session/grant/disconnection check
  → existing model fact-ID selection → revalidation → server-owned answer
```

The expected context is the validated request `value.context`, never copied from
`snapshot.context`. Acquisition, its read gate and final lifecycle checks are
unchanged. Rejected/discarded acquisitions bypass graph construction. Cancellation
prevents subsequent model use; the existing synchronous read may finish its bounded
GETs in its worker thread. A graph is request-local, never cached or persisted.

The narrow private helper returns the public Inspector projection beside its
validated query, so graph construction is shared rather than repeated. Direct
Inspector still uses its unchanged public `inspect_graph` entry point. Complete
inventory/order/count/completeness/metadata correspondence is checked before display
caps. Rich feature evidence joins by exact opaque provider ID within this Snapshot,
never name, lexical ID or index alone; duplicate names cannot swap parameters.
Parameters, parts/bodies/metadata, physical evidence, source and capture proof retain
their existing projection. Structural names come from checked sanitized graph labels
with the same missing-name fallback. Neither public schema nor UI changes.

`GroundedCad` is an internal carrier of the Inspector and already minimized facts;
the graph/query stays inside the pure projection. Existing plain-Inspector `project`
callers, including Tutor, retain their previous behavior. The HTTP Ask Forge route
always uses `ground`; it has no legacy successful-Snapshot fallback.

## Canonical facts and limits

- `order_1_2`, etc.: at most 19 adjacent AVAILABLE PRECEDES relationships within
  the existing 20-feature AI cap. Statements say that one numbered captured modeled
  feature appears before another in returned order. Names use JSON quoting.
- `terminal_feature`: emitted only when the unchanged `terminal_feature()` query
  proves an explicitly complete feature list with end rollback evidence, and that
  terminal is within the AI-visible cap. No terminal is inferred from the last
  visible feature, partial list, missing completeness or missing rollback evidence.
- `order_semantics`: server-owned evidence semantics explaining that returned
  order establishes no dependency, ownership or parent-child relation; selection
  references establish no ownership and missing relationships prove nothing.
  This fixed caveat also accompanies normal grounded answers as an uncertainty.

AVAILABLE order and established terminal statements are observed/VERIFIED facts,
not engineering validation. UNKNOWN relationships yield no verified relationship;
absence yields no negative CAD fact. PRECEDES is returned order, not dependency,
execution order, causality, consumption or topology. Incomplete captured order
does not prove immediate full-tree adjacency. There is no dependency DAG.

All graph facts count toward the existing 65,536-byte evidence bound, alongside
the unchanged feature/part/body and four-parameter minimization. Overflow fails
with `evidence_unavailable`; caveats are never silently removed to fit. Fact
generation is bounded and adjacent, not an all-pairs expansion. A known terminal
beyond feature 20 is deliberately withheld. Public answer/evidence caps are unchanged.

No graph JSON, node/edge IDs, provider/context IDs, provenance or serialization
bytes reach either model provider or browser. CAD names remain quoted untrusted
data under fixed policy. Only canonical ID selection can produce verified CAD
statements; the model cannot author new verified facts or grant write authority.

## Preserved boundaries and failures

Selection facts and server-owned selection answers remain authoritative. A FACE
or EDGE has unknown owning feature/part/body even with one part, one body, one
feature or a terminal feature. No topology join or reference transport is added.

Recognized modification requests retain one authorized inspection and a deterministic
read-only capability answer: zero model requests, zero CAD writes, no inferred
controlling dimension, proposal or Modify invocation. Graph adoption grants no
autonomous CAD authority, new tool, scope, FeatureScript or public graph endpoint.

Graph validation or graph/Snapshot correspondence failure discards evidence with
the fixed unavailable shape and existing `evidence_unavailable` handling. No rejected
Snapshot is reinterpreted through legacy structure; no validation input or exception
text is returned/logged. Existing authorization-specific stops remain distinct,
including `read_permission_required` and final-agent `session_expired`. There is no
new persistence, database mutation or migration; existing token refresh behavior
remains unchanged. Normal reads add zero provider requests and perform at most the
existing four GETs. CAD writes remain OFF.

## Automated verification

For the original implementation, frozen `npm ci` and `uv sync --locked` passed
without dependency/lockfile changes. The later recovery audit updates are recorded
below.
The focused Phase 14 suite passed **50 tests**. The full `make test` passed
**827 frontend / 2,762 API tests**, including all **42 PostgreSQL cases**, with
no skips. Existing AI, Tutor, Learn/Check my step, Modify and recovery tests passed;
Modify tests are unchanged. Strict type checking covers 170 source files.

| Gate                                         | Result                                             |
| -------------------------------------------- | -------------------------------------------------- |
| `make format`, `make lint`, `make typecheck` | PASS                                               |
| `make test` with isolated PostgreSQL         | PASS: 827 frontend / 2,762 API, no skips           |
| `make build`                                 | PASS; existing unchanged bundle-size advisory      |
| `make test-e2e`                              | PASS: 594 cases, 198 in each browser, zero retries |
| `make migration-check`, `make compose-check` | PASS; no migration drift                           |
| `make audit`                                 | PASS; npm/Python report no known vulnerabilities   |

The final frontend run uses the existing `VITEST_MAX_WORKERS=2` environment
override after an initial default-worker run hit four five-second timeouts. An
initial temporary runner incorrectly forced ENVIRONMENT=test, causing 21 existing
development-only diagnostic cases to reject; restoring the normal development
setting fixed the runner. All 69 diagnostic tests and the final full API suite
then passed. No assertion, timeout, test selection or product code was weakened.

The initial four-worker browser run was stopped after timeouts: 508 passed,
22 failed, four interrupted and 60 not run. The subsequent complete 594-case suite
ran with one worker and zero retries: **589 passed / 5 failed**, with no unexecuted
cases. Chromium passed 197/198, Firefox passed 198/198 and WebKit passed 194/198.

Those five failures were in unchanged browser tests:

- Chromium `design.spec.ts:172`: material-performance median frame time was
  50.1 ms; the unchanged requirement is under 35 ms.
- WebKit `ai.spec.ts:90`, 380 px: Design prompt visibility timed out.
- WebKit `auth.spec.ts:5`: page fixture setup timed out.
- WebKit `bracket.spec.ts:86`: Beginner control interaction timed out.
- WebKit `bracket.spec.ts:198`: cooldown control remained disabled before timeout.

Host load was high/fluctuating during those attempts; this is context, not proof
of the cause of every earlier failure. The user subsequently confirmed that the
machine was available. A fresh complete **`make test-e2e` passed all 594 tests in
3.7 minutes**, using the unchanged normal four-worker configuration, all three
browsers and zero retries. Chromium, Firefox and WebKit each passed 198/198,
including the earlier performance/timeout cases. No source, assertion, time budget,
retry policy or test selection changed between the failed and successful runs.
The complete automated gate is now green. Human read-only validation remains
pending and was not executed. Local verification logs are retained in ignored
`.cache/phase14/`; generated browser artifacts are also ignored.

The disposable synthetic PostgreSQL instance was health-checked and migrated,
then removed after database verification. The pre-existing local database remains
healthy and untouched. Scope review covers six backend files, one new test file
and six documentation files. Changed-file secret-pattern review found no matches.
All tests use invented fixtures and mocked CAD/model transports; no live provider
validation or production readiness is claimed.

## Browser recovery and fresh audit

The continuation request described an uncommitted implementation, but inspection
found a clean `phase14/ask-forge-graph-grounding` at
`6b17074bfd12b1ad3d96563e92a79c5da39e29cd`, already matching its upstream and remote.
The exact initial modified-file list was `[]`; the untracked-file list was `[]`.
The 13 implementation files remained present. No reset, branch switch, stash,
clean, discarded work, history rewrite or merge was performed.

The original failure log and actual test bodies/helpers were inspected. The
failure log referenced error contexts and traces, but those original artifacts
were no longer present after subsequent Playwright runs; no original screenshot
was available. The classification does not claim inspection of missing artifacts.

| Project  | Exact original test title                                                     | Spec and failure location                                                                                                             | Relation to Phase 14                                                                                      |
| -------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Chromium | Phase 6.5 material idle and interaction performance sample                    | `design.spec.ts:172`; assertion at `:226`: median 50.1 ms, required <35 ms                                                            | UI Lab material rendering and requestAnimationFrame sampling; no Phase 14 frontend/backend path           |
| WebKit   | Phase 6 explicit send, grounded evidence, accessibility and overflow at 380px | `ai.spec.ts:90`; Design prompt visibility at helper `:63`, called at `:94`; 5 s expectation within 30 s test budget                   | Related Ask Forge consumer UI, unchanged and mocked; failure before send, with no graph backend execution |
| WebKit   | sign in, account verification, disconnect, reconnect, and logout              | `auth.spec.ts:5`; page fixture setup exceeded 30 s before test body                                                                   | Synthetic auth routes; no Phase 14 graph path                                                             |
| WebKit   | correct step: Forge verifies it and learner completion stays separate         | `bracket.spec.ts:86`; Beginner radio check at helper `:75`, called at `:89`, exceeded 30 s test budget                                | Unchanged Learn setup and mocked check-step routes; no Phase 14 graph path                                |
| WebKit   | cooldown is explained, throttles the control and never auto-retries           | `bracket.spec.ts:198`; assertion at `:208`: aria-disabled stayed true after the 6500 ms wait; 5 s expectation within 30 s test budget | Unchanged frontend timer over a mocked 429 response; no Phase 14 graph path                               |

All spec paths above are under `tests/e2e/`. No stale repository-owned browser
services needed termination; unrelated user processes were left alone. A fresh
disposable PostgreSQL instance used the repository's pinned image, a synthetic
database and ephemeral storage, and was health-checked and migrated. Browser
fixtures use mocked API routes rather than this database.

The exact five scenarios passed targeted reruns in their original projects:
**1 Chromium / 4 WebKit**. The targeted Chromium median was **16.7 ms** against
the unchanged **<35 ms** requirement. Assertions, timeout limits, test bodies,
retry policy and Playwright configuration remained unchanged. All five are
classified **C: NONDETERMINISTIC** because outcomes changed without source
changes. This establishes neither a host-load root cause nor reproduction on
baseline. Per the requested decision rule, all five targeted passes proceeded
directly to the complete browser suite; no baseline worktree was needed or created.
That pre-dependency-update complete `make test-e2e` passed **594/594** with the
normal four workers and zero retries.

The fresh audit then found two development-only transitive dependencies requiring
updates:

- ESLint's `eslint-plugin-react-hooks` dependency Zod: **4.6.5 → 4.6.7** in
  `package-lock.json`; [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)
  lists 4.6.6 as the first patched release.
- pip-audit's CacheControl file-cache dependency filelock: **4.0.9 → 4.2.1** in
  `apps/api/uv.lock`; the [maintainer advisory](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8)
  lists 4.2.1 as the fix for CVE-2026-112940.

Only those two existing lock entries changed; package manifests, dependency count,
Phase 14 product code, tests and browser requirements did not change. Frozen
`npm ci` and `uv sync --locked` installed the updated locks. Both dependency audits
pass without suppressions. After both updates, a fresh complete gate passed:

- **50** focused Phase 14 tests.
- Formatting, lint and strict typing, including **170** mypy source files.
- **827** frontend and **2,762** API tests, including all **42** PostgreSQL cases;
  zero skips.
- Build, migration drift and Compose checks; the existing bundle-size advisory
  remains unchanged.
- **594/594** browser tests in **4.0 minutes**, **198** per browser, using the
  unchanged four-worker configuration, zero retries and zero skips.
- npm and Python dependency audits: zero known vulnerabilities.

Recovery changes are limited to the two lock entries and this verification
record. There is no Phase 14 product or test change during recovery. Recovery
logs and the initial file manifest are retained in ignored
`.cache/phase14-recovery/`. The recovery's disposable database was removed after
verification; the pre-existing database was left healthy and untouched. Human
read-only validation remains prepared but unexecuted, with CAD writes OFF and
Railway unhosted.

## Human read-only validation plan — prepared, not executed

Use the local HTTPS development environment and a real workspace Part Studio with
writes OFF. Human validation is a separate later step; do not run it automatically.

| Case               | Human action/question                                                         | Required observation                                                       |
| ------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| A: normal model    | Sketch → Extrude → Fillet; “What features are in my model and in what order?” | Correct modeled inventory and returned order                               |
| B: order           | “What comes before the final fillet?”                                         | Captured returned-order relationship, with no dependency claim             |
| C: terminal        | “What is the final feature?”                                                  | Fillet only if completeness/end rollback establishes it; otherwise unknown |
| D: dependency trap | “Does the extrude depend on the sketch?”                                      | Returned order is known; dependency is not established                     |
| E: suppression     | Ask whether the final fillet is active/suppressed; compare with Onshape       | Matches explicitly captured suppression, with no correctness claim         |
| F: selection       | Select a FACE; “What feature owns this face?”                                 | Ownership remains unknown                                                  |
| G: write boundary  | “Make the extrude wider.”                                                     | Read-only capability reply, no proposal/model call/CAD change              |
| H: empty Studio    | Switch to an empty Part Studio; ask what features exist                       | Successful empty inventory, no stale prior model                           |

Record human observations separately from automated results. No live CAD write,
write enablement, document modification or Phase 9 validation is part of this plan.

## Remaining limitations

Reads remain sequential/non-atomic, captured-unverified and unpinned. PRECEDES is
returned order, not dependency. No feature ownership is inferred, including
ownership of a selected FACE or EDGE. There is no dependency DAG, topology
continuity guarantee or engineering correctness claim. Tutor/Learn/Check my step/Modify
are not graph-migrated by this phase; direct Inspector remains Phase 13. Existing evidence caps may withhold a
terminal outside the first 20 features. No new CAD authority exists. Railway remains
unhosted. Automated mocks do not establish general provider conformance, live model
quality or production readiness. Human read-only validation remains pending.
