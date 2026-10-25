"""Synthetic v17 creation acknowledgements and real local approval transactions."""

import json
from copy import deepcopy
from typing import Any, cast

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_cad_read import REF
from test_safe_edit import M0, bodies, config, features, running

from forge_api.cad_create.natural_language import schema
from forge_api.cad_create.planner import plan_creation
from forge_api.db.models import WriteFence

BRIEF: dict[str, Any] = {
    "width": {"value": 60, "unit": "mm"},
    "length": {"value": 40, "unit": "mm"},
    "thickness": {"value": 10, "unit": "mm"},
    "holes": [],
}


class Provider:
    def __init__(self, mode: str = "ok") -> None:
        self.data = features()
        self.data.update(features=[], featureStates={}, rollbackIndex=0)
        self.marker = M0
        self.writes = 0
        self.mode = mode
        self.calls: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if request.method == "POST":
            assert path.endswith("/features")
            payload = json.loads(request.content)
            assert payload["sourceMicroversion"] == self.marker
            assert payload["rejectMicroversionSkew"] is True
            self.writes += 1
            self.marker = f"{self.writes:024x}"
            feature = {**payload["feature"], "featureId": f"synthetic-{self.writes}"}
            self.data.update(
                sourceMicroversion=self.marker,
                features=[*self.data["features"], feature],
                rollbackIndex=self.writes,
            )
            ack: dict[str, Any] = {
                "sourceMicroversion": self.marker,
                "microversionSkew": False,
                "feature": deepcopy(feature),
            }
            if self.mode == "ack":
                ack["feature"]["name"] = "wrong"
            if self.mode == "fresh":
                self.data["features"][-1] = {**feature, "name": "wrong"}
            if self.mode == "prior" and self.writes == 2:
                self.data["features"][0] = {
                    **self.data["features"][0],
                    "name": "unrelated-change",
                }
            if self.mode == "transport":
                raise httpx.ReadTimeout("synthetic")
            return httpx.Response(200, json=ack)
        if path.endswith("currentmicroversion"):
            return httpx.Response(200, json={"microversion": self.marker})
        if path.endswith("features"):
            return httpx.Response(200, json=self.data)
        if path.endswith("configuration"):
            return httpx.Response(200, json=config(self.marker))
        if path.endswith("bodydetails"):
            body = bodies(self.marker)
            if self.writes < 2:
                body["bodies"] = []
            return httpx.Response(200, json=body)
        raise AssertionError("unexpected provider call")


def post(h: Harness, path: str, body: Any) -> Any:
    return h.client.post(path, json=body, headers=h.headers())


@pytest.mark.parametrize(
    "mode",
    [
        "ok",
        "ack",
        "fresh",
        "transport",
        "disabled",
        "tamper",
        "unconfirmed",
        "stale",
        "prior",
    ],
)
def test_approved_plan_is_one_use_and_failure_retains_fence(
    harness: Harness, mode: str
) -> None:
    p = Provider(mode)
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        )
        assert preview.status_code == 200, preview.text
        value = preview.json()
        handle = value["proposal_id"]
        assert p.writes == 0
        if mode == "disabled":
            harness.runtime.settings.forge_cad_writes_enabled = False
        if mode == "stale":
            p.data["unknown_change"] = True
        response = post(
            harness,
            f"/api/create/plans/{handle}/approve",
            {
                "digest": "0" * 64 if mode == "tamper" else value["digest"],
                "brief_confirmed": mode != "unconfirmed",
            },
        )
        if mode in ("disabled", "tamper", "unconfirmed"):
            assert response.status_code in (400, 403, 409)
            assert p.writes == 0
        else:
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["state"] == (
                "verified_success"
                if mode == "ok"
                else "rejected_stale"
                if mode == "stale"
                else "execution_uncertain"
            )
            assert p.writes == (
                2 if mode in ("ok", "prior") else 0 if mode == "stale" else 1
            )
            with harness.runtime.sessions() as db:
                assert (db.scalar(select(WriteFence)) is not None) == (
                    mode not in ("ok", "stale")
                )
            again = post(
                harness,
                f"/api/create/plans/{handle}/approve",
                {"digest": value["digest"], "brief_confirmed": True},
            )
            assert again.status_code == 409
            assert p.writes == (
                2 if mode in ("ok", "prior") else 0 if mode == "stale" else 1
            )


def test_complete_unsupported_plan_cannot_partially_dispatch(harness: Harness) -> None:
    p = Provider()
    brief = deepcopy(BRIEF)
    brief["holes"] = [
        {
            "diameter": {"value": 8, "unit": "mm"},
            "center_x": {"value": 0, "unit": "mm"},
            "center_y": {"value": 0, "unit": "mm"},
        }
    ]
    with running(harness, cast(Any, p)):
        response = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": brief}
        )
        assert response.status_code == 422 and not p.calls


