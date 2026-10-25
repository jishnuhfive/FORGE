# Roadmap

Advance only with explicit phase authorization. Security, tests, deterministic
verification, documentation, and maintainability are requirements of every phase.
Later hardening does not defer security for earlier live integrations.

| Phase          | Actual scope and status                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0–5            | Foundations, UI, OAuth, extension, REST and Inspector: complete; preserved review records below                                                                                |
| 6              | Read-only AI: complete and human validated                                                                                                                                     |
| 6.5            | Design system: approved and frozen                                                                                                                                             |
| 7              | Learning Mode foundation: COMPLETE and merged                                                                                                                                  |
| 8              | Mounting Bracket + Check my step: COMPLETE, HUMAN VALIDATED, MERGED at 81199ea                                                                                                 |
| 9A             | First safe CAD edit architecture/preparation: PREPARATION COMPLETE                                                                                                             |
| 9B             | Narrow terminal-Fillet suppression: IMPLEMENTED and automated tested                                                                                                           |
| 9 human Gate A | PROVEN: approved real suppression and Forge verified success from fresh evidence                                                                                               |
| 9 human Gate B | Expected stale-write behavior observed; provider-side rejection audit confirmation deferred; full provider conformance not proven                                              |
| 10             | Investigation, prediction, fading guidance and transfer: IMPLEMENTED, automated validation complete, merged to main and integrated here; real-Onshape human validation pending |
| 11             | NOT STARTED; no new phase scope is authorized by this integration                                                                                                              |

The original numbering is superseded by this actual sequence. Unassigned future
backlog remains: assemblies/mates, broader deterministic engineering validation,
full agent execution, general selection-aware Modify, tool/inventory Reality Lock,
expanded learning, the camera-slider evaluation, account/history polish, security
and reliability hardening, production deployment and App Store preparation.
These topics require separate authorization and have no current phase assignment.

Phase 0 is preserved in commit `2b68754`. Phase 1 implements the accessible UI
foundation, local preferences and development-only synthetic previews. Subsequent implemented capabilities are recorded below. Phase 2 now implements Onshape OAuth, identity persistence, encrypted refresh tokens,
revocable sessions, CSRF and account UI. Automated verification is recorded in
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md); real OAuth requires human credential setup.
Phase 1 remains preserved in `31f545a`; Phase 2 is `676414f`. The human reports real
OAuth login verified. Phase 3 implements validated launch context, exact-origin/parent
messaging and a bounded single-face/edge/clear adapter. The human verified embedding,
authenticated iframe session and launch context. The corrected live FACE structure,
along with EDGE and clear captures, matches the implemented adapter. The full gate
and targeted FACE regressions pass. Phase 3 is complete and its commit/push authorized.
Phase 4 is complete: implementation, external live verification and the complete
final repository gate passed. The user has
verified 2 features, 1 part and 1 body live. The final sign capture proves the scalar bug: zero nominal mass
with a negative lower tolerance was rejected despite ordered bounds and a valid
unavailable-mass flag. The repair now validates exactly three finite numbers,
nonnegative physical nominal and ordered bounds for mass/volume/surface area.
Unavailable mass suppresses the normalized estimate; missing counts stay valid,
other CAD sections remain usable, and the UI reports unavailability safely.
DEV diagnostics stay bounded and exclude provider numeric values; temporary
validator replay is removed. The final real read now safely reports missing mass,
and a separate empty Part Studio returns 0/0/0 without stale prior results. The
single Phase 4 commit and normal push are explicitly authorized, conditional on
the reviewed staged tree. Phase 5 is complete: final real CAD Inspector verification and the complete
repository gate passed.
At Phase 5 completion, the user authorized one scoped commit/push after the full
gate; Phase 6 required separate authorization, subsequently granted below. See [ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md) and
[PHASE_4_REVIEW.md](PHASE_4_REVIEW.md).

Multi-selection, assembly paths, version messaging and browser-wide session behavior
are not established by these Part Studio samples. The camera-slider example remains
a future evaluation scenario, not a generated design or engineering certification.
Forge v1 targets education, makers, low-risk prototypes and student engineering.

Phase 5 adds the versioned structured evidence model and human inspector using the
existing Phase 4 acquisition. It intentionally supports workspace Part Studios only.
Assemblies and mates remain unassigned future work; no assembly permission or operation is added.
Phase 6 is now the first read-only AI consumer, separately authorized and verified
as recorded below. The inspector itself does not implement deterministic validation,
certification, Reality Lock, Modify or Learn behavior.
See [PHASE_5_REVIEW.md](PHASE_5_REVIEW.md) for the preserved Phase 5 evidence/gate.
Topology semantics and ordinary browser-tab preservation are live verified;
real CAD context/session changes still clear evidence.

## Phase 6 — complete, 2026-10-16

The user authorized read-only AI from clean main
`0405104f9fb2feb3611aaf534855bad0225e57bf`. The provider-neutral agent, bounded
session-owned inspection, strict answers, ephemeral conversation, progress,
cancellation, safe errors and adversarial regression coverage are implemented.
Groq / `openai/gpt-oss-120b` is the default hosted provider. OpenAI Responses remains
an explicit operator-selected option; no automatic paid fallback exists. Groq tool
and strict-output stages are separate, and its shared free quota remains finite.

The user reported final real live acceptance passed: inventory/feature order,
parameter explanation, Evidence copying/expansion, unavailable mass, FACE/EDGE and
clear selection, hard ownership unknowns, UNVERIFIED deterministic validation,
explicit read-only write handling, the normal read regression, same-context Chrome
tab preservation and real Part Studio context clearing. Passive events do not
initiate AI analysis. These observations verify the recorded scenarios, not
universal model quality or production readiness.

The live write prompt originally returned Groq `tool_use_failed` because it forced
inspection generation for an unavailable action. Explicit CAD modification requests
now take a deterministic server path: the same authorized inspection, zero provider
requests, no mutation and no invented controlling dimension. Normal read questions
retain the bounded model/tool path. Selection ownership remains unknown regardless
of singleton part/body/feature inventory, and model-written sidecars cannot bypass
that boundary.

The complete final repository gate and secret/privacy review passed after all
repairs. The user authorized one Phase 6 commit and normal push to existing
`origin/main`, conditional on a clean staged review. See
[PHASE_6_REVIEW.md](PHASE_6_REVIEW.md) for exact counts, live evidence, architecture,
provider retention caveats and known limitations.

## Phase 6.5 — complete, visually approved, design system frozen

