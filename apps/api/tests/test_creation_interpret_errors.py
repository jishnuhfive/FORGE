"""Provider failures during interpretation say what they are, not 'rewrite'."""

from typing import Any, cast

import pytest
from conftest import Harness
from test_creation_api import Provider, post
from test_safe_edit import running

from forge_api.ai.models import AiError, ErrorCode
from forge_api.cad_create import routes


def interpret_with(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> Any:
    async def boom(*_: Any, **__: Any) -> Any:
        raise error

    monkeypatch.setattr(routes, "interpret", boom)
    with running(harness, cast(Any, Provider())):
        return post(
            harness, "/api/create/interpret", {"request": "a 60 by 40 by 10 mm plate"}
        )


@pytest.mark.parametrize(
    ("code", "status", "detail"),
    [
        ("invalid_response", 502, "plan_unavailable"),
        ("incomplete", 502, "plan_unavailable"),
        ("refused", 502, "plan_unavailable"),
        ("rate_limited", 429, "rate_limited"),
        ("quota_unavailable", 503, "quota_unavailable"),
        ("capacity_unavailable", 503, "capacity_unavailable"),
        ("authentication_failed", 503, "authentication_failed"),
        ("connection_unavailable", 503, "connection_unavailable"),
        ("not_configured", 503, "not_configured"),
        ("timeout", 504, "timeout"),
    ],
)
def test_each_provider_failure_keeps_its_own_closed_code(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    code: ErrorCode,
    status: int,
    detail: str,
) -> None:
    response = interpret_with(harness, monkeypatch, AiError(code))
    assert response.status_code == status
    assert response.json()["detail"] == detail
    assert response.headers["cache-control"] == "no-store"


def test_a_rate_limit_defers_the_next_interpretation(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = interpret_with(harness, monkeypatch, AiError("rate_limited", 17))
    assert first.status_code == 429
    assert first.json()["retry_after_seconds"] == 17
    assert first.headers["retry-after"] == "17"
    again = interpret_with(harness, monkeypatch, AiError("rate_limited", 17))
    assert again.status_code == 429


def test_a_timeout_error_is_a_timeout_not_a_rewrite_request(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = interpret_with(harness, monkeypatch, TimeoutError())
    assert response.status_code == 504 and response.json()["detail"] == "timeout"


@pytest.mark.parametrize("flag", [False, True])
def test_interpretation_does_not_depend_on_the_write_flag(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, flag: bool
) -> None:
    from forge_api.cad_create.planner import plan_creation

    async def ok(*_: Any, **__: Any) -> Any:
        return plan_creation({"outcome": "unsupported", "reason": "unsupported_object"})

    monkeypatch.setattr(routes, "interpret", ok)
    harness.runtime.settings.forge_cad_writes_enabled = flag
    with running(harness, cast(Any, Provider())):
        response = post(harness, "/api/create/interpret", {"request": "x"})
    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"
