# Phase 9A preparation review

> Historical Phase 9A design/preparation checkpoint. Its “9B not started” and
> future-tense statements describe that checkpoint. Subsequent explicit Phase 9B
> authorization produced the [runtime implementation review](PHASE_9_REVIEW.md),
> which governs current implementation status, operational deviations and pending
> human conformance gates. Phase 9A remains PREPARATION COMPLETE; Phase 8 remains
> COMPLETE, HUMAN VALIDATED, and MERGED. No real OAuth app change or CAD-write
> validation is claimed. Phase 10 remains NOT STARTED.

2026-10-17. Branch: `phase9/safe-cad-edit-prep`. Initial tree clean; base
`9c12dfb` is the merged Phase 7 Learning Mode checkpoint. The user's Phase 9A
request authorizes preparation, one scoped commit and normal branch push only.
At the original preparation checkpoint Phase 8B was separate unfinished work; no
teammate branch was copied or recreated. Phase 8 is now **COMPLETE, HUMAN VALIDATED,
and MERGED** into main at `81199ea95df04b34e6065441cad87d60b637dcf2`, confirmed by
the user, and integrated here by merge `4f168423ce917014312c6946015f9659be0e8e0e`.
**Phase 9A: PREPARATION COMPLETE. Phase 9B: NOT STARTED.**

## Preparation outcome

[PHASE_9_SAFE_WRITE_SPEC.md](PHASE_9_SAFE_WRITE_SPEC.md) is the design and handoff
authority. Exactly one selected operation: suppress one active ordinary standard
Fillet at the end of an unconfigured workspace Part Studio. Strict Boolean
false→true, no measurement or FeatureScript. Official `updateFeatures` permits a
partial suppression update; its inherited source-microversion guard is required.