Phase 6.5 was visually approved after two human-review passes in real Onshape.
The accepted Obsidian/Arc Blue/Oblique Plane direction, functional Liquid Glass,
compact navigation/composer and answer-first hierarchy are frozen in
[FORGE_DESIGN_SYSTEM.md](FORGE_DESIGN_SYSTEM.md). Final work is limited to timeless
product copy, Settings micro-polish, accessibility fallback repair, full verification
and one authorized commit/normal push. No CAD writes, OAuth write scope, provider or
grounding redesign, or Phase 7 work is included. Server-owned response text changed
only to express the same capability and unknowns without internal roadmap language.
See [PHASE_6_5_FINAL_REVIEW.md](PHASE_6_5_FINAL_REVIEW.md) for the final gate and scope.
The earlier review records preserve the two-pass history.

## Phase 7 — complete, real Onshape human acceptance passed

The user authorized Learning Mode on `phase7/learning-foundation`, from current
main `24aaf675ba3726b850f229013e95c1ce72765158`. This supersedes the original
write-first scope of phases 7 and 8. Forge is evolving toward an AI engineering
tutor inside Onshape; the learner performs CAD operations.

The foundation includes a serializable validated lesson schema, deterministic
session transitions, concise experience/goal setup, one three-step Sketch to solid
sample, Why disclosures, vocabulary, three deliberately requested hint levels,
learner-marked progress and an observed-interaction completion summary. It needs
no AI provider or CAD data. Session state is memory-only and survives ordinary
mode/settings/history navigation. No CAD checker, write operation, OAuth permission,
student record, mastery score or persistent learning table is introduced.

The user reported successful real Onshape human acceptance on 2026-10-17,
including lesson flow, progressive help, honest progress, navigation preservation,
reset and narrow-panel usability. Screenshots were reviewed outside the repository
and must not be committed. Results are recorded in
[PHASE_7_REVIEW.md](PHASE_7_REVIEW.md). The branch is approved and ready for PR/merge;
the agent must not merge it. Phase 7 subsequently merged in `9c12dfb`.

## Phase 8 — COMPLETE, HUMAN VALIDATED, and MERGED

The user confirms final real Onshape validation and merge to main at
`81199ea95df04b34e6065441cad87d60b637dcf2`. This integration brings the actual
Mounting Bracket guided project and deterministic Check my step into the Phase 9
branch without squashing Phase 8 history. See
[PHASE_8_REVIEW.md](PHASE_8_REVIEW.md) and
[PHASE_8_LESSON_SPEC.md](PHASE_8_LESSON_SPEC.md). The review remains unchanged;
its provisional status wording is superseded by the user's final confirmation.

The five-step lesson uses the Phase 7 engine. Explicit checks acquire fresh,
session-owned CAD evidence and produce deterministic PASS / FAIL / WARNING /
UNVERIFIED. Feature names are not evidence. The single-L-profile alternative and
two-extrusion path remain supported; verification can be revoked and restored by
subsequent checks independently of learner-marked completion. Evidence limits stay
explicit; no whole-design or engineering-certification claim is introduced.
No CAD writes, FeatureScript, new OAuth scope or AI-chosen status is added.

## Phase 9 — FIRST SAFE CAD EDIT

Phase 9A is **PREPARATION COMPLETE** on `phase9/safe-cad-edit-prep`, recorded in
`b95e866687e024d88dcd2e8c0e4304b94390f296`.
[The safe-write specification](PHASE_9_SAFE_WRITE_SPEC.md) selects exactly
`suppress_terminal_fillet_v1`: suppress an active ordinary standard Fillet at the
end of an unconfigured workspace Part Studio. Its architecture remains proposal →
explicit approval → fresh state/version check → guarded write → post-write
verification. Stale approval is rejected and the provider microversion guard is
mandatory. No generic Onshape API authority or arbitrary FeatureScript is allowed.
[The preparation review](PHASE_9_PREP_REVIEW.md) records the preparation gate.

Phase 8 is integrated. Phase 9B is **IMPLEMENTED / AUTOMATED TESTED**; see
[the runtime review](PHASE_9_REVIEW.md). Opaque candidates, explicit approval,
atomic PostgreSQL claims/fences, fresh full-definition evidence, the original
provider microversion guard and deterministic verification implement the 9A
boundary. Known OAuth2Write consent remains required; no generic write authority
exists. The backend flag defaults OFF and writes returned OFF after testing.

**Gate A: PROVEN.** The human-approved real terminal-Fillet suppression succeeded
and Forge reached verified success from fresh evidence. **Gate B: expected
stale-write behavior observed.** The human advanced the workspace during the
conformance pause and stale suppression did not apply. Provider-side rejection
audit confirmation was deferred; full provider conformance is not yet proven.

The explicitly authorized terminal-suppression evidence revision supports a present
empty v17 state map as unavailable, with no inferred feature health. Complete maps
remain strict; partial/invalid maps reject. Structural suppression, one solid-body
result, original-version approval/guard and fresh verification remain required.
This changes no phase scope or human conformance gate.

The subsequent explicit auxiliary-suppression revision permits exactly null as
unavailable evidence only when all other suppression evidence is safe.
Strict ordinary objects remain supported; specialized/malformed/missing states
reject. The next explicit revision supports omitted parent/configured flags through
complete restricted top-level structure and the pinned independent configuration
endpoint. These are evidence modes, not inferred false. Explicit conflicts reject;
raw presence and modes remain approval/verification-bound. No feature-state policy,
broader edit authority or Gate A/B change.

The current body policy binds exact immutable requested/returned microversion
identity. Both optional marker flags absent means explicitly unavailable evidence,
never false; both explicit false flags remain supported. True/null/malformed/mixed
flags reject. One SOLID, supported body error state, pinned reads, head bracketing,
approval and original provider guard remain required. The evidence modes do not
relax approval, execution or verification. Writes remain OFF after human testing.

The first real human-approved suppression reached uncertainty, with no retry or
success claim. The comprehensive repair retains strict comparisons, adds full
returned Sketch evidence and fixed complete failure diagnostics under policy 6.
The exact historical failure is not recoverable; no unobserved normalization or
timeout relaxation is justified. Separately authorized development-only operator
recovery has now removed the exact orphaned uncertainty fence under the existing
user lock, with an atomic fixed audit, no Onshape contact and writes OFF. Normal
fence semantics and the historical uncertain result are unchanged. The subsequent
fresh Gate A rerun is proven; Gate B still lacks provider-side rejection audit
confirmation. Phase 10 main history is now integrated here without squashing.

The earlier Reality Lock/inventory and assemblies/mates topics remain unassigned
future work. Mistake investigation is implemented in the actual Phase 10 below;
obsolete phase numbers do not authorize broader Modify or autonomous workflows.

## Phase 10 — Mistake investigation + independent transfer learning (merged, not yet human-validated)

