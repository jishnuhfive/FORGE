# Phase 15 — graph-grounded Learn Tutor

**COMPLETE — HUMAN READ-ONLY VALIDATION PASSED — READY FOR FINAL MERGE REVIEW**

Implementation on `phase15/tutor-graph-grounding`. Started from clean synchronized `main` at
`500e114b7356b90499988633dd7811c49b94937c`. No merge or deployment is included.
CAD writes remain OFF. Railway remains unhosted.

Final real-Onshape human read-only validation passed all seven scenarios, as
reported by the user. The agent did not independently execute those human checks.
This closeout changes documentation only; the validated implementation remains
`cd9cf86709db4c8841a9a7325bc81833f1016660`. Phase 15 is not yet merged and no
production-readiness claim is made.

## Implementation history

| Commit                                     | Message                                         |
| ------------------------------------------ | ----------------------------------------------- |
| `21640495f9998e9e1a7903c01b94fc6294ac07d7` | `feat: ground Learn tutor with ForgeModelGraph` |
| `1f65c85e11e96e56b59c2e221e500a8c6db4bdad` | `fix: narrow Tutor relationship guard`          |
| `7f357ab65dd8c825e1cf7fcf6fd791bea03c839c` | `fix: preserve Tutor structural answers`        |
| `cd9cf86709db4c8841a9a7325bc81833f1016660` | `fix: ground Tutor relationship answers`        |

## Scope and architecture

Phase 15 migrates **only learner-requested Tutor CAD grounding**. Direct Inspector
is the Phase 13 consumer, Design Ask Forge is the Phase 14 consumer, and Learn
Tutor is the Phase 15 consumer. Modify remains unmigrated. Check my step remains
deterministic and unchanged, including its signed, session-bound evidence tokens.

```text
explicit Tutor send → authenticated, origin/CSRF-checked strict request
  → validate lesson/step and optional signed check token
  → existing provider decides whether current CAD is needed
  → existing acquire_bound(TutorRequest.context): at most four sequential GETs
  → final acquisition session/grant revalidation
  → ground(the same Snapshot, independent TutorRequest.context, correlation)
  → shared graph-backed Inspector + bounded canonical structural facts
  → existing project(..., "none") + combined application-context byte check
  → final session/grant/disconnection check → existing strict tutor model
  → revalidation → server-owned check/CAD rows and presentation guards
```

`GroundedCad`, `ground` and `project` reuse Phase 14 semantics; no competing graph
projection exists. `GraphQuery.ordered_features()` owns the modeled inventory/order;
the shared projection checks full graph/Snapshot correspondence before caps and
joins rich evidence by exact opaque provider ID within that Snapshot. Duplicate
display names cannot swap parameters or state. Graph construction is pure and adds
zero provider requests. Nothing is cached, persisted, polled or refreshed in the
background. No new selected FACE/EDGE Tutor grounding is introduced.

The route supplies the independently validated request context, never
`snapshot.context` as its own expected context. A rejected graph does not fall
back to legacy Snapshot interpretation. Graph construction/validation/correspondence
failure returns fixed evidence-unavailable handling without exception details or
CAD evidence reaching the answer model. Session loss, read permission/access,
admission in-progress and throttle failures retain distinct safe handling.
Tutor now forwards CAD admission/provider throttle stops before graph construction,
discarding any preceding partial evidence.

## Facts, bounds and unknowns

The same feature state, four-parameter-per-feature projection and rich Snapshot
observations remain available. The existing 20-feature cap bounds structural facts
to at most 19 adjacent AVAILABLE PRECEDES statements, one `order_semantics` fact,
and one `terminal_feature` only when the existing query proves complete feature-list
and end rollback evidence and the feature is within the AI cap. Partial, unknown
or empty inventories never invent a terminal; even a proven terminal beyond the
visible cap is withheld. A successful empty Part Studio reports zero features,
parts and bodies, without retaining a previous context's inventory.

PRECEDES is returned feature-list order, **not dependency**. It establishes no
parent/child, sketch ownership, consumption, driving, geometric ownership,
causality or topology relationship. UNKNOWN stays unknown; a missing relationship
proves nothing. There is no dependency DAG, feature ownership inference, topology
continuity guarantee or engineering-correctness claim. Reads remain
sequential/non-atomic and captured-unverified.

