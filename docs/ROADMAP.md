# Roadmap

Advance only with explicit phase authorization. Security, tests, deterministic
verification, documentation, and maintainability are requirements of every phase.
Later hardening does not defer security for earlier live integrations.

| Phase | Scope and completion gate                                                                                           |
| ----- | ------------------------------------------------------------------------------------------------------------------- |
| 0     | Repository foundation: reproducible scaffold, docs, tools, tests, database health, local Git                        |
| 1     | UI foundation: narrow-panel accessible layout and presentation system; no fake integrations                         |
| 2     | Onshape OAuth: secure state, server sessions, encrypted tokens, refresh/logout/disconnect tests                     |
| 3     | Onshape extension shell: real embedding, messaging and selection security, browser/session compatibility            |
| 4     | Onshape REST client: official APIs, response contracts, permissions, retries and rate limits                        |
| 5     | CAD inspector: bounded read-only workspace Part Studio evidence; live verification                                  |
| 6     | Read-only AI agent: provider adapters, strict read tools, bounded budgets, progress streaming                       |
| 7     | Learning Mode foundation: authored lesson, setup, hint ladder, vocabulary, ephemeral progress; human review: PASSED |
| 8     | Mounting Bracket + Check My Step: COMPLETE, HUMAN VALIDATED, MERGED at 81199ea                                      |
| 9     | FIRST SAFE CAD EDIT: 9A PREPARATION COMPLETE; 9B IMPLEMENTED, awaiting human CAD-write validation                   |
| 10    | Assemblies and mates: supported instances/mates verified through official APIs                                      |
| 11    | Validation engine: deterministic PASS/WARNING/FAIL/UNVERIFIED checks and evidence                                   |
| 12    | Full agent execution loop: understand/inspect/plan/approve/execute/reinspect/validate/revise/report                 |
| 13    | Modify mode: selection-aware approved changes and context freshness                                                 |
| 14    | Expanded learning and later mistake investigation; supported operations and scope require separate authorization    |
| 15    | Camera slider flagship demo: approved design using supplied inventory and at least 400 mm travel                    |
| 16    | Product/account/history polish: useful user-facing plans/actions/results, data deletion and account controls        |
| 17    | Security hardening: adversarial assessment, production policy, privilege and data boundary review                   |
| 18    | Reliability/evaluation suite: provider failure, limits, regressions, manufacturing and write-safety evaluation      |
| 19    | Production deployment: HTTPS, managed secrets/database, images, migrations, backups, observability                  |
| 20    | Onshape App Store preparation: current official launch checklist and review requirements                            |

Phase 0 is preserved in commit `2b68754`. Phase 1 implements the accessible UI
foundation, local preferences and development-only synthetic previews. Live
functionality described by later phases remains planned. Phase 2 now implements Onshape OAuth, identity persistence, encrypted refresh tokens,
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
Assemblies and mates remain Phase 10; no assembly permission or operation is added.
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

Phase 8 is integrated. Phase 9B is **IMPLEMENTED / AUTOMATED TESTED / AWAITING
CONTROLLED HUMAN CAD-WRITE VALIDATION**; see [the runtime review](PHASE_9_REVIEW.md).
The backend flag defaults OFF; external OAuth2Write permission was not enabled.
Opaque candidates, explicit approval, atomic PostgreSQL claims/fences, fresh pinned
reads, original provider guard and deterministic verification implement the 9A
boundary. Real suppression-payload and atomic stale-update gates remain mandatory
and unvalidated. Human permission changes and disposable CAD validation occur later.
Phase 10 is **NOT STARTED**.

The prior Phase 9 Reality Lock inventory topic remains planned for later explicit
resequencing; it is not dropped or implemented by this preparation. Mistake
investigation moves to the later learning backlog (Phase 14). Assemblies/mates
retain Phase 10; general Modify, a CAD tool library, Reality Lock and autonomous
workflows remain separately authorized future work.
