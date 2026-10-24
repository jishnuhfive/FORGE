"""Source-vocabulary discovery only; deliberately confers no edit eligibility.

The public standard library declares semantic inputs, not the exact provider JSON
of a UI-created feature. This projection exposes only those fixed identifiers and
closed shape categories so a human can resolve that gap without sharing CAD.
See docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md for provenance and the NO-GO boundary.
"""

from typing import Literal

from pydantic import Field, JsonValue

from forge_api.cad_edits.domain import Closed, EditError

from ..eligibility import MISSING
from .modify_representation import (
    Category,
    ParameterType,
    QueryShape,
    _category,
    _query,
    _type,
)

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
SourceKind = Literal["enum", "boolean", "length", "angle", "real", "query", "array"]
State = Literal["missing", "null", "wrong_type", "empty", "nonempty"]

# Fixed source input vocabulary, NOT an adapter allowlist. Neither enabled nor
# disabled values here are writable. Internal computed FS fields are excluded.
EXTRUDE: dict[StandardId, SourceKind] = {
    "bodyType": "enum",
    "operationType": "enum",
    "entities": "query",
    "endBound": "enum",
    "depth": "length",
    "domain": "enum",
    "surfaceEntities": "query",
    "surfaceOperationType": "enum",
    "flatOperationType": "enum",
    "wallShape": "query",
    "midplane": "boolean",
    "thickness": "length",
    "thickness1": "length",
    "thickness2": "length",
    "flipWall": "boolean",
    "oppositeDirection": "boolean",
    "symmetric": "boolean",
    "hasDraft": "boolean",
    "draftAngle": "angle",
    "draftPullDirection": "boolean",
    "hasSecondDirection": "boolean",
    "secondDirectionBound": "enum",
    "secondDirectionDepth": "length",
    "secondDirectionOppositeDirection": "boolean",
    "hasSecondDirectionDraft": "boolean",
    "secondDirectionDraftAngle": "angle",
    "secondDirectionDraftPullDirection": "boolean",
    "endBoundEntityFace": "query",
    "endBoundEntityBody": "query",
    "endBoundEntityVertex": "query",
    "hasOffset": "boolean",
    "offsetDistance": "length",
    "offsetOppositeDirection": "boolean",
    "secondDirectionBoundEntityFace": "query",
    "secondDirectionBoundEntityBody": "query",
    "secondDirectionBoundEntityVertex": "query",
    "hasSecondDirectionOffset": "boolean",
    "secondDirectionOffsetDistance": "length",
    "secondDirectionOffsetOppositeDirection": "boolean",
    "hasExtrudeDirection": "boolean",
    "extrudeDirection": "query",
    "startOffset": "boolean",
    "startOffsetBound": "enum",
    "startOffsetDistance": "length",
    "startOffsetEntity": "query",
    "startOffsetOppositeDirection": "boolean",
    "defaultScope": "boolean",
    "booleanScope": "query",
    "defaultSurfaceScope": "boolean",
    "booleanSurfaceScope": "query",
}
FILLET: dict[StandardId, SourceKind] = {
    "entities": "query",
    "radius": "length",
    "tangentPropagation": "boolean",
    "filletType": "enum",
    "side1Face": "query",
    "side2Face": "query",
    "centerFaces": "query",
    "blendControlType": "enum",
    "crossSection": "enum",
    "nonCircularRadius": "length",
    "width": "length",
    "rho": "real",
    "magnitude": "real",
    "defaultsChanged": "boolean",
    "isAsymmetric": "boolean",
    "otherRadius": "length",
    "flipAsymmetric": "boolean",
    "isPartial": "boolean",
    "startPartialType": "enum",
    "startPartialOffset": "length",
    "startPartialEntity": "query",
    "partialFirstEdgeTotalParameter": "real",
    "partialOppositeParameter": "boolean",
    "useTrimmedFirstBound": "boolean",
    "secondBound": "boolean",
    "endPartialType": "enum",
    "endPartialOffset": "length",
    "endPartialEntity": "query",
    "partialSecondEdgeTotalParameter": "real",
    "useTrimmedSecondBound": "boolean",
    "isVariable": "boolean",
    "vertexSettings": "array",
    "pointOnEdgeSettings": "array",
    "smoothTransition": "boolean",
    "allowEdgeOverflow": "boolean",
    "keepEdges": "query",
    "smoothCorners": "boolean",
    "smoothCornerExceptions": "query",
}
VOCABULARY = {"extrude": EXTRUDE, "fillet": FILLET}
ENUMS: dict[StandardId, tuple[str, str]] = {
    "bodyType": ("ExtendedToolBodyType", "SOLID"),
    "operationType": ("NewBodyOperationType", "NEW"),
    "endBound": ("BoundingType", "BLIND"),
    "domain": ("OperationDomain", "MODEL"),
    "surfaceOperationType": ("NewSurfaceOperationType", "NEW"),
    "flatOperationType": ("FlatOperationType", "REMOVE"),
    "secondDirectionBound": ("BoundingType", "BLIND"),
    "startOffsetBound": ("StartOffsetType", "BLIND"),
    "filletType": ("FilletType", "EDGE"),
    "blendControlType": ("BlendControlType", "RADIUS"),
    "crossSection": ("FilletCrossSection", "CIRCULAR"),
    "startPartialType": ("EndTypePartialFillet", "PERCENTAGE"),
    "endPartialType": ("EndTypePartialFillet", "PERCENTAGE"),
}