CAD names remain JSON-quoted untrusted data under fixed policy. Model/browser
payloads contain no graph JSON, node/edge/provider/context IDs, OAuth/session data
or provenance internals. The 65,536-byte evidence bound includes graph facts and
caveats; Tutor additionally requires the combined application/check context and
projected CAD payload to fit that same bound. Overflow fails closed without
dropping semantics. Strict model output, six fact IDs, six check refs, twelve
observations, eight unknowns and six notes remain unchanged. An overfull unknowns
list fails unavailable rather than truncating check limitations or graph caveats.

## Presentation and educational usefulness

No Tutor UI redesign is included. Ask Forge disclosure, composer, What Forge
observed, Still unknown, Latest check, next action, reasoning question and progress/
error handling retain their existing contracts. The shared ordering caveat always
appears in Still unknown after a graph-backed read, regardless of model selection.
Internal graph terminology is not normal learner-facing copy.

The deterministic presentation guard separates learner relationship intent from
model-authored relationship claims. Explicit dependency/ownership questions still
receive server-owned safe teaching, even if the model says only yes. Ordinary
educational questions containing use, input, references, connected or based on retain normal
teaching. Each of the three model prose fields is checked independently: clearly
general CAD teaching is allowed. Only explicit learner relationship intent selects
the relationship explanation. Incidental named/current-model dependency,
ownership, driving, consumption or input prose is discarded by field; safe teaching
can remain. An unsupported main explanation receives fixed conservative copy,
without turning an unrelated question into a dependency lesson.
General wording cannot exempt a later specific-model claim or infer an absent
dependency from a missing relationship. Exact closed lack-of-proof caveats are
allowed; an arbitrary occurrence of unknown is not a bypass.

Only already-projected feature display names identify model-specific prose; they
are escaped literal data, never relationship proof or regex/policy syntax. Generic
CAD type names do not hijack general education. No additional evidence, provider
read, model/browser field or authority is added. This remains a conservative
presentation safeguard, not complete natural-language understanding or a dependency
classifier. Questions without CAD inspection keep their existing behavior.

Simple inventory/order and preceding-feature questions now have deterministic
server-owned primary answers from the existing canonical catalog, independent of
model prose or selected IDs. A closed statement grammar decodes JSON-quoted
`feature_N` names by captured index. Counts require the verified `features` fact;
arrows and preceding answers require the matching verified adjacent `order_*`
facts. No names or ordinal positions create a missing order link. UNKNOWN/missing
links yield an inventory plus an order limitation, not a negative relationship.
Duplicate names are indexed for inventory and ambiguous for name-only lookup.
Complete zero count is a legitimate empty studio; partial inventory does not
invent total count or terminal. Whole entries may be omitted with explicit copy
to fit the unchanged public explanation bound; evidence limits are unchanged.

For the closed question form “Does [feature] depend on [feature]?”, the primary
answer also includes their exact verified adjacent order without requiring the
model to select an `order_X_Y` ID. All candidate pairs are matched against whole
literal names, optionally JSON/single quoted, case-insensitively. A unique pair
and the matching verified canonical order statement are both required. Duplicate
names, ambiguous quotes or question delimiters, missing/malformed feature facts,
missing/UNKNOWN order and nonadjacent pairs keep the existing conservative lesson.
No presentation code queries graph internals, infers order from indices alone or
chains adjacent facts into transitive order. Either question direction keeps the
canonical order direction. Dependency stays unconfirmed, with an explicit caveat;
other relationship forms, including ownership, keep the existing safety response.
Long escaped names remain whole and quoted; optional general teaching is omitted
if needed to preserve the unchanged explanation bound and dependency limitation.

For final-feature questions, server presentation uses the canonical terminal
statement when proven, otherwise the existing fixed unknown explanation. Incidental
model terminal claims cannot redirect unrelated questions. Existing verdict,
dimension and strength/safety guards still apply. Canonical observed rows, signed
check authority, freshness and ordering limitations are unchanged.

## Check authority and staleness

There remain two separate sources:

- **Check findings:** only a verified signed token can establish their exact
  wording, PASS/FAIL/WARNING/UNVERIFIED status, outcome and historical capture time.
- **Current CAD observations:** only this explicit authorized acquisition can
  establish their canonical statements and newer capture time.

Graph facts never enter the token or checker. Tutor cannot change learner
verification/completion, step requirements, check outcome or investigation
resolution. Forged, altered, foreign-session and wrong-step tokens still reject;
authentic expired tokens retain their existing ignored behavior. Tokens are never
sent to the model. A check may predate later edits; a newer CAD read does not
reinterpret it. Latest check remains historical until another explicit **Check my
step**, with the existing visible recheck note. Check my step remains the only
correctness authority.

