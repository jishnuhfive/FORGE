"""Additional write-critical projection over existing bounded Onshape JSON.

No parallel inspector/checker. Existing provider models validate body evidence;
this projection retains only identity, revision and cryptographic comparisons.
"""

from typing import cast

from pydantic import JsonValue

from forge_api.cad_edits.domain import Baseline, EditError, fingerprint

from .contracts import WorkspaceReference
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
    def obj(value: JsonValue) -> dict[str, JsonValue]:
        if not isinstance(value, dict):
            raise EditError("unsupported_target", 422)
        return value

    data, config = obj(feature_data), obj(configuration)
    if (
        data.get("isComplete") is not True
        or data.get("microversionSkew") is not False
        or data.get("sourceMicroversion") != microversion
        or data.get("rollbackIndex") != -1
        or config.get("configurationParameters") != []
        or config.get("currentConfiguration") != []
        or config.get("sourceMicroversion") != microversion
        or config.get("microversionSkew") is not False
    ):
        raise EditError("unsupported_target", 422)
    items = data.get("features")
    if not isinstance(items, list) or not 3 <= len(items) <= 20:
        raise EditError("unsupported_target", 422)
    features = [obj(f) for f in items]
    ids = [f.get("featureId") for f in features]
    if any(not isinstance(i, str) or not 1 <= len(i) <= 256 for i in ids):
        raise EditError("unsupported_target", 422)
    if len(set(cast(list[str], ids))) != len(ids):
        raise EditError("ambiguous_target")
    states = obj(data.get("featureStates"))
    definitions: list[dict[str, JsonValue]] = []
    for index, feature in enumerate(features):
        target = index == len(features) - 1
        kind = feature.get("featureType")
        state = obj(states.get(cast(str, ids[index])))
        suppression = obj(feature.get("suppressionState"))
        if (
            kind not in ("newSketch", "extrude", "fillet")
            or feature.get("btType")
            != ("BTMSketch-151" if kind == "newSketch" else "BTMFeature-134")
            or feature.get("namespace") != ""
            or feature.get("subFeatures") != []
            or feature.get("parentSuppressed") is not False
            or feature.get("suppressionConfigured") is not False
            or feature.get("returnAfterSubfeatures") is not False
            or suppression.get("btType") != "BTMSuppressionState-1924"
            or suppression.get("suppressionConfigured") is not False
            or set(suppression) - {"btType", "nodeId", "suppressionConfigured"}
            or feature.get("suppressed") is not (after and target)
            or state.get("featureStatus") != "OK"
            or state.get("inactive") is not (after and target)
            or (target and kind != "fillet")
        ):
            raise EditError("unsupported_target", 422)
        # Preserve ALL definition fields, including queries/parameters/unknown
        # bookkeeping. Only the target's explicit suppression flag is excluded.
        definition = dict(feature)
        if target:
            definition.pop("suppressed")
        definitions.append(definition)
    if not any(f.get("featureType") == "newSketch" for f in features) or not any(
        f.get("featureType") == "extrude" for f in features
    ):
        raise EditError("unsupported_target", 422)
    bodies = Bodies.model_validate(body_data)
    if (
        len(bodies.bodies) != 1
        or bodies.bodies[0].type != "SOLID"
        or bodies.errorEnum != "NO_ERROR"
        or bodies.microversionId is None
        or bodies.microversionId.theId != microversion
        or bodies.microversionId.ambiguous is not False
        or bodies.microversionId.deleted is not False
    ):
        raise EditError("unsupported_target", 422)
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
        serialization=cast(str, data.get("serializationVersion")),
        library=cast(int, data.get("libraryVersion")),
        suppressed=after,
    )
