# Phase 8 lesson specification — Mounting Bracket + Check My Step

Status: **Phase 8A (preparation) only.** Phase 7 (Learning Mode foundation) is not
merged, so no lesson runtime, UI or route exists for this lesson. Everything below
is derived from the evidence Forge **actually** produces today (Phase 5 `CadInspector`).
The one piece of code, `apps/api/src/forge_api/step_checks/`, is pure and unwired.

## 1. Evidence capability map (from code, not documentation)

Source: `integrations/onshape/inspector.py`, `parameters.py`, `models.py`,
`docs/PHASE_5_REVIEW.md`. Workspace Part Studio, default configuration, end of list.

| Property                       | Class                | Notes                                                                                                                                                                  |
| ------------------------------ | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Feature list and order         | SUPPORTED            | Ordered, bounded to 100; `omitted_count` exposes truncation.                                                                                                           |
| Feature type                   | WITH LIMITATIONS     | Allowlist only: sketch, extrude, fillet, chamfer. Everything else (hole, revolve, shell, custom) is `unknown`. Custom namespaces never gain a standard meaning.        |
| Feature name                   | SUPPORTED, UNTRUSTED | User-editable. Never proof of anything. Omitted when over display bounds.                                                                                              |
| Active / suppressed            | WITH LIMITATIONS     | `active`, `suppressed`, or `unverified` when the provider omits it.                                                                                                    |
| Feature parameters             | WITH LIMITATIONS     | Only boolean, string, enum, quantity-expression text, and query _count_. Labels derive from provider parameter ids; not live-verified for lesson use. Not relied upon. |
| Sketch geometry/constraints    | NOT AVAILABLE        | No entities, closedness, plane, or constraint state.                                                                                                                   |
| Dimensions (numeric)           | NOT AVAILABLE        | Expression text is literal; never evaluated or converted.                                                                                                              |
| Units                          | UNVERIFIED           | Physical units are `provider_native_unverified`. Never assumed mm.                                                                                                     |
| Parts                          | WITH LIMITATIONS     | Metadata only; per-part mass is always `unverified`.                                                                                                                   |
| Bodies and body type           | SUPPORTED            | `SOLID` etc.; `None` when unreported (then unknown, not "not solid").                                                                                                  |
| Face count                     | WITH LIMITATIONS     | Reported per body; live-verified (6 for a box). Cannot say which feature produced a face.                                                                              |
| Edge / vertex count            | UNVERIFIED           | Live capture returned unknown. Not used.                                                                                                                               |
| Mass / volume                  | UNVERIFIED           | Aggregate only; mass often unavailable without material; units unverified.                                                                                             |
| Geometry (positions, sizes)    | NOT AVAILABLE        | No coordinates, bounding box or hole data.                                                                                                                             |
| Selection type                 | WITH LIMITATIONS     | Single FACE/EDGE/clear; Phase 3 adapter.                                                                                                                               |
| Selection / feature / body own | UNVERIFIED           | Ownership is deliberately unknown; selection is not used in this lesson.                                                                                               |

**Consequence:** Forge can prove _what kinds of features exist and whether they are
active_, and _what bodies exist and how many faces they have_. It cannot prove any
shape, size, position, hole, dimension or unit. The lesson is designed within that.

## 2. Lesson: Mounting Bracket

**Learner:** a beginner who has used Onshape's sketch and extrude tools once.
**Prerequisites:** open a Part Studio, select a plane, draw a rectangle.
**Objectives:** (1) build a part from a profile, (2) recognise when extrusion fits
(constant cross-section), (3) add a second portion, (4) add mounting features,
(5) learn what a model check can and cannot prove.
**Why useful:** an L-bracket is the simplest part with a real mounting interface.
**Final shape (conceptual):** an L-shaped prismatic bracket with two mounting holes.

The student performs every CAD operation. Forge never writes to Onshape.

### Steps

Each step lists: Objective, How, Why, Vocabulary, Hints (conceptual, tool-specific),
Full explanation, Checks, Unverifiable expectations, Accepted alternatives.

#### Step 1 — `base-sketch`: draw the base profile

- **Objective:** make a sketch of the bracket's base.
- **How:** pick a plane, start a sketch, draw a rectangle, finish.
- **Why:** a 2D profile is the cheapest way to describe a shape whose cross-section
  is constant; solids are built from profiles.
