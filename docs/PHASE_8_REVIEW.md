# Phase 8 — Mounting Bracket guided project + Check my step

**Status: implemented and automatically verified; awaiting human validation in a real Onshape
Part Studio.** Branch `phase8/bracket-check-step`, built on Phase 7 (merge `9c12dfb`). Phase 9 is
not started. Nothing here was checked against live Onshape or live Groq.

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

| Check                       | Result                                                                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| New backend tests           | 44 (21 checker, 23 endpoint), all pass                                                                                            |
| Backend suite               | pass except the two Windows-only items above                                                                                      |
| Ruff, strict mypy           | pass                                                                                                                              |
| ESLint (`--max-warnings 0`) | pass                                                                                                                              |
| TypeScript typecheck        | pass                                                                                                                              |
| Frontend tests              | 612 total (26 new); all pass except the pre-existing Auth UI-lab test                                                             |
| Playwright (new)            | 6 scenarios x 3 engines = 18 pass                                                                                                 |
| Playwright (full suite)     | 476 of 480 passed on a 4-worker run; the 4 timeouts (older ai/extension/preview specs, Firefox/WebKit) all pass when re-run alone |
| Not run                     | `compose-check`, `audit` (no dependency or infrastructure change); real Onshape; manual screenshots                               |

## Human validation (to do)

Use a disposable document. In Onshape: Learn → Beginner → _Complete a guided project_ → Begin.
Build step 1, press **Check my step** (expect PASS), then deliberately skip an extrude on step 2
(expect FAIL, no hint revealed), fix it and re-check (PASS), try the single L-profile approach on
step 3, and observe UNVERIFIED lines. Confirm the face-count thresholds hold. Keep screenshots out
of the repository.

## Phase 9

Not started.
