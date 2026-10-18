"""A2 HTTP/task authority tests: synthetic CAD and no model/provider network."""

import asyncio
import json
from collections.abc import Iterator
from threading import Event
from typing import Any, cast

import httpx2 as httpx
import pytest
from conftest import Harness
from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from test_cad_read import REF
from test_modify_plan import PlanProvider, prepare, request_for
from test_safe_edit import M0, running

from forge_api.cad_edits import plan_routes, plan_service, plan_storage, storage
from forge_api.cad_edits.plan_events import (
    MAX_EVENT_BYTES,
    MAX_EVENTS,
    MAX_STREAM_BYTES,
    OperationResultEvent,
    Progress,
    ProgressEvent,
    StreamEvent,
)
from forge_api.cad_edits.plans import PlanPreview, PlanResult
from forge_api.db.models import AuditEvent, User, WriteFence, WriteRecord

TYPES = (
    "SET_EXTRUDE_DEPTH",
    "SET_FILLET_RADIUS",
    "RENAME_FEATURE",
    "SET_SUPPRESSED",
    "SET_UNSUPPRESSED",
)
EVENTS: TypeAdapter[StreamEvent] = TypeAdapter(StreamEvent)


@pytest.fixture(autouse=True)
def no_ai(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    from forge_api.ai import adapter, groq, service
    from forge_api.modify_planner import providers
    from forge_api.modify_planner import service as planner
    from forge_api.tutor import service as tutor

    calls: list[str] = []

    def forbidden(*_: object, **__: object) -> None:
        calls.append("ai")
        raise AssertionError("AI has no execution authority")

    for module, name in (
        (service, "run_agent"),
        (tutor, "run_tutor"),
        (planner, "plan"),
        (providers.GroqPlanner, "plan"),
        (providers.OpenAIPlanner, "plan"),
        (groq.GroqProvider, "request_inspection"),
        (groq.GroqProvider, "answer_with_evidence"),
        (adapter.ResponsesAdapter, "request_inspection"),
        (adapter.ResponsesAdapter, "answer_with_evidence"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    yield
    # A1 catches unexpected failures; a swallowed forbidden call must still fail.
    assert calls == []


def path(preview: PlanPreview, action: str = "") -> str:
    return "/api/modify/plans/" + preview.proposal_id + action


def send(h: Harness, p: PlanPreview, action: str = "/approve") -> httpx.Response:
    return h.client.post(
        path(p, action),
        json={"digest": p.digest} if action == "/approve" else {},
        headers=h.headers(),
    )


def status(h: Harness, p: PlanPreview) -> dict[str, Any]:
    response = h.client.get(path(p), headers=h.headers())
    assert response.status_code == 200
    body = cast(dict[str, Any], response.json())
    assert set(body) == {"state", "operations"}
    return body


def private_free(value: object) -> None:
    text = json.dumps(value)
    for forbidden in (
        "synthetic-feature-",
        "synthetic-private",
        "synthetic-access",
        "synthetic-refresh",
        "featureId",
        "feature_id",
        "providerFeatureId",
        "documentId",
        "workspaceId",
        "elementId",
        "microversion",
        "workspace_key",
        "binding",
        "parameters",
        "parameterId",
        "payload",
        "https://cad.onshape.com",
        "OAuth",
        "cookie",
        "csrf",
        M0,
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
    ):
        assert forbidden not in text


def events(response: httpx.Response) -> list[dict[str, Any]]:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-store"
    lines = response.content.splitlines(keepends=True)
    assert len(lines) <= MAX_EVENTS
    assert len(response.content) <= MAX_STREAM_BYTES
    for line in lines:
        assert len(line) <= MAX_EVENT_BYTES
        EVENTS.validate_json(line)
    result = [json.loads(line) for line in lines]
    private_free(result)
    return result


@pytest.mark.parametrize("count", [1, 3, 5])
def test_success_order_and_verified_progress(harness: Harness, count: int) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness, TYPES[:count])
        private_free(preview.model_dump(mode="json"))
        response = events(send(harness, preview))
        expected: list[dict[str, Any]] = []
        for i in range(1, count + 1):
            expected.extend(
                {"type": "progress", "operation": i, "total": count, "stage": stage}
                for stage in ("checking", "executing", "verifying")
            )
            expected.append(
                {
                    "type": "operation_result",
                    "operation": i,
                    "total": count,
                    "state": "verified_success",
                }
            )
        final = {
            "state": "verified_success",
            "operations": ["verified_success"] * count,
        }
        expected.append({"type": "result", **final})
        assert response == expected
        assert provider.writes == count
        assert provider.guards == [M0] + [f"{n:024x}" for n in range(1, count)]
        assert status(harness, preview) == final
        assert send(harness, preview).status_code == 409
        assert provider.writes == count


@pytest.mark.parametrize(
    "case,code",
    [
        ("unauthenticated", 401),
        ("missing_csrf", 403),
        ("invalid_csrf", 403),
        ("wrong_origin", 403),
        ("cross_site", 403),
        ("content_type", 400),
        ("extra", 400),
        ("missing_digest", 400),
        ("malformed_digest", 400),
        ("invalid_handle", 404),
        ("wrong_digest", 409),
        ("expired", 409),
        ("wrong_owner", 404),
        ("wrong_session", 404),
        ("disabled", 403),
        ("oversize", 413),
        ("query", 400),
        ("duplicate_json", 400),
    ],
)
def test_approval_denials_are_http_and_zero_writes(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, case: str, code: int
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        headers = harness.headers()
        body: dict[str, Any] = {"digest": preview.digest}
        url = path(preview, "/approve")
        if case == "unauthenticated":
            harness.client.cookies.clear()
        elif case == "missing_csrf":
            del headers["X-CSRF-Token"]
        elif case == "invalid_csrf":
            headers["X-CSRF-Token"] = "0" * 64
        elif case == "wrong_origin":
            headers["Origin"] = "https://synthetic.invalid"
        elif case == "cross_site":
            headers["Sec-Fetch-Site"] = "cross-site"
        elif case == "content_type":
            headers["Content-Type"] = "text/plain"
        elif case == "extra":
            body["operations"] = []
        elif case == "missing_digest":
            body = {}
        elif case == "malformed_digest":
            body["digest"] = "x" * 64
        elif case == "invalid_handle":
            url = "/api/modify/plans/invalid/approve"
        elif case == "wrong_digest":
            body["digest"] = "0" * 64
        elif case == "expired":
            monkeypatch.setattr(storage, "now", lambda: preview.expires_at)
        elif case in ("wrong_owner", "wrong_session"):
            with harness.runtime.sessions.begin() as db:
                row = db.get(WriteRecord, preview.proposal_id)
                assert row
                if case == "wrong_session":
                    row.session_hash = "0" * 64
                else:
                    user = User(
                        onshape_user_id="synthetic-other",
                        display_name="Other",
                        stack="https://cad.onshape.com/api",
                    )
                    db.add(user)
                    db.flush()
                    row.user_id = user.id
        elif case == "disabled":
            harness.runtime.settings.forge_cad_writes_enabled = False
        elif case == "oversize":
            body["payload"] = "x" * 8192
        elif case == "query":
            url += "?approve=true"
        if case == "duplicate_json":
            headers["Content-Type"] = "application/json"
            response = harness.client.post(
                url, headers=headers, content='{"digest":"a","digest":"b"}'
            )
        else:
            response = harness.client.post(url, headers=headers, json=body)
        assert response.status_code == code, response.text
        assert response.headers["content-type"] == "application/json"
        assert set(response.json()) == {"detail"}
        assert provider.writes == 0
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None


@pytest.mark.parametrize(
    "key",
    [
        "operations",
        "context",
        "target_catalog",
        "target",
        "name",
        "featureId",
        "providerFeatureId",
        "microversion",
        "workspaceId",
        "elementId",
        "documentId",
        "approved",
        "response",
        "payload",
        "url",
        "method",
        "FeatureScript",
    ],
)
def test_request_cannot_supply_authority(harness: Harness, key: str) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        for action, body in (("/approve", {"digest": preview.digest}), ("/cancel", {})):
            response = harness.client.post(
                path(preview, action),
                headers=harness.headers(),
                json={**body, key: "synthetic-private"},
            )
            assert response.status_code == 400
            assert response.json() == {"detail": "invalid_request"}
        assert provider.writes == 0


@pytest.mark.parametrize(
    "mode,state,last,writes",
    [
        ("before_failure", "partial_failure", "write_failed", 1),
        ("stale", "partial_failure", "rejected_stale", 1),
        ("timeout", "execution_uncertain", "execution_uncertain", 2),
        ("malformed", "execution_uncertain", "execution_uncertain", 2),
        ("unexpected", "execution_uncertain", "execution_uncertain", 2),
        ("guard_reject", "execution_uncertain", "execution_uncertain", 2),
    ],
)
def test_stop_preserves_prefix_no_retry_no_rollback(
    harness: Harness, mode: str, state: str, last: str, writes: int
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        provider.mode = mode
        stream = events(send(harness, preview))
        final = {"state": state, "operations": ["verified_success", last, "skipped"]}
        assert stream[-1] == {"type": "result", **final}
        assert [e["state"] for e in stream if e["type"] == "operation_result"] == final[
            "operations"
        ]
        assert provider.writes == writes
        assert provider.data["features"][1]["parameters"][-1]["expression"] == "30 mm"
        assert status(harness, preview) == final
        assert send(harness, preview).status_code == 409
        assert send(harness, preview, "/cancel").status_code == 409
        assert provider.writes == writes
        with harness.runtime.sessions() as db:
            assert (db.scalar(select(WriteFence)) is not None) == (
                state == "execution_uncertain"
            )


def test_first_dispatch_timeout_is_exactly_one_call(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness, TYPES[:1])
        provider.mode, provider.fail_on = "timeout", 1
        stream = events(send(harness, preview))
        assert stream[-1] == {
            "type": "result",
            "state": "execution_uncertain",
            "operations": ["execution_uncertain"],
        }
        assert provider.writes == 1
        assert status(harness, preview)["state"] == "execution_uncertain"
        assert send(harness, preview).status_code == 409
        assert provider.writes == 1


@pytest.mark.parametrize(
    "case,state", [("stale", "rejected_stale"), ("failure", "write_failed")]
)
def test_first_operation_failure_status(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, case: str, state: str
) -> None:
    from forge_api.cad_edits.domain import EditError
    from forge_api.integrations.onshape.write_client import SafeEditClient

    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        if case == "stale":
            provider.marker = "f" * 24
            provider.data["sourceMicroversion"] = provider.marker
        else:

            def fail(*_: object) -> None:
                raise EditError("unsupported_target", 422)

            monkeypatch.setattr(SafeEditClient, "check_operation", fail)
        stream = events(send(harness, preview))
        assert stream[-1] == {
            "type": "result",
            "state": state,
            "operations": [state, "skipped", "skipped"],
        }
        assert status(harness, preview) == {
            k: v for k, v in stream[-1].items() if k != "type"
        }
        assert provider.writes == 0


@pytest.mark.parametrize("count", [1, 3, 5])
def test_cancel_is_queryable_and_never_executes(harness: Harness, count: int) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness, TYPES[:count])
        calls = len(provider.calls)
        assert status(harness, preview) == {
            "state": "pending",
            "operations": ["pending"] * count,
        }
        # Users may reject/query even after an operator disables future writes.
        harness.runtime.settings.forge_cad_writes_enabled = False
        cancelled = send(harness, preview, "/cancel")
        final = {"state": "cancelled", "operations": ["skipped"] * count}
        assert cancelled.status_code == 200 and cancelled.json() == final
        private_free(final)
        assert status(harness, preview) == final
        assert send(harness, preview, "/cancel").status_code == 409
        harness.runtime.settings.forge_cad_writes_enabled = True
        assert send(harness, preview).status_code == 409
        assert len(provider.calls) == calls and provider.writes == 0
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
            row = db.get(WriteRecord, preview.proposal_id)
            assert (
                row
                and row.payload
                == PlanResult.model_validate_json(cancelled.content).model_dump_json()
            )
            assert (
                len(
                    list(
                        db.scalars(
                            select(AuditEvent).where(
                                AuditEvent.kind == "write_proposal_cancelled"
                            )
                        )
                    )
                )
                == 1
            )


@pytest.mark.parametrize("state", ["claimed", "verifying"])
def test_inflight_status_does_not_execute_or_cancel(
    harness: Harness, state: str
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            saved = plan_storage.load(row)
            plan = plan_storage.claim(
                db,
                preview.proposal_id,
                saved.plan.binding.user,
                saved.plan.binding.session,
                preview.digest,
            )
            result = PlanResult.model_validate_json(
                json.dumps(
                    {
                        "state": state,
                        "operations": [
                            "checking" if state == "claimed" else "verifying",
                            "pending",
                            "pending",
                        ],
                    }
                )
            )
            plan_storage.journal(db, plan, result)
        calls = len(provider.calls)
        assert status(harness, preview) == result.model_dump(mode="json")
        assert send(harness, preview, "/cancel").status_code == 409
        assert send(harness, preview).status_code == 409
        assert len(provider.calls) == calls and provider.writes == 0
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result


@pytest.mark.parametrize("action", ["", "/cancel"])
@pytest.mark.parametrize(
    "case",
    ["unauthenticated", "csrf", "origin", "cross_site", "owner", "session", "handle"],
)
def test_status_cancel_guard_and_existence_privacy(
    harness: Harness, action: str, case: str
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        headers = harness.headers()
        url = path(preview, action)
        expected = 403
        if case == "unauthenticated":
            harness.client.cookies.clear()
            expected = 401
        elif case == "csrf":
            headers.pop("X-CSRF-Token")
        elif case == "origin":
            headers["Origin"] = "https://synthetic.invalid"
        elif case == "cross_site":
            headers["Sec-Fetch-Site"] = "cross-site"
        elif case == "handle":
            url = "/api/modify/plans/invalid" + action
            expected = 404
        else:
            with harness.runtime.sessions.begin() as db:
                row = db.get(WriteRecord, preview.proposal_id)
                assert row
                if case == "session":
                    row.session_hash = "0" * 64
                else:
                    other = User(
                        onshape_user_id="synthetic-stranger",
                        display_name="Other",
                        stack="https://cad.onshape.com/api",
                    )
                    db.add(other)
                    db.flush()
                    row.user_id = other.id
            expected = 404
        response = (
            harness.client.post(url, headers=headers, json={})
            if action
            else harness.client.get(url, headers=headers)
        )
        assert response.status_code == expected
        if expected == 404:
            assert response.json() == {"detail": "proposal_unavailable"}
        assert provider.writes == 0


def test_progress_observer_failure_cannot_change_or_replay_execution(
    harness: Harness,
) -> None:
    provider = PlanProvider()
    calls: list[Progress] = []
    durable: list[str] = []
    with running(harness, provider):
        req, preview = prepare(harness)

        def broken(event: Progress) -> None:
            calls.append(event)
            if isinstance(event, OperationResultEvent):
                with harness.runtime.sessions() as db:
                    row = db.get(WriteRecord, preview.proposal_id)
                    assert row
                    durable.append(
                        plan_storage.result(row).operations[event.operation - 1]
                    )
            raise RuntimeError("synthetic-private-observer")

        result = plan_service.approve(
            req, harness.runtime, preview.proposal_id, preview.digest, broken
        )
        assert result.operations == ("verified_success",) * 3
        assert len(calls) == 12 and provider.writes == 3
        assert durable == ["verified_success"] * 3


def test_status_and_cancel_cannot_invoke_approval(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    calls = 0

    def forbidden(*_: object, **__: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("only the human approval route may approve")

    monkeypatch.setattr(plan_service, "approve", forbidden)
    with running(harness, provider):
        _, preview = prepare(harness)
        assert status(harness, preview)["state"] == "pending"
        assert send(harness, preview, "/cancel").status_code == 200
        assert status(harness, preview)["state"] == "cancelled"
        assert calls == 0 and provider.writes == 0


def test_status_only_retains_cancel_until_normal_purge(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        assert send(harness, preview, "/cancel").status_code == 200
        monkeypatch.setattr(storage, "now", lambda: preview.expires_at + 1)
        assert status(harness, preview)["state"] == "cancelled"
        monkeypatch.setattr(storage, "now", lambda: preview.expires_at + 901)
        assert (
            harness.client.get(path(preview), headers=harness.headers()).status_code
            == 404
        )
        assert provider.writes == 0


def test_cancellation_audit_failure_rolls_back_authority_transition(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)

        def fail(*_: object, **__: object) -> None:
            raise RuntimeError("synthetic-private-audit-failure")

        with monkeypatch.context() as patch:
            patch.setattr(plan_storage, "audit", fail)
            response = send(harness, preview, "/cancel")
        assert response.status_code == 503
        assert response.json() == {"detail": "service_unavailable"}
        assert status(harness, preview)["state"] == "pending"
        assert provider.writes == 0
        assert events(send(harness, preview))[-1]["state"] == "verified_success"
        assert provider.writes == 3


def approval_request(h: Harness, preview: PlanPreview) -> Request:
    req = request_for(h)
    body = json.dumps({"digest": preview.digest}).encode()
    scope = {
        **req.scope,
        "method": "POST",
        "path": path(preview, "/approve"),
        "query_string": b"",
    }
    scope["headers"] = [
        *req.scope["headers"],
        *[(k.lower().encode(), v.encode()) for k, v in h.headers().items()],
        (b"content-type", b"application/json"),
    ]

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


def test_disconnect_during_dispatch_keeps_backend_task_and_status(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_api.integrations.onshape.write_client import SafeEditClient

    provider = PlanProvider()
    entered, release = Event(), Event()
    original = SafeEditClient.execute_operation
    approvals = 0
    original_approve = plan_service.approve

    def approve(*args: Any, **kwargs: Any) -> PlanResult:
        nonlocal approvals
        approvals += 1
        return original_approve(*args, **kwargs)

    def dispatch(self: SafeEditClient, *args: Any) -> str:
        if provider.writes == 0:
            entered.set()
            assert release.wait(10)
        return original(self, *args)

    monkeypatch.setattr(plan_service, "approve", approve)
    monkeypatch.setattr(SafeEditClient, "execute_operation", dispatch)
    with running(harness, provider):
        _, preview = prepare(harness)
        request = approval_request(harness, preview)

        async def exercise() -> None:
            response = await plan_routes.approve(
                request, harness.runtime, preview.proposal_id
            )
            assert isinstance(response, StreamingResponse)
            assert await asyncio.to_thread(entered.wait, 5)
            tasks = set(request.app.state.plan_executions)
            assert len(tasks) == 1
            saw_first = asyncio.Event()

            async def consume() -> None:
                async for _ in response.body_iterator:
                    saw_first.set()

            consumer = asyncio.create_task(consume())
            await saw_first.wait()
            consumer.cancel()
            await asyncio.sleep(0)
            assert all(not t.cancelled() and not t.done() for t in tasks)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await consumer
            await asyncio.wait_for(asyncio.gather(*tasks), 10)

        asyncio.run(exercise())
        assert approvals == 1 and provider.writes == 3
        assert status(harness, preview)["state"] == "verified_success"
        assert send(harness, preview).status_code == 409
        assert provider.writes == 3


def test_public_event_models_are_closed_and_bounded() -> None:
    for raw in (
        {"type": "progress", "operation": 0, "total": 3, "stage": "checking"},
        {"type": "progress", "operation": 4, "total": 3, "stage": "checking"},
        {"type": "progress", "operation": 1, "total": 6, "stage": "checking"},
        {"type": "progress", "operation": 1, "total": 1, "stage": "success"},
        {"type": "operation_result", "operation": 1, "total": 1, "state": "success"},
        {"type": "error", "code": "synthetic-private"},
        {
            "type": "progress",
            "operation": 1,
            "total": 1,
            "stage": "checking",
            "payload": {},
        },
    ):
        with pytest.raises(ValidationError):
            EVENTS.validate_json(json.dumps(raw))
    buffer = plan_routes.EventBuffer()
    for _ in range(100):
        buffer.put(ProgressEvent(operation=1, total=1, stage="checking"))
    from forge_api.cad_edits.plan_events import ResultEvent

    buffer.put(ResultEvent(state="verified_success", operations=("verified_success",)))
    assert buffer.count == MAX_EVENTS and buffer.queue.qsize() == MAX_EVENTS
    assert buffer.size <= MAX_STREAM_BYTES


def test_finish_storage_failure_is_conservative_and_never_retried(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)

        def fail(*_: object, **__: object) -> None:
            raise RuntimeError("synthetic-private-persistence-error")

        monkeypatch.setattr(plan_storage, "finish", fail)
        stream = events(send(harness, preview))
        assert stream[-1] == {"type": "error", "code": "execution_uncertain"}
        assert provider.writes == 3
        assert send(harness, preview).status_code == 409
        assert status(harness, preview)["state"] == "verifying"
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        assert provider.writes == 3
