"""Bounded writes-OFF evidence for every source-declared Extrude quantity role.

This projector never validates a replacement or grants edit authority. It emits
only fixed role names, schema field names and closed value classifications.
"""

import re
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Literal, cast

from pydantic import Field, JsonValue

from forge_api.cad_edits.domain import Closed, EditError

from ..eligibility import MISSING
from ..standard_edit_shapes import QUANTITY_FIELDS
from ..standard_shape_contract import StandardId
from .standard_parameters import EXTRUDE, SourceKind

MAX_FEATURES = 20
MAX_PARAMETERS = 100
MAX_EXPRESSION_CHARS = 256
MAX_UNEXPECTED_FIELDS = 20
MAX_LOG_CHARS = 16 * 1024
QUANTITY_SOURCE_KINDS = frozenset({"length", "angle", "real"})
EXTRUDE_QUANTITY_ROLES: tuple[StandardId, ...] = tuple(
    key for key, kind in EXTRUDE.items() if kind in QUANTITY_SOURCE_KINDS
)
FIELD_ORDER = (
    "btType",
    "parameterId",
    "expression",
    "nodeId",
    "isInteger",
    "value",
    "units",
    "importMicroversion",
    "parameterName",
    "valueString",
    "libraryRelationType",
)
assert set(FIELD_ORDER) == QUANTITY_FIELDS

ExtrudeQuantityKind = Literal["length", "angle", "real"]
ProviderType = Literal[
    "quantity", "missing", "null", "wrong_type", "other_provider_type"
]
ExpressionClass = Literal[
    "missing",
    "null",
    "wrong_type",
    "empty",
    "too_long",
    "literal",
    "scientific_literal",
    "configuration_reference",
    "arithmetic_expression",
    "other_string",
]
NumberClass = Literal["unavailable", "negative", "zero", "positive"]
NumberFormat = Literal["unavailable", "integer", "decimal", "scientific"]
SignClass = Literal["unavailable", "unsigned", "plus", "minus"]
ExpressionUnits = Literal[
    "unavailable", "unitless", "mm", "cm", "m", "in", "ft", "deg", "rad"
]
ValueClass = Literal[
    "missing", "null", "wrong_type", "nonfinite", "negative", "zero", "positive"
]
StringState = Literal["missing", "null", "wrong_type", "empty", "default", "nonempty"]
NodeState = Literal["missing", "null", "wrong_type", "empty", "string_present"]
IntegerState = Literal["missing", "null", "wrong_type", "false", "true"]
QuantityField = Literal[
    "btType",
    "parameterId",
    "expression",
    "nodeId",
    "isInteger",
    "value",
    "units",
    "importMicroversion",
    "parameterName",
    "valueString",
    "libraryRelationType",
]

LITERAL = re.compile(
    r"(?P<sign>[+-]?)(?P<integer>[0-9]{1,12})"
    r"(?P<fraction>\.[0-9]{1,12})?"
    r"(?: (?P<units>mm|cm|m|in|ft|deg|rad))?"
)
SCIENTIFIC = re.compile(
    r"[+-]?[0-9]{1,12}(?:\.[0-9]{1,12})?[eE][+-]?[0-9]{1,3}"
    r"(?: (?:mm|cm|m|in|ft|deg|rad))?"
)


class ExpressionEvidence(Closed):
    expression_class: ExpressionClass
    number_class: NumberClass
    number_format: NumberFormat
    sign: SignClass
    units: ExpressionUnits


class QuantityEvidence(Closed):
    provider_type: ProviderType
    expression: ExpressionEvidence
    value: ValueClass
    cached_units: StringState
    node_id: NodeState
    is_integer: IntegerState
    import_microversion: StringState
    parameter_name: StringState
    value_string: StringState
    library_relation_type: StringState
    present_allowed_fields: tuple[QuantityField, ...] = Field(max_length=11)
    required_fields_present: bool
    allowed_fields_only: bool
    unexpected_field_count: int = Field(ge=0, le=MAX_UNEXPECTED_FIELDS)
    unexpected_field_count_capped: bool


class ExtrudeQuantityRole(Closed):
    role: StandardId
    source_kind: ExtrudeQuantityKind
    activity: Literal["active", "dormant"]
    occurrences: int = Field(ge=0, le=MAX_PARAMETERS)
    duplicate: bool
    evidence: QuantityEvidence | None
    expression_dimension_matches_source: bool | None
    malformed: bool
    unexpected_fields: bool
    uninspected: bool


