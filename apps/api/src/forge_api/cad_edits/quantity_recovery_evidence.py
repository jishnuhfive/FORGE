"""Pure depth-recovery comparison prerequisite; grants no closure authority.

Inputs must come from independently reviewed, bounded provider captures. This
module performs no I/O, accepts no credentials and cannot release a fence. A
successful comparison proves current-state agreement, never upstream settlement
or original-write causality. No recovery entry point consumes this prerequisite.
"""

from dataclasses import dataclass

from pydantic import JsonValue

from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)

from .domain import EditError
from .plans import StoredPlan


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
