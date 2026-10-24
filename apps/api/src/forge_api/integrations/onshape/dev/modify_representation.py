"""Request-local shape minimization. No logging, provider IO or write authority.

An exact_match describes the current registry's replacement *representation*,
not runtime target eligibility, complete model health or live write conformance.
"""

from typing import Literal

from pydantic import Field, JsonValue

from forge_api.cad_edits.domain import Closed, EditError
from forge_api.cad_edits.plans import valid_quantity

from ..edit_registry import quantity_parameter
from ..eligibility import MISSING
from ..parameters import display_text
from ..standard_edit_shapes import QUANTITY_FIELDS, UI_RULES

Category = Literal["sketch", "extrude", "fillet", "unsupported"]
DefinitionType = Literal[
    "recognized_standard", "other", "missing", "null", "wrong_type"
]
ParameterId = Literal[
    "bodyType",
    "operationType",
    "entities",
    "endBound",
    "depth",
    "radius",
    "tangentPropagation",
]
ParameterType = Literal[
    "enum",
    "query_list",
    "quantity",
    "boolean",
    "array",
    "other",
    "missing",
    "null",
    "wrong_type",
]
ShapeMatch = Literal["exact_match", "unsupported_shape", "unavailable"]
QueryItem = Literal[
    "individual_query", "sketch_region_query", "other", "missing", "null", "wrong_type"
]

VOCABULARY: dict[str, tuple[ParameterId, ...]] = {
    "extrude": ("bodyType", "operationType", "entities", "endBound", "depth"),
    "fillet": ("entities", "radius", "tangentPropagation"),
}
ENUMS = {
    "bodyType": ("ExtendedToolBodyType", "SOLID"),
    "operationType": ("NewBodyOperationType", "NEW"),
    "endBound": ("BoundingType", "BLIND"),
}
PARAMETER_TYPES: dict[str, ParameterType] = {
    "BTMParameterEnum-145": "enum",
    "BTMParameterQueryList-148": "query_list",
    "BTMParameterQuantity-147": "quantity",
    "BTMParameterBoolean-144": "boolean",
    "BTMParameterArray-2025": "array",
}


class QuantityShape(Closed):
    expression: Literal[
        "positive_mm_literal", "positive_in_literal", "other", "missing", "wrong_type"
    ]
    node_id: Literal["missing", "string_present", "wrong_type"]
    is_integer: Literal["missing", "false", "true", "wrong_type"]
    supported_fields_only: bool


class QueryShape(Closed):
    correct_envelope: bool
    state: Literal["missing", "null", "wrong_type", "empty", "nonempty"]
    count: int | None = Field(ge=0, le=2000)
    count_capped: bool
    # Unique categories from at most the first 2000 items, never raw btTypes.
    item_types: tuple[QueryItem, ...] = Field(max_length=6)


class ParameterShape(Closed):
    parameter_id: ParameterId
    present: bool
    occurrences: int = Field(ge=0, le=20)
    duplicate: bool
    bt_type: ParameterType
    enum_value: Literal["SOLID", "NEW", "BLIND", "other"] | None
    enum_name_matches: bool | None
    quantity: QuantityShape | None
    query: QueryShape | None
    boolean_type_valid: bool | None
    boolean_value: bool | None


class FeatureRepresentation(Closed):
    position: int = Field(ge=1, le=20)
    category: Category
    definition_bt_type: DefinitionType
    ordinary_top_level: bool
    identity_usable: bool
    name_usable: bool
    parameters_state: Literal["array", "missing", "null", "wrong_type"]
    parameter_count: int | None = Field(ge=0, le=20)
    parameter_count_capped: bool
    malformed_parameter_present: bool
    unknown_present: bool
    unknown_count: int = Field(ge=0, le=20)
    unknown_count_capped: bool
    duplicate_known_present: bool
    parameters: tuple[ParameterShape, ...] = Field(max_length=5)
    parameter_shape_matches_registry: bool
    replacement: ShapeMatch
    rename: ShapeMatch


class RepresentationCoverage(Closed):
    inventory_complete: bool
    source_matches: bool
    positions: tuple[FeatureRepresentation, ...] = Field(max_length=20)