## Preserved authority and lifecycle

Explicit sends, authenticated sessions, exact Origin/CSRF checks, lesson/step
validation, three client exchanges, one request in flight, cooldown, hourly cap,
current provider configuration, cancellation and session/grant revalidation remain.
No passive AI calls or Tutor conversation persistence is added. No OAuth scope,
CAD write, FeatureScript, Modify invocation, proposal/approval UI, deployment or
database migration is added. Requests such as “Make the fillet bigger” receive the
fixed read-only teaching response with zero model requests and zero CAD reads or
writes. The narrow Tutor imperative screen now recognizes “make” for this boundary.
No shared Design write routing changes. Phase 15 adds no new CAD authority.

## Automated verification

The focused tests are in `apps/api/tests/test_tutor_graph.py`, using invented CAD
and mocked transports only. They cover same-Snapshot acquisition/four GETs,
independent context and self-validation rejection, correspondence failure without
fallback, query inventory/duplicate names, AVAILABLE/UNKNOWN/missing relationships,
terminal completeness/caps, dependency prose and general teaching, separately
sourced historical check status, tokens, lifecycle loss, no-inspection behavior,
deterministic write boundaries, empty context transitions, malicious names,
identity minimization, existing guards, byte bounds and cancellation.

The initial implementation at `21640495f9998e9e1a7903c01b94fc6294ac07d7`
passed **69 focused Phase 15 tests**, followed by **226 existing
Tutor/token/Check-my-step/Phase 14 tests**. Frozen `make setup` (`npm ci` and
`uv sync --locked`) passed without dependency or lockfile changes. The complete
repository gate passed on this branch:

| Gate                                   | Actual result                                                |
| -------------------------------------- | ------------------------------------------------------------ |
| `make format`, `make lint`             | PASS                                                         |
| `make typecheck`                       | PASS; strict TypeScript/Python, 171 Python files             |
| `make test`                            | **869 frontend / 2,831 API passed**, no skips                |
| All PostgreSQL cases in full API suite | **42 passed**, isolated synthetic database                   |
| `make build`                           | PASS; existing unchanged bundle-size advisory                |
| `make test-e2e`                        | **633 passed**, 211 per Chromium/Firefox/WebKit, 4.9 minutes |
| `make migration-check`                 | PASS; no new upgrade operations/schema drift                 |
| `make compose-check`                   | PASS                                                         |
| `make audit`                           | PASS; npm and Python report no known vulnerabilities         |

Browser tests used the unchanged normal four workers and zero retries. No
assertions, timeouts, thresholds, evidence limits or authority boundaries were
weakened. Existing Check-my-step/token tests, Design Ask Forge, direct Inspector
and Modify implementations/tests remain unchanged. The new suite also exercises
both existing model adapters and distinct CAD admission/throttle stops.

The disposable synthetic PostgreSQL container was health-checked and migrated
before the full suite, then removed; existing local database/data were untouched.
Final review covers four backend files, one new test file and seven documentation
files. Credential-pattern review found no matches; no browser artifacts or secrets
are included. Verification logs stay under ignored `.cache/phase15/`.
No real OAuth, model-provider or Onshape call is part of automated validation.
Passing tests does not establish production readiness or security certification.

## Relationship-guard precision review — 2026-10-23

Started with a clean `phase15/tutor-graph-grounding` at required HEAD
`21640495f9998e9e1a7903c01b94fc6294ac07d7`; fetched `origin/main` remained
`500e114b7356b90499988633dd7811c49b94937c`. No merge is included.

The original combined question/prose regex treated ordinary use, input, references,
connected and based-on wording as relationship intent. The initial 82-case
reproduction had 34 failures, including normal questions and general teaching.
The refined pure presentation helper now distinguishes question intent from
model-authored claims as described above. It reads only already-projected feature
names; there are no acquisition or model-payload changes. Explicit relationship
questions and unsupported current-model claims still receive the same fixed safe
explanation. General teaching is not itself added to verified observations.

The new `test_tutor_relationship_precision.py` passes **100 cases** covering normal
questions with actual graph-backed projection, explicit relationship questions,
all three model prose fields, general dependency/sketch-input teaching, disguised
specific claims, literal name escaping and generic feature labels. All **69 Phase
15 tests** pass. Their existing general-teaching case retains every safety
assertion and now additionally checks exact model-prose preservation; the original
general explanation plus unknown caveat is separately covered by the new suite.
Existing Tutor/token and Phase 14 graph suites pass **169 tests**.

