# Modify recovery reliability hotfix

Branch: `cap/hotfix-modify-recovery`, based on `cap/2026` at
`682dfcf721fce74d350c5e0667f70a1cf1219929`. No merge is authorized.

## Uncertainty and authority

A dispatched write whose final deterministic verification fails stays
`execution_uncertain`. HTTP success or a visually changed model is insufficient.
The durable WriteFence denies both workspace writes and other writes by its user.
It prevents blind retries after lost acknowledgements or incomplete evidence.

Approval still requires the original immutable plan digest, a pending single-use
record, exact session/grant/context, fresh evidence and the existing guarded write
path. Discovery never renews a consumed plan or its approval expiry. All UI
proposal authority remains in component memory. Recovery uses the existing Forge
session cookie and CSRF token; it introduces no localStorage, sessionStorage,
IndexedDB, URL, cookie, provider permission or OAuth-scope change.

## Server-owned discovery

`POST /api/modify/recovery` accepts exactly `{ "context": WorkspaceReference }`.
The existing Modify guard authenticates and checks origin, CSRF, bounded JSON and
absence of query parameters. `authority()` derives user, session, grant generation,
exact Part Studio context and the workspace fence key on the server. Discovery
uses only its matching fence and user/session-owned record. It performs no CAD
read, provider call or write. Responses use `Cache-Control: no-store`.

Response variants:

```json
{ "state": "none" }
```

```text
{
  state: "execution_uncertain" | "claimed" | "verifying" | "recovery_required",
  plan: consumed opaque handle | null,
  operations: OperationPreview[],
  operation_states: OperationState[],
  reconciliation: "available" | "manual_required"
}
```

Only a valid same-session, exact-binding A2 record supplies a consumed handle or
previews. A different user/session/workspace/Part Studio/grant cannot obtain the
plan. Legacy orphaned fences and unavailable evidence produce a fixed manual-recovery
view with null handle and empty arrays. No digest, provider/CAD identity, revision,
fingerprint, target handle, definition, OAuth data or provider URL is returned.
Labels and reviewed values remain the existing untrusted display text.

On valid connected Modify mounts, discovery runs alongside capability inspection.
The composer waits for successful discovery and disappears behind an unresolved
card. Tab remount, reopening and page refresh query the server again. Context and
session changes remount the flow, abort old requests and discard old authority.
Uncertainty in the mounted execution flow also triggers discovery. Neither render,
effect, recovery discovery nor status polling can approve or retry a CAD write.

## Read-only reconciliation

`POST /api/modify/plans/{handle}/reconcile` accepts exactly `{}` and uses the same
authentication/origin/CSRF guard. Only an explicit **Inspect current CAD** click
calls it. Duplicate in-flight UI clicks are suppressed. It never calls a model,
mutation, approval, retry, resume or rollback path.

Automatic V1 reconciliation requires every predicate below:

- The stored record is consumed and `execution_uncertain`, with its matching
  workspace/user fence, authenticated session and unchanged full Binding.
- Exactly one operation is `SET_SUPPRESSED` or `SET_UNSUPPRESSED` on the supported
  terminal Fillet; original target identity and position match the Baseline.
- The original explicit suppression Boolean is the opposite of the requested
  final Boolean.
- Fresh authenticated head-bracketed, pinned Modify evidence passes all existing
  scope, body, state-coverage, unconfigured and ambiguity predicates.
- The current suppression Boolean equals the intended final Boolean.
- Every Baseline field other than microversion, whole-snapshot fingerprint and
  the intended terminal suppression Boolean equals the original Baseline.
  In particular definitions, target identity, label, position, serialization,
  library, body evidence, state evidence, auxiliary/parent/configuration evidence
  and exact context remain equal. The definitions fingerprint intentionally
  excludes only the terminal suppression Boolean. Independent current
  configuration must still prove the existing unconfigured scope.
- After reading, the same authority, immutable plan, uncertain record and fence
  are rechecked under the existing user/session/grant locks. A final head read
  must still match the captured revision.

One transaction sets the new closed **plan state** `reconciled_current_state`,
retains the historical operation journal, drops private plan authority, releases
only the exact matching user/workspace/record fence and audits the fixed event
`write_current_state_reconciled`. Future fresh plans may then be prepared. Two
workers cannot close or audit the same fence twice.

This means **fresh current CAD evidence matches the intended final state**. It
does not infer causality or prove the original provider write succeeded. It never
changes the plan to `verified_success`, which remains the original sequential
execution path's stronger acknowledgement-and-verification result. Historical
operation states are not rewritten to manufacture verified success.

Mismatched, stale, unavailable or incompatible evidence returns
`recovery_required` and retains the fence. Rename, depth, radius and multiple
operations remain manual recovery, with no automatic CAD read for those cases.
The stored evidence cannot prove their exact final state, so the UI says:
“Manual recovery required. Forge cannot safely prove the final result. Further
writes remain blocked.” There is no automatic fence-release path for these cases.

