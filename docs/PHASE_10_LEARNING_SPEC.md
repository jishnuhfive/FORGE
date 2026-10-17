# Phase 10 learning specification — Mistake investigation, prediction and transfer

Design reference for the tutoring behavior added on top of Phase 8. Everything here is authored,
deterministic and session-local. No AI provider is involved and Learn performs no CAD
write or Phase 9 Modify call. The separate narrow Modify capability is independent.

## 1. Investigation model

An investigation is Forge's response to a **meaningful, supported** result. It never replaces the
deterministic checker; it follows it.

| Section                 | Source                                                    | Meaning                                                                |
| ----------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| What Forge observed     | The server's own `finding` for the triggering requirement | Proven by deterministic evidence. Never authored, never reworded.      |
| Your prediction         | The student's choice (or "I'm not sure yet")              | Reflection. Not graded, not an input to any status.                    |
| Possible explanation    | Authored from the evidence's limits                       | A possibility, labeled as one. Never a diagnosis or root cause.        |
| Try next                | Authored, short                                           | A suggestion, labeled as one. Not a guarantee. Reuses the hint ladder. |
| Verified after re-check | The server's finding from a **fresh** explicit check      | The only place resolution is claimed. Follows the latest result.       |

The four categories are never merged: Observed is evidence, the explanation is a hypothesis, the
recommendation is guidance, and only a re-check produces a verified result.

### Triggers

An investigation opens only when a result for an authored **blocking** requirement has an authored
status (and, where given, reason): a blocking FAIL, or a blocking WARNING where a case is authored.
It never opens for PASS, for non-blocking items (dimensions, units, mass), for evidence that is
merely unavailable or stale, for request errors, or when a result belongs to another step. At most
one investigation is open per step, so help never piles up.

### Lifecycle (follows the latest deterministic result)

- Open: created from a matching result. `observed` is that result's finding.
- Re-check with the trigger requirement PASS: `resolved`, `latest` = the fresh PASS finding.
- Re-check with FAIL, WARNING **or an inability to verify**: `open` again (a resolved claim is
  revoked), `latest` = the fresh finding. This mirrors the "Steps Forge verified" rule from Phase 8.
- Nothing re-checks on its own. Answering, revealing, focus, tab and model changes never check.

### Prediction rules

Offered before the explanation. Any answer, including "I'm not sure yet", unlocks it, so it never
blocks the student. Feedback is neutral ("That is one possibility. Compare it with what Forge can
actually observe."). No grade, no red/green, no "Incorrect". Choices and the response text are
authored per case; the prediction is session-local and cannot change a status.

A separate **expectation** prompt ("If you extrude the closed sketch, what should Forge be able to
see afterward?") appears on one authored step before the change. It is reflection only.

## 2. Supported mistake cases (Mounting Bracket)

Wording is limited to what the Phase 8 evidence can show.

| Case | Step | Trigger (blocking requirement)                        | Hypothesis (a possibility)                                                   |
| ---- | ---- | ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| A    | 2    | `extrude.exists` FAIL (`missing`/`suppressed`)        | The sketch may not be a 3D feature yet, or an Extrude may be suppressed.     |
| B    | 2    | `body.solid` FAIL (`missing`)                         | No solid-making extrusion yet, a suppressed one, or a surface instead.       |
| C    | 3    | `bracket.second_portion` FAIL (`missing`)             | Still a plain block so far; Forge reads feature types and face counts only.  |
| D    | 3    | `bracket.second_portion` WARNING (`ambiguous_signal`) | Face count alone cannot separate a second portion from fillet/chamfer faces. |
| E    | 4    | `bracket.mounting_faces` FAIL (`missing`)             | Holes not cut yet, or only sketched. Forge sees added faces, not holes.      |

Case D teaches an evidence lesson: the prediction "Would the added faces still prove a second
portion?" leads to the point that they would not. Forge never says the bracket "is not L-shaped" or
that "your holes are missing", because it cannot inspect that.

## 3. Guidance fading (deterministic and explainable)

Each investigation records its guidance level when it opens:

| Level         | When                                                                                            | What is shown                                                                |
| ------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `full`        | The first issue of a kind                                                                       | Observed → prediction → explanation → try next (each on request)             |
| `reduced`     | A **different** investigation of the **same family** is currently resolved earlier this session | Observed → prediction → short try next; the explanation stays one click away |
| `independent` | Any investigation inside the transfer challenge                                                 | Same as reduced, with an "Independent challenge" note                        |

Families: `missing-feature`, `ambiguous-evidence`, `constraint`. A different family does not reduce
guidance, and an unresolved earlier issue does not either. The reason is printed in the panel.
Fading never hides what Forge observed, the prediction prompt, UNVERIFIED items, checker
limitations or the whole-design caveats, and the full hint ladder is always available on request.
There is no hidden score.

## 4. Transfer challenge — "one profile, one extrusion"

- **Goal:** build an L-shaped solid from one closed L-shaped sketch and exactly one extrusion.
- **Student prompt:** constraints only; the instruction is two sentences. Conceptual help on request.
- **Why it tests transfer:** the guided lesson built the bracket from a base and a separate leg. The
  challenge asks for the other valid method, so copying the earlier steps fails the constraint.
- **Checks (server, step `transfer-single-profile`, same framework as Phase 8):**
  `transfer.sketch` (active sketch), `transfer.one_extrusion` (exactly one active extrusion; two or
  more is FAIL `constraint_not_met`; suppressed extras do not count), `transfer.solid_body`,
  `transfer.l_profile` (a body with more faces than a plain block; an active fillet/chamfer makes it a
  WARNING). `transfer.dimensions` is non-blocking and always UNVERIFIED.
- **Allowed variation:** any plane, size, orientation and feature names.
- **Unsupported properties (stay UNVERIFIED):** dimensions, units, the outline's real shape, mass, fit,
  strength. The challenge omits holes because an extrude-remove hole would be a second extrusion.
- **Hints:** the existing Phase 7 ladder, one deliberate level at a time. Nothing is revealed up front.
- **Completion policy:** the learner marks it done; Forge separately reports whether its latest check
  verified it. The two are never merged.
- **Progress shown:** steps Forge verified, hints requested, and at the end "completed without hints"
  and "full explanation used". No score, grade or mastery claim.
- **Reset:** "Restart challenge" clears only challenge progress; "Reset lesson" clears everything.

## 5. Session metrics (all session-local, all plain counts)

Steps learner completed · steps Forge currently verifies · hints requested · prediction questions
answered · investigations resolved after re-check (currently resolved, of those opened) · challenge:
verified / hints / completed without hints / full explanation used. Prohibited: mastery or skill
percentages, grades, ranks, readiness levels, streaks.

## 6. Boundaries

Read-only: no CAD write, FeatureScript, OAuth scope, provider mutation or new endpoint (the existing
`POST /api/learning/check-step` serves the new step id). No database table or persistence. No AI call
is made by checking, predicting, revealing or re-checking; if an AI explanation is ever added it must
be explicit, must not alter a status and must not mark the challenge successful.
