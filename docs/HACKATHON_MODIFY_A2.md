# Hackathon Modify A2 — human approval and execution API

A2 adds a transport over A1's deterministic executor. B1 still stops at the exact
authoritative preview. B2's browser implementation is future work. No CAD adapter,
OAuth configuration, dependency, frontend file, database table or migration changes.
Development and verification use synthetic CAD, mocked AI/provider transports and
isolated PostgreSQL schemas. **Real Onshape writes: ZERO. OAuth changes: ZERO.**

## Stable API for B2

All requests use the authenticated same-origin session and `X-CSRF-Token`, including
GET. Reuse the original Modify guard: exact Origin (or existing Referer/GET policy),
cross-site rejection, no query parameters, JSON POST bodies bounded to 8 KiB and
five seconds, duplicate JSON key rejection and closed schemas. Errors never echo
input. Responses have `Cache-Control: no-store`.

| Endpoint                                  | Body                 | Response                                                   |
| ----------------------------------------- | -------------------- | ---------------------------------------------------------- |
| `POST /api/modify/plan` (unchanged B1)    | `{context, request}` | Clarification or `{outcome: "plan", preview: PlanPreview}` |
| `POST /api/modify/plans/{handle}/approve` | `{"digest": "..."}`  | `application/x-ndjson` progress and final A1 result        |
| `POST /api/modify/plans/{handle}/cancel`  | `{}`                 | A1 `PlanResult`, state `cancelled`, all steps `skipped`    |
| `GET /api/modify/plans/{handle}`          | None                 | A1 `PlanResult` with only `state` and `operations`         |

The handle is exactly 43 URL-safe opaque characters from `preview.proposal_id`.
The digest is exactly 64 lowercase hexadecimal characters from `preview.digest`.
Approval accepts **only** `digest`; cancellation accepts **only** an empty object.
Extra operations, targets, context, feature identities, revisions, URLs, methods,
provider definitions, payloads, model content or approval flags reject. The browser
must show the complete ordered preview and send approval only after a human action.
Never substitute a new digest or approve the newest plan automatically.

Approval requires writes enabled and current user/session ownership, immutable-plan
integrity, exact digest, unexpired authority and A1's original atomic claim/fence.
Wrong/missing/malformed digest, wrong owner/session, expiry or reuse causes zero
additional writes. Schema errors are `400 invalid_request`, unauthenticated is
`401 session_expired`, guard errors are `403 csrf_failed`, disabled approval is
`403 write_disabled`, invalid/unowned/nonexistent handles are indistinguishably
`404 proposal_unavailable`, and claim/digest/expiry/reuse conflicts are bounded 409
errors. Oversized bodies are 413. Admission errors before streaming retain normal
HTTP codes. Once execution may have started, errors never claim a pre-dispatch
failure or expose exception text.

Cancellation and status remain available when an operator disables future writes.
They do not contact CAD, refresh OAuth, call any model or invoke approval.

## NDJSON contract

Each line is one strict, extra-forbidden JSON object followed by a newline. The
closed event discriminator is `progress | operation_result | result | error`:

```json
{"type":"progress","operation":1,"total":3,"stage":"checking"}
{"type":"progress","operation":1,"total":3,"stage":"executing"}
{"type":"progress","operation":1,"total":3,"stage":"verifying"}
{"type":"operation_result","operation":1,"total":3,"state":"verified_success"}
```

`operation` is 1-based; `1 <= operation <= total <= 5`. The closed stage enum is
`checking | executing | verifying`. The closed operation-result enum is
`verified_success | rejected_stale | write_failed | execution_uncertain | skipped`.
An operation emits at most three ordered stages and one outcome. Verification
success emits only after fresh deterministic verification, renewed authority and
the operation journal commit. An early failure can omit later stages. The failed
operation and every skipped suffix operation emit their outcomes after final
storage commits. No later operation starts before its predecessor verifies.

The terminal `result` contains the actual A1 `PlanResult`, plus its discriminator:

```json
{
  "type": "result",
  "state": "partial_failure",
  "operations": ["verified_success", "write_failed", "skipped"]
}
```

Status/cancel return this same shape without `type`. Plan states are
`pending | claimed | verifying | verified_success | partial_failure | rejected_stale |
write_failed | execution_uncertain | cancelled`. Journal operation states also allow
`pending | checking | executing | verifying` during status retrieval. A result event
from a completed approval has A1's terminal execution state. Cancellation returns
`cancelled` and one `skipped` entry for each operation, never `write_failed`.