## Retention

Normal candidates/plans keep their existing two-minute approval expiry and
15-minute purge policy. Abandoned claimed/verifying records become uncertain
under the existing 150-second rule; they are never resumed.

Cleanup excludes every live fenced record from ordinary deletion and preserves
its complete reconciliation payload until safe resolution. Retention is bounded
by the existing one-fence-per-user invariant and the fixed closed plan schema
(at most five operations and bounded fingerprints/previews), rather than a growing
history. Raw CAD is never retained. A live denial never expires into permission,
and its evidence is never erased to satisfy an arbitrary TTL. Same-session access
remains bounded by existing session expiry/revocation.

Successful reconciliation drops private plan authority immediately; the status-only
record is purged 15 minutes after closure. Unresolved records necessarily remain
while their corresponding denial remains unresolved; there is no unsafe
clock-based fence release. Legacy missing/corrupt evidence produces a fixed
manual-recovery view and cannot be automatically reconciled. No database table
or migration changes.

Existing development-only historical orphan-recovery restrictions are unchanged.
This hotfix neither invokes that tool nor adds a general administrative bypass.
Unrecoverable/manual cases require a separately reviewed recovery decision; users
must not delete fences, replay approvals or edit database records to continue.

## Deterministic Modify planning

`modify_planner/deterministic.py` consumes only safe TargetOption handle, label,
type, position and supported operations. It has no provider identity or execution
authority. The flow is screening → fresh A1 discovery → deterministic parse →
server SemanticPlan → A1 prepare. Unknown language goes to the existing AI planner,
then its existing validation and A1 prepare. Recognized ambiguity, unsupported
operations, conflicts and invalid values produce server-owned clarification.

Supported explicit forms include:

- Suppress/Unsuppress the final fillet.
- Set the depth of Extrude 1 to 30 mm.
- Set Extrude 1 to 30 mm.
- Make Extrude 1 30 mm deep.
- Set the radius of Fillet 1 to 4 mm.
- Set Fillet 1 radius to 4 mm.
- Rename Fillet 1 to Edge Rounds.
- Make the extrude 30 mm deep and the fillet radius 4 mm, when each type is unique.

Period/newline/semicolon/conjunction-separated explicit clauses allow at most five
operations. The hero request resolves in order to depth `30 mm`, radius `4 mm`,
name `Edge Rounds`. All quantities and names use the original A1 validators;
there is no second value grammar or unit inference. Duplicate operations and
conflicting fields clarify. Ambiguous names/types and invalid ordinals never
select an arbitrary feature. Labels are compared as text and rendered as text;
there is no dynamic regular expression from a label, eval or FeatureScript.

Deterministic plans work without configured AI credentials and make zero AI calls
and zero CAD writes. Fresh A1 reads and prepare validation remain required.

## AI fallback and diagnostics

AI fallback remains one request to the explicitly selected provider. There is no
retry or provider switch. Groq `json_validate_failed` still maps through the
existing safe fixed error handling to `plan_unavailable`; no provider message or
failed generation reaches the browser or log.

`FORGE_MODIFY_REASONING_EFFORT` defaults to `high` and accepts `low`, `medium` or
`high`. A request-local Groq settings copy applies it only to Modify; OpenAI Modify
uses the same planner-specific setting. Design/Learn retain their prior settings,
models and budgets. This is no guarantee of provider structured-output success.

Generalized A2 emits development-only `a2_verify` diagnostics at `post_read`,
`operation_compare`, `deadline` and `authority`, with fixed `pass`/`fail` values.
Production emits none. The function accepts no payload or exception. No feature
name, value, identifier, revision, URL, body, credential or exception text is logged.
The verification and dispatch predicates remain unchanged.

## Live validation procedure (human-operated, after review)

1. Deploy the reviewed branch without merging or changing OAuth scopes. Preserve
   the actual unresolved fence and plan. Confirm the same authenticated session
   and supported workspace are used, while its original session and evidence remain available.
2. Reopen Modify, switch Part Studio tabs and return, then refresh/reopen Forge.
   Each time confirm the unresolved card replaces the composer and no automatic
   write, AI call or reconciliation occurs.
3. Review the operation preview and click Inspect current CAD once. This action
   performs live reads only. For the eligible single suppression operation,
   expect `reconciled_current_state` only when all fresh evidence agrees.
4. Verify that current-state semantics are shown, the original consumed handle
   cannot approve again, and a new plan can be previewed after successful closure.
   Preparing another plan does not approve it.
5. For disagreement or manual-only cases expect retained fencing and manual
   messaging. Stop; do not delete fences, retry writes or force reconciliation.
6. Try the deterministic hero request on a separately authorized disposable model
   to review the three-operation preview. Any subsequent write requires its own
   explicit human approval and is outside this automated validation.

Implementation and automated verification use only synthetic providers. Real
Onshape reads, real Onshape writes and real AI calls are all zero.

## Dependency audit repairs

