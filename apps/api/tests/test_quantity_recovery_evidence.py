"""Offline prerequisite comparisons never invoke recovery or provider transport."""

from copy import deepcopy

import pytest
from conftest import Harness
from test_cad_read import REF
from test_modify_plan import PlanProvider, prepare
from test_safe_edit import M0, bodies, config, running

from forge_api.cad_edits import plan_storage
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import PlanResult
from forge_api.cad_edits.quantity_recovery_evidence import (
    DepthRecoveryCapture,
    check_depth_recovery_state,
)
from forge_api.db.models import WriteRecord
from forge_api.integrations.onshape.edit_registry import change


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "depth",
        "unrelated",
        "metadata",
        "order",
        "configuration",
        "revision",
        "historical",
        "body",
        "missing",
        "state",
        "multiple",
        "fillet",
    ],
)
def test_exact_depth_prerequisite(harness: Harness, mutation: str) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row is not None
            saved = plan_storage.load(row)
        saved = saved.model_copy(
            update={
                "result": PlanResult(
                    state="execution_uncertain", operations=("execution_uncertain",)
                )
            }
        )
        before = deepcopy(provider.data)
        after = deepcopy(before)
        operation = saved.plan.operations[0]
        updated, _ = change(after["features"], operation.target, operation.operation)
        after["features"][1] = updated
        marker = "e" * 24
        after["sourceMicroversion"] = marker
        configuration = config(marker)
        body = bodies(marker, explicit_flags=False)
        if mutation == "depth":
            after["features"][1]["parameters"][-1]["expression"] = "31 mm"
        elif mutation == "unrelated":
            after["features"][-1]["name"] = "Other"
        elif mutation == "metadata":
            updated["unexpected"] = True
        elif mutation == "order":
            after["features"].reverse()
        elif mutation == "configuration":
            configuration["unexpected"] = True
        elif mutation == "revision":
            marker = M0
        elif mutation == "historical":
            before["features"][1]["name"] = "Other"
        elif mutation == "body":
            body = {}
        elif mutation == "missing":
            after["features"] = []
        elif mutation == "state":
            saved = saved.model_copy(
                update={"result": PlanResult(state="claimed", operations=("pending",))}
            )
        elif mutation == "multiple":
            saved = saved.model_copy(
                update={
                    "plan": saved.plan.model_copy(
                        update={"operations": (operation, operation)}
                    )
                }
            )
        elif mutation == "fillet":
            saved = saved.model_copy(
                update={
                    "plan": saved.plan.model_copy(
                        update={
                            "operations": (
                                operation.model_copy(
                                    update={
                                        "target": operation.target.model_copy(
                                            update={"feature_type": "fillet"}
                                        )
                                    }
                                ),
                            )
                        }
                    )
                }
            )
        historical = DepthRecoveryCapture(
            REF, M0, before, config(), bodies(explicit_flags=False)
        )
        current = DepthRecoveryCapture(REF, marker, after, configuration, body)
        if mutation == "none":
            check_depth_recovery_state(saved, historical, current)
        else:
            with pytest.raises(EditError, match="recovery_required"):
                check_depth_recovery_state(saved, historical, current)
        assert provider.writes == 0
