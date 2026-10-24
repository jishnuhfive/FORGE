# Phase 14 — graph-grounded Ask Forge

**COMPLETE — HUMAN READ-ONLY + UX VISUAL VALIDATED — READY FOR FINAL MERGE REVIEW**

The user reports that real Onshape human read-only validation **PASSED all eight
scenarios** and the post-polish targeted real-Onshape UX visual recheck **PASSED
all seven scenarios**. These are user-supplied observations, not live validation
independently performed by this agent. They validate the scoped Phase 14 behavior;
a full product UI redesign and final overall visual design remain future work.
CAD writes remain OFF; Railway remains unhosted. The branch is not merged, and
main remains unchanged. Do not merge automatically.

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
The complete implementation automated gate was green. Human read-only validation
was still pending at that point. Local verification logs are retained in ignored
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
verification; the pre-existing database was left healthy and untouched. At that
recovery gate, human read-only validation remained unexecuted, with CAD writes OFF and
Railway unhosted.

## Human read-only validation — user-reported PASS

Before authorizing this polish, the user reported successful real Onshape
read-only validation of the implementation at
`f756564cf7818d3060adf09e5808105413cece45`. The observations below are supplied by
the user, not inferred from automated fixtures or independently repeated by this
agent. The user reaffirmed all eight PASS outcomes for this closeout. The validated
model was a disposable Part Studio containing **Sketch Gate → Extrude 1 → Fillet 1**,
with **CAD writes OFF**. These observations apply to the listed scenarios, not
general provider conformance or engineering correctness.

| Case                       | Question / setup                                           | User-reported observation                                                                                             | Result |
| -------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------ |
| 1: inventory/order         | “What features are in my model and in what order?”         | 3 modeled features: Sketch Gate → Extrude 1 → Fillet 1; order matched Onshape                                         | PASS   |
| 2: returned order          | “What comes before the final fillet?”                      | Extrude 1 correctly appeared before Fillet 1; relation remained feature order only                                    | PASS   |
| 3: terminal                | “What is the final feature?”                               | Fillet 1 correctly reported as the final/terminal feature                                                             | PASS   |
| 4: dependency boundary     | “Does Extrude 1 depend on Sketch Gate?”                    | No dependency claim; only Sketch Gate before Extrude 1 in feature order, with dependency explicitly unestablished     | PASS   |
| 5: feature state           | “Is Fillet 1 active or suppressed?”                        | Fillet 1 correctly reported active, matching Onshape                                                                  | PASS   |
| 6: selected FACE ownership | Select a real FACE; “What feature owns this face?”         | One selected face recognized; owning feature remained unknown; no ownership inference                                 | PASS   |
| 7: write boundary          | “Make Extrude 1 wider.”                                    | Stayed read-only: no Modify flow, proposal, approval UI or CAD mutation; no verified width-driving parameter invented | PASS   |
| 8: empty Part Studio       | “What features are in this model?” in an empty Part Studio | 0 modeled features / 0 parts / 0 bodies; no stale Sketch/Extrude/Fillet evidence                                      | PASS   |

No live CAD write validation, write enablement, deployment or merge is part of
this follow-up.

## Narrow UX presentation/navigation follow-up

Starting checks passed from a clean synchronized
`phase14/ask-forge-graph-grounding` at exactly
`f756564cf7818d3060adf09e5808105413cece45`; fetched `origin/main` remained exactly
`204725ce141df6f2cccdaa7241f618b0989a7f62`.

This is a display-only layer over the unchanged Answer contract. The original
canonical answer, fact IDs/statements/statuses and full `uncertainties` array are
retained. `ai/friendly.ts` recognizes exact server-owned statement grammar,
verified/unknown statuses and canonical feature positions. Duplicate IDs, duplicate
names at different positions, conflicting positions, unknown activity and unmatched
or qualified prose fail back to the current answer. No arbitrary model prose is
summarized into verified truth and no label-based identity join is introduced.

Recognized inventory, terminal, order, activity, dependency, selection-ownership and
read-only capability answers use concise wording. Dependency answers state the
limitation directly and report order only when an exact verified order fact is
present. Empty modeled inventory remains valid evidence. Its primary answer omits
irrelevant suggestions and zero-omission prose; optional guidance remains in details.
The existing broad-overview display grammar remains available as a fallback.

The primary answer shows a quiet **Limits** section only for relevant known limits:
order/dependency, selection ownership, parameter/unit evidence or engineering
validation. Unrecognized future limitations remain visible conservatively. Full
technical limits, canonical evidence, original full answer, capture time and any
secondary guidance remain available inside the initially collapsed **Evidence**
disclosure. It uses a native keyboard-operable button with expanded/control labels;
empty sections and rows are omitted. No safety data is removed from the API.