Implemented on `phase10/mistake-transfer-learning`, branched from main after Phase 8, in parallel with
Phase 9 (first safe CAD write, a separate branch). Phase 10 is read-only, authored and session-local, with no
AI in the core flow. It was merged to `main` at the team's request before Phase 9 and before real Onshape
validation; this merge integrates it into the Phase 9 branch. See [PHASE_10_REVIEW.md](PHASE_10_REVIEW.md) and
[PHASE_10_LEARNING_SPEC.md](PHASE_10_LEARNING_SPEC.md). Automated validation is
complete; the real-Onshape human plan is not yet recorded as complete. Phase 10
Learn remains independent of Modify and requires no write consent.

## Phase 11 — Contextual AI tutor in Learn Mode (merged, automated checks pass; human validation not recorded)

`phase11/contextual-ai-tutor`, from main after Phases 9 and 10. Ask Forge is explicit-send only, read-only and
session-only; check results reach it only through a server-signed, session-bound evidence token; deterministic
checkers keep all authority. Implementation commit `7f86ba4` was merged into main
through PR #5 at `56bf83b85eb33c6c2d6277b9a289ae1edab8b71c`. Subsequent full
automated repository gates passed; real Onshape human validation is not recorded
as complete. The historical review's unmerged status is superseded by that merge.
Phase 9 Gate B's provider-side audit remains deferred. See
[PHASE_11_REVIEW.md](PHASE_11_REVIEW.md) and [PHASE_11_TUTOR_SPEC.md](PHASE_11_TUTOR_SPEC.md).
At the Phase 11 review, Phase 12 had not started; the separately authorized
Phase 12 work is recorded below.

## Hackathon Modify A1 — deterministic core implemented on its branch

A1 adds five typed semantic operations, server-owned 1–5 operation plans, private
target resolution, sequential guarded execution and deterministic per-step results.
The Phase 9 browser workflow remains unchanged. No AI planner or general Modify UI
is included; Team B planner integration is next. Exact narrow provider shapes and
remaining live-validation work are documented in [HACKATHON_MODIFY_A1.md](HACKATHON_MODIFY_A1.md).
CAD writes stay OFF. Phase 9 Gate A remains proven; Gate B provider audit remains
deferred. This branch is not merged by A1 implementation work.

## Hackathon Modify B1

B1 adds the natural-language planner backend, stopping at the A1 plan preview. B2 will add
the plan-preview UI and the human approval flow. CAD writes stay OFF by default; Phase 9
Gate A remains proven and Gate B provider audit remains deferred. See
[HACKATHON_MODIFY_B1.md](HACKATHON_MODIFY_B1.md).

## Hackathon Modify A2

A2 exposes A1 human approval, bounded execution progress, owner-scoped status and
atomic pending cancellation through generalized plan routes. It preserves B1's
preview-only authority and the existing Phase 9 browser flow. B2's live Modify UI
and disposable real Onshape validation remain future work. No new operation,
OAuth permission or migration. See [HACKATHON_MODIFY_A2.md](HACKATHON_MODIFY_A2.md).

B2 implements the live natural-language Modify UI over the integrated A1/B1/A2
contracts. Controlled disposable-document validation is still pending; no CAD scope
or OAuth changes are added. See [HACKATHON_MODIFY_B2.md](HACKATHON_MODIFY_B2.md).

Retained-record administrative recovery V1 is implemented for development, writes
OFF and synthetic verification only. It supports a separately authorized narrow
single terminal Fillet suppression closure without restoring historical browser
authority. Actual live recovery is a separate review/authorization step and remains
pending; no fence is cleared by implementation work. See
[RETAINED_RECORD_OPERATOR_RECOVERY.md](RETAINED_RECORD_OPERATOR_RECOVERY.md).

The October 20 administrative recovery is CLOSED. The temporary one-incident
implementation, enrollment, sunset logic, audit emitter allowance and dedicated
tests have been removed. Normal retained-record V1 and Modify remain unchanged;
no serialization exception was introduced. See the
[closed incident record](LEGACY_RETAINED_RETIREMENT.md).

## Deployment track Phase 1 — production hosting foundation

**DEPLOYMENT FOUNDATION MERGED INTO MAIN — NOT YET HOSTED.**
Authorized separately from product phases, starting at
`c10744b10d897ab9bd4ebb8b650b5d8ce39c1a9f` on `deploy/railway-foundation`.
One Railway service/image serves the SPA and FastAPI on one HTTPS origin; private
PostgreSQL, pre-deploy Alembic, exact production iframe headers, fail-closed static
configuration and a one-worker runtime are prepared and locally testable.
Phase 9 and normal retained recovery V1 remain unchanged. No legacy recovery path
returns, no CAD writes are enabled, and no live data or Onshape registration changes
are authorized. [DEPLOYMENT.md](DEPLOYMENT.md) records the foundation and gates.

Railway provisioning, runtime secrets, real migrations, callback/Action URL changes,
real OAuth/AI/embedded validation and custom-domain transition are later authorized
operations. The foundation merged into main at
`8d72cafc5cf94b79a7e38e15f17e4bc7b37817c1`. Live Railway provisioning is not
completed; no production secrets, OAuth cutover or hosted validation have occurred.

## Phase 12 — ForgeModelGraph foundation

**COMPLETE — AUTOMATED GATE PASSED — MERGED INTO MAIN.**
Merged at `e6a14d32a1a95d92fe9d03cf4edce71ee22a4640`, preserving the foundation
commit `ee827e191dc8e9c85085363686b68990dcf2f442` and query review-fix commit
`ee5040fd54bf6deca03974298542b6da4ac05c9b` without squashing.

Starting from merged deployment main `8d72cafc5cf94b79a7e38e15f17e4bc7b37817c1`
on `phase12/forge-model-graph`, this separately authorized product phase adds a
versioned deterministic read-only internal structural graph over existing normalized
workspace Part Studio evidence. Typed IDs, supported membership/order/reference
edges, provenance, validation, bounded serialization and narrow queries are in scope.

No live Onshape validation was required or claimed for Phase 12. ForgeModelGraph
remains an internal foundation without broad production consumer adoption.
No deployment changes, new provider acquisition, public graph endpoint,
OAuth scope, CAD-write/recovery authority or broad subsystem migration is included.
There is no selection ownership inference, dependency DAG, topology continuity
guarantee or engineering-correctness claim. Railway remains not hosted. See
[the Phase 12 specification/review](PHASE_12_FORGE_MODEL_GRAPH.md).
After the narrow query review fix, the gate passed 127 focused graph tests,
827 frontend / 2,612 API tests (including
all 42 PostgreSQL cases), 594 browser tests and all required format/lint/type/build /
migration/Compose/audit checks. This is automated evidence only. At that merge, Phase 13 was not started;
its subsequent separate authorization and implementation are recorded below.

