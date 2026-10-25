"""Synthetic operation-local resolution, with exact fresh identity verification."""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_modify_ack_query_ids import PRIVATE, query
from test_modify_current_query_contracts import current_inventory
from test_modify_plan import PlanProvider, approve, prepare
from test_modify_semantic_nodes import operation, projection
from test_safe_edit import M1, running

from forge_api.cad_edits.domain import EditError
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.modify_evidence import verify_operation
from forge_api.integrations.onshape.query_receipt import (
    OperationAcknowledgement,
    QueryIdentityReceipt,
)


def setup() -> Any:
    data = current_inventory()
    query(data["features"][1])["deterministicIds"] = []
    op, expected = operation(data)
    returned = deepcopy(expected["features"][1])
    query(returned)["deterministicIds"] = ["synthetic-one", "synthetic-two"]
    return data, op, expected, returned


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "value",
        "count",
        "order",
        "missing",
        "string",
        "type",
        "filter",
        "other",
        "unknown",
    ],
)
def test_receipt_requires_exact_fresh_inventory(mutation: str) -> None:
    data, op, expected, returned = setup()
    receipt = QueryIdentityReceipt.resolve(expected["features"][1], returned)
    assert receipt.ids == ("synthetic-one", "synthetic-two")
    before = projection(data)
    ack = OperationAcknowledgement(M1, receipt, before, op)
    after = deepcopy(expected)
    after["features"][1] = returned
    q = query(returned)
    if mutation == "value":
        q["deterministicIds"] = ["other", "synthetic-two"]
    elif mutation == "count":
        q["deterministicIds"].pop()
    elif mutation == "order":
        q["deterministicIds"].reverse()
    elif mutation == "missing":
        q.pop("deterministicIds")
    elif mutation == "string":
        q["queryString"] = "other"
    elif mutation == "type":
        q["btType"] = "unknown"
    elif mutation == "filter":
        next(p for p in returned["parameters"] if p["parameterId"] == "entities")[
            "filter"
        ]["unknown"] = True
    elif mutation == "other":
        after["features"][0]["name"] = "other"
    elif mutation == "unknown":
        q["unknown"] = True
    if mutation == "none":
        verify_operation(before, projection(after, M1), op, M1, ack)
    else:
        with pytest.raises(EditError):
            verify_operation(before, projection(after, M1), op, M1, ack)
    if ack.consumed:
        with pytest.raises(EditError):
            ack.consume(before, op, M1)
    assert query(data["features"][1])["deterministicIds"] == []


@pytest.mark.parametrize(
    "change",
    [
        "string",
        "feature",
        "inner",
        "type",
        "count",
        "filter",
        "parameter",
        "nonempty",
        "malformed",
        "unknown",
    ],
)
def test_ack_exception_is_closed(change: str) -> None:
    _, _, expected, returned = setup()
    a, b = expected["features"][1], returned
    if change == "string":
        query(b)["queryString"] = "other"
    elif change == "feature":
        query(b)["featureId"] = "other"
    elif change == "inner":
        query(b)["filterInnerLoops"] = False
    elif change == "type":
        query(b)["btType"] = "BTMIndividualSketchRegionQuery-140"
    elif change == "count":
        next(p for p in b["parameters"] if p["parameterId"] == "entities")[
            "queries"
        ].append(deepcopy(query(b)))
    elif change == "filter":
        next(p for p in b["parameters"] if p["parameterId"] == "entities")["filter"][
            "unknown"
        ] = True
    elif change == "parameter":
        b["parameters"][-1]["unknown"] = True
    elif change == "nonempty":
        query(a)["deterministicIds"] = ["original"]
    elif change == "malformed":
        query(b)["deterministicIds"] = [None]
    else:
        query(b)["unknown"] = True
    with pytest.raises(EditError):
        QueryIdentityReceipt.resolve(a, b)


@pytest.mark.parametrize("change", ["operation", "evidence", "marker"])
def test_handoff_cannot_cross_operation_or_proposal(change: str) -> None:
    data, op, expected, returned = setup()
    before = projection(data)
    ack = OperationAcknowledgement(
        M1, QueryIdentityReceipt.resolve(expected["features"][1], returned), before, op
    )
    with pytest.raises(EditError):
        ack.consume(
            projection(data) if change == "evidence" else before,
            op.model_copy() if change == "operation" else op,
            "f" * 24 if change == "marker" else M1,
        )
    with pytest.raises(EditError):
        ack.consume(before, op, M1)


@pytest.mark.parametrize(
    "edit,index", [("SET_EXTRUDE_DEPTH", 1), ("SET_FILLET_RADIUS", 2)]
)
@pytest.mark.parametrize("failure", ["none", "post", "ack_marker", "ack_other"])
def test_real_pipeline_receipt_and_fence(
    harness: Harness, failure: str, edit: str, index: int
) -> None:
    class Provider(PlanProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST":
                result = response.json()
                query(result["feature"])["deterministicIds"] = [PRIVATE]
                query(self.data["features"][index])["deterministicIds"] = [
                    PRIVATE if failure != "post" else "different"
                ]
                if failure == "ack_marker":
                    result["sourceMicroversion"] = "invalid"
                if failure == "ack_other":
                    result["feature"]["name"] = "other"
                return httpx.Response(200, json=result)
            return response

    provider = Provider()
    provider.data = current_inventory()
    query(provider.data["features"][index])["deterministicIds"] = []
    with running(harness, provider):
        req, preview = prepare(harness, (edit,))
        result = approve(harness, req, preview)
        assert result.state == (
            "verified_success" if failure == "none" else "execution_uncertain"
        )
        assert query(provider.payloads[0]["feature"])["deterministicIds"] == []
        assert provider.writes == 1
        with harness.runtime.sessions() as db:
            assert (db.scalar(select(WriteFence)) is not None) == (failure != "none")
