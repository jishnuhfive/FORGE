# Temporary single-incident legacy administrative retirement

Implementation and verification are **synthetic only**. Live recovery is **NO-GO**.
The shipped static policy is **unenrolled** (`_ENROLLMENT = None`): it denies before
opening a DB transaction or obtaining a credential. No live record, fence, session,
grant, token or CAD document is inspected or changed by implementation work.

The normal [retained-record V1](RETAINED_RECORD_OPERATOR_RECOVERY.md), browser
discovery/reconciliation and orphan helper are unchanged. V1 never falls back to
legacy. There is no API, CLI, browser control, AI tool, startup hook, configuration
loader, automatic enrollment or general clear-fence operation.

## Frozen scope and provenance

| Field                                       | Fixed policy                                                 |
| ------------------------------------------- | ------------------------------------------------------------ |
| Case                                        | `oct20-terminal-fillet-reactivation`                         |
| Environment                                 | development, configured **and effective** CAD writes OFF     |
| Reviewer-declared receipt adoption boundary | `2026-10-21T00:00:00Z`                                       |
| Proposal creation                           | `2026-10-20T16:24:03Z`                                       |
| Execution interval                          | `[2026-10-20T16:24:46Z, 2026-10-20T16:24:50Z)`               |
| Document                                    | `616f4c98dfb6deed0a0c40e6`                                   |
| Workspace                                   | `75018163dba1b8c05d651a5b`                                   |
| Part Studio                                 | `6dfea845bb52ec251a31af43`                                   |
| Revision kind                               | workspace                                                    |
| Human context                               | Forge phase 8 test → Part Studio 2                           |
| Operation                                   | exactly one terminal Fillet `SET_UNSUPPRESSED`, true → false |
| Stack/company                               | `https://cad.onshape.com/api`, no company                    |
| Nonextendable sunset                        | `2026-10-23T00:00:00Z`                                       |

The corrected independently preserved October 20 conversation supplies this scope.
The other Gate A suppression procedure is not the scope anchor. Missing receipt,
Git history and DB timestamps alone do not prove legacy classification. The
boundary is a reviewer-declared classification rule, not an assertion of the exact
instant receipt enforcement became operational. After it, normal V1 provenance is
required. No future incident can enroll here.

For this exception, historical operation identity is explicitly
`identity_basis = trusted_retained_database`. There is no independent operation
receipt. Integrity checks and unique audits are consistency evidence, not independent
identity authentication. This is a lower-assurance development administrative
decision; it does not defend against a malicious DB administrator or a dishonest
privileged Python process. Context identifiers, references and evidence digests are
neither bearer credentials nor signatures and never confer browser authority.

The earlier read-only review found one compatible candidate, but deliberately did
not persist private pins. This patch neither reads them again nor invents them.
`LegacyEnrollment` supports a separately reviewed closed snapshot with historical
Binding, protected user, exact record/fence tuple, plan digest, canonical StoredPlan
fingerprint, target identity/position, creation/expiry, expected current generation,
scope-history evidence digest and enrollment reviewer metadata. Only the private
static policy slot may supply it. The coordinator accepts no enrollment/reference,
context, record, date, operation or sunset argument. There is no DB-to-enrollment
builder or runtime setter. Supplying real pins requires a separate reviewed private
enrollment procedure; do not commit private handles, hashes, digests or credentials.
An arbitrary current row must never become the enrollment source by default.

Historical source at `b728d422…` and pre-incident `682dfcf7…` supports durable
pre-dispatch claim/fence, user coordination, dispatch/ack journals and uncertain
finish preservation. No deployed build SHA or provider request/ack identifier was
persisted, so exact runtime-binary attribution and independent causal audit linkage
remain unavailable. Indefinite fenced-payload retention was introduced later.

## Capability separation and eligibility

1. `legacy_contracts.py`: strict, frozen, extra-forbidden models, distinct evidence,
   redacted result and private run state. Boolean/numeric literals reject coercion.
2. `legacy_policy.py`: literal single-case policy, unarmed static enrollment and
   bounded, exact enrollment/proof checks. No file/env/DB policy loader.
3. `legacy_enrollment.py`: locked DB consistency checks, never enrollment discovery.
4. `integrations/onshape/legacy_reader.py`: distinct legacy adapter using unchanged
   fixed GET transport and pure Modify projection. No V1 receipt/reference is built.
5. `legacy_recovery.py`: internal bounded coordinator, cache-only credential,
   capture, close reader, register evidence, release and commit. No retry.
6. `legacy_release.py`: provider-free exact conditional closure. No reader, token
   manager, provider, HTTP, callback or normal execution finish capability.

