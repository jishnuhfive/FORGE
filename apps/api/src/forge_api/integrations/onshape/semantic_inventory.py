"""Closed provider-node bookkeeping projection; never an eligibility adapter.

Only declared, validated node locations lose nodeId. Unknown fields/containers
are retained verbatim. Raw evidence/payloads are never modified.
"""

from copy import deepcopy
from typing import cast

from pydantic import JsonValue

from forge_api.cad_edits.domain import EditError

from .edit_registry import quantity_parameter

_PARAMETERS = frozenset(
    {
        "BTMParameterQuantity-147",
        "BTMParameterEnum-145",
        "BTMParameterBoolean-144",
        "BTMParameterQueryList-148",
        "BTMParameterArray-2025",
    }
)
_QUERIES = frozenset({"BTMIndividualQuery-138", "BTMIndividualSketchRegionQuery-140"})


def _node(value: dict[str, JsonValue]) -> None:
    if "nodeId" in value and (
        not isinstance(value["nodeId"], str) or not 1 <= len(value["nodeId"]) <= 256
    ):
        raise EditError("unsupported_target", 422)


def canonical_feature(raw: dict[str, JsonValue]) -> dict[str, JsonValue]:
    feature = deepcopy(raw)
    kind = feature.get("featureType")
    if (kind, feature.get("btType")) not in (
        ("extrude", "BTMFeature-134"),
        ("fillet", "BTMFeature-134"),
        ("newSketch", "BTMSketch-151"),
    ):
        return feature  # Unknown structure remains exact, grants no eligibility.
    _node(feature)
    feature.pop("nodeId", None)
    suppression = feature.get("suppressionState")
    if (
        isinstance(suppression, dict)
        and suppression.get("btType") == "BTMSuppressionState-1924"
    ):
        _node(suppression)
        if (
            not set(suppression) - {"btType", "nodeId", "suppressionConfigured"}
            and suppression.get("suppressionConfigured") is False
        ):
            suppression.pop("nodeId", None)
    if kind not in ("extrude", "fillet"):
        return feature  # Sketch internals are not modeled by the Modify adapter.
    parameters = feature.get("parameters")
    if not isinstance(parameters, list):
        return feature
    # Validate declared node slots even if the whole adapter shape is unsupported.
    # No traversal into queries/filters/JSON other than the explicit item envelope.
    for parameter in parameters:
        if (
            not isinstance(parameter, dict)
            or not isinstance(parameter.get("btType"), str)
            or parameter.get("btType") not in _PARAMETERS
        ):
            continue
        _node(parameter)
        queries = parameter.get("queries")
        if parameter.get("btType") == "BTMParameterQueryList-148" and isinstance(
            queries, list
        ):
            for query in queries:
                if (
                    isinstance(query, dict)
                    and isinstance(query.get("btType"), str)
                    and query.get("btType") in _QUERIES
                ):
                    _node(query)
    try:
        # Existing complete legacy/current-UI shape validators run before removal.
        quantity_parameter(
            raw, "SET_EXTRUDE_DEPTH" if kind == "extrude" else "SET_FILLET_RADIUS"
        )
    except EditError:
        return feature  # Unsupported parameter structures retain ALL raw fields.
    for parameter in parameters:
        assert isinstance(parameter, dict)
        parameter.pop("nodeId", None)
        queries = parameter.get("queries")
        if parameter.get("btType") == "BTMParameterQueryList-148" and isinstance(
            queries, list
        ):
            for query in queries:
                assert isinstance(query, dict)
                query.pop("nodeId", None)
    return feature


def canonical_inventory(raw: dict[str, JsonValue]) -> dict[str, JsonValue]:
    result = deepcopy(raw)
    features = result.get("features")
    if not isinstance(features, list) or any(not isinstance(f, dict) for f in features):
        raise EditError("unsupported_target", 422)
    result["features"] = [
        canonical_feature(cast(dict[str, JsonValue], f)) for f in features
    ]
    return result


def _profile(raw: dict[str, JsonValue]) -> bool:
    if raw.get("featureType") not in ("extrude", "fillet"):
        return False
    try:
        quantity_parameter(
            raw,
            "SET_EXTRUDE_DEPTH"
            if raw["featureType"] == "extrude"
            else "SET_FILLET_RADIUS",
        )
    except EditError:
        return False
    return True


def semantic_feature(raw: dict[str, JsonValue]) -> list[JsonValue]:
    # A validated profile cannot compare equal to an unsupported raw envelope
    # merely because the latter omitted every node field. This is a discriminator
    # in the comparison representation, never a field added to provider payloads.
    return [canonical_feature(raw), _profile(raw)]


def semantic_inventory(raw: dict[str, JsonValue]) -> dict[str, JsonValue]:
    inventory = canonical_inventory(raw)
    features = cast(list[dict[str, JsonValue]], raw["features"])
    return {
        "inventory": inventory,
        "parameter_profiles": [_profile(f) for f in features],
    }