The shared Tabs primitive optionally follows its supplied workspace scroller.
One passive scroll listener queues at most one animation frame; it reads only
scrollTop and changes a visibility attribute only when needed. Downward travel of
48 px hides navigation; 16 px upward travel reveals it; within 24 px of the top
it stays visible. Direction changes reset accumulated travel, preventing tiny
alternating movement from flickering. Focus immediately reveals navigation and
keeps it visible while a tab is focused. Mode changes reset it to visible; cleanup
cancels pending work and removes listeners. CSS uses transform/opacity and keeps
the original layout space, with no height/top/margin animation. Reduced motion
disables the transition. The header, composer, typography, colors, spacing and
glass appearance are preserved. No new dependency is introduced.

GraphQuery, canonical graph evidence, provider identity joins, acquisition,
session/grant checks, write handling, Modify/Tutor/Learn/Check my step semantics,
OAuth, persistence, deployment and recovery are unchanged. CAD writes remain OFF.

### Follow-up automated verification

Frozen `npm ci` and `uv sync --locked` passed; this follow-up changes no dependency
or lockfile. Final verification passed on the final production code and tests:

| Gate                                                     | Result                                                                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Focused frontend/presentation/navigation                 | 83 passed                                                                                                     |
| Focused Phase 14 graph regressions                       | 50 passed                                                                                                     |
| Focused browser polish, refinement and performance cases | 51 passed across all three projects                                                                           |
| Formatting, lint and strict typecheck                    | PASS, including 170 mypy source files                                                                         |
| Full frontend suite                                      | 869 passed                                                                                                    |
| Full API suite with real disposable PostgreSQL           | 2,762 passed, including all 42 PostgreSQL cases; zero skips                                                   |
| Build, migration drift and Compose                       | PASS; existing bundle-size advisory remains                                                                   |
| npm/Python audits                                        | Zero known vulnerabilities                                                                                    |
| Complete normal browser suite                            | 633 passed in 5.8 minutes; 211 each in Chromium/Firefox/WebKit; four workers, zero retries, failures or skips |

The final unchanged synthetic material sample measured median frame times of
**16.7 ms Chromium / 16.66 ms Firefox / 17 ms WebKit**, each below the unchanged
**35 ms** requirement, with zero idle animations. These are localhost samples,
not live Onshape GPU or trackpad validation. Earlier attempts failed performance
or browser timing checks before the user confirmed machine availability; this
context does not establish a root cause for every failure.

The new Firefox fixture initially ran native keyboard checks after axe had opened
and closed a temporary page. Keyboard checks now run before that lifecycle, with
the same Enter/Space assertions and expanded-content accessibility scan. The first
complete run passed 624/633; its nine failures were existing refinement checks
expecting topology detail in the primary inventory. Those checks now assert the
compact primary counts, then verify the unchanged full body fact (including known
faces and unknown edges/vertices) and original answer in Evidence. No assertion
budget, threshold, browser worker/retry setting, required scenario or product
authority was weakened. The entire gate was rerun after these test updates.

Synthetic screenshots of inventory, dependency, empty inventory and hidden
navigation were visually inspected. Logs, traces and synthetic screenshots are
retained only in ignored `.cache/phase14-polish/`. Both owned disposable database
instances were health-checked, migrated and removed; the pre-existing database
remained healthy and untouched. Browser services were stopped after verification.
At that automated gate, the targeted human visual recheck was still pending; the
subsequent user-reported PASS is recorded below.

### Follow-up files

| Area                        | Files                                                                                                                                                                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Answer presentation         | `apps/web/src/ai/Analysis.tsx`, `apps/web/src/ai/friendly.ts`                                                                                                                                                                         |
| Navigation and styles       | `apps/web/src/App.tsx`, `apps/web/src/components/Shell.tsx`, `apps/web/src/styles.css`, `packages/design-system/src/components.tsx`, `packages/design-system/src/components.css`, `packages/design-system/src/useScrollNavigation.ts` |
| Frontend tests and fixtures | `apps/web/src/ai/Analysis.test.tsx`, `apps/web/src/ai/presentation.test.tsx`, `apps/web/src/ai/friendly.test.tsx`, `apps/web/src/ai/__fixtures__/phase14.ts`, `apps/web/src/components/ModeNavigation.test.tsx`                       |
| Browser tests               | `tests/e2e/ai.spec.ts`, `tests/e2e/refinement.spec.ts`, `tests/e2e/phase14-polish.spec.ts`                                                                                                                                            |
| Records                     | `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md`, `docs/ROADMAP.md`, `docs/SECURITY.md`, `docs/UI.md`                                                                                      |

No backend, dependency, composer, performance-test or Playwright-configuration file
changed during this polish. No generated artifact or detected secret is committed.

### Targeted human UX visual recheck — user-reported PASS

After the polish at `53ff762b30a358818e6f6b57a447aa7d9cbd1267`, the user reports
that the targeted visual recheck **PASSED in real Onshape**, with CAD writes OFF.
These observations were supplied by the human, not inferred from browser fixtures
or independently repeated by this agent.