Eligibility requires the exact static enrolled identity and one related same-user
fence; valid bounded ≤64 KiB StoredPlan with existing digest/identity/time checks;
canonical fingerprint, original Binding and target pins; exact expired proposal;
explicit single uncertain journal; original suppressed=true and intended=false;
terminal target/preview consistent with the original deterministic Baseline. No
other same-user operational or unknown record may exist. Closed unrelated rows
are not authority. No candidate search can substitute a different retained row.

Original Session must survive, identify the same owner, predate the proposal and
be hard-expired or revoked. Idle-only expiry rejects. It is never revived or
updated. Current authorization must be same-user connected, exact reviewed
stack/company/generation, explicit `OAuth2Read`, and outside retry cooldown.
Changed generation is administrative context only; historical Binding stays intact.

Require exactly one `ok` claim → dispatch → provider acknowledgement → uncertainty
sequence in the fixed execution interval, claim at its start and nondecreasing
timestamps. Any duplicate, wrong user, conflicting/overlapping/unknown execution,
V1 retirement or prior legacy retirement denies. Legacy retirement audits are also
checked outside the interval. Ordinary proposal creation/expiry/invalidation/
cancellation events are excluded. Existing audits have no operation identifier;
this conservative unique-user sequence cannot manufacture a historical receipt.

## Settlement and quiescence contracts

The reviewer accepts **SETTLEMENT ESTABLISHED BY SYNCHRONOUS PROVIDER
ACKNOWLEDGEMENT** for this exact historical incident, subject to matching the live
candidate's unique audit sequence. This establishes only that the acknowledged
document mutation is terminal and cannot later execute again through a supported
retry/replay path. It does not establish `verified_success`, current CAD agreement,
absence of later edits or writer quiescence. Fresh five-GET evidence remains mandatory.
No provider settlement request or new history/completion endpoint is implemented.

`SettlementReview.evidence` is a closed discriminated union. The distinct
`synchronous_provider_acknowledgement` category fixes this case/context/window,
`SET_UNSUPPRESSED`, the exact v17 `features/updates` endpoint class and reviewed
historical source family `b728d422…` / `682dfcf7…`. Required response predicates
are HTTP 200, bounded valid JSON, exactly one approved feature ID, pre-dispatch
terminal Fillet validation, explicit suppressed=false and microversionSkew=false,
a valid resulting microversion different from baseline, and consumed single-operation
approval without a supported replay path. The closed review also requires the
reviewer-accepted development-history basis and explicit terminal-mutation disposition.

Its audit-sequence digest pins the exact reviewed four rows (IDs, owner, kind,
outcome and timestamp); locked validation checks that digest and the exact
acknowledgement timestamp before and after capture. Audit identity is still trusted
DB evidence, not an independent receipt. Source-family attribution is not deployed
binary attestation; the original response was not retained. The different-marker
check was not a microversion ancestry proof. Response type/position and complete
serialization/library/definition agreement still require the existing fresh evidence.

The optional, separately reviewed external-confirmation category remains unchanged.
For that category, `SettlementReview` requires exact case/enrollment fingerprint,
reviewer identity, review ID, bounded review validity and a
`ProviderSettlementEvidence` object with:

- category `provider_issued_terminal_confirmation`;
- issuer, privately retained evidence reference/digest and issue timestamp;
- exact protected user, fixed context and historical execution interval;
- explicit disposition `terminated_no_outstanding_activity_can_later_apply`.

The reviewer must independently inspect the actual provider-issued confirmation,
correlate actor/context/window (including justified clock interpretation), establish
that its semantics support that disposition, and retain the source securely. The
review disposition must be `approved_for_exact_legacy_retirement`. These fields
record a trusted review; filling them in cannot prove it happened. Digests identify
evidence but are not signatures. No Onshape head/history/ack field is assigned
undocumented completion semantics. Elapsed time, session expiry, writes OFF, quiet
DB, stable head, current suppression and a bare acknowledgement alone are insufficient.
Do not fabricate an external confirmation to represent the accepted synchronous basis.
Unavailable, conflicting, ambiguous or incomplete evidence leaves the fence intact.

`QuiescenceReview` separately requires case/enrollment pins, reviewer/review ID,
review times and evidence digests for deployment inventory, write-admission block,
worker drain, queue inspection, consumed/expired approval inspection and recovery
exclusion. All six explicit predicates must be true: effective writes OFF, drained
workers, no queued same-user write, no resumable historical approval, original
session hard inactive, no competing recovery. Missing evidence or a Boolean alone
rejects. Review validity is at most 900 seconds and never extends past sunset.

Actual maintenance must inventory every API/write worker, block new admission,
drain already admitted tasks/transactions/queues and exclude other operator runs.
DB counts supplement this proof; they do not establish process-wide quiescence or
upstream settlement. Preserve the owning process's sufficiently unexpired cached
read token; no bootstrap/export/refresh is permitted. No drain or maintenance was
performed for implementation testing.

