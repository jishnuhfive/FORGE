"""Closed current-UI replacement contracts; no payload construction or authority.

Source predicates and human writes-OFF provenance are recorded in Phase 16.
Inactive inputs are validated, never discarded. Missing mode guards are never
inferred from defaults. The original minimal A1 representation stays separate.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, NoReturn

from pydantic import JsonValue

from forge_api.cad_edits.plans import valid_quantity

from .standard_shape_contract import (
    CommonMetadataFailure,
    FailureParameter,
    FailureReason,
    ShapeValidationError,
    StandardId,
)

QuantityKind = Literal["length", "offset", "angle", "fraction", "open_fraction"]
SequenceKind = Literal["entities", "edges", "empty_queries", "empty_items"]


@dataclass(frozen=True)
class ParameterRule:
    bt_type: str
    boolean: tuple[bool, ...] | None = None
    enum: tuple[str, str] | None = None
    quantity: QuantityKind | None = None
    sequence: SequenceKind | None = None


def _boolean(*values: bool) -> ParameterRule:
    return ParameterRule("BTMParameterBoolean-144", boolean=values)


def _enum(name: str, value: str) -> ParameterRule:
    return ParameterRule("BTMParameterEnum-145", enum=(name, value))


def _quantity(kind: QuantityKind = "length") -> ParameterRule:
    return ParameterRule("BTMParameterQuantity-147", quantity=kind)


EMPTY_QUERY = ParameterRule("BTMParameterQueryList-148", sequence="empty_queries")
ENTITIES = ParameterRule("BTMParameterQueryList-148", sequence="entities")
EDGES = ParameterRule("BTMParameterQueryList-148", sequence="edges")
EMPTY_ARRAY = ParameterRule("BTMParameterArray-2025", sequence="empty_items")

EXTRUDE_RULES: Mapping[StandardId, ParameterRule] = MappingProxyType(
    {
        "bodyType": _enum("ExtendedToolBodyType", "SOLID"),
        "operationType": _enum("NewBodyOperationType", "NEW"),
        "entities": ENTITIES,
        "endBound": _enum("BoundingType", "BLIND"),
        "depth": _quantity(),
        "domain": _enum("OperationDomain", "MODEL"),
        "surfaceEntities": EMPTY_QUERY,
        "surfaceOperationType": _enum("NewSurfaceOperationType", "NEW"),
        "flatOperationType": _enum("FlatOperationType", "REMOVE"),
        "wallShape": EMPTY_QUERY,
        "midplane": _boolean(False),
        "thickness": _quantity(),
        "thickness1": _quantity(),
        "thickness2": _quantity(),
        "flipWall": _boolean(False),
        "oppositeDirection": _boolean(False),
        "symmetric": _boolean(False),
        "hasDraft": _boolean(False),
        "draftAngle": _quantity("angle"),
        "draftPullDirection": _boolean(False),
        "hasSecondDirection": _boolean(False),
        "secondDirectionBound": _enum("BoundingType", "BLIND"),
        "secondDirectionDepth": _quantity(),
        "secondDirectionOppositeDirection": _boolean(True),
        "hasSecondDirectionDraft": _boolean(False),
        "secondDirectionDraftAngle": _quantity("angle"),
        "secondDirectionDraftPullDirection": _boolean(False),
        "endBoundEntityFace": EMPTY_QUERY,
        "endBoundEntityBody": EMPTY_QUERY,
        "endBoundEntityVertex": EMPTY_QUERY,
        "hasOffset": _boolean(False),
        "offsetDistance": _quantity("offset"),
        "offsetOppositeDirection": _boolean(False),
        "secondDirectionBoundEntityFace": EMPTY_QUERY,
        "secondDirectionBoundEntityBody": EMPTY_QUERY,
        "secondDirectionBoundEntityVertex": EMPTY_QUERY,
        "hasSecondDirectionOffset": _boolean(False),
        "secondDirectionOffsetDistance": _quantity("offset"),
        "secondDirectionOffsetOppositeDirection": _boolean(False),
        "hasExtrudeDirection": _boolean(False),
        "extrudeDirection": EMPTY_QUERY,
        "startOffset": _boolean(False),
        "startOffsetBound": _enum("StartOffsetType", "BLIND"),
        "startOffsetDistance": _quantity("offset"),
        "startOffsetEntity": EMPTY_QUERY,
        "startOffsetOppositeDirection": _boolean(False),
        "defaultScope": _boolean(False),
        "booleanScope": EMPTY_QUERY,
        "defaultSurfaceScope": _boolean(True),
        "booleanSurfaceScope": EMPTY_QUERY,
    }
)
FILLET_RULES: Mapping[StandardId, ParameterRule] = MappingProxyType(
    {
        "entities": EDGES,
        "radius": _quantity(),
        "tangentPropagation": _boolean(False, True),
        "filletType": _enum("FilletType", "EDGE"),
        "side1Face": EMPTY_QUERY,
        "side2Face": EMPTY_QUERY,
        "centerFaces": EMPTY_QUERY,
        "blendControlType": _enum("BlendControlType", "RADIUS"),
        "crossSection": _enum("FilletCrossSection", "CIRCULAR"),
        "nonCircularRadius": _quantity(),
        "width": _quantity(),
        "rho": _quantity("open_fraction"),
        "magnitude": _quantity("open_fraction"),
        # FS uses this only to suppress an informational NO_EFFECT status; it is
        # not a geometry mode. Keep either explicit Boolean unchanged.
        "defaultsChanged": _boolean(False, True),
        "isAsymmetric": _boolean(False),
        "otherRadius": _quantity(),
        "flipAsymmetric": _boolean(False),
        "isPartial": _boolean(False),
        "startPartialType": _enum("EndTypePartialFillet", "PERCENTAGE"),
        "startPartialOffset": _quantity("offset"),
        "startPartialEntity": EMPTY_QUERY,
        "partialFirstEdgeTotalParameter": _quantity("fraction"),
        "partialOppositeParameter": _boolean(True),
        "useTrimmedFirstBound": _boolean(False),
        "secondBound": _boolean(False),
        "endPartialType": _enum("EndTypePartialFillet", "PERCENTAGE"),
        "endPartialOffset": _quantity("offset"),
        "endPartialEntity": EMPTY_QUERY,
        "partialSecondEdgeTotalParameter": _quantity("fraction"),
        "useTrimmedSecondBound": _boolean(False),
        "isVariable": _boolean(False),
        "vertexSettings": EMPTY_ARRAY,
        "pointOnEdgeSettings": EMPTY_ARRAY,
        "smoothTransition": _boolean(False),
        "allowEdgeOverflow": _boolean(True),
        "keepEdges": EMPTY_QUERY,
        "smoothCorners": _boolean(False),
        "smoothCornerExceptions": EMPTY_QUERY,
    }
)
UI_RULES: Mapping[str, Mapping[StandardId, ParameterRule]] = MappingProxyType(
    {
        "extrude": EXTRUDE_RULES,
        "fillet": FILLET_RULES,
    }
)
UI_REQUIRED = MappingProxyType(
    {
        "extrude": frozenset(
            {
                "bodyType",
                "operationType",
                "entities",
                "endBound",
                "depth",
                "domain",
                "oppositeDirection",
                "symmetric",
                "hasDraft",
                "hasSecondDirection",
                "hasSecondDirectionDraft",
                "hasOffset",
                "hasSecondDirectionOffset",
                "hasExtrudeDirection",
                "startOffset",
                "defaultScope",
                "defaultSurfaceScope",
            }
        ),
        "fillet": frozenset(
            {
                "entities",
                "radius",
                "tangentPropagation",
                "filletType",
                "blendControlType",
                "crossSection",
                "isAsymmetric",
                "isPartial",
                "isVariable",
                "smoothTransition",
                "allowEdgeOverflow",
                "keepEdges",
                "smoothCorners",
                "smoothCornerExceptions",
                "vertexSettings",
                "pointOnEdgeSettings",
            }
        ),
    }
)
BASE_FIELDS = frozenset(
    {
        "btType",
        "parameterId",
        "nodeId",
        "importMicroversion",
        "parameterName",
        "valueString",
    }
)
QUANTITY_FIELDS = BASE_FIELDS | frozenset(
    {
        "expression",
        "isInteger",
        "value",
        "units",
    }
)
NUMBER = r"[0-9]{1,6}(?:\.[0-9]{1,6})?"


def _reject(parameter: FailureParameter, reason: FailureReason) -> NoReturn:
    raise ShapeValidationError(parameter, reason) from None


def _bookkeeping(param: dict[str, JsonValue], parameter: StandardId) -> None:
    if "nodeId" in param and (
        not isinstance(param["nodeId"], str) or not 1 <= len(param["nodeId"]) <= 256
    ):
        _reject(parameter, "bookkeeping_node_id")
    # An absent/empty import marker denotes no imported definition. Never accept
    # a nonempty reference or try to interpret configuration/tolerance metadata.
    if "importMicroversion" in param and param["importMicroversion"] != "":
        _reject(parameter, "bookkeeping_import_microversion")


def _common_metadata(param: dict[str, JsonValue], parameter: StandardId) -> None:
    # Current /api/openapi BTMParameter-1 documents these fields, but gives no
    # semantics for nonempty text or library DEFAULT. Only empty string defaults
    # are supported. No inference from a field name or enum member is authority.
    for field in ("parameterName", "valueString", "libraryRelationType"):
        if field not in param:
            continue
        value = param[field]
        if field != "libraryRelationType" and value == "":
            continue
        state: str
        if value is None:
            state = "null"
        elif type(value) is bool:
            state = "boolean"
        elif isinstance(value, (int, float)):
            state = "number"
        elif isinstance(value, list):
            state = "array"
        elif isinstance(value, dict):
            state = "object"
        elif field == "libraryRelationType":
            state = {
                "DEFAULT": "default",
                "IGNORE_LIBRARY_VALUES": "ignore_library_values",
                "UNKNOWN": "unknown_library_value",
                "": "empty_string",
            }.get(value, "unrecognized_string")
        else:
            state = "nonempty_string"
        # Construct exclusively from constant labels, never raw strings. Keeping
        # the closed model on the production exception makes DEV use the exact
        # same first failure without another parser or provider read.
        raise ShapeValidationError(
            parameter,
            "unexpected_field",
            common=CommonMetadataFailure.model_validate(
                {"field": field, "present": True, "state": state}
            ),
        ) from None


def _quantity_value(
    param: dict[str, JsonValue], kind: QuantityKind, parameter: StandardId
) -> None:
    if set(param) - QUANTITY_FIELDS:
        _reject(parameter, "unexpected_field")
    if "isInteger" in param and param["isInteger"] is not False:
        _reject(parameter, "wrong_is_integer")
    if "value" in param and (
        type(param["value"]) not in (int, float) or param["value"] != 0
    ):
        _reject(parameter, "wrong_quantity_value")
    if "units" in param and param["units"] != "":
        _reject(parameter, "wrong_quantity_units")
    expression = param.get("expression")
    if not isinstance(expression, str):
        _reject(parameter, "wrong_quantity_expression")
    if kind == "length":
        try:
            valid_quantity(expression)
        except ValueError:
            _reject(parameter, "wrong_quantity_expression")
    elif kind == "offset":
        if expression not in ("0 mm", "0 in"):
            try:
                valid_quantity(expression)
            except ValueError:
                _reject(parameter, "wrong_quantity_expression")
    else:
        match = re.fullmatch(
            f"({NUMBER})" + (" deg" if kind == "angle" else ""), expression
        )
        if match is None:
            _reject(parameter, "wrong_quantity_expression")
        number = Decimal(match[1])
        if not (
            0 < number < 90
            if kind == "angle"
            else 0 < number < 1
            if kind == "open_fraction"
            else 0 <= number <= 1
        ):
            _reject(parameter, "wrong_quantity_expression")


def _entity_query(raw: JsonValue, parameter: StandardId, *, allow_region: bool) -> None:
    if not isinstance(raw, dict):
        _reject(parameter, "query_item_wrong_type")
    bt = raw.get("btType")
    if bt not in ("BTMIndividualQuery-138", "BTMIndividualSketchRegionQuery-140"):
        _reject(parameter, "query_item_wrong_type")
    if bt == "BTMIndividualSketchRegionQuery-140" and not allow_region:
        _reject(parameter, "query_item_wrong_type")
    base = {"btType", "nodeId", "importMicroversion", "queryString", "deterministicIds"}
    null_fields = {
        "query",
        "deterministicIdList",
        "persistentQuery",
        "queryStatement",
        "variableName",
    }
    allowed = (
        base
        | null_fields
        | (
            {"featureId", "filterInnerLoops"}
            if bt == "BTMIndividualSketchRegionQuery-140"
            else set()
        )
    )
    if set(raw) - allowed or any(raw.get(k) is not None for k in null_fields):
        _reject(parameter, "query_item_unexpected_field")
    try:
        _bookkeeping(raw, parameter)
    except ShapeValidationError:
        _reject(parameter, "query_item_bookkeeping")
    query = raw.get("queryString", "")
    ids = raw.get("deterministicIds", [])
    if (
        not isinstance(query, str)
        or len(query) > 8192
        or not isinstance(ids, list)
        or len(ids) > 2000
    ):
        _reject(parameter, "query_item_identity")
    if any(not isinstance(i, str) or not 1 <= len(i) <= 256 for i in ids):
        _reject(parameter, "query_item_identity")
    if bt == "BTMIndividualSketchRegionQuery-140":
        feature_id = raw.get("featureId")
        if not (
            isinstance(feature_id, str)
            and 1 <= len(feature_id) <= 256
            and ("filterInnerLoops" not in raw or type(raw["filterInnerLoops"]) is bool)
        ):
            _reject(parameter, "query_item_identity")
    elif not (query.strip() or ids):
        _reject(parameter, "query_item_identity")


def _validate(
    param: dict[str, JsonValue], rule: ParameterRule, parameter: StandardId
) -> None:
    if param.get("btType") != rule.bt_type:
        _reject(parameter, "wrong_bt_type")
    _bookkeeping(param, parameter)
    _common_metadata(param, parameter)
    if rule.boolean is not None:
        if set(param) - (BASE_FIELDS | {"value"}):
            _reject(parameter, "unexpected_field")
        if type(param.get("value")) is not bool or param["value"] not in rule.boolean:
            _reject(parameter, "wrong_boolean")
    elif rule.enum is not None:
        if set(param) - (BASE_FIELDS | {"enumName", "namespace", "value"}):
            _reject(parameter, "unexpected_field")
        if "namespace" in param and param["namespace"] != "":
            _reject(parameter, "wrong_enum_namespace")
        if param.get("enumName") != rule.enum[0]:
            _reject(parameter, "wrong_enum_name")
        if param.get("value") != rule.enum[1]:
            _reject(parameter, "wrong_enum_value")
    elif rule.quantity is not None:
        _quantity_value(param, rule.quantity, parameter)
    else:
        field = "items" if rule.sequence == "empty_items" else "queries"
        value = param.get(field)
        if set(param) - (BASE_FIELDS | {field}):
            _reject(parameter, "unexpected_field")
        if not isinstance(value, list):
            _reject(
                parameter,
                "array_not_empty" if field == "items" else "query_wrong_envelope",
            )
        if rule.sequence in ("entities", "edges"):
            if not value:
                _reject(parameter, "query_empty")
            if len(value) > 2000:
                _reject(parameter, "query_wrong_envelope")
            for query in value:
                _entity_query(
                    query, parameter, allow_region=rule.sequence == "entities"
                )
        elif value != []:
            _reject(
                parameter, "array_not_empty" if field == "items" else "query_nonempty"
            )


def ui_quantity_parameter(
    feature: dict[str, JsonValue], parameter_id: str
) -> dict[str, JsonValue]:
    feature_type = feature.get("featureType")
    rules = UI_RULES.get(feature_type) if isinstance(feature_type, str) else None
    raw = feature.get("parameters")
    if rules is None:
        _reject("feature", "wrong_bt_type")
    if not isinstance(raw, list) or not raw:
        _reject("parameters", "missing_required")
    if len(raw) > len(rules):
        _reject("parameters", "too_many_parameters")
    params: dict[StandardId, dict[str, JsonValue]] = {}
    for item in raw:
        if not isinstance(item, dict):
            _reject("parameters", "wrong_bt_type")
        raw_key = item.get("parameterId")
        # Select the constant catalog key, never include arbitrary input text
        # in the closed failure detail (including malformed/unknown IDs).
        key = next((key for key in rules if key == raw_key), None)
        if key is None:
            _reject("unknown_parameter", "unknown_parameter")
        if key in params:
            _reject("duplicate_parameter", "duplicate_parameter")
        _validate(item, rules[key], key)
        params[key] = item
    assert isinstance(feature_type, str)
    missing = next(
        (
            key
            for key in rules
            if key in UI_REQUIRED[feature_type] and key not in params
        ),
        None,
    )
    if missing is not None:
        _reject(missing, "missing_required")
    if parameter_id not in params:
        _reject("required_parameter", "missing_required")
    return params[parameter_id]
