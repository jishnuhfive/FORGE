"""Strict, closed contracts for the creation kernel.

Two layers:

* ``CreationPlan`` / ``CreationStep`` / the operation union are generic and
  provider-neutral. They describe an ordered DAG of semantic CAD operations using
  plan-local step ids and integer micrometre geometry. They name no capability's
  shape, and carry no provider ids, query strings, payloads or microversions.
* Engineering briefs (see the bottom of this module) are the validated input to one
  capability compiler. New capabilities add a brief and a compiler, and new
  operations extend ``Operation``; ``CreationPlan`` itself does not change.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from forge_api.ai.models import StrictModel

SCHEMA_VERSION: Literal[1] = 1
MAX_STEPS = 64
MAX_COORD_UM = 2_000_000  # +-2 m: sanity bound for any sketch coordinate
MAX_EXTENT_UM = 2_000_000

StepId = Annotated[str, Field(pattern=r"^s[0-9]{2,3}$")]
Micrometres = Annotated[int, Field(strict=True, gt=0, le=MAX_EXTENT_UM)]
SignedMicrometres = Annotated[
    int, Field(strict=True, ge=-MAX_COORD_UM, le=MAX_COORD_UM)
]
Unit = Literal["mm", "cm", "m", "in"]
UNIT_TO_UM: dict[str, int] = {"mm": 1_000, "cm": 10_000, "m": 1_000_000, "in": 25_400}

# Closed, provider-independent rationale keys a future Tutor can explain. They
# carry no prose and no authority; Learn never gains write capability from them.
IntentKey = Literal[
    "define_base_profile",
    "form_base_body",
    "define_cut_profile",
    "remove_material",
]


class Dimension(StrictModel):
    """An explicit-unit length as a user or normalizer states it."""

    value: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    unit: Unit

    def to_um(self) -> int:
        return round(self.value * UNIT_TO_UM[self.unit])


class SignedDimension(StrictModel):
    """An explicit-unit signed offset (e.g. from a reference origin)."""

    value: Annotated[float, Field(allow_inf_nan=False)]
    unit: Unit

    def to_um(self) -> int:
        return round(self.value * UNIT_TO_UM[self.unit])


# --- generic references -----------------------------------------------------


class BasePlaneRef(StrictModel):
    kind: Literal["base_plane"] = "base_plane"
    plane: Literal["TOP", "FRONT", "RIGHT"]


class StepFaceRef(StrictModel):
    """A semantic face of an earlier step's result, never a provider face id."""

    kind: Literal["step_face"] = "step_face"
    step: StepId
    face: Literal["start_cap", "end_cap"]


SketchTarget = Annotated[BasePlaneRef | StepFaceRef, Field(discriminator="kind")]


class BlindExtent(StrictModel):
    kind: Literal["blind"] = "blind"
    depth_um: Micrometres


class ThroughAllExtent(StrictModel):
    kind: Literal["through_all"] = "through_all"


Extent = Annotated[BlindExtent | ThroughAllExtent, Field(discriminator="kind")]


# --- operations -------------------------------------------------------------


class CreateSketchRect(StrictModel):
    operation: Literal["CREATE_SKETCH_RECT"] = "CREATE_SKETCH_RECT"
    target: SketchTarget
    center_x_um: SignedMicrometres
    center_y_um: SignedMicrometres
    width_um: Micrometres
    height_um: Micrometres


class CreateSketchCircle(StrictModel):
    operation: Literal["CREATE_SKETCH_CIRCLE"] = "CREATE_SKETCH_CIRCLE"
    target: SketchTarget
    center_x_um: SignedMicrometres
    center_y_um: SignedMicrometres
    diameter_um: Micrometres


class ExtrudeNew(StrictModel):
    operation: Literal["EXTRUDE_NEW"] = "EXTRUDE_NEW"
    profile: StepId
    extent: Extent


class ExtrudeRemove(StrictModel):
    operation: Literal["EXTRUDE_REMOVE"] = "EXTRUDE_REMOVE"
    profile: StepId
    target_body: StepId
    extent: Extent


# Extend with line/arc/constraint/revolve/fillet/chamfer/pattern/mirror/...
Operation = Annotated[
    CreateSketchRect | CreateSketchCircle | ExtrudeNew | ExtrudeRemove,
    Field(discriminator="operation"),
]
SKETCH_OPERATIONS = ("CREATE_SKETCH_RECT", "CREATE_SKETCH_CIRCLE")


def references(op: Operation) -> tuple[tuple[str, str], ...]:
    """(step id, required operation kinds joined by '|') the operation consumes."""
    sketches = "|".join(SKETCH_OPERATIONS)
    match op:
        case CreateSketchRect() | CreateSketchCircle():
            if isinstance(op.target, StepFaceRef):
                return ((op.target.step, "EXTRUDE_NEW|EXTRUDE_REMOVE"),)
            return ()
        case ExtrudeNew():
            return ((op.profile, sketches),)
        case ExtrudeRemove():
            return ((op.profile, sketches), (op.target_body, "EXTRUDE_NEW"))


class CreationStep(StrictModel):
    id: StepId
    intent: IntentKey
    depends_on: tuple[StepId, ...]
    op: Operation


class CreationPlan(StrictModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    capability: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")]
    units: Literal["um"] = "um"
    steps: Annotated[
        tuple[CreationStep, ...], Field(min_length=1, max_length=MAX_STEPS)
    ]
    digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def _validate_graph(self) -> CreationPlan:
        kinds: dict[str, str] = {}
        for step in self.steps:
            if step.id in kinds:
                raise ValueError("duplicate step id")
            wanted = tuple(sorted({ref for ref, _ in references(step.op)}))
            if step.depends_on != wanted:
                raise ValueError("depends_on must equal the sorted referenced steps")
            for ref, allowed in references(step.op):
                # Only earlier steps are in `kinds`: no forward refs, no cycles.
                if kinds.get(ref) not in allowed.split("|"):
                    raise ValueError("invalid dependency reference")
            kinds[step.id] = step.op.operation
        from forge_api.cad_create.compile import plan_digest

        if self.digest != plan_digest(self.capability, self.steps):
            raise ValueError("digest does not match plan content")
        return self


# --- the first constrained capability's brief --------------------------------


MAX_HOLES = 4


class ThroughHole(StrictModel):
    diameter: Dimension
    # Offset of the hole centre from the plate centre.
    center_x: SignedDimension
    center_y: SignedDimension


class PlateWithHolesBrief(StrictModel):
    """Rectangular plate (width x length x thickness) with 0-4 through-holes."""

    kind: Literal["rect_plate_with_through_holes"] = "rect_plate_with_through_holes"
    width: Dimension
    length: Dimension
    thickness: Dimension
    holes: Annotated[tuple[ThroughHole, ...], Field(max_length=MAX_HOLES)] = ()