| Case               | User-reported observation                                                                                                                                                                                             | Result |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| A: dependency      | Concise direct dependency limitation followed by verified feature order; visible Limits showed only the relevant dependency limitation; full technical caveats remained available inside initially collapsed Evidence | PASS   |
| B: feature state   | “Is Fillet 1 active or suppressed?” answered “Fillet 1 is active.” without generic unrelated warnings in the primary response                                                                                         | PASS   |
| C: face ownership  | Concise recognition of one selected face with owning feature unknown; relevant ownership limit shown; full unknown-selection detail remained inside Evidence                                                          | PASS   |
| D: inventory       | Concise Sketch Gate → Extrude 1 → Fillet 1 presentation without raw canonical wording in the main response                                                                                                            | PASS   |
| E: empty model     | Clean empty Part Studio presentation: no modeled features, no stale prior inventory and no irrelevant generic suggestions                                                                                             | PASS   |
| F: mode navigation | Design / Modify / Learn visible near the top; scrolling down hid the mode bar and scrolling up restored it; content did not jump and the sticky composer remained reachable                                           | PASS   |
| G: keyboard        | Keyboard focus on mode navigation kept it visible or revealed it                                                                                                                                                      | PASS   |

The observed dependency response was equivalent to:

> I can't confirm that Extrude 1 depends on Sketch Gate.
>
> I can verify that Sketch Gate comes before Extrude 1 in the feature order.

The observed selected-face response was equivalent to:

> I can see that one face is selected, but its owning feature isn't known yet.

This closes the scoped human UX visual gate. It does not establish a full product
UI redesign or final overall visual design. A larger UI overhaul remains future
work. No live CAD write validation, write enablement, deployment or merge is part
of this closeout.

## Documentation-only human-validation closeout

Starting verification found a clean synchronized
`phase14/ask-forge-graph-grounding` at
`53ff762b30a358818e6f6b57a447aa7d9cbd1267`, matching its fetched origin branch.
Fetched `origin/main` remained `204725ce141df6f2cccdaa7241f618b0989a7f62`, with
`0 3` left/right divergence (zero behind, three ahead). The existing commits are
preserved in order:

1. `6b17074bfd12b1ad3d96563e92a79c5da39e29cd` — graph-grounded Ask Forge.
2. `f756564cf7818d3060adf09e5808105413cece45` — audit/browser recovery record and lock updates.
3. `53ff762b30a358818e6f6b57a447aa7d9cbd1267` — narrow UX presentation/navigation polish.

The closeout changes this validation record and `docs/ROADMAP.md` only, plus the
Phase 14 status pointer in `docs/UI.md`: its explicit “pending targeted visual
recheck” statement would otherwise contradict the reported PASS. The validated
implementation, tests, dependencies, lockfiles, deployment, OAuth, database,
migrations, Modify, safe writes and recovery remain unchanged. Full browser/API/
database gates are retained above as implementation verification; this docs-only
closeout uses the requested lightweight checks. Final merge review is still
required; no merge is performed.

### Closeout check results

| Check                                                            | Result                                                                                                                      |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `make lint`                                                      | PASS: ESLint, Prettier, Ruff check and Ruff format check                                                                    |
| `make typecheck`                                                 | PASS: strict TypeScript and mypy, 170 Python source files                                                                   |
| `make audit`                                                     | PASS: npm/Python report zero known vulnerabilities; editable local API distribution excluded as configured                  |
| `uv run --frozen pytest tests/test_ai_graph.py -q` in `apps/api` | 50 passed                                                                                                                   |
| Focused frontend presentation/navigation                         | 83 passed across five files: `ai/friendly`, `ai/presentation`, `ai/Analysis`, `ai/chatLead` and `components/ModeNavigation` |

The focused frontend command uses the existing `VITEST_MAX_WORKERS=2` override.
No test requirement, assertion, timeout or configuration changed. No full browser,
API or database suite was rerun for this documentation-only closeout, and no
provider read, CAD write, hosting action or service startup was performed.

## Remaining limitations

Reads remain sequential/non-atomic, captured-unverified and unpinned. PRECEDES is
returned order, not dependency. No feature ownership is inferred, including
ownership of a selected FACE or EDGE. There is no dependency DAG, topology
continuity guarantee or engineering correctness claim. Tutor/Learn/Check my step/Modify
are not graph-migrated by this phase; direct Inspector remains Phase 13. Existing evidence caps may withhold a
terminal outside the first 20 features. No new CAD authority exists. Railway remains
unhosted. Automated mocks do not establish general provider conformance, live model
quality or production readiness. All eight human read-only observations and seven
targeted post-polish UX visual observations are user-reported PASS; a full UI
overhaul remains future work. Exact display grammar intentionally falls back for
unsupported question/evidence shapes.
