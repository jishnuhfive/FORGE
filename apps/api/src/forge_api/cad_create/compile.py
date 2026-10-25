"""Deterministic brief -> CreationPlan compilers. Pure: no I/O of any kind."""

import hashlib
import json
from collections.abc import Callable, Sequence
from typing import Literal

from forge_api.cad_create.models import (
    BasePlaneRef,
    BlindExtent,
    CreateSketchCircle,
    CreateSketchRect,
    CreationPlan,
    CreationStep,
    ExtrudeNew,
    ExtrudeRemove,
    IntentKey,
    Operation,
    PlateWithHolesBrief,
    StepFaceRef,
    ThroughAllExtent,
    references,
)

MIN_WALL_UM = 2_000
MIN_HOLE_DIAMETER_UM = 1_000

BriefErrorCode = Literal[
    "hole_outside_plate",
    "insufficient_wall",
    "holes_overlap",
    "hole_too_small",
]


class BriefError(Exception):
    """A well-formed brief that is geometrically unbuildable. Closed code only."""

    def __init__(self, code: BriefErrorCode) -> None:
        super().__init__(code)
        self.code: BriefErrorCode = code


def plan_digest(capability: str, steps: Sequence[CreationStep]) -> str:
    body = {
        "capability": capability,
        "steps": [s.model_dump(mode="json") for s in steps],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class _Builder:
    def __init__(self) -> None:
        self.steps: list[CreationStep] = []

    def add(self, intent: IntentKey, op: Operation) -> str:
        step_id = f"s{len(self.steps) + 1:02d}"
        deps = tuple(sorted({ref for ref, _ in references(op)}))
        self.steps.append(
            CreationStep(id=step_id, intent=intent, depends_on=deps, op=op)
        )
        return step_id

    def finish(self, capability: str) -> CreationPlan:
        steps = tuple(self.steps)
        return CreationPlan(
            capability=capability,
            steps=steps,
            digest=plan_digest(capability, steps),
        )


def _check_holes(
    width: int, length: int, holes: Sequence[tuple[int, int, int]]
) -> None:
    """Integer-exact checks on (x, y, diameter) holes centred on a plate."""
    for x, y, d in holes:
        if d < MIN_HOLE_DIAMETER_UM:
            raise BriefError("hole_too_small")
        # Doubled units keep radii integral.
        if 2 * abs(x) + d > width or 2 * abs(y) + d > length:
            raise BriefError("hole_outside_plate")
    for x, y, d in holes:
        if 2 * abs(x) + d + 2 * MIN_WALL_UM > width:
            raise BriefError("insufficient_wall")
        if 2 * abs(y) + d + 2 * MIN_WALL_UM > length:
            raise BriefError("insufficient_wall")
    for i, (x1, y1, d1) in enumerate(holes):
        for x2, y2, d2 in holes[i + 1 :]:
            dist2 = 4 * ((x1 - x2) ** 2 + (y1 - y2) ** 2)  # (2*distance)^2
            if dist2 < (d1 + d2) ** 2:
                raise BriefError("holes_overlap")
            if dist2 < (d1 + d2 + 2 * MIN_WALL_UM) ** 2:
                raise BriefError("insufficient_wall")


def compile_plate_with_holes(brief: PlateWithHolesBrief) -> CreationPlan:
    width = brief.width.to_um()
    length = brief.length.to_um()
    thickness = brief.thickness.to_um()
    # Canonical order so equivalent briefs yield identical plans and digests.
    holes = sorted(
        (h.center_x.to_um(), h.center_y.to_um(), h.diameter.to_um())
        for h in brief.holes
    )
    _check_holes(width, length, holes)

    b = _Builder()
    base_sketch = b.add(
        "define_base_profile",
        CreateSketchRect(
            target=BasePlaneRef(plane="TOP"),
            center_x_um=0,
            center_y_um=0,
            width_um=width,
            height_um=length,
        ),
    )
    body = b.add(
        "form_base_body",
        ExtrudeNew(profile=base_sketch, extent=BlindExtent(depth_um=thickness)),
    )
    for x, y, d in holes:
        sketch = b.add(
            "define_cut_profile",
            CreateSketchCircle(
                target=StepFaceRef(step=body, face="end_cap"),
                center_x_um=x,
                center_y_um=y,
                diameter_um=d,
            ),
        )
        b.add(
            "remove_material",
            ExtrudeRemove(profile=sketch, target_body=body, extent=ThroughAllExtent()),
        )
    return b.finish(brief.kind)


# Capability registry: new briefs register a compiler; CreationPlan is unchanged.
_COMPILERS: dict[str, Callable[..., CreationPlan]] = {
    "rect_plate_with_through_holes": compile_plate_with_holes,
}


def compile_brief(brief: PlateWithHolesBrief) -> CreationPlan:
    return _COMPILERS[brief.kind](brief)