An unexpected transport/persistence error after progress yields only:

```json
{ "type": "error", "code": "execution_uncertain" }
```

This means retrieve status; it is not an invented final `PlanResult`. If final
storage failed, status can still show `claimed`/`verifying` until the existing
150-second abandoned-claim rule yields uncertainty. No route resumes execution.

Hard bounds: **21 events, 512 UTF-8 bytes per line including newline, 8,192 bytes
per stream**. The queue is bounded to 21 entries and reserves space for the terminal
event. A presentation overflow drops progress without blocking/replaying writes.
The ordinary maximum five-operation stream delivers all 20 progress/outcome events
and its final result. B2 must validate the closed schemas and bounds, treat incomplete
streams as unresolved and use authenticated status retrieval. It must never retry
approval or infer success merely from HTTP 200, `executing`, an acknowledgement or
the end of a connection.

## Authority, cancellation and persistence

`cad_edits/plan_routes.py` reuses `routes.guard`, `enabled`, `Approve` and
`error_response`. The human approval handler is the sole product caller of
`plan_service.approve()`. Neither planner, model provider/tool, Design AI, tutor,
status, cancellation nor a scheduled/background initiator can approve. The
application-owned task continues **already human-approved** work; it never mints
approval. Runtime spies and retained B1 authority tests enforce the separation.

The immutable plan/digest, atomic conditional database claim, unique workspace and
user fences, auth lock order, provider dispatch boundary and verification logic
remain A1's. No duplicate executor or in-memory authority is introduced. Multiple
approvals produce exactly one winner. Cancellation takes the shared user lock and
conditionally updates only an owned, unexpired, intact pending record to cancelled.
Its status-only journal and fixed `write_proposal_cancelled` audit commit together.
It creates no fence, sends no provider request and performs no rollback. Repeated
cancel and cancel-after-claim return 409 rather than claiming another cancellation.

PostgreSQL tests race approval/cancellation simultaneously, force both lock-order
outcomes, and race the conditional storage updates with both transactions having
loaded pending without a process/user lock. Exactly one authority wins. Cancel wins:
zero writes and queryable cancelled state. Approve wins: normal one-use execution
and cancel cannot change the journal. A cancelled plan never has CAD writes.
Cancellation clears private plan bindings, retaining only closed statuses until the
original 15-minute operational purge. Existing fences never expire open.

## Execution and disconnects

A1's optional observer receives only frozen, server-created presentation models.
It has no target selection, approval, retry or state mutation interface. Callback
exceptions are swallowed; tests deliberately throw on every stage/outcome and
prove execution/verification still occurs once.

The route starts one application-owned execution task and waits for the first
event/admission error before constructing the stream. Strong task references and
shielding keep it independent of the consumer, including disconnect while waiting
for a stream event. Queuing never waits for the browser. Graceful application
shutdown drains approved tasks before closing CAD transports. A process crash is
not resumable: A1's durable claim/fence and abandoned-claim uncertainty remain the
fail-closed boundary. Lost connections never call approve again; B2 uses GET status.

The five supported operations and narrow evidence adapters are unchanged:
SET_SUPPRESSED, SET_UNSUPPRESSED, RENAME_FEATURE, SET_EXTRUDE_DEPTH,
SET_FILLET_RADIUS, in 1–5 ordered steps. Each mutation uses the preceding freshly
verified microversion: M0 → verified M1 → verified M2. A stale next step never
dispatches. A verified prefix remains applied on later failure (`partial_failure`).
A dispatched timeout, malformed acknowledgement or unprovable outcome yields
`execution_uncertain`, skips the suffix and retains A1's fence. There is **no
automatic retry, resume, rollback or undo write**. The unchanged whole-plan bounds
remain 25 seconds before dispatch and 30 seconds through verification; operations
do not renew the budget or approval expiry.

## Privacy and compatibility

Progress/status/cancel contain only fixed enums and bounded numbers/status arrays.
They expose no feature IDs, target identities, CAD context IDs, microversions,
workspace keys, records/bindings, raw definitions/parameters/provider payloads,
provider URLs, credentials, model content or audit records. The existing B1 preview
contains only its intentional opaque proposal handle, digest, expiry and exact
semantic display fields. Untrusted feature names must be rendered as text in B2.
Audit fields use fixed event/outcome codes and user association only; they contain
no prompt, feature label/name, quantity, provider content or plan payload.

