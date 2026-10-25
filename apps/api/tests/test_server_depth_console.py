"""The console never starts a real service or contacts a real provider in tests."""

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from server_depth_support import ServerCase
from test_server_depth_recovery import case as case

from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied

spec = importlib.util.spec_from_file_location(
    "depth_operator_console",
    Path(__file__).resolve().parents[3] / "scripts/depth_incident_operator.py",
)
assert spec and spec.loader
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)


@pytest.mark.parametrize(
    "mode", ["pass", "cancel", "short_review", "denied", "unknown"]
)
def test_one_attempt_and_sanitized_output(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    calls = []
    output: list[str] = []
    answers = iter(
        [
            "DISPOSABLE SETTLED DRAINED AUTHORIZE" if mode != "cancel" else "no",
            case.reference.review.stack,
            "",
        ]
    )

    def recover(*a: Any, **kw: Any) -> Any:
        calls.append("attempt")
        if mode == "denied":
            raise DepthRecoveryDenied("cached_read_credential_required")
        if mode == "unknown":
            raise RuntimeError("synthetic-private secret provider definition")
        return object()

    monkeypatch.setattr(console, "recover_development_depth_incident", recover)
    result = console.operator_attempt(
        case.harness.runtime,
        ask=lambda _: next(answers),
        private=lambda _: (
            "bad"
            if mode == "short_review"
            else "Synthetic upstream settlement independently reviewed"
        ),
        report=output.append,
    )
    assert result == (0 if mode == "pass" else 1)
    assert calls == ([] if mode in ("cancel", "short_review") else ["attempt"])
    assert "synthetic-private" not in str(output)
    assert "Synthetic upstream" not in str(output)
    assert output[-1].startswith("PASS" if mode == "pass" else "DENIED")


@pytest.mark.parametrize("mode", ["production", "writes"])
def test_console_cannot_start_unsafe_backend(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    settings = case.harness.runtime.settings
    if mode == "production":
        settings.environment = "production"
    else:
        settings.forge_cad_writes_enabled = True
    monkeypatch.setattr(console, "Settings", lambda: settings)
    monkeypatch.setattr(
        console, "serve_operator", lambda _: pytest.fail("must not start")
    )
    assert console.main() == 1


@pytest.mark.parametrize("mode", ["ready", "no_runtime", "cancel"])
def test_launcher_shares_actual_runtime_and_stops_its_server(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from time import sleep

    from fastapi import FastAPI

    app = FastAPI()
    app.state.auth = case.harness.runtime if mode != "no_runtime" else None
    servers = []
    configs = []

    def config(*a: Any, **kw: Any) -> object:
        configs.append(kw)
        return object()

    class Server:
        def __init__(self, _: object) -> None:
            self.started = False
            self.should_exit = False
            self.finished = False
            servers.append(self)

        def run(self) -> None:
            self.started = True
            while not self.should_exit:
                sleep(0.001)
            self.finished = True

    def attempt(runtime: object) -> int:
        assert runtime is case.harness.runtime
        if mode == "cancel":
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(console.uvicorn, "Config", config)
    monkeypatch.setattr(console.uvicorn, "Server", Server)
    monkeypatch.setattr(console, "operator_attempt", attempt)
    if mode == "cancel":
        with pytest.raises(KeyboardInterrupt):
            console.serve_operator(app)
    else:
        assert console.serve_operator(app) == (0 if mode == "ready" else 1)
    assert servers[0].finished
    assert configs[0]["host"] == "127.0.0.1" and configs[0]["access_log"] is False