- **Vocabulary:** sketch, plane, profile, closed profile.
- **Conceptual hint:** what 2D outline would the foot of your bracket have?
- **Tool hint:** Sketch tool, then Corner rectangle, then finish.
- **Checks (blocking):** `sketch.exists` — an active sketch feature exists.
- **Cannot verify:** rectangle shape, size, plane, closedness, dimensions (`sketch.profile`, UNVERIFIED, non-blocking).
- **Alternatives:** any plane, any outline, any sketch name.

#### Step 2 — `base-solid`: turn the profile into a solid

- **Objective:** give the profile thickness.
- **How:** extrude the sketch region as a new solid.
- **Why:** extrusion is appropriate because this portion keeps one cross-section
  through its thickness.
- **Vocabulary:** extrude, depth, solid body, new vs add.
- **Hints:** Which feature turns a closed 2D profile into 3D? / Extrude, new part.
- **Checks (blocking):** `extrude.exists` (active extrude), `body.solid` (a SOLID body).
- **Cannot verify:** thickness value or units (`extrude.depth`).
- **Alternatives:** any depth; blind or symmetric; any names.

#### Step 3 — `second-portion`: add the leg

- **Objective:** make the bracket L-shaped.
- **How:** sketch the leg on a face and extrude it as an **add**, or draw an L-shaped
  profile in step 1 and extrude once.
- **Why:** the leg shares the base's constant cross-section along its width, so a
  second extrusion (or an L profile) fits; a plain block cannot bolt to a second surface.
- **Checks (blocking):** `bracket.second_portion` — two active extrusions, **or** a
  SOLID body with ≥ 8 faces (an L prism).
- **Authored WARNING:** if the 8-face route is the only signal and a fillet/chamfer is
  active, face count could come from those, so the result is WARNING, not PASS.
- **Cannot verify:** leg size, orientation, that it is joined to the base.
- **Alternatives (real):** (a) two extrusions; (b) one L-profile extrusion.

#### Step 4 — `mounting-holes`: add two mounting holes

- **Objective:** add mounting holes in the bracket.
- **How:** sketch circles on the mounting face, then remove-extrude or use Hole.
- **Why:** holes are cuts through constant material depth; extrude-remove or Hole both fit.
- **Checks (blocking):** `bracket.mounting_faces` — a SOLID body with ≥ 10 faces.
- **Honest limit:** this counts faces. Forge **cannot** tell holes from other
  face-adding features; the lesson tells students to add exactly two simple through
  holes (+2 faces) and says so in the disclosure. `holes.placement` is UNVERIFIED.
- **Alternatives:** Hole feature or extrude-remove; both appear as faces. The Hole
  feature type is `unknown` to Forge and is therefore not relied upon.

#### Step 5 — `review`: look over the model

- **Objective:** review what is known and unknown.
- **Checks:** none blocking. Completion is **learner-reported**; Forge states what
  it could not check (mass, fit, strength, manufacturability, dimensions, units).
  The step is never "Forge-verified".

### Final completion criteria

Steps 1–4 each `verified`, step 5 acknowledged by the learner. The summary reports
supported checks passed, hints requested, and an explicit "not verified" list. It does
not claim the design is correct, safe or manufacturable.

## 3. Requirement contract

Implemented as `Requirement` in `step_checks/model.py`:

| Field         | Meaning                                                     |
| ------------- | ----------------------------------------------------------- |
| `id`          | Stable, e.g. `extrude.exists`                               |
| `description` | Student-facing sentence                                     |
| `evidence`    | Evidence families consulted (disclosure)                    |
| `blocking`    | Only blocking PASS can make a step `verified`               |
| `evaluate`    | Pure function `CadInspector -> Outcome(status,reason,text)` |

Findings are fixed server-authored strings. Reasons are a closed set: `met`,
`met_by_alternative`, `missing`, `suppressed`, `evidence_unavailable`,
`evidence_incomplete`, `evidence_stale`, `not_observable`, `ambiguous_signal`.
Step outcome: `verified` (all blocking PASS), `not_met` (any blocking FAIL),
otherwise `unverified`.

### Status semantics

- **PASS** — evidence proves the supported requirement is met.
- **FAIL** — evidence proves it is not met (complete, successfully read lists).
- **WARNING** — an authored, supported situation worth attention (currently only the
  fillet/chamfer ambiguity). Never used for generic doubt.
- **UNVERIFIED** — not enough trustworthy evidence. Unknown units, face counts,
  body types, suppression state, unreadable sections, stale snapshots and every
  non-observable expectation land here. It is never converted to FAIL or zero.

The AI provider cannot assign or alter any status. It may later explain results.

## 4. Test vectors (implemented in `tests/test_step_checks.py`)