## Phase 13 — first ForgeModelGraph consumer: CAD Inspector

**COMPLETE — HUMAN READ-ONLY VALIDATION PASSED — MERGED INTO MAIN**

Authorized from `main` at `6f7d147dc4239dbe7b52c775eef9c4e2a7f12039` on
`phase13/inspector-graph-adoption`; implementation commit
`7696aa0e51002725811379123f498cb91da1e3ff` and human-validation documentation commit
`bef41d2e13cca67e7436f06e4c09564e232867e8`. Human read-only validation passed.
Phase 13 merged into main at `c200f0af5695a3c603074bdf3e640965a8d84171`,
preserving both commits without squashing. Only direct read-only Inspector feature
inventory/order adopts the graph, preserving an independent validated request
context and same-Snapshot rich evidence. Public schema/UI, parts/bodies/physical
presentation, provider reads and other consumers remain unchanged. Invalid graph
evidence fails closed. The implementation gate passed **276 focused tests**,
**827 frontend / 2,712 API tests**, **594 browser tests** and all required automated
checks; the implementation's full verification record is preserved in
[the Phase 13 review](PHASE_13_INSPECTOR_GRAPH_ADOPTION.md).

The human reported read-only validation in real Onshape workspace Part Studios,
using the local HTTPS Forge development environment on the Phase 13 branch, with
**CAD writes OFF**. The normal model contained Sketch Gate → Extrude 1 → Fillet 1
and 1 part. Refresh CAD showed those **3 modeled features in exact order**, recognized
as **Sketch, Extrude and Fillet**, all **Active**, with normal expanded parameter
presentation, **1 part**, **1 SOLID body** and conservative physical evidence
(mass unavailable; no invented mass value). No graph/provider IDs, provenance,
graph bytes or other graph internals were exposed. Onshape's larger visible Features
count includes default Origin/planes and does not contradict the three modeled features.

The empty Part Studio refreshed to **0 features / 0 parts / 0 bodies**, as successful
empty inventory rather than unavailable evidence, with no previous inventory remaining.
Switching back and refreshing restored **3 / 1 / 1** and
**Sketch Gate → Extrude 1 → Fillet 1**; switching again to the empty Part Studio and
refreshing restored **0 / 0 / 0**. No stale inventory persisted across those transitions.

The human observed no CAD mutation, feature suppression/unsuppression, write proposal,
approval prompt or additional Onshape consent prompt. No Phase 9 write validation
was performed or required. This evidence does not establish atomic reads, general
production readiness, graph adoption in AI/Tutor/Learn/Modify, topology continuity,
feature ownership, dependency DAG correctness or engineering correctness. Known
limitations remain: reads are sequential/non-atomic, Phase 13 adds no CAD authority,
ownership inference or dependency DAG, and gives no topology continuity guarantee
or engineering-correctness claim. Railway remains unhosted. See the linked review
for the complete human-observed record.

## Phase 14 — graph-grounded Ask Forge

**COMPLETE — HUMAN READ-ONLY + UX VISUAL VALIDATED — MERGED INTO MAIN**

Real Onshape human read-only validation passed all eight scenarios, and the
post-polish targeted real-Onshape UX visual recheck passed all seven scenarios,
as reported by the user. Phase 14 was merged into `main` at
`c70c649b64a40ae6cd941854f018f5fb789579b8`, preserving all four Phase 14 commits
without squashing or rewriting. CAD writes remain OFF. A larger UI overhaul and
final overall visual design remain future work; no production readiness is claimed.

Authorized from clean synchronized main
`204725ce141df6f2cccdaa7241f618b0989a7f62` on
`phase14/ask-forge-graph-grounding`. Implementation migrates only normal read-only
Ask Forge feature inventory/order to the existing graph, sharing one construction
with its same-Snapshot rich Inspector projection. Bounded canonical AVAILABLE
returned-order and completeness-proven terminal facts retain fixed semantics and
the existing evidence limits. Graph/context/correspondence rejection fails closed.
Direct Inspector remains the Phase 13 consumer; Tutor/Learn/Check my step/Modify
remain unmigrated. Explicit sends, session/grant revalidation, at most four GETs,
selection ownership UNKNOWN and zero-model-call write capability replies remain.

Automated verification and human-validation status are recorded in
[Phase 14](PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md). The user reported PASS for all
eight real Onshape read-only scenarios on the pre-polish implementation, using a
disposable Part Studio containing Sketch Gate → Extrude 1 → Fillet 1, plus an
empty Part Studio. The recorded checks cover inventory/order, returned order,
terminal feature, explicitly unestablished dependency, active feature state,
unknown ownership of a selected real FACE, read-only write rejection without
invented width parameters, and empty counts without stale evidence. These are
human-supplied observations, not live checks independently repeated by the agent.
The pre-polish implementation's
focused tests (50), full frontend/API tests (827/2,762, including all 42
PostgreSQL cases), format/lint/types, build, migrations, Compose and audits passed.
The final complete `make test-e2e` passed all 594 cases with the normal four workers
and zero retries after the user confirmed machine availability. Earlier loaded-host
browser failures are retained in the Phase 14 record; no source, tests or time
budgets were changed to obtain the pass.
The follow-up changes concise answer formatting, contextual Limits/detail hierarchy
and auto-hiding mode navigation only; the eight semantic outcomes and all backend
authority boundaries are preserved. Its final gate passed 83 focused frontend
tests, 50 graph regressions, 51 focused browser cases, 869 frontend / 2,762 API
tests (including all 42 PostgreSQL cases), all standard quality targets and all
633 browser cases with four workers and zero retries/skips. The user subsequently
reported PASS for concise dependency and active-state answers, selected-face
unknown ownership, inventory and empty-model presentation, scrolling mode-bar
visibility without content jumps or loss of composer access, and keyboard focus
revealing/retaining navigation. Relevant Limits stayed visible while full
technical caveats remained in Evidence. The complete seven-case UX record is in
the same Phase 14 record, alongside the earlier automated results.

The pre-merge human-validation closeout was documentation only; the validated implementation
at `53ff762b30a358818e6f6b57a447aa7d9cbd1267` and its two preceding Phase 14
commits are preserved. The closeout passed lint, strict typing, dependency audits
(zero known vulnerabilities), all 50 graph regressions and all 83 focused
presentation/navigation tests. No full browser/API/database rerun was required
for those documentation changes. At that closeout, final merge review was still
required and no merge was performed.

