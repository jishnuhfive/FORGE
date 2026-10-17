"""Strict write-critical projection with fixed internal rejection diagnostics.

No eligibility defaults or public provider details. Raw evidence stays local.
"""

from typing import cast

from pydantic import JsonValue, ValidationError

from forge_api.cad_edits.domain import Baseline, FeatureStateEvidence, fingerprint

from .contracts import WorkspaceReference
from .eligibility import MISSING, Expected, FieldName, Reason, require
from .models import Bodies


def project_write_evidence(
    context: WorkspaceReference,
    microversion: str,
    feature_data: JsonValue,
    configuration: JsonValue,
    body_data: JsonValue,
    *,
    after: bool = False,
) -> Baseline:
    def obj(
        value: object, reason: Reason, field: FieldName, position: int | None = None
    ) -> dict[str, JsonValue]:
        require(isinstance(value, dict), reason, field, "object", value, position)
        return cast(dict[str, JsonValue], value)

    data = obj(feature_data, Reason.INVENTORY_SHAPE, "inventory")
    config = obj(configuration, Reason.CONFIGURATION_SHAPE, "configuration")
    for container, field, expected, reason, category in (
        (data, "isComplete", True, Reason.INCOMPLETE, "true"),
        (data, "microversionSkew", False, Reason.SKEW, "false"),
        (
            data,
            "sourceMicroversion",
            microversion,
            Reason.REVISION,
            "matching_revision",
        ),
        (config, "configurationParameters", [], Reason.CONFIGURED, "empty_array"),
        (config, "currentConfiguration", [], Reason.CONFIGURED, "empty_array"),
        (
            config,
            "sourceMicroversion",
            microversion,
            Reason.REVISION,
            "matching_revision",
        ),
        (config, "microversionSkew", False, Reason.SKEW, "false"),
    ):
        actual = container.get(field, MISSING)
        matches = (
            actual is expected if isinstance(expected, bool) else actual == expected
        )
        require(
            matches, reason, cast(FieldName, field), cast(Expected, category), actual
        )
    items = data.get("features", MISSING)
    require(
        isinstance(items, list) and 3 <= len(items) <= 20,
        Reason.COUNT,
        "features",
        "three_to_twenty",
        items,
    )
    # Request rollbackBarIndex=-1 asks for the end; the response can report
    # its concrete position. The OpenAPI also explicitly documents -1 as an
    # end sentinel. Only those two end representations are safe for a complete
    # inventory. Strict int excludes bool and numerically equal floats.
    rollback = data.get("rollbackIndex", MISSING)
    require(
        type(rollback) is int and rollback in (-1, len(cast(list[JsonValue], items))),
        Reason.ROLLBACK,
        "rollbackIndex",
        "end_of_list",
        rollback,
    )
    features = [
        obj(f, Reason.FEATURE_SHAPE, "feature", i + 1)
        for i, f in enumerate(cast(list[JsonValue], items))
    ]
    ids = [f.get("featureId") for f in features]
    for position, identity in enumerate(ids, 1):
        require(
            isinstance(identity, str) and 1 <= len(identity) <= 256,
            Reason.ID,
            "featureId",
            "bounded_identity",
            identity,
            position,
        )
    require(
        len(set(cast(list[str], ids))) == len(ids),
        Reason.DUPLICATE,
        "featureId",
        "unique_identity",
        ids,
    )
    states = obj(data.get("featureStates", MISSING), Reason.STATES, "featureStates")
    # An exactly empty object is an explicit unavailable-evidence mode for this
    # sole operation. It supplies no synthetic OK status or inactive Boolean.
    # Any nonempty map must cover the inventory exactly, with no unexplained keys.
    if len(states) == 0:
        state_evidence = FeatureStateEvidence.UNAVAILABLE_EMPTY
    else:
        require(
            set(states) == set(cast(list[str], ids)),
            Reason.STATE_COVERAGE,
            "featureStates",
            "exact_feature_coverage",
            states,
        )
        state_evidence = FeatureStateEvidence.COMPLETE
    definitions: list[dict[str, JsonValue]] = []
    for index, feature in enumerate(features):
        target, position = index == len(features) - 1, index + 1
        kind = feature.get("featureType")
        suppression = obj(
            feature.get("suppressionState", MISSING),
            Reason.SUPPRESSION,
            "suppressionState",
            position,
        )
        require(
            kind in ("newSketch", "extrude", "fillet"),
            Reason.TYPE,
            "featureType",
            "standard_feature",
            kind,
            position,
        )
        require(
            feature.get("btType")
            == ("BTMSketch-151" if kind == "newSketch" else "BTMFeature-134"),
            Reason.BT_TYPE,
            "btType",
            "standard_bt_type",
            feature.get("btType", MISSING),
            position,
        )
        require(
            feature.get("namespace") == "",
            Reason.NAMESPACE,
            "namespace",
            "empty_namespace",
            feature.get("namespace", MISSING),
            position,
        )
        require(
            feature.get("subFeatures") == [],
            Reason.SUBFEATURES,
            "subFeatures",
            "empty_array",
            feature.get("subFeatures", MISSING),
            position,
        )
        for field, reason in (
            ("parentSuppressed", Reason.PARENT),
            ("suppressionConfigured", Reason.CONFIGURED_SUPPRESSION),
            ("returnAfterSubfeatures", Reason.RETURN),
        ):
            require(
                feature.get(field) is False,
                reason,
                cast(FieldName, field),
                "false",
                feature.get(field, MISSING),
                position,
            )
        require(
            suppression.get("btType") == "BTMSuppressionState-1924",
            Reason.SUPPRESSION,
            "suppressionState",
            "ordinary_suppression",
            suppression.get("btType", MISSING),
            position,
        )
        require(
            suppression.get("suppressionConfigured") is False,
            Reason.CONFIGURED_SUPPRESSION,
            "suppressionConfigured",
            "false",
            suppression.get("suppressionConfigured", MISSING),
            position,
        )
        require(
            not (set(suppression) - {"btType", "nodeId", "suppressionConfigured"}),
            Reason.SUPPRESSION_FIELDS,
            "suppressionState",
            "known_fields",
            suppression,
            position,
        )
        require(
            feature.get("suppressed") is (after and target),
            Reason.SUPPRESSED,
            "suppressed",
            "true" if after and target else "false",
            feature.get("suppressed", MISSING),
            position,
        )
        if state_evidence is FeatureStateEvidence.COMPLETE:
            state = obj(
                states[cast(str, ids[index])], Reason.STATE, "featureState", position
            )
            require(
                state.get("featureStatus") == "OK",
                Reason.STATUS,
                "featureStatus",
                "OK",
                state.get("featureStatus", MISSING),
                position,
            )
            require(
                state.get("inactive") is (after and target),
                Reason.INACTIVE,
                "inactive",
                "true" if after and target else "false",
                state.get("inactive", MISSING),
                position,
            )
        require(
            not target or kind == "fillet",
            Reason.TERMINAL,
            "featureType",
            "fillet",
            kind,
            position,
        )
        # No broad ignore-list: every captured definition field remains bound.
        definition = dict(feature)
        if target:
            definition.pop("suppressed")
        definitions.append(definition)
    require(
        any(f.get("featureType") == "newSketch" for f in features),
        Reason.SKETCH,
        "features",
        "sketch",
        features,
    )
    require(
        any(f.get("featureType") == "extrude" for f in features),
        Reason.EXTRUDE,
        "features",
        "extrude",
        features,
    )
    try:
        bodies = Bodies.model_validate(body_data)
    except ValidationError:
        require(False, Reason.BODY_SCHEMA, "bodies", "object", body_data)
        raise AssertionError("unreachable") from None
    body_raw = body_data if isinstance(body_data, dict) else {}
    micro_raw = body_raw.get("microversionId", MISSING)
    micro_fields = micro_raw if isinstance(micro_raw, dict) else {}
    require(
        len(bodies.bodies) == 1,
        Reason.BODY_COUNT,
        "bodies",
        "one",
        body_raw.get("bodies", MISSING),
    )
    require(
        bodies.bodies[0].type == "SOLID",
        Reason.BODY_TYPE,
        "bodyType",
        "SOLID",
        bodies.bodies[0].type,
    )
    require(
        bodies.errorEnum == "NO_ERROR",
        Reason.BODY_ERROR,
        "errorEnum",
        "NO_ERROR",
        body_raw.get("errorEnum", MISSING),
    )
    require(
        bodies.microversionId is not None,
        Reason.BODY_REVISION_MISSING,
        "microversionId",
        "object",
        micro_raw,
    )
    assert bodies.microversionId is not None
    require(
        bodies.microversionId.theId == microversion,
        Reason.BODY_REVISION,
        "microversionId",
        "matching_revision",
        micro_fields.get("theId", MISSING),
    )
    require(
        bodies.microversionId.ambiguous is False,
        Reason.BODY_AMBIGUOUS,
        "ambiguous",
        "false",
        micro_fields.get("ambiguous", MISSING),
    )
    require(
        bodies.microversionId.deleted is False,
        Reason.BODY_DELETED,
        "deleted",
        "false",
        micro_fields.get("deleted", MISSING),
    )
    serialization, library = (
        data.get("serializationVersion", MISSING),
        data.get("libraryVersion", MISSING),
    )
    require(
        isinstance(serialization, str) and 1 <= len(serialization) <= 64,
        Reason.SERIALIZATION,
        "serializationVersion",
        "bounded_string",
        serialization,
    )
    require(
        type(library) is int and 0 <= library <= 2147483647,
        Reason.LIBRARY,
        "libraryVersion",
        "nonnegative_int32",
        library,
    )
    label = features[-1].get("name")
    if (
        not isinstance(label, str)
        or not label.strip()
        or len(label.encode()) > 256
        or any(ord(c) < 32 or ord(c) == 127 for c in label)
    ):
        label = "Terminal Fillet"
    return Baseline(
        context=context,
        microversion=microversion,
        feature_id=cast(str, ids[-1]),
        label=label,
        position=len(features),
        definitions=fingerprint(definitions),
        fingerprint=fingerprint([feature_data, configuration]),
        serialization=cast(str, serialization),
        library=cast(int, library),
        suppressed=after,
        feature_state_evidence=state_evidence,
    )
