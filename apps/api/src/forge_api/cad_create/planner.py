"""Model output -> strict brief -> deterministic compiler. Pure and offline.

The model is not an authority. It supplies design intent through ``wire``; this
module re-validates it, canonicalizes units, owns every user-facing sentence, and
hands the brief to the deterministic compiler, which alone decides geometry.
"""

import json
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, model_validator

from forge_api.ai.models import StrictModel
from forge_api.cad_create.compile import BriefError, BriefErrorCode, compile_brief
from forge_api.cad_create.models import (
    CreationPlan,
    Dimension,
    PlateWithHolesBrief,
    SignedDimension,
    ThroughHole,
)
from forge_api.cad_create.wire import (
    CLARIFY_FIELDS,
    WIRE_ADAPTER,
    BriefWire,
    ClarificationWire,
    ClarifyField,
    ClarifyReason,
    OffsetPlacement,
    PlateWire,
    UnsupportedReason,
    UnsupportedWire,
)

# Server-owned wording; model text is never shown.
QUESTIONS: dict[str, str] = {
    "object_kind": "What kind of part do you want to create?",
    "units": "Which unit are the dimensions in (mm, cm, m or in)?",
    "width": "What is the width?",
    "length": "What is the length?",
    "thickness": "What is the thickness?",
    "hole_count": "How many holes should it have?",
    "hole_diameter": "What diameter should the hole(s) be?",
    "hole_position": "Where should the hole(s) be, relative to the center?",
}
UNSUPPORTED_MESSAGES: dict[str, str] = {
    "unsupported_object": "Forge cannot create that kind of part yet.",
    "unsupported_feature": "Forge cannot create that feature or quantity yet.",
    "not_a_creation_request": "That does not look like a request to create a part.",
}
RejectionCode = Literal["invalid_model_output", BriefErrorCode]


class PlanReady(StrictModel):
    status: Literal["ready"] = "ready"
    brief: PlateWithHolesBrief
    plan: CreationPlan


class NeedsClarification(StrictModel):
    status: Literal["needs_clarification"] = "needs_clarification"
    reason: ClarifyReason
    fields: tuple[ClarifyField, ...]
    questions: tuple[str, ...]

    @model_validator(mode="after")
    def _owned_questions(self) -> NeedsClarification:
        if self.questions != tuple(QUESTIONS[f] for f in self.fields):
            raise ValueError("questions are server-owned")
        return self


class Unsupported(StrictModel):
    status: Literal["unsupported"] = "unsupported"
    reason: UnsupportedReason
    message: str

    @model_validator(mode="after")
    def _owned_message(self) -> Unsupported:
        if self.message != UNSUPPORTED_MESSAGES[self.reason]:
            raise ValueError("message is server-owned")
        return self


class Rejected(StrictModel):
    """Output the server will not act on: malformed, or geometrically unbuildable."""

    status: Literal["rejected"] = "rejected"
    code: RejectionCode


PlannerResult = Annotated[
    PlanReady | NeedsClarification | Unsupported | Rejected,
    Field(discriminator="status"),
]


def _canonical_length(d: Dimension) -> Dimension:
    return Dimension(value=d.to_um() / 1_000, unit="mm")


def _canonical_offset(d: SignedDimension) -> SignedDimension:
    return SignedDimension(value=d.to_um() / 1_000, unit="mm")


def normalize_plate(design: PlateWire) -> PlateWithHolesBrief:
    """Canonical brief (mm, explicit offsets): equal intent gives an equal brief."""
    zero = SignedDimension(value=0, unit="mm")
    holes = []
    for h in design.holes:
        if isinstance(h.placement, OffsetPlacement):
            x, y = _canonical_offset(h.placement.x), _canonical_offset(h.placement.y)
        else:
            x = y = zero
        holes.append(
            ThroughHole(diameter=_canonical_length(h.diameter), center_x=x, center_y=y)
        )
    return PlateWithHolesBrief(
        width=_canonical_length(design.width),
        length=_canonical_length(design.length),
        thickness=_canonical_length(design.thickness),
        holes=tuple(holes),
    )


def _parse(
    raw: str | Mapping[str, Any],
) -> BriefWire | ClarificationWire | UnsupportedWire:
    # JSON-mode validation keeps strictness (no "60" -> 60) while accepting arrays.
    text = raw if isinstance(raw, str) else json.dumps(raw, allow_nan=False)
    return WIRE_ADAPTER.validate_json(text)


def plan_creation(raw: str | Mapping[str, Any]) -> PlannerResult:
    """Never raises on bad model output; always returns a closed result."""
    try:
        wire = _parse(raw)
        if isinstance(wire, ClarificationWire):
            fields = tuple(sorted(set(wire.fields), key=CLARIFY_FIELDS.index))
            return NeedsClarification(
                reason=wire.reason,
                fields=fields,
                questions=tuple(QUESTIONS[f] for f in fields),
            )
        if isinstance(wire, UnsupportedWire):
            return Unsupported(
                reason=wire.reason, message=UNSUPPORTED_MESSAGES[wire.reason]
            )
        brief = normalize_plate(wire.design)
    except ValidationError, ValueError, TypeError:
        return Rejected(code="invalid_model_output")
    try:
        return PlanReady(brief=brief, plan=compile_brief(brief))
    except BriefError as error:
        return Rejected(code=error.code)