## Fresh evidence, locking and atomic lifecycle

One operator process/transaction holds the existing user advisory lock → original
Session `FOR UPDATE` → current grant `FOR UPDATE` → related fence `FOR UPDATE` →
retained record `FOR UPDATE`. Relevant audits use `FOR SHARE`. No broad table lock.
Same-user claims/admission/grant rotation share the advisory lock; duplicate V1/
legacy attempts serialize. Cleanup preserves fenced payloads and serializes on
the target record. Counts are rechecked before and after capture under the user
lock; they do not prevent global phantoms or control external CAD editors.

The unchanged owned GET guard permits only the fixed five reads: workspace head,
complete features pinned to that microversion, pinned configuration, pinned body
details, and the same workspace head again. It enforces exact origin/path/query/
ordering, empty bodies, no redirects/proxies/retries, response/JSON bounds, and a
30-second total capture deadline. Pure projection enforces the existing coverage,
parent/configuration/suppression/body ambiguity predicates. Both heads must agree.

Distinct `LegacyEvidence` pins enrollment, reviews, context, Baseline, equal heads
and monotonic times. Only the exact object registered on the exact root DB
transaction/run is consumable once, within five seconds. The reader is closed and
its credential discarded before release. Copies, deserialization, cross-run/
transaction, stale/future/substituted evidence deny. The run ceiling is 40 seconds;
local PG lock/statement/idle timeouts are 2/35/40 seconds, unchanged defaults.

After complete locked revalidation, current suppression must be false and Baseline
must match with only `microversion`, `fingerprint`, `suppressed` excluded. Target,
position, other definitions, serialization/library and evidence modes must agree.
This preserves the approved deterministic comparison; it does not prove complete
geometric/history equivalence or original-write causality. External workspace edits
after the final head cannot be excluded by DB locks; maintain coordinated access.

Exactly one conditional unchanged-record UPDATE produces internal
`operator_recovered`, original outcome `execution_uncertain`, identity basis
`trusted_retained_database`, disposition `legacy_administrative_retirement` and
recovery timestamp. Private plan contents are removed; original DB identity/digest
columns remain. Purge becomes recovery time + 900 seconds. Exactly one conditional
user/workspace/record fence DELETE and one fixed
`write_legacy_retained_retirement` / `local_only` audit commit together. Existing
consumed-record handling rejects later plan loading/replay. No `verified_success`,
`reconciled_current_state`, retry, rollback operation or normal `finish()` is used.

Policy, proofs, integrity, counts and sunset are checked again after capture and
immediately before mutation; the coordinator rechecks eligibility before commit.
Every precommit failure rolls back the entire closure. A committed duplicate
denies without another capture/audit. A lost commit response is unknown completion,
never automatic retry. The closed result is distinguishable from the original
fenced state without restoring authority.

## Sunset, removal and live blockers

At `2026-10-23T00:00:00Z`, expiry only disables this path. It never releases a fence
and has no caller-selected extension. Remove the legacy invocation/modules after
the single incident's retirement, before ending maintenance, or sunset the unused
path. Keep the historical audit kind interpretable. New incidents require new
design review; absence of a receipt never selects legacy automatically.

Separate live-validation review still needs private static enrollment, adequate
candidate-matched settlement review, complete quiescence proof, exact current grant/cache,
fresh deterministic evidence and explicit authorization. Implementation approval
does not authorize any of those live actions. No general DB editing instructions
or manual deletion substitute for this reviewed helper.

## Synthetic verification

`test_legacy_recovery.py`, `test_legacy_evidence.py`, `test_legacy_boundaries.py`
and `test_legacy_postgres.py` use invented users/record pins/reviews/settlement and
invented CAD with mock GET transports. PostgreSQL uses an independently created
tmpfs service and random schemas, never the live FORGE URL or volume. Test-run
isolation disables dotenv and blocks real synchronous/asynchronous HTTP transports.
Concurrency covers duplicate/V1/cleanup/admission/claim/browser/grant races;
atomicity covers UPDATE/DELETE/audit/commit failure and ambiguous commit response.
Normal V1 and orphan tests must continue unchanged. No migrations, schema, public
contracts, OAuth scopes, sessions/grants or production defaults are changed.

Verification on `cap/retained-record-recovery`, pinned base
`2d9e6f87c6182c5725891e3032fe042994ec1a74`:

