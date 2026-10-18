"""Closed A1 adapters. This is the sole source of operation/parameter support.

See docs/HACKATHON_MODIFY_A1.md for fixture provenance and deliberately narrow
shapes. No aliases, tolerant quantity subclasses or general expressions.
"""

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, assert_never, cast

from pydantic import JsonValue

from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import (
    ModifyOperation,
    OperationPreview,
    OperationType,
    RenameFeature,
    SetExtrudeDepth,
    SetFilletRadius,
    SetSuppressed,
    SetUnsuppressed,
    Target,
    valid_name,
    valid_quantity,
)

from .parameters import display_text


@dataclass(frozen=True)
class EditAdapter:
    feature_types: tuple[str, ...]
    parameter_id: str | None = None
    allowed_parameters: frozenset[str] = frozenset()


SUPPORTED_EDITS = MappingProxyType(
    {
        "SET_SUPPRESSED": EditAdapter(("fillet",)),
        "SET_UNSUPPRESSED": EditAdapter(("fillet",)),
        "RENAME_FEATURE": EditAdapter(("extrude", "fillet")),
        "SET_EXTRUDE_DEPTH": EditAdapter(
            ("extrude",),
            "depth",
            frozenset({"bodyType", "operationType", "entities", "endBound", "depth"}),
        ),
        "SET_FILLET_RADIUS": EditAdapter(
            ("fillet",),
            "radius",
            frozenset({"entities", "radius", "tangentPropagation"}),
        ),
    }
)


def label(feature: dict[str, JsonValue], target: Target) -> str:
    value = feature.get("name")
    text = display_text(value) if isinstance(value, str) else None
    return (
        text
        if text and text.strip()
        else f"{target.feature_type.title()} {target.position}"
    )


def locate(
    features: list[dict[str, JsonValue]], target: Target
) -> dict[str, JsonValue]:
    matches = [f for f in features if f.get("featureId") == target.feature_id]
    if len(matches) != 1:
        raise EditError("ambiguous_target" if matches else "model_changed")
    feature = matches[0]
    if (
        target.position > len(features)
        or features[target.position - 1] is not feature
        or feature.get("featureType") != target.feature_type
        or feature.get("btType") != "BTMFeature-134"
    ):
        raise EditError("model_changed")
    return feature


def _parameters(
    feature: dict[str, JsonValue], adapter: EditAdapter
) -> dict[str, dict[str, JsonValue]]:
    raw = feature.get("parameters")
    if not isinstance(raw, list) or not raw or len(raw) > 20:
        raise EditError("unsupported_target", 422)
    params: dict[str, dict[str, JsonValue]] = {}
    for param in raw:
        if not isinstance(param, dict):
            raise EditError("unsupported_target", 422)
        key = param.get("parameterId")
        if (
            not isinstance(key, str)
            or key in params
            or key not in adapter.allowed_parameters
        ):
            raise EditError("unsupported_target", 422)
        params[key] = param
    entities = params.get("entities", {})
    if (
        entities.get("btType") != "BTMParameterQueryList-148"
        or not isinstance(entities.get("queries"), list)
        or not entities["queries"]
    ):
        raise EditError("unsupported_target", 422)
    if adapter.parameter_id == "depth":
        for key, enum, value in (
            ("bodyType", "ExtendedToolBodyType", "SOLID"),
            ("operationType", "NewBodyOperationType", "NEW"),
            ("endBound", "BoundingType", "BLIND"),
        ):
            p = params.get(key, {})
            if (
                p.get("btType") != "BTMParameterEnum-145"
                or p.get("enumName") != enum
                or p.get("value") != value
            ):
                raise EditError("unsupported_target", 422)
    elif "tangentPropagation" in params:
        p = params["tangentPropagation"]
        if (
            p.get("btType") != "BTMParameterBoolean-144"
            or type(p.get("value")) is not bool
        ):
            raise EditError("unsupported_target", 422)
    return params


