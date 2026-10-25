"""A stop before the first write is named by a closed category; budgets are per step."""

import json
from types import SimpleNamespace
from typing import Any, cast

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_cad_read import REF
from test_creation_api import BRIEF, Provider, post
from test_safe_edit import running

from forge_api.cad_create import provider as creation_provider
from forge_api.cad_create import service
from forge_api.cad_create.service import BaselineParts
from forge_api.cad_edits.domain import EditError
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord
from forge_api.integrations.onshape import write_client


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Timed(Provider):
    """Provider whose every request costs `latency` seconds on a fake clock."""

    def __init__(self, clock: Clock, latency: float = 0.0) -> None:
        super().__init__()
        self.clock = clock
        self.latency = latency
        self.fail_reads = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.clock.now += self.latency
        if self.fail_reads and request.method == "GET":
            raise httpx.ReadTimeout("synthetic")
        return super().handle(request)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    for module in (write_client, creation_provider, service):
        monkeypatch.setattr(module, "monotonic", fake)
    return fake


def stop_outcomes(harness: Harness) -> list[str]:
    with harness.runtime.sessions() as db:
        return [
            e.outcome
            for e in db.scalars(
                select(AuditEvent).where(AuditEvent.kind == "write_rejected_stale")
            )
        ]


def prepare_and_approve(
    harness: Harness, p: Timed, between: Any = None
) -> tuple[Any, str]:
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        if between:
            between()
        p.writes = 0
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
        return response, preview["proposal_id"]


def assert_closed_before_dispatch(harness: Harness, p: Timed, response: Any) -> None:
    assert response.status_code == 200, response.text
    assert response.json() == {
        "state": "rejected_stale",
        "steps": ["pending", "pending"],
    }
    assert p.writes == 0
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None
        states = [r.state for r in db.scalars(select(WriteRecord))]
        assert states.count("rejected_stale") == 1 and "claimed" not in states


def test_advanced_revision_is_named_as_a_marker_change(
    harness: Harness, clock: Clock
) -> None:
    p = Timed(clock)

    def advance() -> None:
        p.marker = "f" * 24
        p.data["sourceMicroversion"] = p.marker

    response, _ = prepare_and_approve(harness, p, advance)
    assert_closed_before_dispatch(harness, p, response)
    assert stop_outcomes(harness) == ["baseline_marker"]


def test_same_revision_with_different_content_is_named_by_category(
    harness: Harness, clock: Clock
) -> None:
    p = Timed(clock)
    response, _ = prepare_and_approve(
        harness, p, lambda: p.data.update(unknown_change=True)
    )
    assert_closed_before_dispatch(harness, p, response)
    assert stop_outcomes(harness) == ["baseline_inventory"]


def test_read_failure_is_not_reported_as_a_model_change(
    harness: Harness, clock: Clock
) -> None:
    p = Timed(clock)

    def fail() -> None:
        p.fail_reads = True

    response, _ = prepare_and_approve(harness, p, fail)
    assert_closed_before_dispatch(harness, p, response)
    assert stop_outcomes(harness) == ["pre_read_failed"]


@pytest.mark.parametrize(
    ("category", "outcome"),
    [
        ("marker", "baseline_marker"),
        ("inventory", "baseline_inventory"),
        ("configuration", "baseline_configuration"),
        ("bodies", "baseline_bodies"),
    ],
)
def test_difference_reports_only_the_first_changed_category(
    category: str, outcome: str
) -> None:
    same = {k: "a" * 64 for k in ("marker", "inventory", "configuration", "bodies")}
    approved = BaselineParts(**same)
    assert service._difference(approved, cast(Any, SimpleNamespace(parts=same))) == (
        "pre_other"
    )
    changed = {**same, category: "b" * 64}
    assert (
        service._difference(approved, cast(Any, SimpleNamespace(parts=changed)))
        == outcome
    )


def test_cause_categories_are_closed_and_carry_no_text() -> None:
    assert service._cause(RuntimeError("secret 123")) == "pre_other"
    assert service._cause(TimeoutError("x")) == "pre_read_failed"
    assert service._cause(EditError("onshape_unavailable")) == "pre_read_failed"
    assert service._cause(EditError("unheard_of")) == "pre_other"


def test_slow_but_live_reads_complete_both_steps(
    harness: Harness, clock: Clock
) -> None:
    # 27 sequential requests at 1.5 s exceed one shared 30 s ceiling; per-step
    # ceilings let a healthy, slow provider finish and still verify every step.
    p = Timed(clock, latency=1.5)
    response, _ = prepare_and_approve(harness, p)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "verified_success"
    assert p.writes == 2


def test_a_hung_capture_still_stops_before_any_write(
    harness: Harness, clock: Clock
) -> None:
    p = Timed(clock)
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        p.latency = 8.0  # five reads of 8 s exceed the 30 s per-capture ceiling
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
    assert_closed_before_dispatch(harness, p, response)
    assert stop_outcomes(harness) == ["pre_read_failed"]


class Variant(Provider):
    """Provider whose first POST acknowledgement carries an extra field."""

    def handle(self, request: httpx.Request) -> httpx.Response:
        response = super().handle(request)
        if request.method == "POST" and self.mode == "extra":
            body = json.loads(response.content)
            body["feature"]["bogusProviderKey"] = 1
            return httpx.Response(200, json=body)
        return response


def uncertain_outcomes(harness: Harness) -> list[str]:
    with harness.runtime.sessions() as db:
        return [
            e.outcome
            for e in db.scalars(
                select(AuditEvent).where(AuditEvent.kind == "write_uncertain")
            )
        ]


@pytest.mark.parametrize(
    ("mode", "label"),
    [
        ("ack", "ack_header"),
        ("extra", "ack_feature_keys"),
        ("fresh", "ver_inventory"),
        ("transport", "post_transport"),
    ],
)
def test_a_post_dispatch_stop_names_the_failed_check_and_keeps_the_fence(
    harness: Harness, mode: str, label: str
) -> None:
    p = Variant()
    p.mode = mode
    with running(harness, cast(Any, p)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
    assert response.json()["state"] == "execution_uncertain"
    assert response.json()["steps"] == ["execution_uncertain", "skipped"]
    assert p.writes == 1  # one dispatch, never retried, step two never started
    assert uncertain_outcomes(harness) == [label]
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None


def test_stop_log_carries_only_a_label_and_field_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = creation_provider.CreationClient(
        cast(Any, SimpleNamespace(_development=True)), cast(Any, None)
    )
    with caplog.at_level("WARNING", logger="forge.creation"):
        client.note_failure("ack_feature_keys", ("bogusProviderKey",))
    assert client.last_rejection == "ack_feature_keys"
    assert caplog.messages == [
        'creation_stop {"check": "ack_feature_keys", "fields": ["bogusProviderKey"]}'
    ]


def test_unsafe_field_names_are_dropped_from_the_label() -> None:
    error = creation_provider.AckRejected("ack_plane", {"ok1", "bad name", "x" * 50})
    assert error.names == ("ok1",)
