"""Request-local complete evidence, reusing Phase 9's unchanged hard predicates."""

import json
from dataclasses import dataclass
from typing import cast

from pydantic import JsonValue

from forge_api.cad_edits.domain import Baseline, EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation

from .contracts import WorkspaceReference
from .edit_registry import change
from .write_evidence import project_write_evidence


@dataclass(frozen=True)
class ModifyEvidence:
    baseline: Baseline
    inventory_json: str
    configuration_json: str

    def inventory(self) -> dict[str, JsonValue]:
        return cast(dict[str, JsonValue], json.loads(self.inventory_json))

    def features(self) -> list[dict[str, JsonValue]]:
        return cast(list[dict[str, JsonValue]], self.inventory()["features"])


def project_modify_evidence(
    context: WorkspaceReference,
    microversion: str,
    feature_data: JsonValue,
    configuration: JsonValue,
    body_data: JsonValue,
) -> ModifyEvidence:
    # Only the last Fillet may be suppressed in A1. This uses the *same* evidence
    # policy for each supported state; missing/unknown never becomes false.
    if not isinstance(feature_data, dict):
        raise EditError("unsupported_target", 422)
    features = feature_data.get("features")
    if (
        not isinstance(features, list)
        or not features
        or not isinstance(features[-1], dict)
    ):
        raise EditError("unsupported_target", 422)
    suppressed = features[-1].get("suppressed")
    if type(suppressed) is not bool:
        raise EditError("unsupported_target", 422)
    baseline = project_write_evidence(
        context,
        microversion,
        feature_data,
        configuration,
        body_data,
        after=suppressed,
        pinned_body_microversion=microversion,
    )
    return ModifyEvidence(
        baseline=baseline,
        inventory_json=json.dumps(feature_data, allow_nan=False),
        configuration_json=json.dumps(configuration, allow_nan=False),
    )


def verify_operation(
    before: ModifyEvidence,
    after: ModifyEvidence,
    operation: ResolvedOperation,
    marker: str,
) -> None:
    b, a = before.baseline, after.baseline
    if a.context != b.context or a.microversion != marker or marker == b.microversion:
        raise EditError("verification_failed")
    inventory = before.inventory()
    features = cast(list[dict[str, JsonValue]], inventory["features"])
    expected, preview = change(features, operation.target, operation.operation)
    if preview != operation.preview:
        raise EditError("verification_failed")
    features[operation.target.position - 1] = expected
    inventory["sourceMicroversion"] = marker
    if operation.operation.type in ("SET_SUPPRESSED", "SET_UNSUPPRESSED"):
        states = cast(dict[str, JsonValue], inventory["featureStates"])
        if states:
            state = cast(dict[str, JsonValue], states[operation.target.feature_id])
            state["inactive"] = expected["suppressed"]
    configuration = cast(dict[str, JsonValue], json.loads(before.configuration_json))
    configuration["sourceMicroversion"] = marker
    # Type-sensitive hashes preserve ordering, every raw definition/metadata field,
    # identity, parameter ordering, state coverage and independent configuration.
    # No geometry equivalence is inferred from the independently re-proved body.
    if (
        fingerprint(inventory) != fingerprint(after.inventory())
        or fingerprint(configuration)
        != fingerprint(json.loads(after.configuration_json))
        or a.serialization != b.serialization
        or a.library != b.library
        or a.parent_suppression_evidence != b.parent_suppression_evidence
        or a.configured_suppression_evidence != b.configured_suppression_evidence
    ):
        raise EditError("verification_failed")