| Evidence                                                  | Requirement                  | Result                  |
| --------------------------------------------------------- | ---------------------------- | ----------------------- |
| sketch present                                            | `sketch.exists`              | PASS                    |
| no features, features readable                            | `sketch.exists`              | FAIL (missing)          |
| features section unavailable                              | any                          | UNVERIFIED              |
| sketch + extrude, SOLID body                              | step 2                       | verified                |
| extrude suppressed                                        | `extrude.exists`             | FAIL (suppressed)       |
| extrude suppression unknown                               | `extrude.exists`             | UNVERIFIED              |
| no bodies, bodies readable                                | `body.solid`                 | FAIL                    |
| body type unknown                                         | `body.solid`                 | UNVERIFIED              |
| renamed features                                          | step 2                       | verified (names unused) |
| 2 extrusions                                              | `second_portion`             | PASS                    |
| 1 extrusion, 8-face body                                  | `second_portion`             | PASS (alternative)      |
| 1 extrusion, 8-face body, active fillet                   | `second_portion`             | WARNING                 |
| 1 extrusion, 6-face body                                  | `second_portion`             | FAIL                    |
| face count unknown                                        | `second_portion`, `mounting` | UNVERIFIED              |
| 10-face body                                              | `mounting_faces`             | PASS                    |
| 8-face body                                               | `mounting_faces`             | FAIL                    |
| snapshot consistency mismatch                             | every blocking               | UNVERIFIED              |
| dimension / unit / mass / hole expectations, any evidence | non-blocking                 | UNVERIFIED              |
| review step                                               | —                            | never `verified`        |

Fixtures are built in the test file from synthetic `CadInspector` values: correct,
incomplete, empty, renamed, alternative approach, unknown face count/body type,
suppressed, unknown suppression, unreadable and stale. No private identifiers.

## 5. Alternative modeling

Real alternatives Forge can distinguish: one L-profile extrusion versus a base plus a
leg extrusion (feature names and counts differ, observable outcome is equivalent).
Not supported: arbitrary alternatives that change only geometry values, positions or
units, because geometry is not observable. Those are documented, not faked.

## 6. Check My Step UX (to implement in 8B, on the frozen design system)

Hierarchy: Step check → primary status → supported findings → what Forge cannot
verify → next student action → evidence/method disclosure (collapsed).

| State               | Presentation                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| Idle                | Functional control "Check my step"; one line saying it reads the current model, changes nothing |
| Checking            | Compact inline text: "Checking current model…", then "Evaluating this step…"; control disabled  |
| PASS                | Status text + check icon, "Forge verified what it can read for this step", findings list        |
| FAIL                | Status text + icon, plain finding, "Review hint" (never auto-reveals strongest hint)            |
| WARNING             | Amber text + icon, the authored caveat, non-blocking                                            |
| UNVERIFIED          | Neutral text + icon, what cannot be checked and why, whether it blocks progression              |
| Retry               | Re-enabled after completion; coalesces double submit                                            |
| Context unavailable | "Open this in a Part Studio in Onshape to check your model"                                     |
| Auth unavailable    | "Sign in with Onshape to check your model"                                                      |
| Cooldown            | "Forge can check again in N seconds" (reuses existing request-in-progress/rate-limit semantics) |
| Stale context       | "The Part Studio changed; check again"                                                          |

Never color-only; `aria-live="polite"` on one status region; disclosure uses a
native button/region; reduced motion and forced-colors respected; 320 px first.
Forbidden copy: "Perfect", "100% correct", "your design is safe".

## 7. Phase 7 integration assumptions and blockers

Assumptions (to be re-validated against `docs/PHASE_7_REVIEW.md`, not forced onto it):
Phase 7 owns lesson types, step state, hint ladder and progress; `step_checks`
supplies pure results keyed by a step id; learner-reported and Forge-verified
completion stay distinct; session-only memory.

Known blockers/gaps for 8B:

1. Provider `isComplete=false` is collapsed into feature `completeness` "partial"; FAIL
   for "missing feature" should additionally require an explicit complete flag.
2. A fresh evidence request per check must use the existing per-user in-flight gate
   (`request_in_progress`) and cooldown; browser must send no document/element ids.
3. Parameter labels (depth, operation type) are not live-verified; not used.
4. Face-count rules for steps 3–4 should be confirmed against a real Part Studio before
   release; thresholds (8, 10) assume prismatic geometry.
5. Hole feature type is `unknown`; extending the allowlist is a separate evidence change.

## 8. What was and was not built

Built: this spec, `step_checks` (pure, unwired, 21 tests). Not built: lesson content in
Learn, routes, UI, fresh-evidence flow, hints, progress. Phase 9 is not started.
