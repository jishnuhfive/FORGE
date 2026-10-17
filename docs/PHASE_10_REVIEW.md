# Phase 10 — Mistake investigation, prediction and independent transfer learning

**Status: implemented and automatically verified; merged to `main` at the team's request BEFORE Phase 9 and BEFORE real Onshape human validation.** The 22-step validation plan below has not been run. Phase 9 (first safe CAD write) is still being built on its own branch and will need to merge on top of this. Phase 11 is not started. Design reference: [PHASE_10_LEARNING_SPEC.md](PHASE_10_LEARNING_SPEC.md).

## Included AI chat fixes (separate from Phase 10 itself)

This merge also carries three small Design chat commits that were developed in parallel: the Groq
first-round fix (`gpt-oss` calling a nonexistent `answer` tool), a friendlier answer lead-in, and
model-driven general chat (the model decides whether to inspect the model or just reply; general chat
reads no CAD). See "Groq first round: inspect or just chat" in [AI_AGENT.md](AI_AGENT.md). They are
unrelated to the lessons and to Phase 9.

## Parallel-development boundary

Branched from `origin/main` at `81199ea` (Phase 8 merged). No Phase 9 code, commit or interface was
used. Phase 10 touches no OAuth/auth code, provider client, migration, write feature, Modify component
or write-security document. It is read-only end to end.

## What was built

- **Investigations** (`learning/Reflection.tsx`, `session.ts`): the authored Observed → prediction →
  possible explanation → try next → verified-after-re-check flow, opened only by a blocking
  deterministic result. Observed is the server's own finding. Cases A–E (step 2 no extrusion / no solid
  body, step 3 second portion / fillet ambiguity, step 4 mounting faces).
- **Prediction**: a radio group with an always-present "I'm not sure yet", neutral feedback, no grading.
  An answer (any) unlocks the explanation, so it never blocks. One authored "what do you expect?"
  prompt before the step 2 change.
- **Recheck linkage**: investigations follow the latest deterministic result; a PASS resolves, and
  FAIL/WARNING/unverifiable revokes. Nothing checks automatically.
- **Guidance fading**: `full` → `reduced` (a different investigation of the same family is currently
  resolved) → `independent` (transfer challenge). The reason is shown; honesty caveats never fade.
- **Transfer challenge**: an optional "one profile, one extrusion" challenge with its own progress,
  restart and summary. It reuses the single Phase 7 hint ladder, `CheckStep`, the Phase 8 endpoint and
  checker (one new server step id, `transfer-single-profile`, composed of existing requirement
  functions plus two small additions).
- **Session metrics**: prediction questions answered, investigations resolved, challenge progress.

Reused unchanged: lesson engine, hint ladder, vocabulary, `CheckStep`, check endpoint/client, evidence
semantics, session-local privacy, design system. Nothing was duplicated.

## Backend change (small, additive)

