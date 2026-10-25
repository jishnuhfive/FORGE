"""Provider-independent sequential creation protocol; no approval or I/O authority.

The coordinator owns authorization, durable claims/journals and the provider. This
kernel cannot be invoked as a planner tool and cannot fabricate verified IDs.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from forge_api.cad_edits.domain import EditError

from .evidence import CreationEvidence, VerifyRejected, verify_added
from .models import CreationPlan, CreationStep


class CreationProvider(Protocol):
    def capture(self) -> CreationEvidence: ...
    def preflight(
        self,
        step: CreationStep,
        verified: dict[str, dict[str, Any]],
        before: CreationEvidence,
    ) -> object: ...
    def dispatch(self, payload: object) -> tuple[str, dict[str, Any]]: ...


@dataclass(frozen=True)
class ExecutionResult:
    state: str
    steps: tuple[str, ...]


def execute(
    plan: CreationPlan,
    baseline: CreationEvidence,
    provider: CreationProvider,
    journal: Callable[[tuple[str, ...], bool], None],
) -> ExecutionResult:
    """Journal BEFORE dispatch; exactly one call, no rollback/retry, never skip reread.

    This is only a protocol kernel. It MUST NOT be wired to routes before a durable
    one-use approval/fence coordinator and a complete grounded adapter exist.
    """
    baseline.require_empty()
    states = ["pending"] * len(plan.steps)
    verified: dict[str, dict[str, Any]] = {}
    previous = baseline
    dispatched = False
    for i, step in enumerate(plan.steps):
        stage = "step_other"
        try:
            stage = "step_read"
            current = provider.capture()
            if current.digest != previous.digest:
                raise VerifyRejected("step_baseline", "model_changed")
            if any(ref not in verified for ref in step.depends_on):
                stage = "step_dependency"
                raise EditError("unsupported_target")
            stage = "step_preflight"
            payload = provider.preflight(step, verified, current)
            stage = "step_other"
            states[i] = "executing"
            journal(tuple(states), True)
            dispatched = True
            marker, ack = provider.dispatch(payload)
            states[i] = "verifying"
            journal(tuple(states), True)
            after = provider.capture()
            verify_added(current, after, ack, marker)
            if ack["featureId"] in {f["featureId"] for f in verified.values()}:
                raise VerifyRejected("ver_duplicate")
            verified[step.id] = ack
            previous = after
            states[i] = "verified_success"
            journal(tuple(states), True)
        except Exception as error:
            note = getattr(provider, "note_failure", None)
            if note is not None:
                label = getattr(error, "check", None) or (
                    "step_head_moved"
                    if getattr(error, "code", "") == "model_changed"
                    else stage
                )
                note(label, getattr(error, "names", ()))
            states[i] = "execution_uncertain" if dispatched else "rejected"
            states[i + 1 :] = ["skipped"] * (len(states) - i - 1)
            result = ExecutionResult(
                "execution_uncertain" if dispatched else "rejected", tuple(states)
            )
            journal(result.steps, dispatched)
            return result
    return ExecutionResult("verified_success", tuple(states))
