"""Private development diagnostics over captured JSON; never verification authority."""

from itertools import zip_longest
from typing import Literal, get_args

from pydantic import JsonValue

from .domain import fingerprint

InventoryDifference = Literal[
    "feature_count_changed",
    "feature_order_or_identity_changed",
    "non_target_feature_changed",
    "target_name_changed",
    "target_suppression_changed",
    "target_definition_metadata_changed",
    "target_parameter_count_changed",
    "target_parameter_order_changed",
    "target_parameter_type_or_shape_changed",
    "target_depth_expression_unexpected",
    "target_depth_parameter_metadata_changed",
    "other_target_parameter_metadata_changed",
    "feature_states_changed",
    "source_revision_metadata_changed",
    "unknown_provider_metadata_changed",
]
# Literal order is the public diagnostic order, independent of provider ordering.
ORDER: tuple[InventoryDifference, ...] = get_args(InventoryDifference)
_FEATURE = frozenset(
    {
        "btType",
        "featureId",
        "featureType",
        "name",
        "namespace",
        "parameters",
        "subFeatures",
        "suppressed",
        "parentSuppressed",
        "suppressionConfigured",
        "suppressionState",
        "returnAfterSubfeatures",
        "nodeId",
    }
)
_PARAMETER = frozenset(
    {
        "btType",
        "parameterId",
        "nodeId",
        "expression",
        "isInteger",
        "value",
        "units",
        "enumName",
        "queries",
        "items",
        "isQuery",
        "hasUserCode",
        "importMicroversion",
        "parameterName",
        "valueString",
        "libraryRelationType",
    }
)
# Only names in this closed diagnostic vocabulary are inspected recursively.
# Unknown nested keys/changes also collapse to the generic category.
_NESTED = (
    _FEATURE
    | _PARAMETER
    | frozenset(
        {
            "queryString",
            "filter",
            "featureStatus",
            "inactive",
            "geometryIds",
        }
    )
)
_MISSING = object()


def _equal(a: object, b: object) -> bool:
    if a is _MISSING or b is _MISSING:
        return a is b
    # Use the verifier's type-sensitive equality, including bool vs number.
    return fingerprint(a) == fingerprint(b)


