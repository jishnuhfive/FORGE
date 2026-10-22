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

## Phase 11 — NOT STARTED

No Phase 11 implementation is included or authorized by this merge.

## Phase 11 — Contextual AI tutor in Learn Mode (implemented on its branch, automated checks pass)

`phase11/contextual-ai-tutor`, from main after Phases 9 and 10. Ask Forge is explicit-send only, read-only and
session-only; check results reach it only through a server-signed, session-bound evidence token; deterministic
checkers keep all authority. Not merged and not human-validated; Phase 9 Gate B's provider-side audit remains
deferred. See [PHASE_11_REVIEW.md](PHASE_11_REVIEW.md) and [PHASE_11_TUTOR_SPEC.md](PHASE_11_TUTOR_SPEC.md).
Phase 12 is not started.

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

**DEPLOYMENT FOUNDATION IMPLEMENTED — NOT YET HOSTED.**
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
operations. This implementation does not deploy or merge into main.