The precision-fix gate passed frozen installs, formatting, lint, strict typing
(173 Python files), **869 frontend / 2,931 API tests**, including all **42 PostgreSQL
cases**, with no skips; build (unchanged bundle-size advisory); **27 focused Tutor
browser tests** across Chromium/Firefox/WebKit with unchanged four workers and zero
retries; migration drift, Compose and dependency audits (no known vulnerabilities).
The disposable synthetic PostgreSQL instance was healthy, migrated and removed;
existing local database/data were untouched. Logs stay in ignored
`.cache/phase15-precision/`.

Graph semantics, Check my step, signed tokens, CAD acquisition, OAuth, Modify,
write authority, Tutor UI, deployment, database/migrations and evidence limits are
unchanged. No CAD writes, live CAD/model-provider validation or Railway deployment
were performed during this automated review. Human read-only validation was still
pending at that stage. The subsequent human failures, repairs and final passing
record are preserved below.

## Live human validation failure and structural repair

**Human validation Test 1 initially FAILED.** The user reports that real Learn →
Ask Forge was asked exactly “What features are in my current model and in what
order?” in a Part Studio containing **Sketch Gate → Extrude 1 → Fillet 1**, all
active. Canonical graph observations were correct, but the primary answer and next
action were incorrectly replaced by the fixed dependency lesson. This is a
presentation regression, not evidence that graph acquisition/order was wrong.

The exact implementation path was `guard_relationships(question, all three prose
fields, cad_names)` → one boolean → unconditional replacement of all prose with
`RELATIONSHIP_EXPLANATION` / `RELATIONSHIP_ACTION`. The original pre-guard live
model text was not supplied and Tutor does not persist conversations. No claim is
made about its exact wording. Controlled tests use the exact reported question,
three active features and a specific unsupported dependency sentence in each
model field. All three reproduced the erroneous dependency replacement before
the repair. These are synthetic reproductions, separate from the human report.

The completed repair separates learner relationship intent from incidental prose
rejection and adds the bounded canonical structural presentation described above.
The original four uncommitted files were preserved when work resumed; no reset,
checkout or discarded work was used. Work remained on `phase15/tutor-graph-grounding`
above `1f65c85e11e96e56b59c2e221e500a8c6db4bdad`; main remained
`500e114b7356b90499988633dd7811c49b94937c`. No merge is included.

The repair gate passed **46 structural/live-regression cases**, **100 relationship
precision cases**, all **69 Phase 15 cases**, and **226 existing Tutor/token/check/
Phase 14 cases**. Existing safety assertions were retained: fixed relationship
answers explicitly ask relationship questions, and additional non-relationship
cases require field rejection without a topic change. General-teaching cases ask
educational questions explicitly. No safety assertion, timeout or evidence bound
was weakened to obtain a pass.

Frozen installs, formatting, lint and strict typing (175 Python files) passed.
The complete `make test` passed **869 frontend / 2,977 API tests**, including all
**42 PostgreSQL cases**, with no skips. Build passed with the unchanged bundle-size
advisory. Focused Tutor browser verification passed **27 cases**, nine per
Chromium/Firefox/WebKit, with the unchanged four workers and zero retries.
Migration drift, Compose and both dependency audits passed; no known vulnerabilities
were reported. The health-checked, migrated disposable synthetic database was
removed, leaving the existing local database/data untouched. Logs remain under
ignored `.cache/phase15-structural/`.

Scope review covers three Tutor backend files, three test files and six current
documentation files. Graph semantics, acquisition/read counts, checks/tokens,
OAuth, Modify, CAD-write authority, UI layout, database/migrations, deployment,
dependencies/lockfiles and evidence limits remain unchanged. No generated browser
artifacts or credential-pattern matches were included. No live CAD read/write,
model-provider repair validation or Railway deployment was performed.

At completion of that repair, the automated gate was green and the implementation
was ready to **restart human read-only validation from Test 1**. The initial human
failure remains part of this record. Later human results are recorded below;
automated tests alone did not establish a human pass.

## Human Test 3 functional failure and relationship answer repair

After the structural repair at `7f357ab65dd8c825e1cf7fcf6fd791bea03c839c`, the
user reports **rerun Test 1 PASSED** and **Test 2 PASSED**. Test 1's initial failure
and repair remain recorded above. These are user-reported human observations,
not independent live checks repeated by the agent.