class ExtrudeQuantitySummary(Closed):
    position: int = Field(ge=1, le=MAX_FEATURES)
    expected_roles: int = Field(ge=1, le=20)
    roles_present: int = Field(ge=0, le=20)
    roles_inspected: int = Field(ge=0, le=20)
    all_roles_inspected: bool
    unrecognized_quantity_parameters: int = Field(ge=0, le=MAX_PARAMETERS)
    parameter_count_capped: bool
    any_missing: bool
    any_duplicate: bool
    any_malformed: bool
    any_unexpected_fields: bool
    any_uninspected: bool


class ExtrudeQuantityInventory(Closed):
    summary: ExtrudeQuantitySummary
    roles: tuple[ExtrudeQuantityRole, ...] = Field(
        min_length=len(EXTRUDE_QUANTITY_ROLES),
        max_length=len(EXTRUDE_QUANTITY_ROLES),
    )


def _string_state(value: object, *, library: bool = False) -> StringState:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) is not str:
        return "wrong_type"
    if value == "":
        return "empty"
    if library and value == "DEFAULT":
        return "default"
    return "nonempty"


def _node_state(value: object) -> NodeState:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) is not str:
        return "wrong_type"
    return "string_present" if value else "empty"


def _integer_state(value: object) -> IntegerState:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if value is False:
        return "false"
    if value is True:
        return "true"
    return "wrong_type"


def _value_class(value: object) -> ValueClass:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) not in (int, float):
        return "wrong_type"
    numeric = cast(int | float, value)
    if not isfinite(numeric):
        return "nonfinite"
    if numeric == 0:
        return "zero"
    return "positive" if numeric > 0 else "negative"


def _unavailable_expression(state: ExpressionClass) -> ExpressionEvidence:
    return ExpressionEvidence(
        expression_class=state,
        number_class="unavailable",
        number_format="unavailable",
        sign="unavailable",
        units="unavailable",
    )


def _expression(value: object) -> ExpressionEvidence:
    if value is MISSING:
        return _unavailable_expression("missing")
    if value is None:
        return _unavailable_expression("null")
    if type(value) is not str:
        return _unavailable_expression("wrong_type")
    if value == "":
        return _unavailable_expression("empty")
    if len(value) > MAX_EXPRESSION_CHARS:
        return _unavailable_expression("too_long")
    match = LITERAL.fullmatch(value)
    if match is not None:
        fraction = match.group("fraction")
        sign_text = match.group("sign")
        try:
            number = Decimal(sign_text + match.group("integer") + (fraction or ""))
        except InvalidOperation:
            return _unavailable_expression("other_string")
        units = cast(ExpressionUnits, match.group("units") or "unitless")
        return ExpressionEvidence(
            expression_class="literal",
            number_class="zero"
            if number == 0
            else "positive"
            if number > 0
            else "negative",
            number_format="decimal" if fraction is not None else "integer",
            sign="plus"
            if sign_text == "+"
            else "minus"
            if sign_text == "-"
            else "unsigned",
            units=units,
        )
    if SCIENTIFIC.fullmatch(value):
        return ExpressionEvidence(
            expression_class="scientific_literal",
            number_class="unavailable",
            number_format="scientific",
            sign="minus"
            if value.startswith("-")
            else "plus"
            if value.startswith("+")
            else "unsigned",
            units="unavailable",
        )
    if value.startswith("#"):
        return _unavailable_expression("configuration_reference")
    if any(character in value for character in "*/()") or any(
        character in value[1:] for character in "+-"
    ):
        return _unavailable_expression("arithmetic_expression")
    return _unavailable_expression("other_string")


def _provider_type(value: object) -> ProviderType:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) is not str:
        return "wrong_type"
    return "quantity" if value == "BTMParameterQuantity-147" else "other_provider_type"


def _evidence(param: dict[str, JsonValue]) -> QuantityEvidence:
    extras = [key for key in param if key not in QUANTITY_FIELDS]
    present = tuple(
        cast(QuantityField, field) for field in FIELD_ORDER if field in param
    )
    return QuantityEvidence(
        provider_type=_provider_type(param.get("btType", MISSING)),
        expression=_expression(param.get("expression", MISSING)),
        value=_value_class(param.get("value", MISSING)),
        cached_units=_string_state(param.get("units", MISSING)),
        node_id=_node_state(param.get("nodeId", MISSING)),
        is_integer=_integer_state(param.get("isInteger", MISSING)),
        import_microversion=_string_state(param.get("importMicroversion", MISSING)),
        parameter_name=_string_state(param.get("parameterName", MISSING)),
        value_string=_string_state(param.get("valueString", MISSING)),
        library_relation_type=_string_state(
            param.get("libraryRelationType", MISSING), library=True
        ),
        present_allowed_fields=present,
        required_fields_present=all(
            field in param for field in ("btType", "parameterId", "expression")
        ),
        allowed_fields_only=not extras,
        unexpected_field_count=min(len(extras), MAX_UNEXPECTED_FIELDS),
        unexpected_field_count_capped=len(extras) > MAX_UNEXPECTED_FIELDS,
    )