The subsequent non-fast-forward merge preserved the exact validated tree at
`587001f485a28fe2dcda724c1ef32b6a50c56d26` and all four commits:
`6b17074bfd12b1ad3d96563e92a79c5da39e29cd`,
`f756564cf7818d3060adf09e5808105413cece45`,
`53ff762b30a358818e6f6b57a447aa7d9cbd1267` and
`587001f485a28fe2dcda724c1ef32b6a50c56d26`. Merged-tree lint, strict typing,
build, audits, all 50 graph regressions and 83 focused presentation/navigation
tests passed before pushing main. Phase 14 and deployment branches were retained;
no Railway deployment or Phase 15 work was performed.

PRECEDES is returned order,
not dependency; no ownership inference, selected-face/edge ownership, dependency
DAG, topology continuity, engineering correctness or new CAD authority is added.
Reads remain sequential/non-atomic, CAD writes remain OFF and Railway remains unhosted.

## Phase 15 — graph-grounded Learn Tutor

**COMPLETE — HUMAN READ-ONLY VALIDATED — MERGED INTO MAIN**

Implementation on `phase15/tutor-graph-grounding` from clean synchronized `main`
`500e114b7356b90499988633dd7811c49b94937c`. Final real-Onshape human read-only
validation passed, as reported by the user; the agent did not independently
execute those checks. Phase 15 merged into main at
`36511d73a7fffd4b219497fe09d2c8d4ff86bca5`, preserving all five Phase 15 commits
without squashing.
Only learner-requested contextual Tutor CAD grounding adopts the Phase 14 shared
`GroundedCad`/`ground`/`project` path, using the same acquired Snapshot and independent
validated request context. Direct Inspector is the Phase 13 consumer, Design Ask
Forge Phase 14 and Learn Tutor Phase 15. Modify remains unmigrated. Check my step
remains deterministic and unchanged, including signed check-token authority and
historical-check/current-CAD separation.

Bounded AVAILABLE adjacent order facts, complete-evidence terminal facts and fixed
relationship caveats add zero provider reads. Server presentation prevents returned
order from becoming a dependency/ownership claim. PRECEDES is returned order, not
dependency; there is no dependency DAG, feature ownership inference, selected-face/
edge Tutor grounding, topology continuity guarantee or engineering-correctness
claim. Graph failure and combined evidence overflow fail closed. No new CAD authority,
scope, persistence, write, migration, deployment or Tutor UI redesign is included.
Reads remain sequential/non-atomic; the full UI overhaul remains future work.
Railway remains unhosted. See [Phase 15](PHASE_15_TUTOR_GRAPH_GROUNDING.md) for
automated verification and the current human read-only validation record.

The branch gate passed **69 focused Phase 15 / 226 existing targeted tests**,
**869 frontend / 2,831 API tests** (including all **42 PostgreSQL cases**, no skips),
and **633 browser tests** (211 in each engine, four workers, zero retries).
Frozen installs, formatting, lint, strict types, build, migration drift, Compose and
dependency audits passed. The isolated synthetic database was removed after checks;
existing local data remain untouched. No real CAD write or hosted deployment was
performed during that automated gate. Human validation subsequently passed as
recorded below; the subsequent merge is also recorded below.

The separately authorized relationship-guard precision refinement distinguishes
explicit relationship questions and unsupported current-model prose from ordinary
use/input questions and clearly general CAD teaching. It preserves the fixed
dependency/ownership boundary and all Phase 15 authority limits; no graph semantics,
acquisition, signed checks, UI or evidence limits change. See the Phase 15 record
for its separate verification results. Human validation was pending at that stage.
Its gate passed **100 precision / 69 Phase 15 / 169 existing targeted cases**,
**869 frontend / 2,931 API tests** (all **42 PostgreSQL cases**, no skips) and
**27 focused Tutor browser tests** with four workers and zero retries. Frozen
installs, formatting, lint, strict typing, build, migration drift, Compose and
audits passed. No scope expansion, CAD write, UI change, merge or deployment.

**Subsequent live human validation Test 1 FAILED:** correct canonical graph
inventory/order was shown, but the presentation guard replaced the primary
inventory answer with a dependency lesson. The repair preserves the
existing working edits, separates explicit relationship intent from incidental
model prose, and makes simple structural primary presentation server-owned from
canonical facts. The repair gate passed **46 structural / 100 precision / 69 Phase
15 / 226 existing targeted cases**, **869 frontend / 2,977 API tests** (all **42
PostgreSQL cases**, no skips) and **27 focused Tutor browser cases** with four
workers and zero retries. Frozen installs, format/lint, strict types, build, drift,
Compose and audits passed. At that repair's completion human revalidation was
pending. Graph semantics,
acquisition, checks/tokens, OAuth, Modify, CAD-write authority,
UI layout, database/migrations, deployment and evidence limits remain unchanged.

**Subsequent human rerun Test 1 PASSED and Test 2 PASSED**, as reported by the
user. **Test 3 was a safety pass / functional validation failure:** the dependency
answer remained conservative but omitted the relevant verified order fact. The
narrow repair adds server-owned adjacent canonical order for uniquely matched
two-name dependency questions; order remains separate from dependency, in either
question direction. Missing/malformed/ambiguous facts keep the existing fallback.
The automated repair gate passed **41 new dependency-grounding cases**, the
existing targeted suites, **869 frontend / 3,018 API tests** (all **42 PostgreSQL
cases**, no skips) and **27 focused Tutor browser cases**. Frozen installs,
format/lint, strict types, build, migration drift, Compose and audits passed.
Human Test 3 rerun and remaining validation were pending at completion of that
repair; the final passing human record follows. CAD writes remain OFF.

### Final Phase 15 human read-only validation

**All seven scenarios PASSED**, as user-reported real-Onshape human observations,
not checks independently executed by the agent. The primary disposable Part
Studio contained **Sketch Gate → Extrude 1 → Fillet 1**, with **one part**; an
empty Part Studio was also used. Forge CAD writes remained **OFF** throughout.

| Test | Result                | Reported observation                                                                                                                                  |
| ---- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | **PASS AFTER REPAIR** | Inventory rerun showed 3 modeled features in correct returned order, with no dependency claim; initial guard failure repaired in `7f357ab`.           |
| 2    | **PASS**              | Extrude 1 comes before Fillet 1; canonical observation shown separately, with no dependency, ownership, parent-child, causal or driving claim.        |
| 3    | **PASS AFTER REPAIR** | Dependency stayed unconfirmed while Sketch Gate-before-Extrude 1 order was verified, with an explicit order/dependency caveat; repaired in `cd9cf86`. |
| 4    | **PASS**              | Fillet 1 was identified as the third, terminal feature using completeness-backed evidence, not merely its visible position.                           |
| 5    | **PASS**              | Latest check stayed Verified after manual Fillet 1 suppression; current CAD correctly showed suppressed and did not update the old sketch check.      |
| 6    | **PASS**              | Fixed read-only teaching response; no Modify flow, proposal, approval UI or CAD mutation. Check my step remained the verifier.                        |
| 7    | **PASS**              | Switching to the empty Part Studio yielded 0 modeled features, with no stale names, inventory, fake terminal or relationship inference.               |