The public official v17 OpenAPI schema was fetched without credentials on
2026-10-17: version `1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
It matches the current integration's reviewed version. The spec links official
API, OAuth/settings, revision, feature, FeatureScript, recovery and limits sources.
No live CAD API/write, AI inference or application-setting change was performed.

The exact ordinary suppression payload and atomic reject-on-skew behavior of
this update endpoint must be proved during controlled disposable-Onshape Phase
9B conformance validation. Shared field wording refers to addition; schema presence
alone is not a live atomicity guarantee. A failing guard rejects the mechanism;
Forge must not fall back to unguarded check-then-write or full replacement.

Documented foundations include candidate ranking, exact target/session/object/
microversion/proposal binding, one-time atomic claim, shared execution fences,
short-lived operational data and privacy, stale rejection, bounded dispatch,
post-write verification, uncertain-result/recovery semantics, threat model,
fixed errors/audits, UI/accessibility, synthetic fixture specifications and the
automated/human/screenshot matrices. Broad OAuth2Write risk remains explicit.

## Scope and preserved boundaries

Documentation only; no optional pure code, executable fixtures, runtime schemas,
routes, adapter functions, tools, frontend controls, auth/CSRF behavior, scopes,
environment examples, dependencies/lockfiles, models or migrations changed.
Pure code was deferred at preparation time to avoid unfinished Phase 8 contracts;
now-merged contracts still require review during separately authorized 9B work.
Temporary PostgreSQL proposal/fence storage is future
reviewed 9B architecture, not implemented persistence or CAD edit history.

Current scopes remain documented OAuth2ReadPII + OAuth2Read. Future OAuth2Write
and fresh consent require explicit human permission-transition authorization in
9B. Existing users cannot assume refresh upgrades consent. No live OAuth settings
were inspected or altered. Current read-only refusal, inspector and Learn remain.

Roadmap Phase 9 is now FIRST SAFE CAD EDIT: 9A preparation, 9B not started. Earlier
mistake investigation moves to later learning; Reality Lock remains a deferred
backlog topic rather than being silently lost. Phase 10/general Modify/tool-library
implementation is not started.

## Verification ledger

Final results below come from this preparation gate. No runtime phase is
declared implemented from documentation or mocked tests. Browser tests, where run,
use existing synthetic intercepts; they do not establish real-write behavior.

| Gate                                          | Result                                                                                                                            |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Frozen npm / uv installs                      | Passed: npm ci and uv sync --locked; no dependency/lockfile change                                                                |
| Format / lint / typecheck                     | Passed: make format/lint/typecheck; strict mypy checked 69 files                                                                  |
| Full frontend/backend unit suites             | 586 frontend passed (26 files); 814 backend passed; three opt-in PostgreSQL tests skipped here and passed separately below        |
| Build                                         | Passed; JS 433.13 kB / 135.01 kB gzip; CSS 54.38 kB / 11.18 kB gzip                                                               |
| Focused browser regression                    | 15 passed: five each Chromium/Firefox/WebKit, no skips/retries, 12.4 seconds                                                      |
| Compose / existing database health            | make compose-check passed; existing PostgreSQL running healthy                                                                    |
| Migration comparison / PostgreSQL regressions | make migration-check passed, no new upgrade operations; all three isolated-schema PostgreSQL tests passed                         |
| Dependency audits                             | make audit passed: npm zero vulnerabilities, pip-audit no known vulnerabilities (editable Forge excluded)                         |
| Diff / secret and private-data review         | Passed: nine intended Markdown files, no credential/private-ID patterns or private artifacts; staged blobs verified before commit |

No full browser rerun is necessary for documentation-only changes. Focused
regressions exercise existing write refusal/read analysis, CAD Inspector and Learn
without changing their tests or product code. The existing database was preserved and its test schemas cleaned up. Playwright
stopped its test-owned servers; no application service was started/stopped.
Sandbox restrictions on public-schema DNS, Docker socket and loopback database/
browser access were resolved with scoped tool approvals; no gate remains blocked.

## Files and publication

Intended changed files:

- `README.md`
- `docs/PHASE_9_SAFE_WRITE_SPEC.md`
- `docs/PHASE_9_PREP_REVIEW.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/DEVELOPMENT.md`
- `docs/AI_AGENT.md`
- `docs/UI.md`

Review status/diff before staging and staged blobs before commit. Exclude secrets,
private CAD identifiers/payloads, local environments/certificates, QA caches,
screenshots, HARs and databases. Public schema download stays outside Git. No
source/runtime/migration/dependency file belongs in this commit.

Use the existing Git identity and origin, commit
`docs: prepare Forge safe CAD write architecture`, then normally push only
`phase9/safe-cad-edit-prep`; never force-push or merge main. Record resulting hash,
push and clean-tree verification in the final report rather than embedding this
commit's own hash here.

## Exact Phase 9B handoff and stop condition

Phase 8 implementation and human validation are complete and its history/docs are
merged into this branch. `docs/PHASE_8_REVIEW.md` is byte-for-byte unchanged from
incoming main; its provisional status is superseded by the user's final completion
confirmation recorded in the current overview documents. Runtime/test files match
incoming main exactly. The existing checker, statuses, fresh reads, feature-name
independence, single-L-profile alternative and verification revocation/restoration
are preserved. Reuse that infrastructure and review its actual contracts before
any future write integration. **Explicit human Phase 9B authorization is still required.**

The merge resolution changed only six conflicting Markdown files manually; the
remaining three Phase 9 handoff documents are synchronized in a separate
status-only documentation commit. Merge parents are the original `b95e866` Phase
9A preparation and the supplied `81199ea` main merge; Phase 8 history is not squashed.
Integration checks passed: conflict-marker scan, git diff --check, targeted Prettier,
local documentation links, typechecking (76 Python files), build, dependency audits,
624 frontend tests and 861 backend tests. Three opt-in PostgreSQL tests were skipped
in this integration run; the original preparation ledger above remains historical.
No browser rerun is needed for documentation conflict resolution; no runtime file
was manually modified or new Phase 9B behavior introduced.

Before any permission transition obtain explicit human approval; do not change
the live app now. In 9B, recheck official contracts and prove ordinary suppression
and atomic stale rejection in disposable CAD under the spec's controlled human
plan. If either fails, stop and amend the decision; do not broaden authority.
Only then implement the single typed operation with all security/verification
gates and frozen UI. No guessed Phase 8 interfaces or second evidence/checker model.

**Phase 9B: NOT STARTED.** Phase 9A preparation and Phase 8 integration are complete;
stop after documentation reconciliation and normal branch publication.
