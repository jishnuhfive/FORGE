# Submission creation slice

Branch: submission/level3-demo. Phase 16 is frozen. **CAD writes default OFF.**
The updated sprint scope prioritizes rectangle sketch + additive Extrude. The
60 × 40 × 10 mm plate **with a hole is not enabled yet**: a plan requiring a face
reference or REMOVE is rejected in full before any provider request/partial build.

The existing wire → normalized brief → generic CreationPlan compiler and Learn
intent explanations are unchanged. The configured model receives only the user
request and strict intent schema, with no tools, CAD identities or approval inputs.
Structured clarification/unsupported/invalid output stays closed. Human confirmation
of dimensions is mandatory. There is no prompt matching or plate-specific mutation
endpoint. Execution dispatches reusable semantic operations through a provider adapter.

## Implemented path

Design → Create (Ask | Create; UI in `apps/web/src/create/`, see
`SUBMISSION_CREATION_UI.md`) → interpret request → review normalized brief → prepare
preview → confirm dimensions/ordered steps → approve once. Cancel invalidates pending
approval. Context/session changes unmount the local flow; stale server evidence denies
execution. Failure/uncertainty never triggers automatic approval retry.

The first supported compiled plan creates a centered Top-plane rectangle sketch and
one NEW/SOLID/BLIND extrusion. The adapter also defines a Top-plane circle operation;
the current brief compiler does not emit a standalone circle plan. REMOVE/through-all
and step-face operations retain their generic semantic schemas but cannot dispatch.
Sketch coordinates and native feature parameters are editable; this slice creates
native sketch geometry, not a fully dimension-constrained sketch. Optional final
mass/analytic-volume comparison is not implemented and is never presented as proof.

CreationEvidence separately proves an empty modeled inventory, pinned source marker,
serialization/library versions, unconfigured workspace, bounded solid/body health and
complete feature-state coverage where available. It does not borrow Modify's target
Baseline. The five bounded GET head-bracketed capture is reused without altering
Modify. Approval binds the entire brief, ordered semantic plan, exact baseline digest,
workspace, authenticated session/user/grant generation and expiry. Existing atomic
one-use WriteRecord/WriteFence claims are reused with a creation-specific payload.
Every dispatch is journaled before POST, once, with rejectMicroversionSkew. Each
acknowledgement and fresh pinned reread must prove the appended feature, order,
parameters/geometry, unchanged prior features and configuration, source advance and
model health before a dependency is added to the internal verified-ID map. Exact
acknowledged query IDs remain part of the fresh reread. No raw CAD/provider IDs enter
the semantic plan or public results. The execution budget remains 30 seconds.
Uncertain dispatch/verification stops, skips later steps and keeps the fence.
No rollback/recovery for creation uncertainty is implemented. Do not use Modify's
quantity/Fillet recovery operators for a creation record.

## Provider authority and remaining contract

Public current OpenAPI fetched from https://cad.onshape.com/api/openapi advertises
https://cad.onshape.com/api/v17, info version 1.222.91980-dcee49ea4d64, SHA-256
6416eff28b497b1bfa5d7fbcc614d3e1a669966f2a4f5b1b5dd9ab808aea76fb.
Its BTMSketch-151, BTMSketchCurveSegment-155, BTCurveGeometryLine-117,
BTMSketchCurve-4, BTCurveGeometryCircle-115 and BTFeatureDefinitionCall-1406
fields were inspected before adapter construction. Geometric coordinates use SI
metres; semantic dimensions remain integer micrometres, extrusion quantities mm.
The official feature guide documents the fixed default-plane query and sketch-region
query form: https://onshape-public.github.io/docs/api-adv/featureaccess/ . Its examples
are v9; their structural fields were cross-checked against the fetched v17 schemas.
NEW/BLIND returned parameter profiles reuse the existing closed validators unchanged.

No authoritative current-v17 rectangle + scoped REMOVE capture exists in the repo
(user-confirmed). The OpenAPI does not define the dynamic FeatureScript REMOVE
parameter contract. Do not guess merge scope, reverse direction or a face ID. The
smallest next contract confirmation is an ordinary disposable UI-built plate with a
circle and scoped blind cut: inspect the pinned feature definitions and face/cap
selection representation, preserving parameter types, quantity modes, query classes,
scope/direction flags and geometry coordinate orientation; replace private identities
with synthetic placeholders in repository fixtures. A separate narrow contract can
then map the already-generic StepFaceRef and EXTRUDE_REMOVE operations. No planner or
approval redesign is needed. No real provider capture or write ran in implementation.

## Human live validation

