# Phase 8 — Mounting Bracket guided project + Check my step

**Status: real Onshape validation round 1 completed; three findings fixed in code and awaiting a short re-validation pass (see below). Not finally approved.** Branch `phase8/bracket-check-step`, built on Phase 7 (merge `9c12dfb`). Phase 9 is
not started. Automated checks use mocked evidence; live results are the human's, recorded below.

## What was built

- **Lesson** (`apps/web/src/learning/bracket.ts`): five authored steps on the Phase 7 engine
  (`base-sketch`, `base-solid`, `second-portion`, `mounting-holes`, `review`). The student does all
  CAD work. Each step has objective, instruction, a design-reasoning _Why_, vocabulary, and the
  existing three-level hint ladder. The `guided-project` goal now opens this lesson; the
  fundamentals goal still opens the Phase 7 sample. The lesson works with no AI provider.
- **Deterministic checker** (`apps/api/src/forge_api/step_checks/`): pure functions over the existing
  `CadInspector` read model. Requirements are server-owned, name their evidence, and are blocking
  or informational. No model is consulted and none can set a status.
- **Endpoint** `POST /api/learning/check-step`: explicit, authenticated, CSRF- and Origin-protected,
  closed request schema, 4 KiB bound. It takes a lesson id, step id and the validated workspace
  context, does one fresh bounded read through the existing `cad_gate` (per-user in-flight guard and
  cooldown), and evaluates the requirements. Authorization/quota stops are returned as clear
  refusals (401/403/409/429), not as model findings.
- **UI** (`CheckStep.tsx`): "Check my step" with a single honest progress line, result headline,
  findings (symbol + word, never color alone), "What Forge can't verify", and a collapsed
  "How Forge checked this" disclosure. Cooldown re-enables once on a timer; nothing retries itself.
- **Progress:** "Steps Forge verified" is a separate session metric from learner-marked completion.
  A step is Forge-verified only by a server `verified` outcome for that exact step id.

## Status semantics

| Status     | Meaning                                                                                                                                                                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS       | Evidence proves the requirement is met.                                                                                                                                                              |
| FAIL       | Evidence proves it is not met (only on successfully read, untruncated lists).                                                                                                                        |
| WARNING    | One authored case: the face-count signal for a second portion could also come from a fillet/chamfer.                                                                                                 |
| UNVERIFIED | Insufficient or untrusted evidence. Unknown units, face counts, body types, suppression, unreadable sections, stale snapshots and every non-observable expectation. Never converted to FAIL or zero. |

A step is `verified` only when every blocking requirement is PASS. The review step has no blocking
requirement and is never Forge-verified.

## Accepted alternatives and name independence

A single extruded L-shaped profile and a base-plus-leg build both satisfy `bracket.second_portion`
(different feature counts, same observable outcome). Feature names are never evidence; tests rename
features and still pass. Alternatives that differ only in sizes, positions or units are **not**
accepted because geometry is not observable; this is documented rather than faked.

## Evidence limits (unchanged by Phase 8)

Dimensions, units, mass/material, sketch geometry, hole count/size/position, edge/vertex counts and
selection ownership are not verified; the relevant requirements are fixed UNVERIFIED with reason
`not_observable`. Hole presence is inferred only from body face count (≥ 10 for an L with two simple
through holes) and cannot distinguish holes from other face-adding features; the lesson says so.
The Hole feature type is `unknown` to Forge and is not relied upon. Thresholds 8 and 10 assume
prismatic geometry and **must be confirmed on a real Part Studio**.

## Boundaries

- **CAD read-only:** only the four existing GETs can reach Onshape; tests assert method == GET.
  No write, FeatureScript, or new OAuth scope.
- **AI:** none involved in checking. A provider could later explain results but not alter status.
- **Privacy:** no persistence, no database table, no history. Results live in React memory only
  and are cleared with the Phase 7 session reset.
- **Browser authority:** the browser sends only lesson id, step id and the validated context it
  already sends for the inspector and AI. It cannot send requirements, statuses, paths, hosts or
  tokens (extra fields are rejected).

## Known limitations / gaps

1. Provider `isComplete=false` is folded into the feature list's `partial` completeness, so a FAIL
   for "no sketch/extrude" is slightly less strict than ideal.
2. Face thresholds are unverified against a real model.
3. Cooldown/in-flight protection is per process (existing `ReadGate` design).
4. `Auth.test.tsx` "keeps the UI lab independent from authentication" fails on clean `main` on this
   Windows machine too; unrelated.

## Windows findings

- No GNU Make; the npm/uv equivalents from `docs/TEAM_DEVELOPMENT.md` were used.
- `core.autocrlf=true` gives CRLF working copies, so `prettier --check .` reports ~50 files that were
  not changed here. Every file changed in Phase 8 passes Prettier.
- `tests/test_dev_key.py` asserts POSIX file mode and fails on Windows; `tests/test_cad_read.py`
  produces two pytest-collection errors from an oversized parametrized test id. Both reproduce on
  clean `main`.
- Under heavy CPU load (parallel Playwright) a few jsdom tests exceed their 5 s timeout; they pass
  alone.

## Verification

