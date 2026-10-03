# Planned AI agent

## Status and ownership

Phase 0 implements no model calls, SDK, agent runner, tools, or fake AI responses.
Codex builds Forge; Forge's eventual runtime AI will be a separate backend service
using the OpenAI Responses API. Its key remains backend-only, and `OPENAI_MODEL`
selects an explicitly evaluated model at deployment time. No default model is
hardcoded or implied by an empty environment variable.

## Intended loop

```text
UNDERSTAND -> INSPECT -> PLAN -> APPROVAL -> EXECUTE
    -> RE-INSPECT -> VALIDATE -> REVISE -> REPORT
```

1. **Understand:** extract functional and dimensional requirements, explicit units,
   inventory, materials, manufacturing capability, uncertainties, and risk scope.
2. **Inspect:** use authorized read-only tools to establish current CAD state.
3. **Plan:** present operations, assumptions, constraints, expected outcomes, and
   unresolved questions as a user-facing plan.
4. **Approval:** obtain approval bound to that plan and inspected document version.
   Model text cannot grant approval. Material revisions require fresh approval.
5. **Execute:** pass approved operations through server-owned tool gates and budgets.
6. **Re-inspect:** retrieve actual CAD state and verify operation outcomes.
7. **Validate:** run deterministic, unit-aware checks with evidence and tolerances.
8. **Revise:** propose corrections; stop or ask for input when limits are reached.
9. **Report:** distinguish completed actions, warnings, failures, uncertainty, and
   unverified checks. A fabricated success message is never acceptable.

## Function contracts and restrictions

Use direct function calling with `strict: true`; object schemas reject additional
properties and represent optional arguments explicitly. Strict shape enforcement
does not establish permission, engineering validity, or accurate units. The backend
must independently parse and validate every tool argument. [Official function
calling guide](https://developers.openai.com/api/docs/guides/function-calling)

Planned allowlisted operations include `inspect_part_studio`, `create_mounting_plate`,
`create_motor_mount`, `create_hole`, `create_extrusion`, `create_slider_mate`, and
`get_mass_properties`. These names describe intended high-level contracts, not
implemented tools or promises of specific Onshape API support. Verify each operation
against official APIs, workspace permissions, and real CAD evidence before enabling it.

There will be no `execute_arbitrary_http_request`, `execute_raw_onshape_api_request`,
or `run_arbitrary_shell_command`. Model-authored code will not be an execution path.
Only the server can select a known adapter operation and its authorized target.
Each CAD-changing tool requires authentication, object-level authorization, schema
validation, unit validation, finite numeric bounds, sanitized operation logging,
and result verification. Unit conversion and calculations live in deterministic
code; the model cannot waive them.

## Budgets, streaming, and failure semantics

Before live use define finite limits for model turns, tool calls, writes per plan,
tokens/cost per user, total wall time, per-request timeout, retries, and concurrency.
Choose limits using evaluation evidence rather than letting the model increase them.
The backend checks budget and cancellation before every call and write. Use bounded
backoff for recoverable reads; uncertain writes require reinspection, not blind retry.

Stream coarse user-facing statuses from the backend, such as inspecting, awaiting
approval, executing, validating, blocked, and complete. Status is derived from actual
work. Do not stream/persist private chain-of-thought. Stop with a clear reason when
credentials expire, targets change, verification fails, or budgets are exhausted.

## Deterministic validation

| Result     | Meaning                                                            |
| ---------- | ------------------------------------------------------------------ |
| PASS       | Implemented deterministic check passed against identified evidence |
| WARNING    | Check completed but a documented caution or margin remains         |
| FAIL       | Check found a supported constraint violation                       |
| UNVERIFIED | No applicable check, insufficient evidence, or unsupported physics |

Validation records should include check name/version, inputs with units, measured
values, tolerance, evidence references, and status. The language model may explain
records but cannot choose or overwrite their results. Future manufacturing checks
may cover printer envelopes, dimensional requirements, part availability, and
supported clearances. Strength, fatigue, load safety, and motion claims need explicit
supported calculations and evidence; absent those, report UNVERIFIED.

Forge v1 supports education, makers, and low-risk prototyping. Results are design
assistance, not professional engineering certification. Do not develop harmful-device
or weapon-specific capabilities. Add adversarial evaluations for prompt injection,
unit confusion, stale approvals, fabricated results, repeated writes, and quota bypass
before enabling real execution.