def _known_changed(a: object, b: object) -> bool:
    """Classify known structure only; unknown paths receive their own label.

    This never rewrites evidence or participates in the authority comparison.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return any(
            _known_changed(a.get(k, _MISSING), b.get(k, _MISSING))
            for k in (a.keys() | b.keys()) & _NESTED
        )
    if isinstance(a, list) and isinstance(b, list):
        return len(a) != len(b) or any(
            _known_changed(x, y) for x, y in zip(a, b, strict=False)
        )
    return not _equal(a, b)


def inventory_differences(
    expected: dict[str, JsonValue],
    actual: dict[str, JsonValue],
    target_id: str,
) -> tuple[InventoryDifference, ...]:
    """Return only fixed labels, never values, keys, indexes or identifiers.

    Inventories are request-local, bounded, already projected evidence. This
    function has no I/O and must only explain an already rejected fingerprint.
    """
    found: set[InventoryDifference] = set()

    def unknown(
        a: dict[str, JsonValue],
        b: dict[str, JsonValue],
        known: frozenset[str],
        skip: frozenset[str] = frozenset(),
    ) -> None:
        for key in (a.keys() | b.keys()) - known:
            if not _equal(a.get(key, _MISSING), b.get(key, _MISSING)):
                found.add("unknown_provider_metadata_changed")
        for key in ((a.keys() | b.keys()) & known) - skip:
            nested(a.get(key), b.get(key))

    def nested(a: JsonValue, b: JsonValue) -> None:
        if isinstance(a, dict) or isinstance(b, dict):
            unknown(
                a if isinstance(a, dict) else {},
                b if isinstance(b, dict) else {},
                _NESTED,
            )
        elif isinstance(a, list) or isinstance(b, list):
            for left, right in zip_longest(
                a if isinstance(a, list) else [], b if isinstance(b, list) else []
            ):
                nested(left, right)

    def parameters(left: JsonValue, right: JsonValue) -> None:
        if not isinstance(left, list) or not isinstance(right, list):
            found.add("target_parameter_type_or_shape_changed")
            return
        if len(left) != len(right):
            found.add("target_parameter_count_changed")
        a_ids = [p.get("parameterId") if isinstance(p, dict) else None for p in left]
        b_ids = [p.get("parameterId") if isinstance(p, dict) else None for p in right]
        if not _equal(a_ids, b_ids):
            if sorted(map(fingerprint, a_ids)) == sorted(map(fingerprint, b_ids)):
                found.add("target_parameter_order_changed")
            else:
                found.add("target_parameter_type_or_shape_changed")
        for added in right:
            if isinstance(added, dict) and not any(
                _equal(added.get("parameterId"), key) for key in a_ids
            ):
                unknown({}, added, _PARAMETER)
        for param in left:
            if not isinstance(param, dict):
                found.add("target_parameter_type_or_shape_changed")
                continue
            matches = [
                p
                for p in right
                if isinstance(p, dict)
                and _equal(p.get("parameterId"), param.get("parameterId"))
            ]
            if len(matches) != 1:
                unknown(param, {}, _PARAMETER)
                found.add("target_parameter_type_or_shape_changed")
                continue
            other = matches[0]
            assert isinstance(other, dict)
            unknown(param, other, _PARAMETER)
            shared = (param.keys() & other.keys()) & _PARAMETER
            if (
                not _equal(param.get("btType"), other.get("btType"))
                or (param.keys() & _PARAMETER) != (other.keys() & _PARAMETER)
                or any(type(param[k]) is not type(other[k]) for k in shared)
            ):
                found.add("target_parameter_type_or_shape_changed")
            depth = param.get("parameterId") == "depth"
            if depth and not _equal(
                param.get("expression", _MISSING), other.get("expression", _MISSING)
            ):
                found.add("target_depth_expression_unexpected")
            fields = (
                _PARAMETER
                - {"parameterId", "btType"}
                - ({"expression"} if depth else set())
            )
            if any(
                _known_changed(param.get(k, _MISSING), other.get(k, _MISSING))
                for k in fields
            ):
                found.add(
                    "target_depth_parameter_metadata_changed"
                    if depth
                    else "other_target_parameter_metadata_changed"
                )

    top = frozenset({"features", "featureStates", "sourceMicroversion"})
    # Other top-level changes have no more specific closed category here.
    for key in (expected.keys() | actual.keys()) - top:
        if not _equal(expected.get(key, _MISSING), actual.get(key, _MISSING)):
            found.add("unknown_provider_metadata_changed")
    comparisons: tuple[tuple[str, InventoryDifference], ...] = (
        ("featureStates", "feature_states_changed"),
        ("sourceMicroversion", "source_revision_metadata_changed"),
    )
    for key, category in comparisons:
        if not _equal(expected.get(key, _MISSING), actual.get(key, _MISSING)):
            found.add(category)
    left, right = expected.get("features"), actual.get("features")
    if not isinstance(left, list) or not isinstance(right, list):
        return ("unknown_provider_metadata_changed",)
    # State dictionaries are keyed by private feature identity; inspect only
    # their fixed semantic fields, never treating those identities as log keys.
    expected_states, actual_states = (
        expected.get("featureStates"),
        actual.get("featureStates"),
    )
    if isinstance(expected_states, dict) and isinstance(actual_states, dict):
        for identity in expected_states.keys() | actual_states.keys():
            a_state, b_state = (
                expected_states.get(identity),
                actual_states.get(identity),
            )
            if isinstance(a_state, dict) or isinstance(b_state, dict):
                unknown(
                    a_state if isinstance(a_state, dict) else {},
                    b_state if isinstance(b_state, dict) else {},
                    frozenset({"featureStatus", "inactive"}),
                )

    if len(left) != len(right):
        found.add("feature_count_changed")

    def identities(items: list[JsonValue]) -> list[JsonValue]:
        return [
            item.get("featureId") if isinstance(item, dict) else None for item in items
        ]

    if not _equal(identities(left), identities(right)):
        found.add("feature_order_or_identity_changed")
    for added in right:
        if isinstance(added, dict) and not any(
            _equal(added.get("featureId"), key) for key in identities(left)
        ):
            unknown({}, added, _FEATURE)
    # Align by identity to avoid interpreting a reorder as a definition change.
    for feature in left:
        if not isinstance(feature, dict):
            found.add("unknown_provider_metadata_changed")
            continue
        matches = [
            f
            for f in right
            if isinstance(f, dict)
            and _equal(f.get("featureId"), feature.get("featureId"))
        ]
        if len(matches) != 1:
            unknown(feature, {}, _FEATURE)
            continue
        other = matches[0]
        assert isinstance(other, dict)
        unknown(
            feature,
            other,
            _FEATURE,
            frozenset({"parameters"})
            if feature.get("featureId") == target_id
            else frozenset(),
        )
        if feature.get("featureId") != target_id:
            if _known_changed(feature, other):
                found.add("non_target_feature_changed")
            continue
        comparisons = (
            ("name", "target_name_changed"),
            ("suppressed", "target_suppression_changed"),
        )
        for key, category in comparisons:
            if _known_changed(feature.get(key, _MISSING), other.get(key, _MISSING)):
                found.add(category)
        for key in _FEATURE - {"name", "suppressed", "parameters", "featureId"}:
            if _known_changed(feature.get(key, _MISSING), other.get(key, _MISSING)):
                found.add("target_definition_metadata_changed")
        parameters(feature.get("parameters"), other.get("parameters"))
    return tuple(category for category in ORDER if category in found)
