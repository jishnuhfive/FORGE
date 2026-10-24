# Phase 15 — graph-grounded Learn Tutor

**IMPLEMENTED — AUTOMATED GATE PASSED — HUMAN READ-ONLY VALIDATION PENDING**

Implementation on `phase15/tutor-graph-grounding`. Started from clean synchronized `main` at
`500e114b7356b90499988633dd7811c49b94937c`. No merge or deployment is included.
CAD writes remain OFF. Railway remains unhosted.

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

A conservative deterministic guard examines the learner's question and all three
model prose fields for dependency/ownership/relationship language. It replaces
that prose with fixed general teaching and an investigation suggestion, retaining
only server-owned CAD observations. It catches even a bare yes to a dependency
question and negative dependency claims inferred from absent relationships.
General education remains explicit: a dependency in CAD means using another
feature's profile or geometry as an input; captured order does not establish that
relationship in this model. This is a presentation safeguard, not a natural-language
dependency classifier. It may replace otherwise safe teaching with less-specific
teaching. Questions without CAD inspection keep their existing behavior.

For final-feature language, server presentation uses the canonical terminal
statement when proven, otherwise a fixed explanation that the final feature is
unestablished. It does not repeat model-invented terminal prose. Existing verdict,
dimension and strength/safety guards still apply.

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

The branch's focused Phase 15 suite passed **69 tests**, followed by **226 existing
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

## Human read-only validation plan — prepared, not executed

Use the existing disposable Mounting Bracket/test workspace with CAD writes OFF.
Open Learn → Ask Forge. Keep all validation read-only; no Gate A/B, real Modify,
CAD mutation or Railway deployment is required.

1. **Structural inventory:** ask “What features are in my current model and in
   what order?” Expect graph-backed captured inventory/order.
2. **Returned order:** ask “What comes before Fillet 1?” Expect returned-order
   observations, without dependency implications.
3. **Dependency trap:** ask “Does Extrude 1 depend on Sketch Gate?” Expect general
   teaching separated from order observations; no verified dependency claim.
4. **Terminal:** ask “What is the final feature?” Expect a terminal only when
   completeness proves one; partial evidence must remain unknown.
5. **Check/current CAD separation:** run Check my step, then ask about current CAD
   in the disposable context. If the model has changed since the check, expect the
   historical Latest check outcome/time to remain until another explicit check.
6. **Write boundary:** ask “Make the fillet larger for me.” Expect the fixed
   learner-action/read-only response, no proposal, Modify or CAD change.
7. **Empty studio/context switch:** ask about current features in an empty Part
   Studio, then switch back and repeat. Expect legitimate zero inventory and no
   stale names, counts or terminal from the previous context.

## Remaining limitations

Reads remain sequential/non-atomic. PRECEDES is returned order, not dependency;
there is no dependency DAG, feature ownership inference, selected-face/edge Tutor
grounding, topology continuity guarantee or engineering-correctness claim. Check
my step remains the only correctness authority. Modify is not graph-migrated by
this phase. No new CAD authority is granted. The full UI overhaul remains future
work. Railway remains unhosted. Human read-only validation is still pending.