The user restored Fillet 1 after Test 5. Only the user performed that manual CAD
change; Forge's write flag remained OFF. Onshape's default Origin/planes in the
empty Part Studio are not modeled-feature inventory and do not contradict zero
modeled features. Full questions, observations, initial failures, repair SHAs and
all five Phase 15 commits/messages are preserved in the
[Phase 15 record](PHASE_15_TUTOR_GRAPH_GROUNDING.md).

The pre-merge documentation-only human-validation closeout was committed as
`dc383b9314d3e7c5798e0e295abd856b90530f23`, leaving the validated implementation
at `cd9cf86709db4c8841a9a7325bc81833f1016660`. That closeout included no
implementation, test, dependency, lockfile, OAuth, database, migration, Modify,
deployment or safe-write change. No merge was performed at that closeout;
production readiness was not claimed.

Closeout checks passed: `make lint`, `make typecheck`, `make audit` (no known
vulnerabilities) and **256 focused Phase 15 tests** across graph, relationship
precision, structural presentation and dependency grounding. The unchanged
implementation's full API/browser verification remains recorded above; no full
API/browser rerun was performed for this documentation-only closeout.

### Phase 15 merge into main

Merge commit `36511d73a7fffd4b219497fe09d2c8d4ff86bca5` preserved all five Phase
15 commits without conflicts or squashing. Its tree was identical to the validated
branch at `dc383b9314d3e7c5798e0e295abd856b90530f23`. Merged-tree lint, strict
types, build, audits and **256 focused Phase 15 tests** passed. Main was pushed and
verified synchronized with origin; the working tree was clean. The Phase 15 and
deployment branches were retained. The merge introduced no changes beyond the
validated branch. No Railway deployment or Onshape write was performed during
the merge. CAD writes remained OFF; this does not establish production readiness.

### Future Learn/Tutor UI work only

Learn currently feels visually crowded, according to the user. A future direction
may make Ask Forge a more dominant/floating assistant entry point: a floating
Forge/chat bubble or icon that expands into a chat surface. Future UI work should
consider smooth open/close animations, narrow-panel responsiveness, keyboard accessibility,
`prefers-reduced-motion` fallback and a compact Limits/details disclosure for
“Still unknown.” None of these UI changes is implemented in Phase 15 or this
closeout; the full Learn/Tutor UI overhaul remains future work.

Reads remain sequential/non-atomic. PRECEDES is returned feature order, not
dependency; no dependency DAG, feature ownership inference, selected-face/edge
Tutor grounding, topology continuity guarantee or engineering-correctness claim
is added. Check my step remains the only correctness authority, signed check-token
authority is unchanged, and Tutor CAD observations cannot update a check result.
Modify is not graph-migrated by Phase 15, and no new CAD authority is granted.
CAD writes remain OFF and Railway remains unhosted. Phase 15 is **COMPLETE — HUMAN
READ-ONLY VALIDATED — MERGED INTO MAIN** at `36511d73a7fffd4b219497fe09d2c8d4ff86bca5`.

## Phase 16 — controlled real Modify conformance

**IN PROGRESS — EXTRUDE QUANTITY CONTRACT REPAIRED; FINAL WRITES-OFF EXACT-MATCH REFRESH REQUIRED**

Latest human evidence is complete and agrees across both existing response
variants. All ten Extrude quantity roles use the exact observed common envelope;
active depth retains its positive-length authority, while each dormant role is
bound explicitly to its observed literal number format, sign, dimension and unit.
In particular, only thickness2 accepts the observed unsigned integer zero-inch
form; there is no general zero/dormant-length rule. Role substitution, missing or
extra fields, malformed metadata and wrong cached states reject. Fillet and all
query-filter contracts are unchanged. The synthetic full profile now reaches
exact_match for both features, with clean 13/13 and 8/8 query evidence. The
automated gate passed: 169 new quantity cases, 3,245 affected cases, 6,898 focused
regressions, all 8,460 API cases (including 42 PostgreSQL cases), 869 frontend
cases and 45 Modify browser cases, without skips. Frozen installs and required
format/lint/type/build/test/migration/Compose/audit checks passed. One final
same-fixture human writes-OFF exact-match refresh remains required. Live
conformance is still unproven and writes stay OFF.

Complete human 13/13 Extrude and 8/8 Fillet evidence now supports explicit typed
production contracts for every current ordinary query role. Active entities require
one query; all 19 dormant roles require empty queries plus their exact observed
subtype/operand topology, leaf fields/values, node counts and depth. Equal trees
retain distinct caller/provider role identities. Only Extrude extrudeDirection
has a fixed depth-9 / 17-node exception; other production role ceilings stay 8.
The filtered ordinary profile requires all 50/38 serialized parameters and every
query filter, without projecting into historical/older profiles. Full preservation
and all authority/fence/post-write/recovery controls remain unchanged. Suppression
retains its independent attribute-only transport. The replacement budget was
initially implemented incorrectly as 32 KiB in 99bc6f8; the authorized ceiling is
now corrected to **24 KiB / 24,576 bytes**. Ordinary/public/suppression limits
remain 8 KiB. Query-role contracts are unchanged by this correction.
The ceiling-correction gate passed 1,243 affected and 6,683 focused cases,
all 8,245 API / 869 frontend cases (all 42 PostgreSQL cases, no skips), and
45 Modify browser cases. Frozen installs and the full format/lint/types/build /
test/migration/Compose/audit gate passed with real CAD writes OFF.
The query-contract gate passed 1,247 new cases, 2,004 targeted cases, all 600
unchanged active-entities cases, 6,673 focused cases, all 8,235 API / 869 frontend
cases (including all 42 PostgreSQL cases, no skips), and 45 Modify browser cases
across Chromium/Firefox/WebKit. Required format/lint/types/build/test/migration /
Compose/audit gates passed; lockfiles are unchanged and real writes remain OFF.
One final same-fixture writes-OFF Inspector refresh must show exact_match for both
features/variants and replacement/rename diagnostics, with the safe no-proposal /
no-write probe. Actual live conformance remains unproven; no writes are enabled.

