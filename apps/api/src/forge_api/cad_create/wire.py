"""Strict wire schema an LLM may produce for creation requests.

Design intent only. The model picks one of three outcomes and fills closed
fields; it cannot express provider payloads, ids, queries, microversions,
approvals or defaults. Every dimension must carry an explicit unit, and a hole is
either explicitly centered or explicitly offset, so nothing has to be guessed.
The wire is never trusted: ``planner`` re-validates and normalizes it.
"""

from typing import Annotated, Literal, get_args

from pydantic import Field, TypeAdapter

from forge_api.ai.models import StrictModel
from forge_api.cad_create.models import MAX_HOLES, Dimension, SignedDimension

# What the model may say it still needs, as closed keys (never free text).
ClarifyField = Literal[
    "object_kind",
    "units",
    "width",
    "length",
    "thickness",
    "hole_count",
    "hole_diameter",
    "hole_position",
]
CLARIFY_FIELDS: tuple[str, ...] = get_args(ClarifyField)
ClarifyReason = Literal["missing_dimension", "ambiguous_intent"]
UnsupportedReason = Literal[
    "unsupported_object", "unsupported_feature", "not_a_creation_request"
]


class CenteredPlacement(StrictModel):
    mode: Literal["center"] = "center"


class OffsetPlacement(StrictModel):
    mode: Literal["offset_from_center"] = "offset_from_center"
    x: SignedDimension
    y: SignedDimension


HolePlacement = Annotated[
    CenteredPlacement | OffsetPlacement, Field(discriminator="mode")
]


class HoleWire(StrictModel):
    diameter: Dimension
    placement: HolePlacement


class PlateWire(StrictModel):
    kind: Literal["rect_plate_with_through_holes"] = "rect_plate_with_through_holes"
    width: Dimension
    length: Dimension
    thickness: Dimension
    holes: Annotated[tuple[HoleWire, ...], Field(max_length=MAX_HOLES)]


# Future designs (brackets, hubs, enclosures, revolved parts) join this alias as a
# discriminated union on ``kind`` and register a normalizer in ``planner``.
DesignWire = PlateWire


class BriefWire(StrictModel):
    outcome: Literal["brief"] = "brief"
    design: DesignWire


class ClarificationWire(StrictModel):
    outcome: Literal["clarification"] = "clarification"
    reason: ClarifyReason
    fields: Annotated[tuple[ClarifyField, ...], Field(min_length=1, max_length=8)]


class UnsupportedWire(StrictModel):
    outcome: Literal["unsupported"] = "unsupported"
    reason: UnsupportedReason


WireResponse = Annotated[
    BriefWire | ClarificationWire | UnsupportedWire, Field(discriminator="outcome")
]
WIRE_ADAPTER: TypeAdapter[BriefWire | ClarificationWire | UnsupportedWire] = (
    TypeAdapter(WireResponse)
)