| Check                       | Result                                                                                                                                          |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 8 backend tests       | 47 (24 checker, 23 endpoint), all pass                                                                                                          |
| Backend suite               | 726 passed; only the two Windows-only items below fail                                                                                          |
| Ruff, strict mypy           | pass                                                                                                                                            |
| ESLint (`--max-warnings 0`) | pass                                                                                                                                            |
| TypeScript typecheck        | pass                                                                                                                                            |
| Frontend tests              | 624 passed (92 in `src/learning`, 38 new since the first Phase 8 commit)                                                                        |
| Playwright, Phase 8 specs   | 8 scenarios x 3 engines = 24 pass, including measured label contrast >= 4.5:1 (dark and light, enabled and cooling down)                        |
| Playwright, full suite      | 482 of 486 passed on a 4-worker run; the 4 failures were Firefox timeouts in older specs (Phase 5/7 and preview) and all pass when re-run alone |
| Not run                     | `compose-check`, `audit` (no dependency or infrastructure change); screenshots                                                                  |

## Real Onshape validation round 1 (provisional)

**Status: real Onshape validation completed; three findings fixed in code and awaiting a short
re-validation pass. Phase 8 is not finally approved.** Round 1 was run by the human in a
disposable Part Studio on macOS, in the real right-panel extension against local Forge. No
screenshots, document/workspace/element identifiers or private URLs are recorded here.

| Area                         | Result                                                                                                                                                               |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Introduction                 | Mounting Bracket introduction opened correctly.                                                                                                                      |
| Step 1 sketch                | One active sketch gave PASS; profile geometry and dimensions stayed UNVERIFIED.                                                                                      |
| Step 2 deliberate failure    | Sketch only, no extrusion or solid body: FAIL / "Not yet"; no hint was revealed.                                                                                     |
| Fresh evidence               | After creating the extrusion, **Check again** (no reload) changed FAIL to PASS; thickness and units stayed UNVERIFIED.                                               |
| Step 3 two-extrusion path    | Base plus added wall, one joined body: verified.                                                                                                                     |
| Step 4 face threshold        | Two through holes met the existing >= 10 face threshold; only added geometry was verified, hole count/size/position UNVERIFIED.                                      |
| Feature renaming             | Custom names (Base, wall, hole, ...) still passed: name independence confirmed live.                                                                                 |
| Completion                   | 5/5 steps done, 4/4 checkable verified, 0 hints; the summary warned that dimensions, units, mass, fit and strength were not verified and made no whole-design claim. |
| Single-L-profile alternative | One closed L sketch, one extrusion, one solid body passed Step 3 via the face-count route.                                                                           |
| Fillet WARNING               | An active fillet changed Step 3 to "Forge can't fully verify this step yet" with the authored "Worth a look" explanation.                                            |
| ~320 px layout               | Mode tabs, inspector row, result text wrapping, evidence disclosure and progress stayed usable; no obvious horizontal scroll.                                        |
| No Onshape context           | Standalone extension page showed "Open this lesson inside a Part Studio in Onshape to check it."; no crash, IDs or fake result.                                      |

### Findings and fixes (awaiting re-validation)

1. **Check button contrast.** "Check my step" / "Check again" were nearly unreadable in the dark
   panel. Cause: `.glass-action` (panel fill) was layered on `Button variant="primary"`, so the
   primary's dark `--on-accent` label sat on a dark panel. Fix: the control is now a plain primary
   button (design-system accent and `--on-accent`) with a `check-action` class that only styles the
   busy/cooldown state (`--surface-hover` fill, `--muted` label, `not-allowed`, no opacity so the
   label stays readable). A second defect surfaced while testing the fix: `aria-disabled` is not
   `:disabled`, so the primary hover fill still applied under the greyed label (1.29:1 after a
   click); hover/active are now overridden for the disabled state. Playwright measures computed
   label/fill contrast (>= 4.5:1) enabled and cooling down, dark and light, in three engines.
   Focus ring and forced-colors behavior are inherited unchanged from the design system.
2. **Requirement wording.** Descriptions were declarative ("An extrusion exists. Forge sees no
   active extrude feature yet."). They are now short labels (Active sketch, Closed, dimensioned
   profile, Active extrusion, Solid body, Intended thickness, Second portion of the bracket, Intended
   leg size, Added mounting geometry, Mounting-hole placement and size, Mass, Fit, strength and
   manufacturability) rendered as "Label — what Forge observed". A backend test rejects claim words
   and sentence-style labels. Findings were also made grammatical ("an active sketch", "2 active
   sketches", unreadable-list wording). No evidence rule or status semantics changed.
3. **Stale Forge-verified progress.** `forgeVerified` was only ever set, so a later WARNING left
   "3 of 4". The session now has one action, `check-result { stepId, outcome }`. For the active,
   checkable step whose id matches: `verified` sets `forgeVerified`, `not_met` or `unverified`
   (including a blocking WARNING) clears it, and a later `verified` sets it again. Identical
   repeats return the same state object. Results for another step, unknown ids, non-checkable
   steps and non-active phases are ignored. Request, auth, cooldown and context errors dispatch
   nothing, so they never change a CAD finding. A response whose `step_id` differs from the active
   step is not dispatched. Learner completion and hints are untouched.

### Re-validation checklist

1. Dark Onshape panel: **Check my step** and, after a result, **Check again** are clearly legible,
   including while cooling down after a click.
2. A failing or unsupported row reads as "Label — observation" with no contradictory claim.
3. Verify Step 3 (3 of 4), add a fillet and check again: Step 3 becomes "can't fully verify" and
   "Steps Forge verified" drops; remove the fillet and re-check: it returns.

## Phase 9

Not started.