def _role(
    key: StandardId, kind: SourceKind, matches: list[dict[str, JsonValue]]
) -> ExtrudeQuantityRole:
    source_kind = cast(ExtrudeQuantityKind, kind)
    activity: Literal["active", "dormant"] = "active" if key == "depth" else "dormant"
    if len(matches) != 1:
        return ExtrudeQuantityRole(
            role=key,
            source_kind=source_kind,
            activity=activity,
            occurrences=min(len(matches), MAX_PARAMETERS),
            duplicate=len(matches) > 1,
            evidence=None,
            expression_dimension_matches_source=None,
            malformed=not matches or len(matches) > 1,
            unexpected_fields=False,
            uninspected=True,
        )
    evidence = _evidence(matches[0])
    expression_units = evidence.expression.units
    dimension_matches = (
        None
        if evidence.expression.expression_class != "literal"
        else expression_units in ("mm", "cm", "m", "in", "ft")
        if source_kind == "length"
        else expression_units in ("deg", "rad")
        if source_kind == "angle"
        else expression_units == "unitless"
    )
    malformed = (
        evidence.provider_type != "quantity"
        or not evidence.required_fields_present
        or evidence.expression.expression_class
        in ("missing", "null", "wrong_type", "empty", "too_long")
    )
    return ExtrudeQuantityRole(
        role=key,
        source_kind=source_kind,
        activity=activity,
        occurrences=1,
        duplicate=False,
        evidence=evidence,
        expression_dimension_matches_source=dimension_matches,
        malformed=malformed,
        unexpected_fields=not evidence.allowed_fields_only,
        uninspected=False,
    )


def extrude_quantity_inventory(
    data: JsonValue,
) -> tuple[ExtrudeQuantityInventory, ...]:
    """Project all ten roles without stopping at the production first failure."""
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise EditError("invalid_provider_response", 503)
    features = data["features"]
    assert isinstance(features, list)
    if len(features) > MAX_FEATURES:
        raise EditError("invalid_provider_response", 503)
    reports: list[ExtrudeQuantityInventory] = []
    for position, feature in enumerate(features, 1):
        if not isinstance(feature, dict) or feature.get("featureType") != "extrude":
            continue
        raw = feature.get("parameters")
        params = raw if isinstance(raw, list) else []
        capped = len(params) > MAX_PARAMETERS
        matches: dict[StandardId, list[dict[str, JsonValue]]] = {
            key: [] for key in EXTRUDE_QUANTITY_ROLES
        }
        unknown_quantities = 0
        for param in params[:MAX_PARAMETERS]:
            if not isinstance(param, dict):
                continue
            raw_key = param.get("parameterId")
            key = next(
                (candidate for candidate in matches if candidate == raw_key), None
            )
            if key is not None:
                matches[key].append(param)
            elif param.get("btType") == "BTMParameterQuantity-147":
                unknown_quantities += 1
        roles = tuple(
            _role(key, EXTRUDE[key], matches[key]) for key in EXTRUDE_QUANTITY_ROLES
        )
        present = sum(bool(matches[key]) for key in EXTRUDE_QUANTITY_ROLES)
        inspected = sum(not role.uninspected for role in roles)
        reports.append(
            ExtrudeQuantityInventory(
                summary=ExtrudeQuantitySummary(
                    position=position,
                    expected_roles=len(EXTRUDE_QUANTITY_ROLES),
                    roles_present=present,
                    roles_inspected=inspected,
                    all_roles_inspected=(
                        present == len(EXTRUDE_QUANTITY_ROLES)
                        and inspected == len(EXTRUDE_QUANTITY_ROLES)
                        and not capped
                    ),
                    unrecognized_quantity_parameters=min(
                        unknown_quantities, MAX_PARAMETERS
                    ),
                    parameter_count_capped=capped,
                    any_missing=any(not matches[key] for key in EXTRUDE_QUANTITY_ROLES),
                    any_duplicate=any(
                        len(matches[key]) > 1 for key in EXTRUDE_QUANTITY_ROLES
                    ),
                    any_malformed=(
                        not isinstance(raw, list)
                        or any(role.malformed for role in roles)
                    ),
                    any_unexpected_fields=any(role.unexpected_fields for role in roles),
                    any_uninspected=capped or any(role.uninspected for role in roles),
                ),
                roles=roles,
            )
        )
    return tuple(reports)


def extrude_quantity_text(inventory: ExtrudeQuantityInventory) -> str:
    """Return one already-closed record under an independent output bound."""
    result = inventory.model_dump_json()
    if len(result) > MAX_LOG_CHARS:
        raise EditError("invalid_provider_response", 503)
    return result