def _category(value: object) -> Category:
    return (
        "sketch"
        if value == "newSketch"
        else "extrude"
        if value == "extrude"
        else "fillet"
        if value == "fillet"
        else "unsupported"
    )


def _type(value: object) -> ParameterType:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if not isinstance(value, str):
        return "wrong_type"
    return PARAMETER_TYPES.get(value, "other")


def _quantity(
    param: dict[str, JsonValue], *, current_ui: bool = False
) -> QuantityShape:
    expression = param.get("expression", MISSING)
    literal = False
    if isinstance(expression, str):
        try:
            valid_quantity(expression)
            literal = True
        except ValueError:
            pass
    integer = param.get("isInteger", MISSING)
    node = param.get("nodeId", MISSING)
    return QuantityShape(
        expression="missing"
        if expression is MISSING
        else "wrong_type"
        if not isinstance(expression, str)
        else "positive_mm_literal"
        if literal and expression.endswith(" mm")
        else "positive_in_literal"
        if literal
        else "other",
        node_id="missing"
        if node is MISSING
        else "string_present"
        if isinstance(node, str)
        else "wrong_type",
        is_integer="missing"
        if integer is MISSING
        else "false"
        if integer is False
        else "true"
        if integer is True
        else "wrong_type",
        supported_fields_only=not set(param)
        - (
            QUANTITY_FIELDS
            if current_ui
            else {"btType", "parameterId", "expression", "nodeId", "isInteger"}
        ),
    )


def _query_item(item: JsonValue) -> QueryItem:
    if not isinstance(item, dict):
        return "wrong_type"
    value = item.get("btType", MISSING)
    return (
        "missing"
        if value is MISSING
        else "null"
        if value is None
        else "wrong_type"
        if not isinstance(value, str)
        else "individual_query"
        if value == "BTMIndividualQuery-138"
        else "sketch_region_query"
        if value == "BTMIndividualSketchRegionQuery-140"
        else "other"
    )


def _query(param: dict[str, JsonValue]) -> QueryShape:
    queries = param.get("queries", MISSING)
    is_list = isinstance(queries, list)
    return QueryShape(
        correct_envelope=param.get("btType") == "BTMParameterQueryList-148" and is_list,
        state="missing"
        if queries is MISSING
        else "null"
        if queries is None
        else "wrong_type"
        if not is_list
        else "nonempty"
        if queries
        else "empty",
        count=min(len(queries), 2000) if isinstance(queries, list) else None,
        count_capped=isinstance(queries, list) and len(queries) > 2000,
        item_types=tuple(sorted({_query_item(q) for q in queries[:2000]}))
        if isinstance(queries, list)
        else (),
    )


def _parameter(
    key: ParameterId, matches: list[dict[str, JsonValue]], *, current_ui: bool = False
) -> ParameterShape:
    # Duplicate details are only illustrative; registry rejection is never relaxed.
    param = matches[0] if matches else {}
    enum = ENUMS.get(key)
    boolean = param.get("value", MISSING)
    enum_value: Literal["SOLID", "NEW", "BLIND", "other"] | None = None
    if matches and enum is not None:
        value = param.get("value")
        enum_value = (
            "SOLID"
            if key == "bodyType" and value == "SOLID"
            else "NEW"
            if key == "operationType" and value == "NEW"
            else "BLIND"
            if key == "endBound" and value == "BLIND"
            else "other"
        )
    return ParameterShape(
        parameter_id=key,
        present=bool(matches),
        occurrences=min(len(matches), 20),
        duplicate=len(matches) > 1,
        bt_type=_type(param.get("btType", MISSING)),
        enum_value=enum_value,
        enum_name_matches=param.get("enumName") == enum[0]
        if matches and enum is not None
        else None,
        quantity=_quantity(param, current_ui=current_ui)
        if matches and key in ("depth", "radius")
        else None,
        query=_query(param) if matches and key == "entities" else None,
        boolean_type_valid=type(boolean) is bool
        if matches and key == "tangentPropagation"
        else None,
        boolean_value=boolean
        if key == "tangentPropagation" and type(boolean) is bool
        else None,
    )


