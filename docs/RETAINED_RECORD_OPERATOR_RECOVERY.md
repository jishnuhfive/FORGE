# Retained-record administrative recovery V1

Implemented for **development, CAD writes OFF, separately authorized operator use**.
Implementation verification is synthetic only. No live record/fence was inspected,
recovered or cleared by this work. A separate live-validation decision is required.

This is not browser recovery, approval renewal, a replay/retry, rollback, or proof
that Forge caused a CAD change. Successful closure means an independently authorized
operator established settlement and fresh deterministic evidence matches the narrow
reviewed intended state, permitting future **new** plans and approvals.

## Capability boundaries

Four internal modules keep capabilities separate:

| Module                                    | Capability                                                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `cad_edits/retained_contracts.py`         | Frozen, strict, extra-forbidden references/results/evidence and private transaction-local run state; no provider I/O                            |
| `integrations/onshape/retained_reader.py` | Owned five-GET client and pure Modify projection; no mutation client or token refresh                                                           |
| `cad_edits/retained_recovery.py`          | Operator coordinator; bounded transaction, locked validation, cached read credential, capture, close reader, register evidence, release, commit |
| `cad_edits/retained_release.py`           | Provider-free DB checks and atomic exact closure; no token manager, client, HTTP, callback, reader or coordinator import                        |

None is registered with app startup, routes, browser controls, CLI entry points,
AI tools or normal product flows. `dev_recovery.py` is unchanged and continues to
reject retained records. Browser discovery and strict same-session/exact-binding
reconciliation are unchanged. A current session or grant never inherits historical
approval or reconciliation authority.

## Reference provenance and review before entry

The operator must establish A before using B to construct the reference, review C
before entering the transaction, and acquire D only inside that transaction.

| Source                                       | Fields                                                                                                                                                                              | Meaning                                                                                                           |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| A: independently preserved operation receipt | Exact user, document/workspace/Part Studio, terminal suppression operation and desired Boolean; preserved record handle **or** previously preserved approval digest; receipt digest | Independent operation scope and historical anchor, reviewed against the independently preserved source            |
| B: retained valid A2 StoredPlan              | Historical Binding/session/generation/workspace key, handle, original approval digest, creation/expiry, canonical full StoredPlan payload fingerprint                               | Consistency and TOCTOU pins, never independent authority unless the approval digest was separately preserved in A |
| C: current operator-reviewed configuration   | Exact stack/company/current generation; explicit operator authorization, independent receipt review, drained writers and upstream settlement attestations                           | Administrative prerequisites; does not grant old-plan browser authority                                           |
| D: fresh pinned GET capture                  | Exact context, equal head bracket, strict Baseline, capture times, reference/record/payload/user/current-generation pins                                                            | Current-state comparison evidence, not original-write causality or upstream settlement by itself                  |

`build_retained_reference` requires a typed independent receipt and checks A against
B; it never derives A from B. Missing anchors and a declared database-only receipt
source reject. The models do **not** authenticate historical provenance by themselves:
a trusted operator must actually review the previously preserved evidence. A receipt
digest is a consistency identifier, not a signature or external trust service. A
privileged Python process could lie about provenance; these modules are not a sandbox
against that process. Without an adequate independent source, stop and keep the fence.

The reference is private, in-memory administrative input. It is not accepted by an
API, browser session or AI, is not logged, and is not a bearer token. Do not copy
current DB values and label them independently preserved. Do not export credentials,
invent signing keys, or use screenshots as deterministic evidence.

All effective writers, across every worker, must be OFF and drained, including
already admitted/queued DB transactions and potentially in-flight upstream activity.
Independent settlement requires separate operator evidence/authorization. Elapsed
time, audit acknowledgement, and matching CAD alone cannot prove upstream settlement.
Resolve conflicting/ambiguous evidence before entry; there is no human pause inside
the locked transaction. External CAD edits after the final head read cannot be
excluded by DB locks; coordinate the disposable workspace and use the bounded handoff.

## Exact eligibility

- Explicit development mode and configured/effective CAD writes OFF; all four
  review attestations true; exact reviewed stack/company match Settings.