`step_checks/bracket.py`: `exactly_one_extrusion` and `l_profile_signal`, a `transfer-single-profile`
step, a `constraint_not_met` reason, and one reworded finding ("Forge doesn't see enough added faces yet
for this step's mounting check."). All Phase 8 requirement semantics are unchanged.

## Semantics

- **Observed** — deterministic evidence only; the server finding verbatim.
- **Hypothesis** — a labeled possibility, authored from evidence limits ("One possibility is…").
- **Recommendation** — a labeled suggestion, never a guarantee; defers to the hint ladder.
- **Verified result** — shown only after a fresh explicit check, and only as the latest server finding.

Triggers: blocking FAIL, or a blocking WARNING with an authored case. Not triggered by PASS, non-blocking
UNVERIFIED, unavailable/stale evidence, request errors, or another step's result. Stale/late results are
rejected by stable step ids (a prediction or result for another step changes nothing).

## Privacy, AI and CAD boundaries

Session memory only; no database, localStorage, analytics or persisted predictions. No AI call is made by
checking, predicting, revealing or re-checking; the core flow needs no provider and the checker remains
authoritative. No CAD write, FeatureScript, scope change or new endpoint.

## Verification (Windows, this machine)

| Check                           | Result                                                                                                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New backend tests               | 10 (`test_transfer_step_checks.py`); backend suite 736 passed                                                                                                       |
| New session/domain tests        | 50 (`Investigation.test.ts`: triggers, prediction, recheck, stale, fading, transfer)                                                                                |
| New component tests             | 16 (`InvestigationUi.test.tsx`)                                                                                                                                     |
| Frontend suite                  | 690 passed (`vitest --maxWorkers=2`); default parallelism has load timeouts                                                                                         |
| New Playwright                  | 12 scenarios x 3 engines = 36 (incl. 6-width sweep, keyboard, axe at 320 px)                                                                                        |
| Phase 7/8 browser regressions   | learning (30) and bracket (24) runs pass alongside Phase 10 (90 together)                                                                                           |
| Ruff, strict mypy, ESLint, tsc  | pass                                                                                                                                                                |
| Compose config, migration check | pass; no drift                                                                                                                                                      |
| Full Playwright                 | 512 of 522 passed on a 4-worker run; the 10 timeouts were in older Firefox/WebKit specs (preview, refinement, foundation, extension) and all pass when re-run alone |
| Dependency audit                | not run: no dependency changed                                                                                                                                      |

Known pre-existing Windows items (also on clean `main`): `test_dev_key.py` (POSIX file mode),
`test_cad_read.py` (2 collection errors from an oversized test id), occasional 5 s jsdom timeouts under
load, and Prettier reporting ~50 untouched files because of CRLF checkouts.

## Known limitations

1. Content is authored for five Mounting Bracket cases plus four challenge cases; other lessons have none.
2. Face-count based signals keep their Phase 8 limits (thresholds 8 and 10 assume prismatic geometry).
3. The challenge omits holes because a remove-extrude hole would break "exactly one extrusion".
4. "Reduced guidance" depends on a same-family issue being resolved this session; it is deliberately simple.
5. No AI explanation exists; adding one later must be explicit and must not influence statuses.

## Parallel Phase 9 handoff

Files most likely to conflict on a later merge (shared, append-only edits in this branch): `README.md`,
`docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/UI.md`. Code overlap with Phase 9 is expected to be
nil; the only shared code surface is `apps/api/src/forge_api/step_checks/` and `apps/web/src/learning/`,
which Phase 9 should not touch. After Phase 9 merges: `git checkout phase10/mistake-transfer-learning`,
`git fetch origin`, `git merge origin/main`, resolve conflicts intentionally (no blanket ours/theirs),
re-run the gate and the human validation below. (Superseded: the team chose to merge Phase 10 first. Phase 9 must now merge `main` into its branch and reconcile the shared files listed above.)

## Human validation plan (real Onshape, disposable document)

1. Open Mounting Bracket (Learn → Beginner → guided project).
2. Deliberately fail step 2 (sketch, no extrusion).
3. Confirm "What Forge observed" states only what is proven.
4. Answer the prediction (try "I'm not sure yet" once).
5. Confirm the explanation is labeled a possibility.
6. Request the recommendation; confirm it is labeled a suggestion.
7. Fix the model manually.
8. Press **Check my step**.
9. Confirm "Verified after re-check" uses the fresh result and the investigation resolves.
10. On step 3, build the single-profile L, then add a fillet.
11. Confirm the investigation explains the ambiguity and makes no geometry claim.
12. Suppress or remove the fillet.
13. Re-check.
14. Confirm the ambiguity investigation resolves.
15. Finish the guided lesson; start the transfer challenge.
16. Confirm less guidance is shown initially (no walkthrough, conceptual help only).
17. Complete it with one L-shaped profile and one extrusion.
18. Confirm the supported checks pass (and that two extrusions fail the constraint).
19. Confirm dimensions/units stay UNVERIFIED.
20. Confirm no mastery, grade or whole-design/safety claim anywhere.
21. Switch Design → Learn and confirm state is preserved; Restart challenge keeps guided progress.
22. Repeat at about 320 px.

## Screenshot plan (do not commit; no secrets, IDs, network tabs or cookies)

A step FAIL + Observed · B prediction question · C prediction selected · D possible explanation ·
E try next · F re-check PASS · G Verified after re-check · H fillet WARNING investigation · I resolved
warning · J challenge introduction · K reduced-guidance challenge · L challenge PASS · M challenge
summary · N 320 px · O no-context/read-only state.