def _feature(raw: JsonValue, position: int, complete: bool) -> FeatureRepresentation:
    feature = raw if isinstance(raw, dict) else {}
    category = _category(feature.get("featureType"))
    bt = feature.get("btType", MISSING)
    standard = "BTMSketch-151" if category == "sketch" else "BTMFeature-134"
    bt_type: DefinitionType = (
        "missing"
        if bt is MISSING
        else "null"
        if bt is None
        else "wrong_type"
        if not isinstance(bt, str)
        else "recognized_standard"
        if category != "unsupported" and bt == standard
        else "other"
    )
    raw_params = feature.get("parameters", MISSING)
    params = raw_params if isinstance(raw_params, list) else []
    vocabulary = VOCABULARY.get(category, ())
    parameter_shape = False
    if category in ("extrude", "fillet"):
        try:
            quantity_parameter(
                feature,
                "SET_EXTRUDE_DEPTH" if category == "extrude" else "SET_FILLET_RADIUS",
            )
            parameter_shape = True
        except EditError:
            pass
    current_ui = parameter_shape and any(
        isinstance(p, dict) and p.get("parameterId") not in vocabulary for p in params
    )
    registry_ids = UI_RULES.get(category, {}) if current_ui else vocabulary
    matches: dict[ParameterId, list[dict[str, JsonValue]]] = {k: [] for k in vocabulary}
    unknown = 0
    malformed = False
    seen: set[str] = set()
    duplicate_known = False
    for param in params:
        if not isinstance(param, dict):
            malformed = True
            continue
        # Never return, log or preserve arbitrary strings in minimized metadata.
        key = param.get("parameterId")
        if not isinstance(key, str):
            malformed = True
            continue
        known = next((k for k in vocabulary if k == key), None)
        if key in UI_RULES.get(category, {}):
            duplicate_known = duplicate_known or key in seen
            seen.add(key)
        if known is not None:
            matches[known].append(param)
        if key not in registry_ids:
            unknown += 1
    ordinary = (
        feature.get("namespace") == ""
        and feature.get("subFeatures") == []
        and feature.get("returnAfterSubfeatures") is False
        and type(feature.get("suppressed")) is bool
    )
    name = feature.get("name")
    name_usable = (
        isinstance(name, str) and display_text(name) is not None and bool(name.strip())
    )
    identity = feature.get("featureId")
    identity_usable = isinstance(identity, str) and 1 <= len(identity) <= 256
    replacement: ShapeMatch = (
        "unavailable"
        if not complete
        or category not in ("extrude", "fillet")
        or raw_params is MISSING
        or raw_params is None
        or bt is MISSING
        or bt is None
        or not identity_usable
        else "exact_match"
        if bt_type == "recognized_standard" and ordinary and parameter_shape
        else "unsupported_shape"
    )
    return FeatureRepresentation(
        position=position,
        category=category,
        definition_bt_type=bt_type,
        ordinary_top_level=ordinary,
        identity_usable=identity_usable,
        name_usable=name_usable,
        parameters_state="missing"
        if raw_params is MISSING
        else "null"
        if raw_params is None
        else "array"
        if isinstance(raw_params, list)
        else "wrong_type",
        parameter_count=min(len(params), 20) if isinstance(raw_params, list) else None,
        parameter_count_capped=len(params) > 20,
        malformed_parameter_present=malformed,
        unknown_present=unknown > 0,
        unknown_count=min(unknown, 20),
        unknown_count_capped=unknown > 20,
        duplicate_known_present=duplicate_known,
        parameters=tuple(
            _parameter(key, values, current_ui=current_ui)
            for key, values in matches.items()
        ),
        parameter_shape_matches_registry=parameter_shape,
        replacement=replacement,
        rename="unsupported_shape"
        if replacement == "exact_match" and not name_usable
        else replacement,
    )


def representation_coverage(
    data: JsonValue, *, source_matches: bool
) -> RepresentationCoverage:
    """Sanitize the existing bounded feature response without IO or mutation."""
    if not isinstance(data, dict):
        raise EditError("invalid_provider_response", 503)
    items = data.get("features")
    if not isinstance(items, list) or len(items) > 20:
        raise EditError("invalid_provider_response", 503)
    complete = data.get("isComplete") is True
    return RepresentationCoverage(
        inventory_complete=complete,
        source_matches=source_matches,
        positions=tuple(
            _feature(f, i, complete and source_matches) for i, f in enumerate(items, 1)
        ),
    )
