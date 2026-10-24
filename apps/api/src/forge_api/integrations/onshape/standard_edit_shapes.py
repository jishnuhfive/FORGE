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

from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import valid_quantity

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

EXTRUDE_RULES = MappingProxyType(
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
        "defaultScope": _boolean(True),
        "booleanScope": EMPTY_QUERY,
        "defaultSurfaceScope": _boolean(True),
        "booleanSurfaceScope": EMPTY_QUERY,
    }
)
FILLET_RULES = MappingProxyType(
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
UI_RULES: Mapping[str, Mapping[str, ParameterRule]] = MappingProxyType(
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
QUANTITY_FIELDS = frozenset(
    {
        "btType",
        "parameterId",
        "nodeId",
        "importMicroversion",
        "expression",
        "isInteger",
        "value",
        "units",
    }
)
BASE_FIELDS = frozenset({"btType", "parameterId", "nodeId", "importMicroversion"})
NUMBER = r"[0-9]{1,6}(?:\.[0-9]{1,6})?"


def _reject() -> NoReturn:
    raise EditError("unsupported_target", 422)


def _bookkeeping(param: dict[str, JsonValue]) -> None:
    if "nodeId" in param and (
        not isinstance(param["nodeId"], str) or not 1 <= len(param["nodeId"]) <= 256
    ):
        _reject()
    # An absent/empty import marker denotes no imported definition. Never accept
    # a nonempty reference or try to interpret configuration/tolerance metadata.
    if "importMicroversion" in param and param["importMicroversion"] != "":
        _reject()


def _quantity_value(param: dict[str, JsonValue], kind: QuantityKind) -> None:
    if (
        set(param) - QUANTITY_FIELDS
        or ("isInteger" in param and param["isInteger"] is not False)
        or (
            "value" in param
            and (type(param["value"]) not in (int, float) or param["value"] != 0)
        )
        or ("units" in param and param["units"] != "")
    ):
        _reject()
    expression = param.get("expression")
    if not isinstance(expression, str):
        _reject()
    if kind == "length":
        try:
            valid_quantity(expression)
        except ValueError:
            _reject()
    elif kind == "offset":
        if expression not in ("0 mm", "0 in"):
            try:
                valid_quantity(expression)
            except ValueError:
                _reject()
    else:
        match = re.fullmatch(
            f"({NUMBER})" + (" deg" if kind == "angle" else ""), expression
        )
        if match is None:
            _reject()
        number = Decimal(match[1])
        if not (
            0 < number < 90
            if kind == "angle"
            else 0 < number < 1
            if kind == "open_fraction"
            else 0 <= number <= 1
        ):
            _reject()


def _entity_query(raw: JsonValue, *, allow_region: bool) -> bool:
    if not isinstance(raw, dict):
        return False
    bt = raw.get("btType")
    if bt not in ("BTMIndividualQuery-138", "BTMIndividualSketchRegionQuery-140"):
        return False
    if bt == "BTMIndividualSketchRegionQuery-140" and not allow_region:
        return False
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
        return False
    try:
        _bookkeeping(raw)
    except EditError:
        return False
    query = raw.get("queryString", "")
    ids = raw.get("deterministicIds", [])
    if (
        not isinstance(query, str)
        or len(query) > 8192
        or not isinstance(ids, list)
        or len(ids) > 2000
    ):
        return False
    if any(not isinstance(i, str) or not 1 <= len(i) <= 256 for i in ids):
        return False
    if bt == "BTMIndividualSketchRegionQuery-140":
        feature_id = raw.get("featureId")
        return (
            isinstance(feature_id, str)
            and 1 <= len(feature_id) <= 256
            and ("filterInnerLoops" not in raw or type(raw["filterInnerLoops"]) is bool)
        )
    return bool(query.strip() or ids)


def _validate(param: dict[str, JsonValue], rule: ParameterRule) -> None:
    if param.get("btType") != rule.bt_type:
        _reject()
    _bookkeeping(param)
    if rule.boolean is not None:
        if (
            set(param) - (BASE_FIELDS | {"value"})
            or type(param.get("value")) is not bool
            or param["value"] not in rule.boolean
        ):
            _reject()
    elif rule.enum is not None:
        if (
            set(param) - (BASE_FIELDS | {"enumName", "namespace", "value"})
            or ("namespace" in param and param["namespace"] != "")
            or param.get("enumName") != rule.enum[0]
            or param.get("value") != rule.enum[1]
        ):
            _reject()
    elif rule.quantity is not None:
        _quantity_value(param, rule.quantity)
    else:
        field = "items" if rule.sequence == "empty_items" else "queries"
        value = param.get(field)
        if set(param) - (BASE_FIELDS | {field}) or not isinstance(value, list):
            _reject()
        if rule.sequence in ("entities", "edges"):
            if (
                not value
                or len(value) > 2000
                or not all(
                    _entity_query(q, allow_region=rule.sequence == "entities")
                    for q in value
                )
            ):
                _reject()
        elif value != []:
            _reject()


def ui_quantity_parameter(
    feature: dict[str, JsonValue], parameter_id: str
) -> dict[str, JsonValue]:
    feature_type = feature.get("featureType")
    rules = UI_RULES.get(feature_type) if isinstance(feature_type, str) else None
    raw = feature.get("parameters")
    if rules is None or not isinstance(raw, list) or not raw or len(raw) > len(rules):
        _reject()
    params: dict[str, dict[str, JsonValue]] = {}
    for item in raw:
        if not isinstance(item, dict):
            _reject()
        key = item.get("parameterId")
        if not isinstance(key, str) or key in params or key not in rules:
            _reject()
        _validate(item, rules[key])
        params[key] = item
    assert isinstance(feature_type, str)
    if not UI_REQUIRED[feature_type] <= params.keys() or parameter_id not in params:
        _reject()
    return params[parameter_id]