| Check                                                                     | Result                                                                         |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Focused legacy                                                            | 214 passed, including 17 PostgreSQL cases                                      |
| Retained V1 / orphan / Modify / safe-edit / auth / PostgreSQL regressions | 1,475 passed; includes all 182 retained V1 cases                               |
| Full backend                                                              | 2,633 passed, zero skipped; includes 59 PostgreSQL cases                       |
| Full frontend                                                             | 827 passed across 33 files                                                     |
| Ruff / format / strict mypy                                               | Passed; 168 formatted files, 164 typechecked files                             |
| ESLint / Prettier / TypeScript / build                                    | Passed; existing approximately 505 kB chunk warning                            |
| Alembic fresh upgrade / current schema / drift                            | Passed in disposable PostgreSQL schemas                                        |
| Dependency audits                                                         | npm zero vulnerabilities; pip-audit none known, editable local package skipped |
| V1 / orphan / browser recovery / token source / schema / lockfiles        | Unchanged against pinned base                                                  |
| Whitespace / credential-pattern / private-material review                 | Passed                                                                         |
| Real Onshape reads / CAD writes / AI / OAuth refreshes                    | 0 / 0 / 0 / 0                                                                  |
| Live DB reads / mutations / live auth changes                             | 0 / 0 / 0                                                                      |
| Migrations / schema / production defaults                                 | Unchanged                                                                      |

The isolated PostgreSQL 18.6 service used only newly created tmpfs storage; it was
stopped and removed after verification. No existing FORGE container, DB or volume
was used. No merge, actual enrollment or recovery was performed. Browser E2E was
not required because no browser behavior or public contract changed.

Initial implementation file inventory (18 files):

- `apps/api/src/forge_api/auth/security.py` (one fixed audit kind only)
- `apps/api/src/forge_api/cad_edits/legacy_contracts.py`
- `apps/api/src/forge_api/cad_edits/legacy_policy.py`
- `apps/api/src/forge_api/cad_edits/legacy_enrollment.py`
- `apps/api/src/forge_api/cad_edits/legacy_recovery.py`
- `apps/api/src/forge_api/cad_edits/legacy_release.py`
- `apps/api/src/forge_api/integrations/onshape/legacy_reader.py`
- `apps/api/tests/legacy_support.py`
- `apps/api/tests/test_legacy_recovery.py`
- `apps/api/tests/test_legacy_evidence.py`
- `apps/api/tests/test_legacy_boundaries.py`
- `apps/api/tests/test_legacy_postgres.py`
- `docs/LEGACY_RETAINED_RETIREMENT.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/DEVELOPMENT.md`
- `docs/ROADMAP.md`
- `docs/MODIFY_RECOVERY_HOTFIX.md`

## Settlement amendment and final read-only preflight

Base `10b01e9343fe924e0e0fe0739d1ec4ecf5db899f`. Only the two legacy
contract/enrollment modules, a new `test_legacy_settlement.py`, and this runbook plus
architecture/security/development/roadmap documentation changed. V1, orphan,
browser recovery, provider reader, token accessor, policy/enrollment slot, release
transaction, migrations/schema, dependency locks and production defaults are unchanged.

Synthetic verification completed **before** live preflight: 71 new settlement
cases (including two isolated PostgreSQL cases); 526 combined legacy/V1/orphan
cases; full backend 2,704 passed, zero skipped, including 61 PostgreSQL cases.
Ruff/format/strict mypy, ESLint/Prettier, TypeScript and build passed. The existing
approximately 505 kB build-chunk warning remains. Test-run isolation disabled dotenv
and real HTTP; the newly created tmpfs PostgreSQL container was stopped/removed
before live inspection. The original implementation's verification table above is
historical; this separate preflight includes live **read-only** DB access.

The PostgreSQL-enforced read-only preflight found exactly one corrected-scope
candidate. All owner/context/record/fence/digest/canonical-payload/Binding/target/
chronology/current-generation and scope-review pins were obtained, closed-model
round-trip validated and held only in process memory. The original session was
hard-inactive, current authorization connected with explicit read scope, the audit
sequence uniquely compatible, and no other same-user operational row existed.
The accepted synchronous settlement type matched the exact live audit rows.
No private identifier, pin or credential was printed or persisted.

The process inventory observed zero local Forge API, supervisor or other Forge
Python processes and no non-database Forge container. Same-user advisory holders
and waiters were zero. These observations did not establish the complete controlled
maintenance/admission-and-recovery exclusion proof required by `QuiescenceReview`.
No owned runtime/task inventory or maintained exclusion evidence was established;
do not replace the missing proof with true flags or database counts.

Preflight therefore stopped at quiescence with **NO-GO**. No cache accessor or
credential bootstrap was attempted, `_ENROLLMENT` remains `None`, the in-memory
candidate was not persisted, and the five-GET capture/post-capture validation were
not performed. A fresh read-only snapshot confirmed the original fence and entire
retained uncertain row unchanged. No API process was stopped or restarted.

Counts: real CAD GETs 0; CAD writes 0; AI calls 0; OAuth refreshes 0; live DB
mutations 0; fence deletions 0; retained-record lifecycle changes 0. No legacy
release, merge, commit, push or sensitive source enrollment was performed.