The required audits found pre-existing advisories in certifi and Vite. The Python
lockfile updates only certifi from 2026.7.22 to 2026.10.19. The npm lockfile updates
Vite from 8.3.2 to 8.3.4 within the existing version range, along with its PostCSS
and nanoid transitive dependencies. No dependency manifest or application framework
changes. README credits received only the whitespace correction needed for the
root Prettier gate. All authoritative checks are rerun after these changes.

## Changed files

This hotfix changes 37 files:

- `README.md`
- `apps/api/src/forge_api/auth/security.py`
- `apps/api/src/forge_api/cad_edits/domain.py`
- `apps/api/src/forge_api/cad_edits/plan_diagnostics.py`
- `apps/api/src/forge_api/cad_edits/plan_recovery.py`
- `apps/api/src/forge_api/cad_edits/plan_routes.py`
- `apps/api/src/forge_api/cad_edits/plan_service.py`
- `apps/api/src/forge_api/cad_edits/plan_storage.py`
- `apps/api/src/forge_api/cad_edits/plans.py`
- `apps/api/src/forge_api/cad_edits/storage.py`
- `apps/api/src/forge_api/core/config.py`
- `apps/api/src/forge_api/modify_planner/deterministic.py`
- `apps/api/src/forge_api/modify_planner/providers.py`
- `apps/api/src/forge_api/modify_planner/routes.py`
- `apps/api/src/forge_api/modify_planner/service.py`
- `apps/api/tests/test_client_context_boundary.py`
- `apps/api/tests/test_modify_deterministic.py`
- `apps/api/tests/test_modify_diagnostics.py`
- `apps/api/tests/test_modify_plan.py`
- `apps/api/tests/test_modify_plan_postgres.py`
- `apps/api/tests/test_modify_planner.py`
- `apps/api/tests/test_modify_recovery.py`
- `apps/api/tests/test_modify_recovery_postgres.py`
- `apps/api/tests/test_safe_edit.py`
- `apps/api/tests/test_safe_edit_operator_recovery.py`
- `apps/api/tests/test_safe_edit_postgres.py`
- `apps/api/uv.lock`
- `apps/web/src/features/Modify.tsx`
- `apps/web/src/modify/Modify.test.tsx`
- `apps/web/src/modify/api.ts`
- `docs/AI_AGENT.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `docs/MODIFY_RECOVERY_HOTFIX.md`
- `docs/SECURITY.md`
- `package-lock.json`
- `tests/e2e/modify.spec.ts`

## Final automated verification

All results below are from the final implementation and patched frozen lockfiles,
with PostgreSQL tests enabled in random isolated schemas. No application data or
real WriteFence was edited. All provider transports were synthetic.

| Gate                                                           | Result                                                    |
| -------------------------------------------------------------- | --------------------------------------------------------- |
| Focused required regression gate                               | 682 passed                                                |
| Recovery                                                       | 37 SQLite/HTTP cases + 1 PostgreSQL race passed           |
| Deterministic parser                                           | 38 passed, including all requested forms and hero preview |
| Generalized privacy-safe diagnostics                           | 4 passed                                                  |
| A1                                                             | 166 + 4 PostgreSQL passed                                 |
| A2                                                             | 73 + 10 PostgreSQL passed                                 |
| B1                                                             | 76 passed                                                 |
| All PostgreSQL cases in full suite                             | 26 passed                                                 |
| Full backend                                                   | 2,230 passed, zero skipped                                |
| Full frontend                                                  | 826 passed across 33 files                                |
| Modify frontend/API                                            | 107 passed within the full frontend suite                 |
| Modify Playwright                                              | 45 passed across Chromium, Firefox and WebKit             |
| Ruff and Ruff format                                           | Passed; 147 files formatted                               |
| Strict mypy                                                    | Passed; 143 source files                                  |
| ESLint and Prettier                                            | Passed via npm run lint                                   |
| TypeScript                                                     | Passed via npm run typecheck                              |
| Production build                                               | Passed on Vite 8.3.4                                      |
| Alembic check                                                  | No new upgrade operations detected                        |
| Compose config                                                 | Passed                                                    |
| npm audit                                                      | Zero reported vulnerabilities                             |
| pip-audit --skip-editable                                      | No known vulnerabilities; local editable API skipped      |
| Frozen dependency installation                                 | npm ci --ignore-scripts and uv sync --frozen passed       |
| Whitespace / private-key / client authority persistence review | Passed                                                    |
| Real Onshape writes / reads / AI calls                         | 0 / 0 / 0                                                 |
| OAuth scopes / migrations                                      | No changes / none                                         |

The build retains its nonblocking warning for the approximately 505 kB minified
application chunk. Live provider conformance is still a human validation step.
Automatic reconciliation remains limited to the exact one-operation suppression
case; session expiry, missing legacy evidence and other uncertain edits remain
manual recovery. Unresolved evidence is bounded per fence and preserved until
safe closure, rather than being destroyed by an arbitrary retention deadline.