- Original session row exists, identifies the exact historical owner, predates
  the plan, and is hard-expired or revoked at the current time. Idle expiry alone
  is insufficient. The row is never authenticated, revived, updated or replaced.
- Current same-user authorization exists, is connected, matches exact stack/company
  and explicitly expected current generation, has a known `OAuth2Read` scope and
  is not in a retry cooldown. Changed generation is permitted only as C; B is intact.
- Exactly one related fence matches user, computed workspace key and retained
  record ID. Related mismatches, absence and foreign ownership reject.
- Exact `execution_uncertain` record; matching user, old session, digest, creation
  and expiry; valid closed StoredPlan and existing storage integrity checks; full
  canonical payload fingerprint matches. At least 900 seconds since creation and
  approval expired. Payload is bounded to 64 KiB before parsing.
- Persisted journal itself has state `execution_uncertain` and exactly one
  `execution_uncertain` operation. Cleanup-derived claimed/verifying journals,
  all-verified journals and other incompatible outcomes reject.
- Exactly one terminal supported Fillet `SET_SUPPRESSED` or `SET_UNSUPPRESSED`.
  Target identity/type/position and suppression preview match the original Baseline;
  original suppression is opposite the desired state. Rename, depth, radius,
  multiple operations, nonterminal/ambiguous targets reject.
- No other protected-user candidate, admission, pending, claimed, verifying,
  uncertain or unknown operational state. Only known closed states are excluded
  from this check. Other users' operational rows are not a global blocker or authority.
- Exactly one each, outcome `ok`, in nondecreasing timestamp order:
  `write_proposal_claimed`, `write_dispatch_started`,
  `write_provider_acknowledged`, `write_uncertain`. All occur from plan creation
  through creation + 900 seconds and no later than now. Any other execution/recovery
  audit from that user's creation window onward rejects, including future unknown
  `write_` kinds. Only proposal creation/expiry/invalidation/cancellation are excluded.
  Audits have no operation ID, so this conservative uniqueness check rejects
  ambiguity; it does not manufacture causal attribution.

## Evidence and credential acquisition

One trusted operator process performs capture and release in the **same transaction**.
Its existing TokenManager must already own the current generation's sufficiently
unexpired cached token. `cached_read_credential` requires exact user/generation,
known read permission, and remaining lifetime strictly greater than the fixed
30-second capture budget. It performs no DB access, cache update, refresh HTTP,
token persistence, grant/session mutation or generation change. A cache miss is a
denial. There is no separate-process cache export, refresh or bootstrap mechanism.

The dedicated reader owns a client with redirects/proxies/environment trust and
retries disabled. The transport checks GET, exact origin, exact ordered URL/query,
and empty body before delegating. Its only sequence is:

1. `GET /api/v17/documents/d/{document}/w/{workspace}/currentmicroversion` → M.
2. `GET /api/v17/partstudios/d/{document}/m/{M}/e/{element}/features?includeGeometryIds=false&noSketchGeometry=false&rollbackBarIndex=-1`.
3. `GET /api/v17/elements/d/{document}/m/{M}/e/{element}/configuration`.
4. `GET /api/v17/partstudios/d/{document}/m/{M}/e/{element}/bodydetails?includeGeometricData=false`.
5. Pure `project_modify_evidence` validation, then GET the same workspace head again;
   require equality with M.

Each response is limited to 2 MiB, identity encoding and JSON; duplicate keys,
nonfinite/deep/oversized JSON, incompatible provider responses and unsupported
projection evidence reject. The total capture budget is at most 30 seconds,
clamped to leave the run's five-second handoff allowance, with bounded
connect/read/write/pool timeouts and no retry. An error closes/discards the reader
and rolls back. No raw provider document is retained in the evidence or DB.

The resulting `VerifiedRetainedRecoveryEvidence` contains only fixed schema/projection
versions, reference/record/digest/payload/user/generation/context pins, Baseline,
head bracket and monotonic timings. The coordinator closes the reader and removes
its credential capability **before** registering the exact object on a private run.
The run is bound to the exact SQLAlchemy Session and active root transaction, and
has a 40-second maximum elapsed lifetime. Only the registered object is consumable;
copies/deserialization, scope substitution, other runs/transactions, reuse and
future/stale evidence reject. The immediate handoff ceiling is five seconds, checked
again before mutation. A failed release attempt consumes that handoff. No signatures
or transportable evidence files are needed.