def test_wire_schema_has_no_provider_or_approval_input() -> None:
    text = json.dumps(schema())
    for field in ("featureId", "microversion", "payload", "approve", "proposal_id"):
        assert field not in text
    assert (
        plan_creation(
            {"outcome": "unsupported", "reason": "unsupported_feature"}
        ).status
        == "unsupported"
    )


@pytest.mark.parametrize("mutation", ["expire", "binding", "payload", "nonempty"])
def test_approval_binding_and_empty_baseline(harness: Harness, mutation: str) -> None:
    from forge_api.db.models import WriteRecord, now

    p = Provider()
    with running(harness, cast(Any, p)):
        if mutation == "nonempty":
            p.data = features()
            response = post(
                harness,
                "/api/create/plan",
                {"context": REF.model_dump(), "brief": BRIEF},
            )
            assert response.status_code in (409, 422) and p.writes == 0
            return
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview["proposal_id"])
            assert row
            if mutation == "expire":
                row.expires_at = now() - 1
            elif mutation == "payload":
                row.payload = "{}"
            else:
                row.session_hash = "f" * 64
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
        assert response.status_code in (404, 409) and not p.writes


@pytest.mark.parametrize(
    "mode", ["success", "unsupported", "clarification", "bad", "tool"]
)
def test_model_intent_never_approves_or_dispatches(harness: Harness, mode: str) -> None:
    from pydantic import SecretStr

    p = Provider()
    settings = harness.runtime.settings
    settings.forge_ai_provider = "openai"
    settings.openai_api_key = SecretStr("synthetic-only")
    result: dict[str, Any]
    if mode == "unsupported":
        result = {"outcome": "unsupported", "reason": "unsupported_feature"}
    elif mode == "clarification":
        result = {
            "outcome": "clarification",
            "reason": "missing_dimension",
            "fields": ["thickness"],
        }
    elif mode == "bad":
        result = {"provider_payload": "forbidden"}
    else:
        result = {"outcome": "brief", "design": BRIEF}
    calls = []

    def ai(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        assert body["tool_choice"] == "none" and "tools" not in body
        assert not any(
            key in json.dumps(body["text"]["format"]["schema"])
            for key in ["featureId", "proposal_id", "microversion"]
        )
        output = [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps({"result": result})}
                ],
            }
        ]
        if mode == "tool":
            output = [{"type": "function_call", "name": "approve"}]
        return httpx.Response(200, json={"status": "completed", "output": output})

    import asyncio

    client = httpx.AsyncClient(transport=httpx.MockTransport(ai))
    with running(harness, cast(Any, p)):
        harness.client.app.state.ai_transport = client  # type: ignore[attr-defined]
        try:
            response = post(
                harness,
                "/api/create/interpret",
                {"request": "Create a rectangle with explicit dimensions and no holes"},
            )
            if mode == "tool":
                assert response.status_code == 503
            else:
                assert response.status_code == 200, response.text
                assert (
                    response.json()["status"]
                    == {
                        "success": "ready",
                        "unsupported": "unsupported",
                        "clarification": "needs_clarification",
                        "bad": "rejected",
                    }[mode]
                )
            assert len(calls) == 1 and not p.calls and p.writes == 0
        finally:
            asyncio.run(client.aclose())


def test_cancel_has_zero_provider_writes_and_cannot_then_approve(
    harness: Harness,
) -> None:
    p = Provider()
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        response = post(
            harness, f"/api/create/plans/{preview['proposal_id']}/cancel", {}
        )
        assert response.status_code == 200 and response.json() == {"state": "cancelled"}
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
        assert response.status_code == 409 and p.writes == 0


def test_lost_final_commit_reply_does_not_create_unfenced_uncertainty(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.orm import SessionTransaction

    from forge_api.db.models import WriteRecord

    p = Provider()
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        original = SessionTransaction.__exit__
        failed = False

        def lost(self: Any, *args: Any, **kwargs: Any) -> Any:
            nonlocal failed
            row = (
                self.session.get(WriteRecord, preview["proposal_id"])
                if self.parent is None and not failed
                else None
            )
            final = bool(row and row.state == "verified_success")
            value = original(self, *args, **kwargs)
            if final:
                failed = True
                raise RuntimeError("synthetic lost commit reply")
            return value

        with monkeypatch.context() as patch:
            patch.setattr(SessionTransaction, "__exit__", lost)
            result = post(
                harness,
                f"/api/create/plans/{preview['proposal_id']}/approve",
                {"digest": preview["digest"], "brief_confirmed": True},
            )
        assert failed and p.writes == 2
        assert (
            result.status_code == 200 and result.json()["state"] == "verified_success"
        )
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview["proposal_id"])
            assert row and row.state == "verified_success"
            assert db.scalar(select(WriteFence)) is None
