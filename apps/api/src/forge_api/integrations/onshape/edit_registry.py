"""Closed Modify registry. This is the sole source of operation support.

See docs/HACKATHON_MODIFY_A1.md for fixture provenance and deliberately narrow
shapes and docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md for the explicit current-UI
parameter contracts. No aliases, tolerant subclasses or general expressions.
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
from .standard_edit_shapes import ui_quantity_parameter


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
    """Complete historical profile, deliberately separate from current UI.

    Only fields exercised by the A1 fixture/metadata preservation tests belong
    here. In particular, query filters and current-UI bookkeeping are forbidden.
    A failed historical profile never falls through to another validator.
    """
    raw = feature.get("parameters")
    if not isinstance(raw, list) or len(raw) != len(adapter.allowed_parameters):
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
        if "nodeId" in param and not isinstance(param["nodeId"], str):
            raise EditError("unsupported_target", 422)
        params[key] = param
    if params.keys() != adapter.allowed_parameters:
        raise EditError("unsupported_target", 422)
    entities = params.get("entities", {})
    base = {"btType", "parameterId", "nodeId"}
    queries = entities.get("queries")
    if (
        entities.get("btType") != "BTMParameterQueryList-148"
        or set(entities) - (base | {"queries"})
        or not isinstance(queries, list)
        or not 1 <= len(queries) <= 2000
    ):
        raise EditError("unsupported_target", 422)
    query_type, query_field = (
        ("BTMIndividualSketchRegionQuery-140", "featureId")
        if adapter.parameter_id == "depth"
        else ("BTMIndividualQuery-138", "queryString")
    )
    for query in queries:
        if (
            not isinstance(query, dict)
            or set(query) != {"btType", query_field}
            or query.get("btType") != query_type
            or not isinstance(query.get(query_field), str)
            or not 1 <= len(cast(str, query[query_field])) <= 8192
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
                or set(p) - (base | {"enumName", "value"})
                or p.get("enumName") != enum
                or p.get("value") != value
            ):
                raise EditError("unsupported_target", 422)
    else:
        p = params["tangentPropagation"]
        if (
            p.get("btType") != "BTMParameterBoolean-144"
            or set(p) - (base | {"value"})
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
        or feature.get("btType") != "BTMFeature-134"
        or adapter.parameter_id is None
    ):
        raise EditError("unsupported_target", 422)
    raw = feature.get("parameters")
    # Select by the complete ID multiset, never by subset membership. Either
    # validate the entire historical shape or give the entire feature to UI.
    # No field stripping, hybrid profile or fallback after historical failure.
    if not (
        isinstance(raw, list)
        and len(raw) == len(adapter.allowed_parameters)
        and all(
            isinstance(item, dict) and isinstance(item.get("parameterId"), str)
            for item in raw
        )
        and {cast(dict[str, JsonValue], item)["parameterId"] for item in raw}
        == adapter.allowed_parameters
    ):
        return ui_quantity_parameter(feature, adapter.parameter_id)
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
