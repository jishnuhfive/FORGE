"""Pure depth-recovery comparison prerequisite; grants no closure authority.

Inputs must come from independently reviewed, bounded provider captures. This
module performs no I/O, accepts no credentials and cannot release a fence. A
successful comparison proves current-state agreement, never upstream settlement
or original-write causality. Only the private recovery reader consumes this check.
"""

import json
from dataclasses import dataclass
from typing import Literal, cast

from pydantic import JsonValue

from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    ModifyEvidence,
    project_modify_evidence,
    verify_operation,
)

from .depth_inventory_diagnostics import InventoryDifference, inventory_differences
from .domain import EditError, fingerprint
from .plans import ResolvedOperation, StoredPlan

ComparisonFailure = Literal[
    "serialization_mismatch",
    "library_mismatch",
    "parent_suppression_mismatch",
    "configured_suppression_mismatch",
    "inventory_mismatch",
    "configuration_mismatch",
    "revision_mismatch",
    "preview_mismatch",
    "unavailable",
]


@dataclass(frozen=True, repr=False)
class DepthRecoveryCapture:
    context: WorkspaceReference
    microversion: str
    features: JsonValue
    configuration: JsonValue
    bodies: JsonValue


def check_depth_recovery_state(
    saved: StoredPlan, historical: DepthRecoveryCapture, current: DepthRecoveryCapture
) -> None:
    """Require the exact approved baseline and exact single depth replacement.

    Historical evidence must be reacquired at the approved immutable microversion
    and projected through the existing complete provider evidence contract. A
    retained database record or a current measurement cannot reconstruct it.
    This deliberately returns no receipt, approval, capability or success state.
    """
    plan = saved.plan
    if (
        saved.result.state != "execution_uncertain"
        or saved.result.operations != ("execution_uncertain",)
        or len(plan.operations) != 1
        or plan.operations[0].operation.type != "SET_EXTRUDE_DEPTH"
        or plan.operations[0].target.feature_type != "extrude"
        or plan.baseline.context != plan.binding.context
        or historical.context != plan.binding.context
        or current.context != plan.binding.context
    ):
        raise EditError("recovery_required")
    try:
        before, after = (
            project_modify_evidence(
                c.context, c.microversion, c.features, c.configuration, c.bodies
            )
            for c in (historical, current)
        )
        if before.baseline != plan.baseline:
            raise EditError("recovery_required")
        verify_operation(before, after, plan.operations[0], after.baseline.microversion)
    except EditError, ValueError, TypeError:
        raise EditError("recovery_required") from None


def classify_depth_comparison(
    before: ModifyEvidence,
    after: ModifyEvidence,
    operation: ResolvedOperation,
    marker: str,
) -> ComparisonFailure | None:
    """Diagnostic only: mirror verify_operation for depth, never grant success.

    The reader calls this only after the unchanged authoritative check rejected.
    Evaluate every exact comparison independently; specific baseline differences
    precede inventory/configuration hashes when several predicates fail together.
    """
    if operation.operation.type != "SET_EXTRUDE_DEPTH":
        return "unavailable"
    b, a = before.baseline, after.baseline
    if a.context != b.context or a.microversion != marker or marker == b.microversion:
        return "revision_mismatch"
    try:
        inventory = before.inventory()
        features = cast(list[dict[str, JsonValue]], inventory["features"])
        expected, preview = change(features, operation.target, operation.operation)
        if preview != operation.preview:
            return "preview_mismatch"
        features[operation.target.position - 1] = expected
        inventory["sourceMicroversion"] = marker
        configuration = cast(
            dict[str, JsonValue], json.loads(before.configuration_json)
        )
        configuration["sourceMicroversion"] = marker
        checks: tuple[tuple[ComparisonFailure, bool], ...] = (
            ("serialization_mismatch", a.serialization == b.serialization),
            ("library_mismatch", a.library == b.library),
            (
                "parent_suppression_mismatch",
                a.parent_suppression_evidence == b.parent_suppression_evidence,
            ),
            (
                "configured_suppression_mismatch",
                a.configured_suppression_evidence == b.configured_suppression_evidence,
            ),
            (
                "inventory_mismatch",
                fingerprint(inventory) == fingerprint(after.inventory()),
            ),
            (
                "configuration_mismatch",
                fingerprint(configuration)
                == fingerprint(json.loads(after.configuration_json)),
            ),
        )
        return next((code for code, passed in checks if not passed), None)
    except EditError, ValueError, TypeError, KeyError, IndexError:
        return "unavailable"


def classify_depth_inventory(
    before: ModifyEvidence,
    after: ModifyEvidence,
    operation: ResolvedOperation,
    marker: str,
) -> tuple[InventoryDifference, ...]:
    """Explain only the already-rejected expected/current inventory fingerprint."""
    if operation.operation.type != "SET_EXTRUDE_DEPTH":
        return ()
    try:
        expected = before.inventory()
        features = cast(list[dict[str, JsonValue]], expected["features"])
        replacement, _ = change(features, operation.target, operation.operation)
        features[operation.target.position - 1] = replacement
        expected["sourceMicroversion"] = marker
        actual = after.inventory()
        if fingerprint(expected) == fingerprint(actual):
            return ()
        return inventory_differences(expected, actual, operation.target.feature_id) or (
            "unknown_provider_metadata_changed",
        )
    except EditError, ValueError, TypeError, KeyError, IndexError, RecursionError:
        return ("unknown_provider_metadata_changed",)