Latest human checkpoint is complete for both variants: 13/13 Extrude and 8/8
Fillet roles, clean evidence flags, one SOLID / NO_ERROR body, no proposals or
mutations. Before accepting dormant roles, reconstructed complete replacement
payloads exposed the inherited 8 KiB fence (14,771 / 10,782 bytes). The human
explicitly authorized a separate bounded payload repair: only validated full
rename/depth/radius replacements gain a fixed 24 KiB envelope; ordinary requests,
suppression and public parsing remain at 8 KiB. Representation acceptance and all
approval/stale/fence/microversion/verification/recovery controls are unchanged.
The original byte-budget gate (before the 24 KiB correction) passed 43 new cases,
5,426 focused cases, all 6,988 API / 869 frontend cases (all 42 PostgreSQL cases,
no skips), and 45 Modify browser
cases across Chromium/Firefox/WebKit. Frozen installs and all required format /
lint / types / build / test / migration / Compose / audit checks passed. Real
writes remain OFF; only the explicitly authorized replacement-byte bound changes.
Exact dormant-role production acceptance and the final writes-OFF exact-match
checkpoint remain pending; no live-write success is claimed.

Started from clean synchronized main `017f4ab7e556b2653661cbda77b7b6f22cdf1a1c`
on `phase16/modify-live-conformance`. Scope is the existing SET_SUPPRESSED,
SET_UNSUPPRESSED, RENAME_FEATURE, SET_EXTRUDE_DEPTH and SET_FILLET_RADIUS only.
The [Phase 16 record](PHASE_16_MODIFY_LIVE_CONFORMANCE.md) audits current authority,
synthetic representation assumptions, conformance tests, automated gate, ordinary
disposable UI fixture and later human one-operation-at-a-time validation.
No live conformance is claimed; no real CAD write, deployment or Phase 17 creation
work is performed during preparation. The real flag stays OFF. Any later live write
requires the passing gate, exact disposable target, representation review, exact
preview and explicit human approval. Graph facts must never authorize a write;
Modify is not graph-migrated in this phase.

Latest human result: **FINAL WRITES-OFF RECHECK — STILL NO-GO**. DEFAULT
metadata now passes; both Extrude and Fillet first fail on entities /
unexpected_field. Structural/source evidence remains good; zero proposals,
approvals or mutations. Current OpenAPI documents optional polymorphic filter
metadata, but the real trees and inactive-role serialization are unknown. Only
closed structural evidence is added to the shared production rejection; no
filter acceptance or authority expansion. One more same-fixture writes-OFF
Inspector refresh is needed. No live conformance is claimed.
The diagnostic-only preparation passed 412 added cases (411 in the new module and
one new shared-failure case), 4,169 focused cases, all 5,731 API / 869 frontend
cases (all 42 PostgreSQL cases, no skips), and 45 Modify browser cases across
Chromium/Firefox/WebKit with four workers and zero retries. Frozen installs,
format/lint/types/build, migration/Compose and audits passed with real writes OFF.
No filter acceptance was added; the verdict remains QUERY FILTER EVIDENCE NEEDED.

Final pre-commit review found a legacy minimal-profile nested-field bypass, before
writes were enabled and with zero real proposals/approvals/mutations. The 13-file
diagnostic work was preserved. Historical profiles now require complete exact
ID multisets and closed parameter/query envelopes; other features validate whole
through the current-UI contract, with no fallback or hybrid. Suppression retains
its separate attribute-only payload and existing terminal-Fillet authority.
The combined repair passed 162 new safety cases plus the preserved 412 diagnostic
cases (574 added total), 4,331 focused cases, all 5,893 API / 869 frontend cases
(including all 42 PostgreSQL cases, no skips), and 45 Modify browser cases across
Chromium/Firefox/WebKit with four workers and zero retries. Frozen installs and
all required format/lint/types/build/test/migration/Compose/audit gates passed.
Final security review confirmed complete replacement profiles, no ignored nested
fields, attribute-only suppression and real writes OFF.
No filter contract or real write conformance is claimed; the next human action
remains one same-fixture writes-OFF Inspector refresh for bounded filter evidence.

Latest human filter evidence confirms and roots, 13 visits/depth 5 (Extrude) and
17/depth 8 (Fillet), but collapsed other_known labels and unordered categories
cannot prove exact role-specific semantics. The diagnostic now distinguishes all
37 concrete SDK types plus the abstract base, and emits closed ordered topology
and finite enum/Boolean states. Depth 8 / visits 64 and existing DEV/writes-OFF
privacy guards remain. Source-derived FeatureScript 3095 candidates have matching
counts, but are synthetic, not real serialization proof. No filter acceptance,
legacy-profile change, suppression authority or new provider GET is introduced.
The diagnostic gate passed 217 new cases, 875 targeted cases, 4,548 focused cases,
all 6,110 API / 869 frontend cases (including all 42 PostgreSQL cases, no skips),
and 45 Modify browser cases across Chromium/Firefox/WebKit with four workers and
zero retries. Frozen installs and format/lint/types/build/test/migration/Compose/
audit gates passed; no dependency change or weakened bound. Real writes stayed OFF.
One same-fixture writes-OFF Inspector refresh is required for closed signature and
leaf-state evidence. All five live operations remain unproven.

The next human refresh reported the exact closed topology for both features.
Fillet reached `uninspected=false`; Extrude's only remaining opaque family was
`flat_sheet_metal`. The follow-up projects its official optional `allows` enum
through fixed labels and checks the exact diagnostic field envelope. It adds no
acceptance, read, approval or write authority. A further single same-fixture human
writes-OFF Inspector refresh must show complete, well-formed Extrude evidence and
explicit closed `allows` states before a later task can construct an exact
role-specific filter acceptance contract. All live writes remain unproven/OFF.

The human has now supplied complete exact Extrude/Fillet entities evidence,
including the two distinct flat-sheet-metal states and all Fillet optional leaf
fields, with every structural flag false. The current-UI validator now accepts
only those two exact role-specific structures/typed states. Other roles and all
deviations still reject. Full-feature requirements, exact historical ID sets,
independent suppression, approval/execution/verification/recovery and graph
boundaries remain unchanged. The next gate is a human writes-OFF exact-match
refresh for both complete feature representations; automated success does not
prove any of the five live writes or authorize Phase 17, deployment or writes ON.

The following human checkpoint progressed through entities but exposed Extrude
surfaceEntities and Fillet side1Face as first unsupported filters. Full
representation exact_match is still unproven. A bounded read-only query-role
inventory now derives every present query-bearing role and emits closed filter
evidence plus feature completeness flags in one Inspector refresh, including all
empty selections. Current full fixtures yield 13 Extrude / 8 Fillet roles; actual
returned sets must be evidenced. Existing strict entities contracts and every
other eligibility/approval/write/recovery boundary are unchanged. The next human
writes-OFF refresh inventories all remaining roles simultaneously; it does not
authorize a dormant filter, proposal, approval or mutation.

