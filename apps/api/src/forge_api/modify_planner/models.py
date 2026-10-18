"""Planner contracts: a flat provider wire format and strict validated results.

The wire format is deliberately flat (no unions, no nullable fields) so strict JSON
schema output works identically on every provider. It is never trusted: the server
converts it into A1's own strict operation types, reusing A1's validators.
"""

from typing import Annotated, Any, Literal

from pydantic import Field

from forge_api.ai.models import StrictModel
from forge_api.cad_edits.domain import Closed
from forge_api.cad_edits.plans import FeatureType, ModifyOperation

MAX_OPERATIONS = 5
MAX_CANDIDATES = 6
MAX_REQUEST_CHARS = 512
OperationName = Literal[
    "SET_SUPPRESSED",
    "SET_UNSUPPRESSED",
    "RENAME_FEATURE",
    "SET_EXTRUDE_DEPTH",
    "SET_FILLET_RADIUS",
]
# Why a request cannot become a plan. Wording is server-owned, never model prose.
ClarificationReason = Literal[
    "ambiguous_target",
    "unsupported_request",
    "missing_value",
    "contradictory_request",
    "no_matching_target",
]
WireReason = Literal[
    "none",
    "ambiguous_target",
    "unsupported_request",
    "missing_value",
    "contradictory_request",
    "no_matching_target",
]


class WireOperation(StrictModel):
    type: OperationName
    # An opaque handle from the supplied catalog. Validated against it server-side.
    target: Annotated[str, Field(max_length=64)]
    # "" unless the operation sets a quantity.
    quantity: Annotated[str, Field(max_length=32)]
    # "" unless the operation renames.
    new_name: Annotated[str, Field(max_length=256)]


class WirePlan(StrictModel):
    """Everything the model may emit. There is no field for CAD state or authority."""

    outcome: Literal["plan", "clarification"]
    operations: list[WireOperation] = Field(max_length=MAX_OPERATIONS)
    reason: WireReason
    candidates: list[Annotated[str, Field(max_length=64)]] = Field(
        max_length=MAX_CANDIDATES
    )


class Choice(Closed):
    """A safe display choice built by the server from the catalog."""

    label: Annotated[str, Field(min_length=1, max_length=256)]
    feature_type: FeatureType
    position: Annotated[int, Field(ge=1, le=20)]


class PlannerPlan(Closed):
    outcome: Literal["plan"] = "plan"
    operations: Annotated[
        tuple[ModifyOperation, ...], Field(min_length=1, max_length=MAX_OPERATIONS)
    ]


class PlannerClarification(Closed):
    outcome: Literal["clarification"] = "clarification"
    reason: ClarificationReason
    choices: Annotated[tuple[Choice, ...], Field(max_length=MAX_CANDIDATES)] = ()


PlannerResult = PlannerPlan | PlannerClarification


def wire_schema() -> dict[str, Any]:
    """The strict JSON schema with every reference inlined, for any provider."""
    schema = WirePlan.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                return inline(definitions[ref.removeprefix("#/$defs/")])
            return {key: inline(value) for key, value in node.items()}
        if isinstance(node, list):
            return [inline(item) for item in node]
        return node

    result = inline(schema)
    assert isinstance(result, dict)
    return result