For Test 3 the user asked exactly “Does Extrude 1 depend on Sketch Gate?” in the
reported **Sketch Gate → Extrude 1 → Fillet 1** CAD. The fixed general dependency
lesson did not invent a relationship, but omitted the independently available
canonical Sketch Gate-before-Extrude 1 fact. **Test 3: SAFETY PASS / FUNCTIONAL
VALIDATION FAIL.** Human validation stopped at this point.

The relationship repair started from the required clean synchronized branch HEAD
`7f357ab65dd8c825e1cf7fcf6fd791bea03c839c`; fetched main remained
`500e114b7356b90499988633dd7811c49b94937c`. It reuses the existing canonical
feature/order decoder and adjacent-fact validator described above. The answer
keeps the requested relationship unconfirmed and independently states that
“Sketch Gate” comes before “Extrude 1” in the returned feature order. Reverse
questions preserve that same order without proving or disproving dependency.
Fallbacks and all graph/read/check/token/write/UI/evidence boundaries remain.

The focused synthetic reproduction failed before repair in all 15 combinations
of question direction/quoting/case and unsafe model prose field. It does not
capture or claim the exact live model output. New dependency-grounding tests also
cover missing/UNKNOWN/unverified order, malformed IDs/statements/feature facts,
duplicate/ambiguous/literal names, nonadjacent pairs, ownership safety, long escaped
names within existing bounds and the real HTTP path with mocked transports and
four GETs. Existing safety assertions are retained; expected server-owned primary
copy now includes relevant verified order for supported dependency questions.

The automated repair gate passed **41 new dependency-grounding / 46 structural /
100 precision / 69 Phase 15 / 226 existing Tutor/token/check/Phase 14 cases**.
Frozen installs, formatting, lint and strict types (176 Python files) passed.
The complete repository test gate passed **869 frontend / 3,018 API tests**,
including all **42 PostgreSQL cases**, with no skips. Build passed with the
existing unchanged bundle-size advisory. Focused Tutor browser tests passed **27
cases**, nine per Chromium/Firefox/WebKit, with unchanged four workers and zero
retries. Migration drift, Compose and both dependency audits passed; no known
vulnerabilities were reported. No assertion, timeout, threshold or bound was
weakened. The health-checked, migrated disposable synthetic PostgreSQL container
was removed; the pre-existing local database/data were untouched.

Scope and credential-pattern review passed for two Tutor presentation files,
four test files and six documentation files. Graph/PRECEDES semantics, provider
acquisition/GET counts, checks/tokens/authority, OAuth, Modify, CAD writes, Tutor
UI, database/migrations, deployment, dependencies/lockfiles and evidence limits
remain unchanged. No secrets or generated browser artifacts are included. No live
CAD/model-provider validation or Railway deployment was performed. Logs remain
ignored under `.cache/phase15-relationship-answer/`.

At completion of the relationship repair, the automated gate was green and human
Test 3 rerun and remaining validation were pending. The final human results are
recorded below. CAD writes remain OFF, and no merge is included.

## Final real-Onshape human read-only validation — PASSED

All observations in this section are **user-reported human observations** from
real Onshape, not checks independently executed by the agent. Forge CAD writes
remained **OFF** throughout. The primary disposable Part Studio contained
**Sketch Gate → Extrude 1 → Fillet 1**, with **one part**. An empty Part Studio was
also used. No merge, deployment or production-readiness claim follows from this
validation.

### Test 1 — structural inventory

Question: “What features are in my current model and in what order?”

The initial human run failed because the relationship presentation guard replaced
the inventory answer with a dependency lesson even though canonical graph evidence
was correct. The defect was repaired in
`7f357ab65dd8c825e1cf7fcf6fd791bea03c839c`. The human rerun reported **3 modeled
features**, **Sketch Gate → Extrude 1 → Fillet 1**, correct returned order and no
dependency claim.

**TEST 1 — PASS AFTER REPAIR**

### Test 2 — preceding feature

Question: “What comes before Fillet 1?”

The reported answer was:

> "Extrude 1" comes before "Fillet 1" in the returned feature order.

The canonical observation appeared separately. No dependency,
ownership, parent-child, causality or driving claim was made.

**TEST 2 — PASS**

### Test 3 — dependency boundary

Question: “Does Extrude 1 depend on Sketch Gate?”

The initial human run was safety-correct but functionally incomplete: Forge
refused to infer dependency but omitted the relevant verified order fact. That
issue was repaired in `cd9cf86709db4c8841a9a7325bc81833f1016660`. On the human
rerun, Forge said “I can't confirm that relationship.” It verified that “Sketch
Gate” comes before “Extrude 1” in the returned feature order and explained that returned
order does not establish dependency. No dependency, ownership, parent-child,
driving or causal relationship was claimed.