class QuantityFields(Closed):
    # Field names are public SDK schema vocabulary; values never leave this call.
    value: Literal["missing", "null", "zero", "nonzero", "wrong_type"]
    units: Literal["missing", "null", "empty", "nonempty", "wrong_type"]
    import_microversion: Literal["missing", "null", "empty", "nonempty", "wrong_type"]
    other_fields_present: bool
    other_field_count: int = Field(ge=0, le=20)
    other_field_count_capped: bool


class StandardParameter(Closed):
    parameter_id: StandardId
    source_kind: SourceKind
    occurrences: int = Field(ge=1, le=20)
    duplicate: bool
    bt_type: ParameterType
    enum_name_matches_source: bool | None
    enum_value_matches_simple_mode: bool | None
    boolean_value: bool | None
    boolean_type_valid: bool | None
    quantity_fields: QuantityFields | None
    query: QueryShape | None
    array_state: State | None


class StandardPosition(Closed):
    position: int = Field(ge=1, le=20)
    category: Category
    # Max source vocabulary is 50 inputs. Counts still use the existing cap 20.
    parameters: tuple[StandardParameter, ...] = Field(max_length=50)
    unrecognized_present: bool
    unrecognized_count: int = Field(ge=0, le=20)
    unrecognized_count_capped: bool
    malformed_present: bool
    duplicate_present: bool


class StandardCoverage(Closed):
    purpose: Literal["source_vocabulary_only_no_edit_authority"] = (
        "source_vocabulary_only_no_edit_authority"
    )
    inventory_complete: bool
    source_matches: bool
    positions: tuple[StandardPosition, ...] = Field(max_length=20)


def _state(value: object, expected: type) -> State:
    return (
        "missing"
        if value is MISSING
        else "null"
        if value is None
        else "wrong_type"
        if not isinstance(value, expected)
        else "nonempty"
        if value
        else "empty"
    )


def _quantity_fields(param: dict[str, JsonValue]) -> QuantityFields:
    value = param.get("value", MISSING)
    other = set(param) - {
        "btType",
        "parameterId",
        "expression",
        "nodeId",
        "isInteger",
        "value",
        "units",
        "importMicroversion",
    }
    return QuantityFields(
        value="missing"
        if value is MISSING
        else "null"
        if value is None
        else "wrong_type"
        if type(value) not in (int, float)
        else "zero"
        if value == 0
        else "nonzero",
        units=_state(param.get("units", MISSING), str),
        import_microversion=_state(param.get("importMicroversion", MISSING), str),
        other_fields_present=bool(other),
        other_field_count=min(len(other), 20),
        other_field_count_capped=len(other) > 20,
    )


def _parameter(
    key: StandardId, kind: SourceKind, matches: list[dict[str, JsonValue]]
) -> StandardParameter:
    first = matches[0]
    enum = ENUMS.get(key)
    value = first.get("value", MISSING)
    return StandardParameter(
        parameter_id=key,
        source_kind=kind,
        occurrences=min(len(matches), 20),
        duplicate=len(matches) > 1,
        bt_type=_type(first.get("btType", MISSING)),
        enum_name_matches_source=first.get("enumName") == enum[0] if enum else None,
        enum_value_matches_simple_mode=value == enum[1] if enum else None,
        boolean_value=value if kind == "boolean" and type(value) is bool else None,
        boolean_type_valid=type(value) is bool if kind == "boolean" else None,
        quantity_fields=_quantity_fields(first)
        if kind in ("length", "angle", "real")
        else None,
        query=_query(first) if kind == "query" else None,
        array_state=_state(first.get("items", MISSING), list)
        if kind == "array"
        else None,
    )


def standard_parameter_coverage(
    data: JsonValue, *, source_matches: bool
) -> StandardCoverage:
    """No IO, raw output, feature reconstruction, validation or eligibility."""
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise EditError("invalid_provider_response", 503)
    features = data["features"]
    assert isinstance(features, list)
    if len(features) > 20:
        raise EditError("invalid_provider_response", 503)
    positions: list[StandardPosition] = []
    for position, raw in enumerate(features, 1):
        feature = raw if isinstance(raw, dict) else {}
        category = _category(feature.get("featureType"))
        vocabulary = VOCABULARY.get(category, {})
        matches: dict[StandardId, list[dict[str, JsonValue]]] = {
            key: [] for key in vocabulary
        }
        params = feature.get("parameters", MISSING)
        malformed = not isinstance(raw, dict) or not isinstance(params, list)
        unknown = 0
        for param in params if isinstance(params, list) else []:
            if not isinstance(param, dict) or not isinstance(
                param.get("parameterId"), str
            ):
                malformed = True
                continue
            # Return the catalog key, never the untrusted input string.
            key = next((key for key in vocabulary if key == param["parameterId"]), None)
            if key is None:
                unknown += 1
            else:
                matches[key].append(param)
        positions.append(
            StandardPosition(
                position=position,
                category=category,
                parameters=tuple(
                    _parameter(key, vocabulary[key], values)
                    for key, values in matches.items()
                    if values
                ),
                unrecognized_present=unknown > 0,
                unrecognized_count=min(unknown, 20),
                unrecognized_count_capped=unknown > 20,
                malformed_present=malformed,
                duplicate_present=any(len(values) > 1 for values in matches.values()),
            )
        )
    return StandardCoverage(
        inventory_complete=data.get("isComplete") is True,
        source_matches=source_matches,
        positions=tuple(positions),
    )
