"""Closed internal shape-failure vocabulary; no raw provider data or authority."""

from typing import Literal

from forge_api.cad_edits.domain import Closed, EditError

ShapeCategory = Literal["extrude", "fillet"]
StandardId = Literal[
    "bodyType",
    "operationType",
    "entities",
    "endBound",
    "depth",
    "domain",
    "surfaceEntities",
    "surfaceOperationType",
    "flatOperationType",
    "wallShape",
    "midplane",
    "thickness",
    "thickness1",
    "thickness2",
    "flipWall",
    "oppositeDirection",
    "symmetric",
    "hasDraft",
    "draftAngle",
    "draftPullDirection",
    "hasSecondDirection",
    "secondDirectionBound",
    "secondDirectionDepth",
    "secondDirectionOppositeDirection",
    "hasSecondDirectionDraft",
    "secondDirectionDraftAngle",
    "secondDirectionDraftPullDirection",
    "endBoundEntityFace",
    "endBoundEntityBody",
    "endBoundEntityVertex",
    "hasOffset",
    "offsetDistance",
    "offsetOppositeDirection",
    "secondDirectionBoundEntityFace",
    "secondDirectionBoundEntityBody",
    "secondDirectionBoundEntityVertex",
    "hasSecondDirectionOffset",
    "secondDirectionOffsetDistance",
    "secondDirectionOffsetOppositeDirection",
    "hasExtrudeDirection",
    "extrudeDirection",
    "startOffset",
    "startOffsetBound",
    "startOffsetDistance",
    "startOffsetEntity",
    "startOffsetOppositeDirection",
    "defaultScope",
    "booleanScope",
    "defaultSurfaceScope",
    "booleanSurfaceScope",
    "radius",
    "tangentPropagation",
    "filletType",
    "side1Face",
    "side2Face",
    "centerFaces",
    "blendControlType",
    "crossSection",
    "nonCircularRadius",
    "width",
    "rho",
    "magnitude",
    "defaultsChanged",
    "isAsymmetric",
    "otherRadius",
    "flipAsymmetric",
    "isPartial",
    "startPartialType",
    "startPartialOffset",
    "startPartialEntity",
    "partialFirstEdgeTotalParameter",
    "partialOppositeParameter",
    "useTrimmedFirstBound",
    "secondBound",
    "endPartialType",
    "endPartialOffset",
    "endPartialEntity",
    "partialSecondEdgeTotalParameter",
    "useTrimmedSecondBound",
    "isVariable",
    "vertexSettings",
    "pointOnEdgeSettings",
    "smoothTransition",
    "allowEdgeOverflow",
    "keepEdges",
    "smoothCorners",
    "smoothCornerExceptions",
]
FailureParameter = (
    StandardId
    | Literal[
        "feature",
        "parameters",
        "unknown_parameter",
        "duplicate_parameter",
        "required_parameter",
    ]
)
FailureReason = Literal[
    "wrong_bt_type",
    "unexpected_field",
    "bookkeeping_node_id",
    "bookkeeping_import_microversion",
    "wrong_boolean",
    "wrong_enum_name",
    "wrong_enum_namespace",
    "wrong_enum_value",
    "wrong_quantity_expression",
    "wrong_quantity_value",
    "wrong_quantity_units",
    "wrong_is_integer",
    "query_wrong_envelope",
    "query_empty",
    "query_nonempty",
    "query_item_wrong_type",
    "query_item_unexpected_field",
    "query_item_bookkeeping",
    "query_item_identity",
    "array_not_empty",
    "missing_required",
    "unknown_parameter",
    "duplicate_parameter",
    "too_many_parameters",
]


class ShapeFailure(Closed):
    parameter: FailureParameter
    reason: FailureReason


class CommonMetadataFailure(Closed):
    """Known field and primitive/state only; never retain the provider value."""

    field: Literal["parameterName", "valueString", "libraryRelationType"]
    present: Literal[True] = True
    state: Literal[
        "empty_string",
        "nonempty_string",
        "default",
        "ignore_library_values",
        "unknown_library_value",
        "unrecognized_string",
        "null",
        "boolean",
        "number",
        "array",
        "object",
    ]


class ShapeValidationError(EditError):
    """Production keeps its generic EditError; internal detail is closed and safe."""

    def __init__(
        self,
        parameter: FailureParameter,
        reason: FailureReason,
        *,
        common: CommonMetadataFailure | None = None,
    ) -> None:
        super().__init__("unsupported_target", 422)
        self.failure = ShapeFailure(parameter=parameter, reason=reason)
        self.common = common