All original Phase 9 routes and frontend files remain unchanged: capabilities,
targets, proposals, proposal approve/cancel/reconcile/status. B2 must use generalized
`plans` routes for A1 previews. It must never send an A1 plan to Phase 9's `proposals`
routes, expose internal executor/storage/provider methods as AI tools, approve from
planning/follow-up/status effects, or retry a lost approval.

## Verification and limitations

Focused tests: `tests/test_modify_plan_routes.py` and
`tests/test_modify_plan_routes_postgres.py`. The latter reuses repository
FORGE_TEST_DATABASE_URL isolation and owns only random test schemas. Retain A1, B1,
the entire Phase 9 safe-edit family, AI/provider/tutor, PostgreSQL and full repository
gates. No provider credentials or real CAD traffic are required.

Local operator dotenv must not fill intentionally unconfigured test settings. The
verification run disables dotenv/credential environment in a temporary pytest plugin,
matching the existing config-test isolation without changing operator files or
unrelated B1 tests. Operator credential files remain unchanged; committed artifacts
contain no credential values.

Real disposable Onshape validation of generalized operations remains pending after
B2 integration. Synthetic adapter conformance is not a live-provider proof, geometry
certification or production-readiness claim. Phase 9 Gate A remains proven; Gate B's
provider-side rejection audit remains deferred. CAD writes remain OFF by default.

## Final automated gate

After the final code change (the exact OpenAPI route allowlist was extended for
the three A2 routes), every authoritative gate was rerun on this tree:

| Gate                                                | Result                         |
| --------------------------------------------------- | ------------------------------ |
| A2 HTTP/task tests                                  | 73 passed, 0 failed/skipped    |
| A2 isolated PostgreSQL tests                        | 10 passed, 0 failed/skipped    |
| A1 executor and PostgreSQL regressions              | 170 passed (166 + 4)           |
| B1 planner                                          | 75 passed                      |
| All `test_safe_edit*.py` plus `test_ai_write.py`    | 858 passed                     |
| AI, Groq/OpenAI provider and tutor regressions      | 371 passed                     |
| All four PostgreSQL test families                   | 25 passed                      |
| Full backend, PostgreSQL enabled                    | 2,149 passed, 0 failed/skipped |
| Frontend, 32 test files, final run with two workers | 737 passed                     |
| ESLint and Prettier, including `make lint`          | Passed                         |
| Ruff check and format check                         | Passed; 140 formatted files    |
| TypeScript and strict mypy                          | Passed; mypy 136 files         |
| Production build                                    | Passed                         |
| Alembic upgrade/check in a fresh isolated schema    | No new upgrade operations      |
| Compose config and existing PostgreSQL health       | Passed; accepting connections  |
| npm audit                                           | 0 vulnerabilities              |
| pip-audit, editable project excluded                | No known vulnerabilities       |
| Changed-file security/privacy and whitespace review | Passed                         |

Frozen `npm ci` and `uv sync --frozen` passed without lockfile changes. The first
sandboxed npm install could not resolve the registry; its authorized network retry
passed. Audits both passed with network access. No dependency was added.

An early B1 run found one intentionally unconfigured-settings test inheriting local
dotenv. Final runs isolated configuration using a temporary pytest plugin that sets
`Settings.model_config["env_file"] = None` and removes settings environment overrides
in the child process, preserving the isolated test database setting. No operator
file or unrelated B1 test changed. The first full backend gate found only the route
allowlist omission; the full gate above follows its repair. No final test failure
or skip remains. Browser E2E was not rerun because no browser code changed.

Static authority review finds exactly one product reference to
`plan_service.approve`, in the explicit human approval handler. Runtime spies cover
AI/planner/tutor zero calls during A2, and retained B1 tests prove no approvals,
dispatches or fences from planning. Public serialization, injected authority fields,
all supported result states, cancellation audit rollback, callback failure and
disconnect/task continuation are covered. No secrets, live CAD IDs, private provider
payloads, debug artifacts, OAuth changes or schema migrations are included.

One incorrectly forwarded npm exec formatting command created an overbroad temporary
local log containing configured credential values. The command was stopped and the
log deleted. Exact-value checks found none of those values in the saved conversation
tool output or remaining verification logs. The corrected formatter invocation and
repository lint passed. No credential file, OAuth configuration or Git artifact
was changed by that command; no generated log is committed.