The complete human inventory confirmed the 13/8 role sets but inspected only
4/6: allow_mesh_geometry and mate_connector were opaque, and extrudeDirection
exceeded diagnostic depth 8. The follow-up closes only these evidence gaps using
verified Boolean schema fields and a separate inventory depth-16/64-node allowance.
Production acceptance remains depth 8 with exact entities contracts; dormant roles
still reject. Current complete projections, privacy, bounded output and every
write/approval/recovery boundary remain. The next human writes-OFF refresh must
show 13/13 + 8/8, clean aggregate flags and the actual complete direction tree
before a later authorized dormant-role contract. No live write conformance claimed.

Previous DEFAULT repair passed 251 new-module cases plus 18 additional malformed
variants (269 added cases), 3,757 focused cases, all 5,319 API / 869 frontend cases
(including all 42 PostgreSQL cases, no skips), and 45 Modify browser cases across
Chromium/Firefox/WebKit with four workers and zero retries. Frozen installs,
format/lint/types/build, migration/Compose and audits passed. Real writes stayed
OFF and actual live write conformance remains unproven.

Previous common-metadata preparation passed 405 new cases, 3,488 focused cases,
all 5,050 API / 869 frontend
cases (including all 42 PostgreSQL cases, no skips), and 45 Modify browser cases
across Chromium/Firefox/WebKit with four workers and zero retries. Frozen installs,
format/lint/types/build, migration/Compose and audits passed. Writes remain OFF;
this automated pass authorizes only the next human writes-OFF recheck.

Preparation passed 129 new conformance cases, 1,585 focused backend cases, 108
focused frontend cases, the full 869 frontend / 3,147 API tests (all 42 PostgreSQL
cases, no skips), and 45 Modify browser cases across Chromium/Firefox/WebKit with
four workers and zero retries. Frozen installs, format/lint, strict types, build,
migration drift, Compose, audits and secret/privacy review passed. Counts overlap.
Initial preparation changed only tests and documentation; adapters and runtime
authority are unchanged.
The isolated synthetic database was removed; application data were untouched.
Actual current-UI feature representations and all five live operations remain
UNVERIFIED. The ordinary disposable fixture and writes-OFF representation checkpoint
must precede the separately human-approved live trials. No merge or deployment.

The human subsequently reported structural eligibility PASS but replacement
conformance FAIL for an ordinary UI Extrude/Fillet: both have >20 parameters and
unrecognized quantity fields. The existing adapters correctly rejected them; no
proposal or write occurred. Public standard-library research establishes input
semantics, not the fixture's exact provider encoding. A separate closed-vocabulary
DEV diagnostic now prepares the missing sanitized evidence without changing
adapter eligibility or safety bounds. That initial repair was NO-GO pending the
second writes-OFF checkpoint; passing diagnostic tests did not advance the live gate.

The human has now supplied the second minimized checkpoint: complete/source-matched
ordinary standard features, zero unknown/malformed/duplicate source inputs and
explicit ordinary option states, including overflow=true with empty keepEdges.
The narrow repair adds closed 50-input Extrude / 38-input Fillet contracts with
explicit simple-mode guards, typed inactive inputs and exact definition copying.
The original minimal profile remains separate. No unknown fields/IDs, active richer
modes or arbitrary payloads are accepted. All authority/execution controls and
transport/quantity limits remain intact. Automation and the same-fixture writes-OFF
recheck must pass before the separate human live stage. See the Phase 16 record
for exact contracts, sources, results and next steps. Phase 16 is not live-validated.

The repair gate passed 1,024 new cases, 2,999 focused regressions, 869 frontend /
4,561 API tests (all 42 PostgreSQL cases, no skips), 45 Modify browser cases and
all required format/lint/type/build/migration/Compose/audit checks. Counts overlap.
No existing assertion, timeout or threshold was weakened. CAD writes remain OFF.
The same disposable fixture must now pass the entire strict replacement/rename
contract on a human Inspector refresh before the separately approved live stage.

That human refresh still rejected both replacements despite structural eligibility
PASS and zero proposals/mutations. The final minimized evidence exposes a definite
Extrude mismatch: defaultScope=false, while the prior contract required true. The
current official standard source excludes merge-scope controls for NEW and uses a
false UI default; the narrow contract and synthetic fixture now require observed
false, retaining NEW/SOLID/BLIND and empty scope. Fillet acceptance is unchanged.
A new guarded DEV first-failure log calls the same production validator and emits
only a fixed category/known parameter/reason. It adds no reads, public payload,
persistence or write authority. Actual conformance remains NO-GO pending the next
same-fixture writes-OFF diagnosis; automated diagnostic success is not a live pass.

Targeted diagnosis passed 84 new cases, 3,083 focused regressions, the full 869
frontend / 4,645 API tests (all 42 PostgreSQL cases, no skips), 45 Modify browser
cases and format/lint/type/audit plus build/migration/Compose checks. Counts overlap.
All writes remain OFF. The next human refresh must identify Fillet's exact first
closed failure rather than broaden its rule table from high-level metadata.

## Future target — Level-3 creation and advanced Learn

The final target is Level-3 CAD creation plus advanced Learn Mode. Planned creation
flow: natural-language requirement → engineering brief → semantic feature plan →
human preview/approval → deterministic feature creation → reread → verify → bounded
repair → editable parametric feature tree. Phase 17 may begin the creation kernel
from an empty Part Studio only after Phase 16's separate real conformance gate and
explicit phase authorization. Bounded repair never bypasses approval/write authority.

Planned advanced Learn includes guided CAD projects, contextual Tutor, Check my step,
mistake diagnosis, adaptive remediation, explanations of feature intent and
constraints/dimensions, “teach me how this model was built,” project/challenge
progression, and model-grounded lessons generated from current CAD. Existing Learn
features do not establish this entire future capability. None is implemented by
Phase 16, and Learn/graph facts gain no Modify approval or write authority.

Phase 16 remains IN PROGRESS / live NO-GO after the uncertain depth trial. A pure
exact depth-state comparison prerequisite is implemented; quantity-specific
administrative closure, historical capture provenance and independent settlement
review remain blockers. No creation or Learn capability is added by this work.

Phase 16 depth-specific administrative closure is implemented and subject to the
separate operator evidence/authorization procedure. The live record remains fenced;
recovery was not executed during development. Final human five-operation conformance
and authority/failure cases remain required before any Phase 17 creation work.
