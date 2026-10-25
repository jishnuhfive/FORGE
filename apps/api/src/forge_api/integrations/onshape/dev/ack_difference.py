"""Development-only bounded schema-path labels; no raw CAD leaves this helper."""

import logging
from typing import Literal, cast, get_args

from pydantic import JsonValue

from forge_api.cad_edits.domain import EditError, fingerprint

from ..edit_registry import quantity_parameter
from ..semantic_inventory import semantic_feature
from ..standard_edit_shapes import UI_RULES
from ..standard_shape_contract import FailureReason, ShapeValidationError

AckDifference = Literal[
    "semantic_projection_rejected",
    "parameter_profile_changed",
    "returned_parameter_profile_unsupported",
    "expected_parameter_profile_unsupported",
    "feature_type_changed",
    "feature_identity_changed",
    "feature_name_changed",
    "feature_namespace_changed",
    "feature_suppression_changed",
    "feature_parent_suppression_changed",
    "feature_configured_suppression_changed",
    "feature_subfeatures_changed",
    "feature_return_mode_changed",
    "feature_field_presence_changed",
    "feature_unknown_fields_changed",
    "feature_node_invalid",
    "feature_node_bookkeeping_changed",
    "suppression_type_changed",
    "suppression_configured_changed",
    "suppression_shape_changed",
    "suppression_field_presence_changed",
    "suppression_unknown_fields_changed",
    "suppression_node_invalid",
    "suppression_node_bookkeeping_changed",
    "parameters_malformed",
    "parameter_count_changed",
    "parameter_order_or_identity_changed",
    "parameter_type_changed",
    "parameter_field_presence_changed",
    "parameter_unknown_fields_changed",
    "parameter_node_invalid",
    "parameter_node_bookkeeping_changed",
    "parameter_import_marker_changed",
    "parameter_name_metadata_changed",
    "parameter_value_string_changed",
    "parameter_library_relation_changed",
    "quantity_expression_changed",
    "quantity_cached_value_changed",
    "quantity_units_changed",
    "quantity_integer_flag_changed",
    "enum_name_changed",
    "enum_namespace_changed",
    "enum_value_changed",
    "boolean_value_changed",
    "unmodeled_parameter_value_changed",
    "array_items_changed",
    "query_filter_changed",
    "queries_malformed",
    "query_count_changed",
    "query_type_changed",
    "query_string_changed",
    "query_deterministic_ids_changed",
    "query_sketch_identity_changed",
    "query_inner_loop_mode_changed",
    "query_optional_representation_changed",
    "query_field_presence_changed",
    "query_unknown_fields_changed",
    "query_node_invalid",
    "query_node_bookkeeping_changed",
    "query_import_marker_changed",
    "diagnostic_structure_limit",
    "unclassified_semantic_difference",
]
ORDER: tuple[AckDifference, ...] = get_args(AckDifference)
SchemaReason = FailureReason | Literal["none", "unsupported_profile"]

_FEATURE: tuple[tuple[str, AckDifference], ...] = (
    ("btType", "feature_type_changed"),
    ("featureType", "feature_type_changed"),
    ("featureId", "feature_identity_changed"),
    ("name", "feature_name_changed"),
    ("namespace", "feature_namespace_changed"),
    ("suppressed", "feature_suppression_changed"),
    ("parentSuppressed", "feature_parent_suppression_changed"),
    ("suppressionConfigured", "feature_configured_suppression_changed"),
    ("subFeatures", "feature_subfeatures_changed"),
    ("returnAfterSubfeatures", "feature_return_mode_changed"),
    ("nodeId", "feature_node_bookkeeping_changed"),
)
_PARAMETER: tuple[tuple[str, AckDifference], ...] = (
    ("btType", "parameter_type_changed"),
    ("nodeId", "parameter_node_bookkeeping_changed"),
    ("importMicroversion", "parameter_import_marker_changed"),
    ("parameterName", "parameter_name_metadata_changed"),
    ("valueString", "parameter_value_string_changed"),
    ("libraryRelationType", "parameter_library_relation_changed"),
    ("expression", "quantity_expression_changed"),
    ("units", "quantity_units_changed"),
    ("isInteger", "quantity_integer_flag_changed"),
    ("enumName", "enum_name_changed"),
    ("namespace", "enum_namespace_changed"),
    ("items", "array_items_changed"),
    ("filter", "query_filter_changed"),
)
_QUERY: tuple[tuple[str, AckDifference], ...] = (
    ("btType", "query_type_changed"),
    ("nodeId", "query_node_bookkeeping_changed"),
    ("importMicroversion", "query_import_marker_changed"),
    ("queryString", "query_string_changed"),
    ("deterministicIds", "query_deterministic_ids_changed"),
    ("featureId", "query_sketch_identity_changed"),
    ("filterInnerLoops", "query_inner_loop_mode_changed"),
    *(
        (field, "query_optional_representation_changed")
        for field in (
            "query",
            "deterministicIdList",
            "persistentQuery",
            "queryStatement",
            "variableName",
        )
    ),
)
_SUPPRESSION: tuple[tuple[str, AckDifference], ...] = (
    ("btType", "suppression_type_changed"),
    ("suppressionConfigured", "suppression_configured_changed"),
    ("nodeId", "suppression_node_bookkeeping_changed"),
)
_MISSING = object()
_MAX_PARAMETERS = max(len(rules) for rules in UI_RULES.values())
_MAX_QUERIES = 2000  # Same per-list bound as the supported query validator.