def quantity_parameter(
    feature: dict[str, JsonValue], kind: OperationType
) -> dict[str, JsonValue]:
    adapter = SUPPORTED_EDITS[kind]
    if (
        feature.get("featureType") not in adapter.feature_types
        or adapter.parameter_id is None
    ):
        raise EditError("unsupported_target", 422)
    param = _parameters(feature, adapter).get(adapter.parameter_id, {})
    if (
        param.get("btType") != "BTMParameterQuantity-147"
        or set(param) - {"btType", "parameterId", "expression", "nodeId", "isInteger"}
        or ("isInteger" in param and param["isInteger"] is not False)
        or ("nodeId" in param and not isinstance(param["nodeId"], str))
        or not isinstance(param.get("expression"), str)
    ):
        raise EditError("unsupported_target", 422)
    try:
        valid_quantity(cast(str, param["expression"]))
    except ValueError:
        raise EditError("unsupported_target", 422) from None
    return param


def supports_operation(kind: str, feature_type: str) -> bool:
    """Semantic capability only; fresh server evidence still decides applicability."""
    adapter = SUPPORTED_EDITS.get(kind)
    return adapter is not None and feature_type in adapter.feature_types


def applicable(
    features: list[dict[str, JsonValue]], target: Target, kind: OperationType
) -> None:
    feature = locate(features, target)
    if not supports_operation(kind, target.feature_type):
        raise EditError("unsupported_target", 422)
    state = feature.get("suppressed")
    if type(state) is not bool:
        raise EditError("unsupported_target", 422)
    if kind in ("SET_SUPPRESSED", "SET_UNSUPPRESSED"):
        if target.position != len(features) or state is (kind == "SET_SUPPRESSED"):
            raise EditError("unsupported_target", 422)
    elif kind == "RENAME_FEATURE":
        old = feature.get("name")
        # Exact old text is previewed; names never resolve identity.
        if not isinstance(old, str) or display_text(old) is None or not old.strip():
            raise EditError("unsupported_target", 422)
        # Rename is a full-definition replacement, so a complete supported
        # parameter shape is mandatory even though no parameter is edited.
        quantity_parameter(
            feature,
            "SET_EXTRUDE_DEPTH"
            if target.feature_type == "extrude"
            else "SET_FILLET_RADIUS",
        )
    else:
        if state:
            raise EditError("unsupported_target", 422)
        quantity_parameter(feature, kind)


def change(
    features: list[dict[str, JsonValue]], target: Target, operation: ModifyOperation
) -> tuple[dict[str, JsonValue], OperationPreview]:
    """Copy a freshly inspected definition and change exactly one allowed field."""
    if operation.target != target.handle:
        raise EditError("unsupported_target", 422)
    applicable(features, target, operation.type)
    feature = locate(features, target)
    updated = deepcopy(feature)
    field: LiteralField
    match operation:
        case SetSuppressed() | SetUnsuppressed():
            desired = isinstance(operation, SetSuppressed)
            current, proposed = (
                ("Active", "Suppressed") if desired else ("Suppressed", "Active")
            )
            updated["suppressed"] = desired
            field = "Suppression"
        case RenameFeature():
            current, proposed = (
                cast(str, feature["name"]),
                valid_name(operation.new_name),
            )
            updated["name"] = proposed
            field = "Name"
        case SetExtrudeDepth() | SetFilletRadius():
            param = quantity_parameter(updated, operation.type)
            current, proposed = (
                cast(str, param["expression"]),
                valid_quantity(operation.quantity),
            )
            param["expression"] = proposed
            field = "Depth" if isinstance(operation, SetExtrudeDepth) else "Radius"
        case _:
            assert_never(operation)
    if current == proposed:
        raise EditError("unsupported_target", 422)
    return updated, OperationPreview(
        type=operation.type,
        label=label(feature, target),
        feature_type=target.feature_type,
        position=target.position,
        field=field,
        current=current,
        proposed=proposed,
    )


# Kept private to the provider adapter; the semantic models carry no field paths.
LiteralField = Literal["Suppression", "Name", "Depth", "Radius"]