Use only a separately identified disposable empty Part Studio and local HTTPS. Keep
writes OFF to confirm context, empty-state preview and Cancel first. For the first
actual validation, request "Create a 60 by 40 by 10 mm plate with no holes", inspect
normalized dimensions and both ordered steps. Only after explicit human approval
of this exact target/plan may the operator enable the CAD-write environment flag.
Approve once; verify two native features, fresh provider evidence, no extra features,
a healthy single SOLID and the dimensions in CAD. Stop on uncertainty or mismatch;
retain the fence and do not retry. The four-step hole demo awaits the separate closed
REMOVE/cap contract. No production deployment, merge, OAuth/domain change or write
flag change is included in this work.

The API surface is POST /api/create/interpret (intent only), POST /api/create/plan
(brief + context), POST /api/create/plans/{handle}/approve (digest + explicit brief
confirmation), POST .../cancel and GET /api/create/plans/{handle}. Every route reuses
authentication/same-origin CSRF guards; model interpretation shares the existing
bounded planner gate. Existing route-boundary tests explicitly enumerate these five
new routes, with no wildcard expansion. Creation-specific generated sketch bookkeeping
is accepted only at declared v17 slots with bounded/default values, retained in the
acknowledgement and required exactly on the fresh reread; unknown fields still reject.
A synthetic lost-final-commit-reply regression proves a completed verified record is
not rewritten into unfenced uncertainty: a separate transaction confirms the exact
committed result of this run without redispatch. Unconfirmed writes retain their fence.

## Pre-dispatch stops and time budgets

A stop before the first write is audited as `write_rejected_stale` with a closed
category outcome, never exception text or CAD data: `baseline_marker`,
`baseline_inventory`, `baseline_configuration`, `baseline_bodies` (approval-time
capture differs from the approved baseline; first differing category, marker
first), `pre_head_moved`, `pre_unsupported`, `pre_context`, `pre_gate`,
`pre_read_failed`, `pre_other`. The UI still shows "Model changed" for the
`rejected_stale` state; the audit category says why. Every capture and dispatch gets
its own 30 s ceiling, and the whole approval a budget of 30 s per step plus one (max
110 s), so a slow but healthy provider can finish a multi-step plan.

## Post-dispatch stop labels

A stop after a dispatch audits `write_uncertain` (or `write_failed`) with the closed
label of the first failed check as its outcome: `post_transport`, `ack_*`
(`ack_skew`, `ack_envelope`, `ack_header`, `ack_defaults`, `ack_feature_keys`,
`ack_suppression`, `ack_parameters`, `ack_plane`, `ack_constraints`, `ack_query`,
`ack_entities`, `ack_entity_keys`, `ack_entity_defaults`, `ack_entity_node`,
`ack_entity_geometry`, `ack_entity_fields`, `ack_contract`), `ver_*` (fresh reread:
`ver_count`, `ver_inventory`, `ver_bodies`, `ver_config`, `ver_duplicate`) or
`step_*` (`step_baseline`, `step_head_moved`, `step_read`, `step_dependency`,
`step_preflight`, `step_other`). In development a log line names only unrecognized
provider field names, never values. The fence and uncertain state are unchanged; the
label is diagnostic only and relaxes no check.

## Partial-creation incident settlement (operator only)

`cad_create/settlement.py` with `scripts/creation_incident_operator.py` closes ONE
partially executed creation incident: a single `execution_uncertain` record whose
first step was dispatched and never acknowledged, its single fence, and a Part
Studio now holding exactly the expected unsuppressed, healthy first sketch, no
Extrude and no solid body. It is not a route, AI tool or general recovery framework.

- Requires development, CAD writes OFF, reviewer flags, the exact typed statement
  (`CONFIRMATION`), the reviewed stack, and this process's cached read credential.
- Reads only, over a GET-only transport, twice; the two captures must agree and the
  revision must have advanced since approval. Nothing is verified, continued, retried
  or cleaned up, and the sketch is left as is.
- `inspect` also runs the creation acknowledgement checks on the current sketch and
  reports only the first failing check label and unrecognized field names.
- Under one locked transaction it moves the record to the existing closed state
  `operator_recovered`, leaves its payload and step states (`execution_uncertain`,
  `skipped`) untouched, deletes exactly the matching fence and adds one
  `write_creation_settlement` / `local_only` audit event, then re-reads the result.
  A failure leaves the fence and uncertain record in place; there is no retry.
- Authority-free leftovers (the `admission` placeholder and an unclaimable expired
  preview) do not count as a conflicting operation; any claimable or in-flight record
  does. Open `admission` rows sit until the next cleanup, which is the likely cause of
  earlier `conflicting_user_operation` denials in other recovery paths.