def _equal(a: object, b: object) -> bool:
    if a is _MISSING or b is _MISSING:
        return a is b
    return fingerprint(a) == fingerprint(b)


def schema_reason(feature: dict[str, JsonValue]) -> SchemaReason:
    """Only existing closed validator reason, never parameter identity or text."""
    if feature.get("featureType") not in ("extrude", "fillet"):
        return "unsupported_profile"
    try:
        quantity_parameter(
            feature,
            "SET_EXTRUDE_DEPTH"
            if feature["featureType"] == "extrude"
            else "SET_FILLET_RADIUS",
        )
    except ShapeValidationError as error:
        return error.failure.reason
    except EditError:
        return "unsupported_profile"
    return "none"


def ack_differences(
    expected: dict[str, JsonValue], returned: dict[str, JsonValue]
) -> tuple[AckDifference, ...]:
    """Compare only declared schema slots. Unknown keys collapse, never emit.

    No recursive generic diff: filter/subfeature/items and unmodeled containers
    yield one fixed class. All output is deduplicated in literal declaration order.
    """
    found: set[AckDifference] = set()
    left, right = expected, returned
    try:
        expected_semantic, returned_semantic = (
            semantic_feature(expected),
            semantic_feature(returned),
        )
        if _equal(expected_semantic, returned_semantic):
            return ()
        if expected_semantic[1] != returned_semantic[1]:
            found.add("parameter_profile_changed")
        if expected_semantic[1] is False:
            found.add("expected_parameter_profile_unsupported")
        if returned_semantic[1] is False:
            found.add("returned_parameter_profile_unsupported")
        if isinstance(expected_semantic[0], dict) and isinstance(
            returned_semantic[0], dict
        ):
            left, right = expected_semantic[0], returned_semantic[0]
    except EditError:
        found.add("semantic_projection_rejected")

    def fields(
        a: dict[str, JsonValue],
        b: dict[str, JsonValue],
        table: tuple[tuple[str, AckDifference], ...],
        presence: AckDifference,
        unknown: AckDifference,
        invalid: AckDifference,
        additional: frozenset[str] = frozenset(),
    ) -> None:
        known = {field for field, _ in table} | additional
        if (a.keys() & known) != (b.keys() & known):
            found.add(presence)
        if any(
            not _equal(a.get(k, _MISSING), b.get(k, _MISSING))
            for k in (a.keys() | b.keys()) - known
        ):
            found.add(unknown)
        for field, category in table:
            if not _equal(a.get(field, _MISSING), b.get(field, _MISSING)):
                found.add(category)
        if any(
            "nodeId" in obj
            and (
                not isinstance(obj["nodeId"], str) or not 1 <= len(obj["nodeId"]) <= 256
            )
            for obj in (a, b)
        ):
            found.add(invalid)

    fields(
        left,
        right,
        _FEATURE,
        "feature_field_presence_changed",
        "feature_unknown_fields_changed",
        "feature_node_invalid",
        frozenset({"parameters", "suppressionState"}),
    )
    a_state, b_state = left.get("suppressionState"), right.get("suppressionState")
    if isinstance(a_state, dict) and isinstance(b_state, dict):
        fields(
            a_state,
            b_state,
            _SUPPRESSION,
            "suppression_field_presence_changed",
            "suppression_unknown_fields_changed",
            "suppression_node_invalid",
        )
    elif not _equal(
        left.get("suppressionState", _MISSING), right.get("suppressionState", _MISSING)
    ):
        found.add("suppression_shape_changed")
    a_params, b_params = left.get("parameters"), right.get("parameters")
    if not isinstance(a_params, list) or not isinstance(b_params, list):
        found.add("parameters_malformed")
    else:
        if len(a_params) != len(b_params):
            found.add("parameter_count_changed")
        a_ids = [
            p.get("parameterId") if isinstance(p, dict) else None for p in a_params
        ]
        b_ids = [
            p.get("parameterId") if isinstance(p, dict) else None for p in b_params
        ]
        if not _equal(a_ids, b_ids):
            found.add("parameter_order_or_identity_changed")
        if any(
            len({fingerprint(key) for key in identities}) != len(identities)
            for identities in (a_ids, b_ids)
        ):
            found.add("parameters_malformed")
        if max(len(a_params), len(b_params)) > _MAX_PARAMETERS:
            found.add("diagnostic_structure_limit")
            return tuple(category for category in ORDER if category in found)
        for parameter in a_params:
            if not isinstance(parameter, dict):
                found.add("parameters_malformed")
                continue
            matches = [
                p
                for p in b_params
                if isinstance(p, dict)
                and _equal(p.get("parameterId"), parameter.get("parameterId"))
            ]
            if len(matches) != 1:
                found.add("parameters_malformed")
                continue
            other = matches[0]
            assert isinstance(other, dict)
            fields(
                parameter,
                other,
                _PARAMETER,
                "parameter_field_presence_changed",
                "parameter_unknown_fields_changed",
                "parameter_node_invalid",
                frozenset({"parameterId", "value", "queries"}),
            )
            if not _equal(
                parameter.get("value", _MISSING), other.get("value", _MISSING)
            ):
                value_class: AckDifference = "unmodeled_parameter_value_changed"
                if parameter.get("btType") == "BTMParameterQuantity-147":
                    value_class = "quantity_cached_value_changed"
                elif parameter.get("btType") == "BTMParameterEnum-145":
                    value_class = "enum_value_changed"
                elif parameter.get("btType") == "BTMParameterBoolean-144":
                    value_class = "boolean_value_changed"
                found.add(value_class)
            queries, actual_queries = (
                parameter.get("queries", _MISSING),
                other.get("queries", _MISSING),
            )
            if queries is _MISSING and actual_queries is _MISSING:
                continue
            if not isinstance(queries, list) or not isinstance(actual_queries, list):
                found.add("queries_malformed")
                continue
            if len(queries) != len(actual_queries):
                found.add("query_count_changed")
            if max(len(queries), len(actual_queries)) > _MAX_QUERIES:
                found.add("diagnostic_structure_limit")
                continue
            for a_query, b_query in zip(queries, actual_queries, strict=False):
                if isinstance(a_query, dict) and isinstance(b_query, dict):
                    fields(
                        a_query,
                        b_query,
                        _QUERY,
                        "query_field_presence_changed",
                        "query_unknown_fields_changed",
                        "query_node_invalid",
                    )
                else:
                    found.add("queries_malformed")
    return tuple(category for category in ORDER if category in found) or (
        "diagnostic_structure_limit",
        "unclassified_semantic_difference",
    )