**TEST 3 — PASS AFTER REPAIR**

### Test 4 — terminal feature

Question: “What is the final feature?”

The reported answer was:

> The terminal feature in the complete captured feature list is the third feature, "Fillet 1".

The answer used completeness-backed terminal evidence rather than merely the
last visible feature.

**TEST 4 — PASS**

### Test 5 — signed check versus current CAD

The user ran **Check my step** and obtained **Latest check: Verified**. Without
running another check, the user manually suppressed Fillet 1 in the disposable
CAD, then asked: “Is Fillet 1 active or suppressed now?”

The latest deterministic check remained **Verified**. Tutor explicitly stated
that only Check my step can change that result, correctly reported Fillet 1 as
currently suppressed, and distinguished the old sketch check from current fillet
state. Newer CAD evidence did not silently update the old signed check result.
This validates separation between historical signed deterministic check evidence
and current Tutor CAD observations; signed check-token authority is unchanged.
The user restored Fillet 1 afterward. These manual CAD actions were performed by
the user; Forge CAD writes remained OFF.

**TEST 5 — PASS**

### Test 6 — write boundary

Question: “Make the fillet larger for me.”

The reported fixed response was equivalent to: “I can explain and suggest, but I
never change your model. You build it yourself in Onshape, and Check my step is
what verifies it.” There was no Modify flow, proposal, approval UI or CAD mutation.
Check my step remained the verifier.

**TEST 6 — PASS**

### Test 7 — empty Part Studio and context switch

The user switched from the populated Part Studio to the empty Part Studio, where
Onshape displayed only its default Origin/planes, and asked: “What features are in
my current model and in what order?”

The reported answer was “This Part Studio has no modeled features.” The canonical
observation was “The captured Part Studio contains 0 features.” No Sketch Gate,
Extrude 1, Fillet 1, stale prior inventory, fake terminal feature or relationship
inference appeared. Onshape's default geometry is not modeled-feature inventory
and does not contradict the zero modeled-features result.

**TEST 7 — PASS**

Final human status: **COMPLETE — HUMAN READ-ONLY VALIDATION PASSED — READY FOR
FINAL MERGE REVIEW**. Phase 15 is not yet merged.

## Documentation-only closeout verification

The closeout started from a clean, synchronized `phase15/tutor-graph-grounding`
at `cd9cf86709db4c8841a9a7325bc81833f1016660`. Fetched `origin/main` remained
`500e114b7356b90499988633dd7811c49b94937c`; the starting comparison was **0 behind /
4 ahead**. Only this record and `docs/ROADMAP.md` change. The validated
implementation tree, tests, dependencies and lockfiles are unchanged.

`make lint`, `make typecheck` (176 Python files plus strict TypeScript) and
`make audit` passed; npm/Python reported no known vulnerabilities. Focused tests
passed **256 cases**: **69 Tutor graph / 100 relationship precision / 46 structural
presentation / 41 dependency grounding**. No test requirements were altered.
No full API/browser rerun was performed for this documentation-only closeout;
the unchanged implementation's prior full verification is preserved above.
Verification logs remain ignored under `.cache/phase15-human-closeout/`.

## Future Learn/Tutor UI work — outside Phase 15

The user reports that Learn currently feels visually crowded. Future UI work may
make Ask Forge a more dominant or floating assistant entry point, possibly a
floating Forge/chat bubble that smoothly expands into a chat surface. This is a
possible direction, not an implemented or approved Phase 15 UI change.

Future work should consider full smooth animations, narrow-panel responsive
behavior, keyboard accessibility and a `prefers-reduced-motion` fallback.
“Still unknown” may later become a compact Limits/details disclosure. The full
Learn/Tutor UI overhaul remains future work; this closeout implements none of
these UI changes.

## Remaining limitations

Reads remain sequential/non-atomic. PRECEDES is returned order, not dependency;
there is no dependency DAG, feature ownership inference, selected-face/edge Tutor
grounding, topology continuity guarantee or engineering-correctness claim. Check
my step remains the only correctness authority. Signed check-token authority is
unchanged; Tutor CAD observations cannot update a check result. Modify is not
graph-migrated by Phase 15. No new CAD authority is granted. CAD writes remain
OFF. The full Learn/Tutor UI overhaul remains future work. Railway remains
unhosted. Human validation passed after the recorded repairs; this does not
establish production readiness.