## Minimal locking and transaction

Lock order: transaction-scoped user advisory lock → original Session `FOR UPDATE`
→ current authorization `FOR UPDATE` → exact related fence `FOR UPDATE` → exact
WriteRecord `FOR UPDATE`. Relevant audits use `FOR SHARE` and are revalidated.
PostgreSQL local lock timeout is two seconds, statement timeout 35 seconds and idle
transaction timeout 40 seconds. These settings are transaction-local;
production/default configuration is unchanged. The monotonic run ceiling is an
eligibility guard checked before release, not a claim that a Python timer can
interrupt a blocked DB call. Lock/statement/idle timeouts bound those waits; capture
has its separate total deadline. No global/table `SHARE ROW EXCLUSIVE` barrier.

Normal same-user admission/claims/auth changes share the advisory lock; these
critical sections cannot enter during capture/release. The fence's workspace key
uniqueness excludes competing ownership before commit. The record lock and existing
fence-preserving cleanup exclude target deletion, and the final future purge time
protects the closed record after commit. Current-session reconciliation has no
authority over the expired-session plan. Row counts are rechecked under the user
lock before and after capture; they do **not** protect global phantoms. Cleanup has
no user advisory lock, and upstream workers/external CAD are not controlled by a DB
lock; draining and settlement remain explicit operator prerequisites.

The release helper consumes the exact fresh evidence, rechecks every eligibility
predicate under the locks and compares Baselines with **only** `microversion`,
`fingerprint` and `suppressed` excluded. Every other Baseline field must match;
fresh suppression must equal the independently reviewed desired Boolean.

On agreement, in the same transaction:

1. Conditional UPDATE must return exactly one unchanged uncertain record matching
   handle/user/old-session/original-digest/creation/expiry/exact raw payload snapshot.
2. Set internal `operator_recovered`, replace payload with closed administrative
   schema/state/original `execution_uncertain` outcome/disposition/recovery time,
   and set purge to recovery time + 900 seconds. Keep historical DB identity/digest
   columns intact; remove all private plan/baseline/labels/target IDs from payload.
3. Conditional DELETE must return exactly one fence matching user/workspace/record.
4. Insert fixed `write_retained_operator_recovery` / `local_only` audit for that user.
5. Flush and commit before returning success.

No normal `finish()` is used. `verified_success` and `reconciled_current_state` are
never produced. The retained record is a consumed redacted tombstone, not deleted
immediately or retained as reusable plan authority. Plan loading/status explicitly
returns `proposal_used` for this administrative state; public PlanState is unchanged.
Normal cleanup purges the tombstone after 900 seconds without releasing any fence.

Disagreement, ambiguity, missing/invalid evidence, cache failure, timeout, integrity
failure, row-count mismatch and any precommit crash/failure leave the original record
and fence intact through rollback. A committed duplicate fails closed without another
success audit or capture. A lost commit reply must be treated as unknown completion;
there is no automatic retry or resume. An atomic committed state remains distinguishable
from the original fence. Failure reasons are fixed codes, without private identifiers,
provider errors, payloads or credentials; the existing audit schema cannot attach an
operation identifier or detailed evidence. External preserved review remains required.

## Verification and remaining live prerequisites

Focused suites: `test_retained_recovery.py`, `test_retained_evidence.py`,
`test_retained_tokens.py`, `test_retained_boundaries.py`, `test_retained_postgres.py`.
They cover both directions, denial matrix, handoff provenance, fixed GET bounds,
credential isolation, atomic failure/lost reply, no public registration, old helper
restrictions, and PostgreSQL duplicate/cleanup/admission/claim/browser/grant races.
Use only invented receipts/CAD and isolated temporary test databases. Regression
suites cover existing Modify/recovery/auth behavior; no migrations or defaults change.

