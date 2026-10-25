"""A1 uses only synthetic CAD, mocked transport and ephemeral test databases."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from fastapi import Request
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from test_cad_read import REF
from test_safe_edit import M0, Provider, bodies, config, features, running

from forge_api.cad_edits import plan_service, plan_storage, storage
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import (
    ModifyOperation,
    PlanPreview,
    RenameFeature,
    ResolvedOperation,
    SemanticPlan,
    SetExtrudeDepth,
    SetFilletRadius,
    SetSuppressed,
    StoredPlan,
    Target,
    TargetPreview,
)
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.edit_registry import (
    change,
    locate,
    supports_operation,
)
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.query_receipt import OperationAcknowledgement
from forge_api.integrations.onshape.service import ReadGate
from forge_api.integrations.onshape.write_client import SafeEditClient

HANDLE = "A" * 43
OP: TypeAdapter[ModifyOperation] = TypeAdapter(ModifyOperation)


def inventory() -> dict[str, Any]:
    data = features()
    params = json.loads(
        (Path(__file__).parent / "fixtures/modify_parameters.json").read_text()
    )
    for f in data["features"]:
        if f["featureType"] in params:
            f["parameters"] = params[f["featureType"]]
    return data


def target(position: int = 3) -> Target:
    return Target(
        handle=HANDLE,
        feature_id=f"synthetic-feature-{position - 1}",
        feature_type="fillet" if position == 3 else "extrude",
        position=position,
    )


class PlanProvider(Provider):
    def __init__(self) -> None:
        super().__init__()
        self.data = inventory()
        self.fail_on = 2
        self.head_reads = 0
        self.guards: list[str] = []
        self.payloads: list[dict[str, Any]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        assert request.url.host == "cad.onshape.com"
        if request.method == "POST":
            body = json.loads(request.content)
            self.payloads.append(body)
            self.guards.append(body["sourceMicroversion"])
            assert body["rejectMicroversionSkew"] is True
            assert body["sourceMicroversion"] == self.marker
            assert body["serializationVersion"] == self.data["serializationVersion"]
            assert body["libraryVersion"] == self.data["libraryVersion"]
            if self.mode == "timeout" and self.writes == self.fail_on:
                raise httpx.ReadTimeout("synthetic-private-error")
            if self.mode == "guard_reject" and self.writes == self.fail_on:
                return httpx.Response(409, json={"private": "synthetic"})
            updated = body["features"][0] if "features" in body else body["feature"]
            if "features" in body:
                assert len(body["features"]) == 1
                assert set(updated) == {"btType", "featureId", "suppressed"}
                assert request.url.path.endswith("/features/updates")
            else:
                assert request.url.path.endswith(
                    "/features/featureid/" + updated["featureId"]
                )
            f = next(
                f
                for f in self.data["features"]
                if f["featureId"] == updated["featureId"]
            )
            f.update(deepcopy(updated))
            if self.data["featureStates"]:
                self.data["featureStates"][f["featureId"]]["inactive"] = f["suppressed"]
            self.marker = f"{self.writes:024x}"
            self.data["sourceMicroversion"] = self.marker
            self.head_reads = 0
            if self.mode == "unexpected" and self.writes == self.fail_on:
                self.data["features"][0]["unexpected"] = "synthetic-private"
            response = {"microversionSkew": False, "sourceMicroversion": self.marker}
            response["features" if "features" in body else "feature"] = (
                [updated] if "features" in body else updated
            )
            if self.mode == "malformed" and self.writes == self.fail_on:
                response["sourceMicroversion"] = None
            return httpx.Response(200, json=response)
        assert request.method == "GET"
        if request.url.path.endswith("/currentmicroversion"):
            self.head_reads += 1
            if self.writes == 1 and self.head_reads == 3:
                if self.mode == "before_failure":
                    return httpx.Response(503, json={})
                if self.mode == "stale":
                    self.marker = "f" * 24
                    self.data["sourceMicroversion"] = self.marker
            return httpx.Response(200, json={"microversion": self.marker})
        assert f"/m/{self.marker}/" in request.url.path
        if request.url.path.endswith("/configuration"):
            return httpx.Response(200, json=config(self.marker))
        if request.url.path.endswith("/bodydetails"):
            return httpx.Response(200, json=bodies(self.marker, explicit_flags=False))
        assert request.url.path.endswith("/features")
        assert request.url.params["noSketchGeometry"] == "false"
        return httpx.Response(200, json=self.data)


def request_for(h: Harness) -> Request:
    cookie = h.runtime.settings.session_cookie
    return Request(
        {
            "type": "http",
            "app": h.client.app,
            "headers": [(b"cookie", f"{cookie}={h.client.cookies[cookie]}".encode())],
        }
    )


def discover(h: Harness) -> tuple[Request, TargetPreview]:
    req = request_for(h)
    req.app.state.cad_gate = ReadGate()
    return req, plan_service.discover(req, h.runtime, REF)


def prepare(
    h: Harness,
    types: tuple[str, ...] = (
        "SET_EXTRUDE_DEPTH",
        "SET_FILLET_RADIUS",
        "RENAME_FEATURE",
    ),
) -> tuple[Request, PlanPreview]:
    req, targets = discover(h)
    operations: list[dict[str, str]] = []
    for kind in types:
        t = next(
            t
            for t in targets.targets
            if t.feature_type
            == ("extrude" if kind == "SET_EXTRUDE_DEPTH" else "fillet")
        )
        op = {"type": kind, "target": t.handle}
        if kind in ("SET_EXTRUDE_DEPTH", "SET_FILLET_RADIUS"):
            op["quantity"] = "30 mm" if kind == "SET_EXTRUDE_DEPTH" else "4 mm"
        if kind == "RENAME_FEATURE":
            op["new_name"] = " Edge Rounds "
        operations.append(op)
    semantic = SemanticPlan.model_validate_json(
        json.dumps({"target_catalog": targets.target_catalog, "operations": operations})
    )
    req.app.state.cad_gate = ReadGate()
    return req, plan_service.prepare(req, h.runtime, semantic)


def approve(h: Harness, req: Request, preview: PlanPreview) -> Any:
    return plan_service.approve(req, h.runtime, preview.proposal_id, preview.digest)


@pytest.mark.parametrize(
    "kind,extra",
    [
        ("SET_SUPPRESSED", {}),
        ("SET_UNSUPPRESSED", {}),
        ("RENAME_FEATURE", {"new_name": "Name"}),
        ("SET_EXTRUDE_DEPTH", {"quantity": "30 mm"}),
        ("SET_FILLET_RADIUS", {"quantity": "0.25 in"}),
    ],
)
def test_closed_operation_types(kind: str, extra: dict[str, str]) -> None:
    op = OP.validate_python({"type": kind, "target": HANDLE, **extra})
    assert op.type == kind
    with pytest.raises(ValidationError):
        op.target = "B" * 43  # type: ignore[misc]  # Runtime frozen boundary.


@pytest.mark.parametrize("count", [0, 1, 5, 6])
def test_plan_cardinality(count: int) -> None:
    payload = json.dumps(
        {
            "target_catalog": HANDLE,
            "operations": [{"type": "SET_SUPPRESSED", "target": HANDLE}] * count,
        }
    )
    if 1 <= count <= 5:
        assert len(SemanticPlan.model_validate_json(payload).operations) == count
    else:
        with pytest.raises(ValidationError):
            SemanticPlan.model_validate_json(payload)


@pytest.mark.parametrize(
    "quantity", ["30 mm", "4 mm", "1 in", "0.25 in", "0.001 mm", "10000 mm", "393 in"]
)
def test_valid_quantity(quantity: str) -> None:
    assert (
        SetExtrudeDepth(
            type="SET_EXTRUDE_DEPTH", target=HANDLE, quantity=quantity
        ).quantity
        == quantity
    )


@pytest.mark.parametrize(
    "quantity",
    [
        "",
        "NaN mm",
        "inf mm",
        "Infinity in",
        "-Infinity mm",
        "-1 mm",
        "0 mm",
        "0.000001 mm",
        "10001 mm",
        "394 in",
        "sqrt(2) mm",
        "#variable",
        "2 * anotherParameter",
        "30",
        "30 cm",
        "1e2 mm",
        "30\nmm",
        " 30 mm",
        "30 mm ",
        "３ mm",
        "30 mm; f()",
        "x" * 33,
    ],
)
def test_invalid_quantity(quantity: str) -> None:
    with pytest.raises(ValidationError):
        SetFilletRadius(type="SET_FILLET_RADIUS", target=HANDLE, quantity=quantity)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "x" * 129,
        "x\n",
        "\tx",
        "x\x00",
        "x\x7f",
        "x\u0085",
        "x\u202e",
        "😀" * 65,
    ],
)
def test_invalid_name(name: str) -> None:
    with pytest.raises(ValidationError):
        RenameFeature(type="RENAME_FEATURE", target=HANDLE, new_name=name)


def test_name_is_trimmed_plain_text() -> None:
    assert (
        RenameFeature(
            type="RENAME_FEATURE", target=HANDLE, new_name=" <script>text</script> "
        ).new_name
        == "<script>text</script>"
    )


@pytest.mark.parametrize(
    "key",
    [
        "featureId",
        "providerFeatureId",
        "url",
        "method",
        "payload",
        "featureDefinition",
        "microversion",
        "FeatureScript",
        "parameterId",
        "documentId",
        "desired_state",
        "unknown",
    ],
)
def test_external_schema_rejects_authority_injection(key: str) -> None:
    for kind, extra in [
        ("SET_SUPPRESSED", {}),
        ("SET_UNSUPPRESSED", {}),
        ("RENAME_FEATURE", {"new_name": "x"}),
        ("SET_EXTRUDE_DEPTH", {"quantity": "1 in"}),
        ("SET_FILLET_RADIUS", {"quantity": "1 mm"}),
    ]:
        with pytest.raises(ValidationError):
            OP.validate_python(
                {"type": kind, "target": HANDLE, **extra, key: "injected"}
            )
    with pytest.raises(ValidationError):
        SemanticPlan.model_validate_json(
            json.dumps(
                {
                    "target_catalog": HANDLE,
                    "operations": [{"type": "SET_SUPPRESSED", "target": HANDLE}],
                    key: "injected",
                }
            )
        )


def test_invalid_type_and_provider_id_as_handle() -> None:
    for op in [
        {"type": "DELETE", "target": HANDLE},
        {"type": "SET_SUPPRESSED", "target": "synthetic-feature-2"},
    ]:
        with pytest.raises(ValidationError):
            OP.validate_python(op)


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "replaced", "wrong_type", "moved"]
)
def test_target_identity_failures(case: str) -> None:
    fs = inventory()["features"]
    if case == "missing":
        fs.pop()
    elif case == "duplicate":
        fs.append(deepcopy(fs[-1]))
    elif case == "replaced":
        fs[-1]["featureId"] = "different-private-id"
    elif case == "wrong_type":
        fs[-1]["featureType"] = "extrude"
    else:
        fs.reverse()
    with pytest.raises(EditError):
        locate(fs, target())


def test_names_do_not_resolve_identity() -> None:
    fs = inventory()["features"]
    fs[1]["name"] = fs[2]["name"] = "Duplicate"
    assert locate(fs, target())["featureId"] == "synthetic-feature-2"
    fs[2]["name"] = "Completely different"
    assert locate(fs, target())["featureId"] == "synthetic-feature-2"
    with pytest.raises(EditError):
        locate(fs, target().model_copy(update={"feature_id": "Duplicate"}))


@pytest.mark.parametrize(
    "state,kind,valid",
    [
        (False, "SET_SUPPRESSED", True),
        (True, "SET_UNSUPPRESSED", True),
        (True, "SET_SUPPRESSED", False),
        (False, "SET_UNSUPPRESSED", False),
        (None, "SET_SUPPRESSED", False),
        (0, "SET_SUPPRESSED", False),
        ("false", "SET_UNSUPPRESSED", False),
    ],
)
def test_affirmative_suppression_only(state: Any, kind: str, valid: bool) -> None:
    fs = inventory()["features"]
    fs[-1]["suppressed"] = state
    op = OP.validate_python({"type": kind, "target": HANDLE})
    if valid:
        updated, _ = change(fs, target(), op)
        assert updated["suppressed"] is not state
        original = deepcopy(fs[-1])
        original["suppressed"] = updated["suppressed"]
        assert fingerprint(original) == fingerprint(updated)
    else:
        with pytest.raises(EditError):
            change(fs, target(), op)


@pytest.mark.parametrize(
    "position,kind,key",
    [(2, "SET_EXTRUDE_DEPTH", "depth"), (3, "SET_FILLET_RADIUS", "radius")],
)
def test_exact_quantity_adapter(position: int, kind: str, key: str) -> None:
    fs = inventory()["features"]
    op = OP.validate_python({"type": kind, "target": HANDLE, "quantity": "1 in"})
    updated, preview = change(fs, target(position), op)
    assert preview.proposed == "1 in"
    original = deepcopy(fs[position - 1])
    next(p for p in original["parameters"] if p["parameterId"] == key)["expression"] = (
        "1 in"
    )
    assert fingerprint(updated) == fingerprint(original)
    assert fs[position - 1] != updated


@pytest.mark.parametrize(
    "kind,position", [("SET_EXTRUDE_DEPTH", 2), ("SET_FILLET_RADIUS", 3)]
)
@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "duplicate",
        "alias",
        "subclass",
        "expression",
        "numeric_cache",
        "units_cache",
        "integer",
        "unknown_parameter",
        "wrong_type",
        "suppressed",
    ],
)
def test_unsupported_quantity_shapes(kind: str, position: int, case: str) -> None:
    fs = inventory()["features"]
    f = fs[position - 1]
    p = next(p for p in f["parameters"] if p["btType"] == "BTMParameterQuantity-147")
    if case == "missing":
        f["parameters"].remove(p)
    elif case == "duplicate":
        f["parameters"].append(deepcopy(p))
    elif case == "alias":
        p["parameterId"] = "endDepth" if position == 2 else "distance"
    elif case == "subclass":
        p["btType"] = "BTMParameterTolerantQuantity-2579"
    elif case == "expression":
        p["expression"] = "#variable"
    elif case == "numeric_cache":
        p["value"] = 1
    elif case == "units_cache":
        p["units"] = "millimeter"
    elif case == "integer":
        p["isInteger"] = True
    elif case == "unknown_parameter":
        f["parameters"].append({"parameterId": "speculative", "value": True})
    elif case == "wrong_type":
        f["featureType"] = "fillet" if position == 2 else "extrude"
    else:
        f["suppressed"] = True
    with pytest.raises(EditError):
        change(
            fs,
            target(position),
            OP.validate_python({"type": kind, "target": HANDLE, "quantity": "4 mm"}),
        )


def test_registry_is_semantic_and_closed() -> None:
    assert supports_operation("SET_EXTRUDE_DEPTH", "extrude")
    assert not supports_operation("SET_EXTRUDE_DEPTH", "fillet")
    assert not supports_operation("POST", "extrude")


@pytest.mark.parametrize("case", ["missing", "null", "empty", "malformed", "duplicate"])
def test_rename_rejects_incomplete_replacement_definition(case: str) -> None:
    fs = inventory()["features"]
    feature = fs[-1]
    if case == "missing":
        del feature["parameters"]
    elif case == "null":
        feature["parameters"] = None
    elif case == "empty":
        feature["parameters"] = []
    elif case == "malformed":
        feature["parameters"] = ["not-a-parameter"]
    else:
        feature["parameters"].append(deepcopy(feature["parameters"][1]))
    with pytest.raises(EditError):
        change(
            fs,
            target(),
            RenameFeature(type="RENAME_FEATURE", target=HANDLE, new_name="Name"),
        )


def test_three_operations_chain_and_privacy(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        assert provider.writes == 0
        public = preview.model_dump_json()
        for private in (
            "synthetic-feature-",
            M0,
            REF.documentId,
            REF.workspaceId,
            REF.elementId,
            "feature_id",
            "parameters",
            "binding",
            "workspace_key",
        ):
            assert private not in public
        result = approve(harness, req, preview)
        assert result.state == "verified_success"
        assert result.operations == ("verified_success",) * 3
        assert provider.writes == 3
        assert provider.guards == [M0, f"{1:024x}", f"{2:024x}"]
        assert provider.data["features"][-1]["name"] == "Edge Rounds"
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        with pytest.raises(EditError):
            approve(harness, req, preview)
        assert provider.writes == 3
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
            row = db.get(WriteRecord, preview.proposal_id)
            assert row and row.payload == result.model_dump_json()


@pytest.mark.parametrize(
    "mode,last_state,plan_state,count,fenced",
    [
        ("before_failure", "write_failed", "partial_failure", 1, False),
        ("stale", "rejected_stale", "partial_failure", 1, False),
        ("timeout", "execution_uncertain", "execution_uncertain", 2, True),
        ("malformed", "execution_uncertain", "execution_uncertain", 2, True),
        ("unexpected", "execution_uncertain", "execution_uncertain", 2, True),
        ("guard_reject", "execution_uncertain", "execution_uncertain", 2, True),
    ],
)
def test_stop_after_second_failure(
    harness: Harness,
    mode: str,
    last_state: str,
    plan_state: str,
    count: int,
    fenced: bool,
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        provider.mode = mode
        result = approve(harness, req, preview)
        assert result.state == plan_state
        assert result.operations == ("verified_success", last_state, "skipped")
        assert provider.writes == count
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        # No rollback: the earlier depth edit remains present after any failure.
        assert provider.data["features"][1]["parameters"][-1]["expression"] == "30 mm"
        with harness.runtime.sessions() as db:
            assert (db.scalar(select(WriteFence)) is not None) is fenced
        with pytest.raises(EditError):
            approve(harness, req, preview)
        assert provider.writes == count


@pytest.mark.parametrize("empty_states", [False, True])
def test_suppress_unsuppress_chain(harness: Harness, empty_states: bool) -> None:
    provider = PlanProvider()
    if empty_states:
        provider.data["featureStates"] = {}
    with running(harness, provider):
        req, preview = prepare(
            harness, ("SET_SUPPRESSED", "SET_UNSUPPRESSED", "RENAME_FEATURE")
        )
        assert preview.operations[1].current == "Suppressed"
        result = approve(harness, req, preview)
        assert result.state == "verified_success"
        assert provider.writes == 3 and len(provider.data["features"]) == 3
        assert provider.data["features"][-1]["suppressed"] is False


def test_same_identity_after_rename_then_suppress(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("RENAME_FEATURE", "SET_SUPPRESSED"))
        assert preview.operations[1].label == "Edge Rounds"
        assert approve(harness, req, preview).state == "verified_success"
        assert provider.writes == 2
        before = inventory()["features"][-1]
        after = provider.payloads[0]["feature"]
        before["name"] = "Edge Rounds"
        assert before == after


@pytest.mark.parametrize(
    "mutation",
    [
        "name",
        "depth",
        "radius",
        "order",
        "removed",
        "added",
        "identity",
        "type",
        "metadata",
        "state_coverage",
    ],
)
def test_rename_verification_rejects_unintended_changes(mutation: str) -> None:
    data = inventory()
    baseline = project_modify_evidence(REF, M0, data, config(), bodies())
    op = RenameFeature(type="RENAME_FEATURE", target=HANDLE, new_name="Rounds")
    updated, preview = change(data["features"], target(), op)
    resolved = ResolvedOperation(operation=op, target=target(), preview=preview)
    marker = "e" * 24
    after = deepcopy(data)
    after["sourceMicroversion"] = marker
    after["features"][-1] = updated
    if mutation == "name":
        updated["name"] = "Wrong"
    elif mutation == "depth":
        after["features"][1]["parameters"][-1]["expression"] = "999 mm"
    elif mutation == "radius":
        after["features"][-1]["parameters"][1]["expression"] = "999 mm"
    elif mutation == "order":
        after["features"][:2] = reversed(after["features"][:2])
    elif mutation == "removed":
        after["features"].pop(0)
    elif mutation == "added":
        after["features"].insert(0, deepcopy(after["features"][0]))
    elif mutation == "identity":
        updated["featureId"] = "recreated"
    elif mutation == "type":
        updated["featureType"] = "extrude"
    elif mutation == "state_coverage":
        after["featureStates"] = {}
    else:
        updated["privateMetadata"] = True
    with pytest.raises(EditError):
        evidence = project_modify_evidence(
            REF, marker, after, config(marker), bodies(marker)
        )
        verify_operation(baseline, evidence, resolved, marker)


@pytest.mark.parametrize(
    "mutation", ["expired", "digest", "payload", "session", "scope", "flag", "stale"]
)
def test_approval_denials_never_write(harness: Harness, mutation: str) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            if mutation == "expired":
                row.expires_at = now() - 1
            elif mutation == "payload":
                assert row.payload
                raw = json.loads(row.payload)
                raw["plan"]["operations"][0]["operation"]["quantity"] = "999 mm"
                row.payload = json.dumps(raw)
            elif mutation == "session":
                session = db.scalar(select(Session))
                assert session
                session.revoked_at = now()
            elif mutation == "scope":
                grant = db.scalar(select(OnshapeAuthorization))
                assert grant
                grant.granted_scope = "OAuth2Read"
        if mutation == "flag":
            harness.runtime.settings.forge_cad_writes_enabled = False
        if mutation == "stale":
            provider.marker = "f" * 24
            provider.data["sourceMicroversion"] = provider.marker
        try:
            result = plan_service.approve(
                req,
                harness.runtime,
                preview.proposal_id,
                "0" * 64 if mutation == "digest" else preview.digest,
            )
            assert result.state in ("write_failed", "rejected_stale")
        except EditError:
            pass
        assert provider.writes == 0


def test_stale_and_foreign_target_catalog(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, targets = discover(harness)
        semantic = SemanticPlan(
            target_catalog=targets.target_catalog,
            operations=(SetSuppressed(type="SET_SUPPRESSED", target="Z" * 43),),
        )
        req.app.state.cad_gate = ReadGate()
        with pytest.raises(EditError):
            plan_service.prepare(req, harness.runtime, semantic)
        provider.marker = "f" * 24
        provider.data["sourceMicroversion"] = provider.marker
        req.app.state.cad_gate = ReadGate()
        semantic = SemanticPlan(
            target_catalog=targets.target_catalog,
            operations=(
                SetSuppressed(type="SET_SUPPRESSED", target=targets.targets[-1].handle),
            ),
        )
        with pytest.raises(EditError, match="model_changed"):
            plan_service.prepare(req, harness.runtime, semantic)
        assert provider.writes == 0


def test_timeout_first_is_one_call_and_no_later_operation(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        provider.mode, provider.fail_on = "timeout", 1
        result = approve(harness, req, preview)
        assert result.operations == ("execution_uncertain", "skipped", "skipped")
        assert provider.writes == 1


def test_plan_frozen_digest_and_phase9_cannot_claim(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            plan = plan_storage.load(row).plan
            assert fingerprint(plan.model_dump(mode="json")) == preview.digest
            with pytest.raises(ValidationError):
                plan.operations[0].target.position = 1  # type: ignore[misc]
            with pytest.raises(EditError):
                storage.claim(
                    db,
                    plan.proposal_id,
                    plan.binding.user,
                    plan.binding.session,
                    preview.digest,
                )
        assert provider.writes == 0


def test_dispatch_journal_is_durable_and_uncertainty_fence_survives_cleanup(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        original = SafeEditClient.execute_operation
        seen = []

        def inspect_boundary(
            self: SafeEditClient, evidence: Any, operation: Any
        ) -> str | OperationAcknowledgement:
            with harness.runtime.sessions() as db:
                row = db.get(WriteRecord, preview.proposal_id)
                assert row and row.payload
                journal = StoredPlan.model_validate_json(row.payload)
                assert "executing" in journal.result.operations
                assert db.scalar(select(WriteFence)) is not None
                seen.append(
                    db.scalar(
                        select(AuditEvent.id).where(
                            AuditEvent.kind == "write_dispatch_started"
                        )
                    )
                )
            return original(self, evidence, operation)

        monkeypatch.setattr(SafeEditClient, "execute_operation", inspect_boundary)
        provider.mode, provider.fail_on = "timeout", 1
        assert approve(harness, req, preview).state == "execution_uncertain"
        assert len(seen) == 1 and seen[0] is not None
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
        with harness.runtime.sessions() as db:
            assert db.get(WriteRecord, preview.proposal_id) is not None
            assert db.scalar(select(WriteFence)) is not None


def test_maximum_five_operations_execute_in_order(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(
            harness,
            (
                "SET_EXTRUDE_DEPTH",
                "SET_FILLET_RADIUS",
                "RENAME_FEATURE",
                "SET_SUPPRESSED",
                "SET_UNSUPPRESSED",
            ),
        )
        result = approve(harness, req, preview)
        assert result.operations == ("verified_success",) * 5
        assert provider.writes == 5
        assert provider.guards == [M0] + [f"{n:024x}" for n in range(1, 5)]


def test_microversion_chain_m0_to_m3_never_reuses_a_baseline(harness: Harness) -> None:
    """M0 -> op1 -> M1 -> op2 -> M2 -> op3 -> M3, each guarded by its predecessor."""
    provider = PlanProvider()
    chain = [M0] + [f"{n:024x}" for n in (1, 2, 3)]  # M0, M1, M2, M3
    with running(harness, provider):
        req, preview = prepare(harness)  # extrude depth, fillet radius, rename
        assert provider.marker == chain[0]
        result = approve(harness, req, preview)
        assert result.operations == ("verified_success",) * 3
        # op1 used M0, op2 used M1 (never M0), op3 used M2 (never M0 or M1).
        assert provider.guards == chain[:3]
        # The final verified state is M3, and no baseline was ever reused.
        assert provider.marker == chain[3]
        assert len(set(chain)) == 4
        for index, guard in enumerate(provider.guards):
            assert guard == chain[index]
            assert all(guard != earlier for earlier in chain[:index])


@pytest.mark.parametrize(
    "kind,position", [("SET_EXTRUDE_DEPTH", 2), ("SET_FILLET_RADIUS", 3)]
)
@pytest.mark.parametrize("mutate", [False, True])
def test_quantity_verification_requires_exact_change(
    kind: str, position: int, mutate: bool
) -> None:
    data = inventory()
    f = data["features"][position - 1]
    quantity = next(
        p for p in f["parameters"] if p["btType"] == "BTMParameterQuantity-147"
    )
    quantity.update({"nodeId": "synthetic-node", "isInteger": False})
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    op = OP.validate_python({"type": kind, "target": HANDLE, "quantity": "4 mm"})
    updated, preview = change(data["features"], target(position), op)
    resolved = ResolvedOperation(operation=op, target=target(position), preview=preview)
    data["features"][position - 1] = updated
    marker = "e" * 24
    data["sourceMicroversion"] = marker
    if mutate:
        params = updated["parameters"]
        assert isinstance(params, list) and isinstance(params[0], dict)
        params[0]["unexpected"] = True
    after = project_modify_evidence(REF, marker, data, config(marker), bodies(marker))
    if mutate:
        with pytest.raises(EditError):
            verify_operation(before, after, resolved, marker)
    else:
        verify_operation(before, after, resolved, marker)


def test_unsuppress_requires_fresh_positive_result(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    provider.data["features"][-1]["suppressed"] = True
    provider.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_UNSUPPRESSED", "RENAME_FEATURE"))
        original = SafeEditClient.execute_operation

        def ambiguous(
            self: SafeEditClient, evidence: Any, operation: Any
        ) -> str | OperationAcknowledgement:
            marker = original(self, evidence, operation)
            del provider.data["features"][-1]["suppressed"]
            return marker

        monkeypatch.setattr(SafeEditClient, "execute_operation", ambiguous)
        result = approve(harness, req, preview)
        assert result.operations == ("execution_uncertain", "skipped")
        assert provider.writes == 1


def test_oversized_feature_fails_before_any_dispatch(harness: Harness) -> None:
    provider = PlanProvider()
    # Evidence remains within read caps but the unchanged full feature exceeds
    # the fixed 24 KiB replacement cap. No reconstruction or retry is allowed.
    provider.data["features"][-1]["syntheticMetadata"] = "x" * 24576
    with running(harness, provider):
        req, preview = prepare(harness, ("RENAME_FEATURE", "SET_SUPPRESSED"))
        result = approve(harness, req, preview)
        assert result.operations == ("write_failed", "skipped")
        assert provider.writes == 0
        with harness.runtime.sessions() as db:
            assert (
                db.scalar(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_dispatch_started"
                    )
                )
                is None
            )
            assert db.scalar(select(WriteFence)) is None


@pytest.mark.parametrize("case", ["expired", "disabled", "generation", "deadline"])
def test_authority_rechecked_before_every_operation(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        original = SafeEditClient.modify_evidence
        reads = 0

        def read(self: SafeEditClient, context: Any) -> Any:
            nonlocal reads
            reads += 1
            if reads == 3:
                if case == "expired":
                    monkeypatch.setattr(plan_service, "now", lambda: preview.expires_at)
                elif case == "disabled":
                    harness.runtime.settings.forge_cad_writes_enabled = False
                elif case == "deadline":
                    monkeypatch.setattr(
                        plan_service, "monotonic", lambda: self._deadline + 1
                    )
                else:
                    with harness.runtime.sessions.begin() as db:
                        grant = db.scalar(select(OnshapeAuthorization))
                        assert grant
                        grant.generation = "new-synthetic-generation"
            return original(self, context)

        monkeypatch.setattr(SafeEditClient, "modify_evidence", read)
        result = approve(harness, req, preview)
        assert result.state == "partial_failure"
        assert (
            result.operations[0] == "verified_success"
            and result.operations[2] == "skipped"
        )
        assert provider.writes == 1


def _break_definition(feature: dict[str, Any], case: str) -> None:
    """Make a supported Extrude/Fillet definition incomplete or malformed."""
    params = feature["parameters"]
    if case == "missing":
        del feature["parameters"]
    elif case == "null":
        feature["parameters"] = None
    elif case == "empty":
        feature["parameters"] = []
    elif case == "malformed":
        feature["parameters"] = ["not-a-parameter"]
    elif case == "duplicate":
        params.append(deepcopy(params[0]))
    elif case == "unknown_parameter":
        params.append({"parameterId": "speculative", "value": True})
    elif case == "wrong_type":
        params[0] = {"parameterId": params[0]["parameterId"], "btType": "Unknown-1"}
    else:
        raise AssertionError(case)


def _no_dispatch(harness: Harness, provider: PlanProvider) -> None:
    assert provider.writes == 0 and not provider.payloads
    assert all(call.method == "GET" for call in provider.calls)
    with harness.runtime.sessions() as db:
        assert (
            db.scalar(
                select(AuditEvent).where(AuditEvent.kind == "write_dispatch_started")
            )
            is None
        )
        assert db.scalar(select(WriteFence)) is None


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "null",
        "empty",
        "malformed",
        "duplicate",
        "unknown_parameter",
        "wrong_type",
    ],
)
def test_rename_of_an_incomplete_definition_never_reaches_the_provider(
    harness: Harness, position: int, case: str
) -> None:
    """Rename replaces the whole feature, so an unproven definition is rejected
    before a plan exists, let alone before any dispatch."""
    provider = PlanProvider()
    _break_definition(provider.data["features"][position - 1], case)
    with running(harness, provider):
        try:
            req, targets = discover(harness)
        except EditError:
            targets = None  # The whole evidence was refused: even earlier, still safe.
        if targets is not None:
            match = next((t for t in targets.targets if t.position == position), None)
            if match is not None:
                # A target may remain listed for other supported edits, but never
                # for rename, and an explicit rename request cannot become a plan.
                assert "RENAME_FEATURE" not in match.supported_operations
                semantic = SemanticPlan.model_validate_json(
                    json.dumps(
                        {
                            "target_catalog": targets.target_catalog,
                            "operations": [
                                {
                                    "type": "RENAME_FEATURE",
                                    "target": match.handle,
                                    "new_name": "Renamed",
                                }
                            ],
                        }
                    )
                )
                req.app.state.cad_gate = ReadGate()
                with pytest.raises(EditError):
                    plan_service.prepare(req, harness.runtime, semantic)
        _no_dispatch(harness, provider)


@pytest.mark.parametrize("case", ["missing", "empty", "malformed", "unknown_parameter"])
def test_a_definition_that_becomes_incomplete_after_preparation_is_never_written(
    harness: Harness, case: str
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("RENAME_FEATURE", "SET_SUPPRESSED"))
        assert provider.writes == 0
        # The definition degrades between approval time and execution.
        _break_definition(provider.data["features"][-1], case)
        result = approve(harness, req, preview)
        # First operation fails before dispatch; the second is never attempted.
        assert result.operations[0] in ("write_failed", "rejected_stale")
        assert result.operations[1] == "skipped"
        assert result.state in ("write_failed", "rejected_stale")
        _no_dispatch(harness, provider)
