# Submission creation + Learn UI

Frontend only. Design tab → **Create** mode (beside **Ask**). Request → engineering
brief → feature plan → human confirmation → approval → verified result → Learn.

## Boundaries

- The browser submits text and relays an approval. It builds no operations, holds no
  provider ids, and performs no CAD writes.
- All endpoint paths and wire shapes live in `apps/web/src/create/api.ts` (`BASE`,
  `requestCreation`, `approveCreation`, `creationStatus`). Changing an endpoint is a
  one-file change.
- The brief is not yet proven to match the user's numbers, so approval requires the
  human to tick a visible confirmation next to the brief. The approval body carries
  `brief_confirmed: true` and the plan `digest`; the server must still enforce both.
- Learn is read-only: text comes from `explain_plan`, is validated as
  `authority: "none"`, and no Learn control can call an execution endpoint.
- Success is shown only when the server result is `verified_success` and every step
  is `verified_success`. A transport failure after approval is shown as uncertain and
  is never retried; "Check status" is a GET.

## API contract the backend must satisfy (`/api/create/…`)

All requests: same-origin, `X-CSRF-Token`, JSON. Errors: `{"detail": "<code>"}` using
existing Modify codes (`write_disabled`, `proposal_expired`, `workspace_fenced`, …).

`POST plan` `{context, request}` (context as Modify's `contextBody`) →

- `{status:"ready", proposal_id, expires_at, brief, plan:{capability,digest,steps}, explanations}`
  where `brief` is `PlateWithHolesBrief`, `plan` is `CreationPlan` minus
  `schema_version`/`units`, and `explanations` is `explain_plan(plan)` as dumped.
  `proposal_id` is a 43-char URL-safe handle; `expires_at` is epoch seconds.
- `{status:"needs_clarification", reason, fields, questions}` (`NeedsClarification`)
- `{status:"unsupported", reason, message}` (`Unsupported`)
- `{status:"rejected", code}` (`Rejected`)

Responses with extra or missing keys are refused by the strict parser.

`POST plans/{proposal_id}/approve` `{digest, brief_confirmed:true}` →
`{state, steps}` once execution finishes (not streamed). `state` ∈ `verified_success |
partial_failure | write_failed | rejected_stale | execution_uncertain`; `steps` has one
entry per plan step (`verified_success | write_failed | rejected_stale |
execution_uncertain | skipped | …`). `verified_success` iff all steps verified.

`GET plans/{proposal_id}` → same shape, plus in-flight `pending | claimed | verifying`.

Discarding or editing an unapproved plan is client-only; the server should let the
proposal expire.

## Known limits

- The shell's "Read-only" badge still reflects Modify write availability only.
- Create unmounts when switching to Ask (locked while interpreting or building) or
  leaving the Design tab, which drops the local plan; a hidden-but-mounted Create
  trips an existing axe landmark rule. The server status endpoint is the source of
  truth for an approved build.
- Only `rect_plate_with_through_holes` is parsed; new capabilities need a parser
  branch here.