The known retained record is **theoretically** eligible despite an inactive original
session, newer session and changed connected grant. Those facts alone are insufficient.
Separate review must establish adequate independent A evidence, exact supported plan
and explicit uncertain journal, surviving hard-expired/revoked historical session,
minimum age, unique compatible audit history, no conflicting work, current expected
grant/read scope/cache availability, global writer drain and independent settlement.
Fresh evidence must then agree within the bounded transaction. None of those live
facts was inspected or asserted by this implementation. A missing process-local
cached credential or missing independent receipt is a blocker; do not refresh,
export tokens, edit DB data or weaken guards to bypass it.

## Implementation verification record

Branch `cap/retained-record-recovery`, base
`0387cb6f81daa8810d33d9eb325bfa783cb81d0a`. The verification process disabled
dotenv loading and real HTTP/async HTTP transports in pytest. PostgreSQL ran in a
new disposable PostgreSQL 18.6 container with tmpfs storage and random per-test
schemas; no existing FORGE service, volume, URL or data was used.

| Check                                                                  | Result                                                                                                   |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Focused retained V1                                                    | 182 passed, including 16 PostgreSQL cases                                                                |
| Existing Modify/recovery/safe-edit/auth regressions                    | 1,290 passed                                                                                             |
| Full backend                                                           | 2,419 passed, zero skipped; includes all 42 PostgreSQL cases                                             |
| Full frontend                                                          | 827 passed across 33 files, rerun on patched Vitest                                                      |
| Ruff / Ruff format / strict mypy                                       | Passed; 157 formatted files, 153 typechecked files                                                       |
| ESLint / Prettier / TypeScript / production build                      | Passed                                                                                                   |
| Alembic/schema drift                                                   | Existing fresh-upgrade/current-schema/check test passed in an isolated schema; no new upgrade operations |
| Dependency audits                                                      | npm: zero vulnerabilities; pip-audit: none known, local editable package skipped                         |
| Frozen installs / whitespace / private-material review                 | Passed                                                                                                   |
| Real Onshape reads / writes / AI calls                                 | 0 / 0 / 0                                                                                                |
| Live database reads / mutations / live OAuth, session or grant changes | 0 / 0 / 0                                                                                                |
| Migrations / schema / production defaults                              | Unchanged                                                                                                |

PostgreSQL coverage includes duplicate closure, cleanup, same-user admission/claim,
replacement-browser denial, grant rotation/disconnect, all five atomic failure
points and idle timeout during capture. Exactly one closure or complete denial;
no second success audit. Lost commit response is also covered synthetically.

The required npm audit exposed two moderate advisories in the prior Vitest 4.1.11
dev dependency (`GHSA-qxg6-89mg-rqv8`, `GHSA-xp26-3454-mjgp`). Only the eight Vitest
family packages in `package-lock.json` advance to 4.1.12 within the existing range;
no manifest or production dependency changes. The build retains its existing
nonblocking approximately 505 kB application-chunk warning. No browser behavior
changed; browser E2E was not required for this internal patch.

Exact changed-file inventory (21 files):

- `apps/api/src/forge_api/auth/security.py`
- `apps/api/src/forge_api/auth/tokens.py`
- `apps/api/src/forge_api/cad_edits/domain.py`
- `apps/api/src/forge_api/cad_edits/plan_storage.py`
- `apps/api/src/forge_api/cad_edits/retained_contracts.py`
- `apps/api/src/forge_api/cad_edits/retained_recovery.py`
- `apps/api/src/forge_api/cad_edits/retained_release.py`
- `apps/api/src/forge_api/integrations/onshape/retained_reader.py`
- `apps/api/tests/retained_support.py`
- `apps/api/tests/test_retained_boundaries.py`
- `apps/api/tests/test_retained_evidence.py`
- `apps/api/tests/test_retained_postgres.py`
- `apps/api/tests/test_retained_recovery.py`
- `apps/api/tests/test_retained_tokens.py`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `docs/MODIFY_RECOVERY_HOTFIX.md`
- `docs/RETAINED_RECORD_OPERATOR_RECOVERY.md`
- `docs/ROADMAP.md`
- `docs/SECURITY.md`
- `package-lock.json`

Implementation is GO for separately reviewed live-validation planning. Actual live
recovery remains NO-GO until its independent prerequisites and explicit authorization
are established; this implementation neither evaluates those live facts nor performs
that recovery. No merge was performed.
