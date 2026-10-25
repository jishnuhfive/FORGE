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

## API contract (implemented in `apps/api/src/forge_api/cad_create/`)

All requests: same-origin, `X-CSRF-Token`, JSON. Errors: `{"detail": "<code>"}`.
`requestCreation` makes two non-mutating calls behind one UI action:

1. `POST /api/create/interpret` `{request}` → `{status:"ready", brief, plan}` |
   `{status:"needs_clarification", reason, fields, questions}` |
   `{status:"unsupported", reason, message}` | `{status:"rejected", code}`.
   The browser keeps only the brief from `ready`.
2. `POST /api/create/plan` `{context, brief}` → `{proposal_id, digest, expires_at,
   brief, plan, explanations, limitations}`. `digest` is the whole-approval digest the
   approval binds to (not `plan.digest`). `422 unsupported_geometry` means the server
   refused the whole plan before any approval exists (any hole/cut today); the UI shows
   the unsupported state and nothing is built.

`POST /api/create/plans/{id}/approve` `{digest, brief_confirmed:true}` → `{state, steps}`
after execution. `state` ∈ `verified_success | rejected | rejected_stale |
execution_uncertain`; the server's `rejected` (refused before any dispatch) is displayed
as "not applied". `GET /api/create/plans/{id}` returns the same shape plus in-flight
`pending | claimed | verifying`. Success needs every step `verified_success`.
An approval is one-use; an uncertain result keeps the server write fence and is never retried.

Currently supported real writes: Top-plane rectangle sketch + additive blind Extrude.
Face-based sketch placement and scoped REMOVE Extrude are unsupported until proven.
The parser still understands cut steps so Learn can explain them once enabled.

## Known limits

- The shell's "Read-only" badge still reflects Modify write availability only.
- Create unmounts when switching to Ask (locked while interpreting or building) or
  leaving the Design tab, which drops the local plan; a hidden-but-mounted Create
  trips an existing axe landmark rule. The server status endpoint is the source of
  truth for an approved build.
- Only the `rect_plate_with_through_holes` capability is parsed; new capabilities need
  a parser branch here.