def query_id_context(
    expected: dict[str, JsonValue], returned: dict[str, JsonValue]
) -> str:
    """Closed single-query role/type/state labels, never selection equivalence.

    Full existing profile validation precedes inspection. Dormant roles cannot
    hold queries in these profiles; only entities is inspected, without recursion.
    A matching remaining envelope does NOT prove IDs are non-semantic: Onshape
    documents ID precedence over queryString for individual-query POSTs.
    """
    if any(schema_reason(feature) != "none" for feature in (expected, returned)):
        return "unvalidated_or_unsupported_location"
    category = (
        "extrude_entities"
        if expected.get("featureType") == returned.get("featureType") == "extrude"
        else "fillet_entities"
        if expected.get("featureType") == returned.get("featureType") == "fillet"
        else None
    )
    if category is None:
        return "unvalidated_or_unsupported_location"
    pair: list[dict[str, JsonValue]] = []
    filters: list[object] = []
    for raw in (expected, returned):
        projected = semantic_feature(raw)[0]
        if not isinstance(projected, dict):
            return "unvalidated_or_unsupported_location"
        parameters = projected.get("parameters")
        if not isinstance(parameters, list) or len(parameters) > _MAX_PARAMETERS:
            return "unvalidated_or_unsupported_location"
        entities = [
            p
            for p in parameters
            if isinstance(p, dict) and p.get("parameterId") == "entities"
        ]
        if len(entities) != 1 or not isinstance(entities[0], dict):
            return "unvalidated_or_unsupported_location"
        parameter = entities[0]
        queries = parameter.get("queries")
        if not isinstance(queries, list) or len(queries) != 1:
            return "query_list_not_single"
        query = queries[0]
        if not isinstance(query, dict):
            return "unvalidated_or_unsupported_location"
        pair.append(query)
        filters.append(parameter.get("filter", _MISSING))
    a, b = pair
    kind = (
        "individual_query"
        if a.get("btType") == b.get("btType") == "BTMIndividualQuery-138"
        else "sketch_region_query"
        if a.get("btType") == b.get("btType") == "BTMIndividualSketchRegionQuery-140"
        else "query_type_changed"
    )

    def ids_state(query: dict[str, JsonValue]) -> str:
        return (
            "absent"
            if "deterministicIds" not in query
            else "empty"
            if query["deterministicIds"] == []
            else "nonempty"
        )

    def string_state(query: dict[str, JsonValue]) -> str:
        return (
            "absent"
            if "queryString" not in query
            else "nonempty"
            if isinstance(query["queryString"], str) and query["queryString"].strip()
            else "blank"
        )

    ids_change = (
        "unchanged"
        if _equal(
            a.get("deterministicIds", _MISSING), b.get("deterministicIds", _MISSING)
        )
        else "presence"
        if ("deterministicIds" in a) != ("deterministicIds" in b)
        else "count"
        if len(cast(list[JsonValue], a.get("deterministicIds", [])))
        != len(cast(list[JsonValue], b.get("deterministicIds", [])))
        else "values_or_order"
    )
    remaining = _equal(
        {key: value for key, value in a.items() if key != "deterministicIds"},
        {key: value for key, value in b.items() if key != "deterministicIds"},
    )
    return (
        category
        + "."
        + kind
        + ".expected_ids_"
        + ids_state(a)
        + ".returned_ids_"
        + ids_state(b)
        + ".expected_string_"
        + string_state(a)
        + ".returned_string_"
        + string_state(b)
        + ".ids_change_"
        + ids_change
        + ".remaining_query_"
        + ("exact" if remaining else "changed")
        + ".filter_"
        + ("exact" if _equal(*filters) else "changed")
    )


def emit_ack_difference(
    development: bool, expected: dict[str, JsonValue], returned: dict[str, JsonValue]
) -> None:
    """Observability only. Never propagates classifier failures or provider text."""
    if not development:
        return
    try:
        categories = ",".join(ack_differences(expected, returned))
        returned_reason, expected_reason = (
            schema_reason(returned),
            schema_reason(expected),
        )
        if "query_deterministic_ids_changed" in categories.split(","):
            # Additional fixed warning before the original summary, development
            # only and only after an already-rejected acknowledgement.
            try:
                context = query_id_context(expected, returned)
            except Exception:
                context = "diagnostic_unavailable"
            logging.getLogger("forge.modify.verification").warning(
                "a2_ack_query_ids context=%s", context
            )
    except Exception:
        categories, returned_reason, expected_reason = (
            "diagnostic_unavailable",
            "unsupported_profile",
            "unsupported_profile",
        )
    logging.getLogger("forge.modify.verification").warning(
        "a2_ack_difference categories=%s returned_schema=%s expected_schema=%s",
        categories,
        returned_reason,
        expected_reason,
    )
