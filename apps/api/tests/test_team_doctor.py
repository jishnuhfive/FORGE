"""Synthetic host checks; never read real integration settings or start services."""

import errno
import importlib
import socket
import subprocess
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from forge_api.core.config import REPOSITORY_ROOT


@pytest.fixture
def doctor(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(REPOSITORY_ROOT / "scripts"))
    module = importlib.import_module("team_doctor")
    for name in module.SETTINGS:
        monkeypatch.delenv(name, raising=False)
    return module


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for name in ("AGENTS.md", "package.json", "apps/api/pyproject.toml"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPOSITORY_ROOT / name).read_bytes())
    return tmp_path


def configure(root: Path) -> list[str]:
    secrets = [f"SYNTHETIC-PRIVATE-{index}" for index in range(6)]
    settings = {
        "ENVIRONMENT": "development",
        "APP_BASE_URL": "https://localhost:5173",
        "ONSHAPE_REDIRECT_URI": "https://localhost:5173/auth/onshape/callback",
        "SESSION_SAMESITE": "lax",
        "FORGE_AI_PROVIDER": "groq",
        "GROQ_API_KEY": secrets[0],
        "ONSHAPE_CLIENT_SECRET": secrets[1],
        "TOKEN_ENCRYPTION_KEY": secrets[2],
        "DATABASE_URL": f"postgresql+psycopg://user:{secrets[3]}@localhost/db",
        "ONSHAPE_CLIENT_ID": secrets[4],
        "OPENAI_API_KEY": secrets[5],
    }
    (root / ".env").write_text("\n".join(f"{k}={v}" for k, v in settings.items()))
    (root / ".certs").mkdir()
    for name in ("localhost.pem", "localhost-key.pem"):
        (root / ".certs" / name).write_text("SYNTHETIC-CERTIFICATE")
    return secrets


@pytest.mark.parametrize(
    ("label", "code", "output", "major", "status"),
    [
        ("Node", 0, "v24.99.1", 24, "PASS"),
        ("Node", 0, "v25.0.0", 24, "FAIL"),
        ("Node", 0, "v22.0.0", 24, "FAIL"),
        ("npm", 0, "11.1.0", 11, "PASS"),
        ("npm", 0, "12.0.0", 11, "FAIL"),
        ("Git", 127, "", None, "FAIL"),
        ("Git", 0, "PRIVATE-unrecognized", None, "FAIL"),
    ],
)
def test_versions(
    doctor: ModuleType,
    label: str,
    code: int,
    output: str,
    major: int | None,
    status: str,
) -> None:
    result = doctor.version_check(label, code, output, major)
    assert result[0] == status
    assert "PRIVATE" not in result[1]


def test_integration_presence_and_secret_safety(doctor: ModuleType, root: Path) -> None:
    secrets = configure(root)
    results = doctor.integration_checks(root)
    assert all(status == "PASS" for status, _ in results)
    text = str(results)
    for secret in secrets:
        assert secret not in text
    for name in ("GROQ_API_KEY", "ONSHAPE_CLIENT_SECRET", "TOKEN_ENCRYPTION_KEY"):
        assert ("PASS", f"{name}: configured") in results


@pytest.mark.parametrize(
    "name", ["GROQ_API_KEY", "ONSHAPE_CLIENT_SECRET", "TOKEN_ENCRYPTION_KEY"]
)
@pytest.mark.parametrize("value", ["", "<developer key>", "   "])
def test_missing_or_placeholder_key(
    doctor: ModuleType, root: Path, name: str, value: str
) -> None:
    configure(root)
    with (root / ".env").open("a") as stream:
        stream.write(f"\n{name}={value}\n")
    assert ("FAIL", f"{name}: missing or placeholder") in doctor.integration_checks(
        root
    )


@pytest.mark.parametrize(
    "name", [".env", ".certs/localhost.pem", ".certs/localhost-key.pem"]
)
def test_missing_integration_file(doctor: ModuleType, root: Path, name: str) -> None:
    configure(root)
    (root / name).unlink()
    assert ("FAIL", f"{name}: missing") in doctor.integration_checks(root)


@pytest.mark.parametrize("value", ["unknown-PRIVATE", ""])
def test_invalid_provider(doctor: ModuleType, root: Path, value: str) -> None:
    configure(root)
    with (root / ".env").open("a") as stream:
        stream.write(f"\nFORGE_AI_PROVIDER={value}")
    results = doctor.integration_checks(root)
    assert ("FAIL", "FORGE_AI_PROVIDER: missing or unsupported") in results
    assert "PRIVATE" not in str(results)


def test_openai_explicit_selection(doctor: ModuleType, root: Path) -> None:
    configure(root)
    with (root / ".env").open("a") as stream:
        stream.write("\nFORGE_AI_PROVIDER=openai\nGROQ_API_KEY=\n")
    results = doctor.integration_checks(root)
    assert ("PASS", "OPENAI_API_KEY: configured") in results
    assert not any("GROQ_API_KEY" in message for _, message in results)


def test_dotenv_and_process_precedence(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(root)
    with (root / ".env").open("a") as stream:
        stream.write('\nexport GROQ_API_KEY="quoted-private" # comment\n')
    assert doctor.local_settings(root)["GROQ_API_KEY"] == "quoted-private"
    monkeypatch.setenv("GROQ_API_KEY", "process-private")
    assert doctor.local_settings(root)["GROQ_API_KEY"] == "process-private"
    monkeypatch.setenv("GROQ_API_KEY", "")
    assert doctor.local_settings(root)["GROQ_API_KEY"] == "quoted-private"


def test_bad_dotenv_and_urls_never_echo_values(doctor: ModuleType, root: Path) -> None:
    configure(root)
    with (root / ".env").open("a") as stream:
        stream.write("\nAPP_BASE_URL=https://user:PRIVATE@localhost/?token=PRIVATE\n")
        stream.write("ONSHAPE_REDIRECT_URI=PRIVATE\nSESSION_SAMESITE=PRIVATE\n")
    results = doctor.integration_checks(root)
    assert "PRIVATE" not in str(results)
    assert any(status == "WARN" for status, _ in results)
    with (root / ".env").open("a") as stream:
        stream.write('BROKEN="PRIVATE\n')
    results = doctor.integration_checks(root)
    assert results[-1][0] == "FAIL"
    assert "PRIVATE" not in str(results)


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("ignored", [False, True])
def test_repository_state(
    doctor: ModuleType,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    dirty: bool,
    ignored: bool,
) -> None:
    def command(_root: Path, args: list[str]) -> tuple[int, str]:
        if args[1] == "rev-parse":
            return 0, str(root)
        if args[1] == "branch":
            return 0, "feature/PRIVATE"
        if args[1] == "status":
            return 0, " M PRIVATE" if dirty else ""
        return (0 if ignored else 1), ""

    monkeypatch.setattr(doctor, "command", command)
    results = doctor.repository_checks(root)
    assert ("PASS", "Forge repository") in results
    assert (
        ("WARN", "Working tree has local changes") in results
        if dirty
        else ("PASS", "Working tree clean") in results
    )
    assert (
        ("PASS", ".env: ignored by Git") in results
        if ignored
        else ("FAIL", ".env: not ignored or Git check unavailable") in results
    )
    assert "PRIVATE" not in str(results)


@pytest.mark.parametrize("code", [0, errno.ECONNREFUSED, 10061, 10060])
def test_port_states(
    doctor: ModuleType, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    connection = MagicMock()
    connection.__enter__.return_value.connect_ex.return_value = code
    monkeypatch.setattr(socket, "socket", MagicMock(return_value=connection))
    status, message = doctor.port_check(5173)
    assert status == ("PASS" if code in (errno.ECONNREFUSED, 10061) else "WARN")
    if code == 0:
        assert message == "Port 5173 is already in use."
    connection.bind.assert_not_called()


def test_port_error(doctor: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "socket", MagicMock(side_effect=OSError("PRIVATE")))
    assert doctor.port_check(8000) == (
        "WARN",
        "Port 8000: availability could not be verified",
    )


@pytest.mark.parametrize("system", ["Darwin", "Windows"])
def test_safe_full_report(
    doctor: ModuleType,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    system: str,
) -> None:
    secrets = configure(root)
    monkeypatch.setattr(doctor.platform, "system", lambda: system)
    monkeypatch.setattr(doctor, "tool_checks", lambda _: [("PASS", "Tools")])
    monkeypatch.setattr(doctor, "repository_checks", lambda _: [("PASS", "Repository")])
    monkeypatch.setattr(
        doctor, "port_check", lambda port: ("WARN", f"Port {port} in use")
    )
    assert doctor.run(root, integration=True) == 0
    output = capsys.readouterr().out
    assert ("PASS macOS" if system == "Darwin" else "WARN Windows") in output
    for secret in secrets:
        assert secret not in output
    before = (root / ".env").read_bytes()
    assert doctor.run(root) == 0
    assert "Integration" not in capsys.readouterr().out
    assert (root / ".env").read_bytes() == before


def test_docker_unavailable_and_python_version(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor, "command", lambda *_: (1, "PRIVATE"))
    results = doctor.tool_checks(root)
    assert ("FAIL", "Docker daemon unavailable; check Docker Desktop") in results
    assert any(
        "Python 3.14" in message and status == "PASS" for status, message in results
    )
    assert "PRIVATE" not in str(results)


@pytest.mark.parametrize("failure", ["missing", "timeout", "oserror"])
def test_command_failures_are_private(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    monkeypatch.setattr(
        doctor.shutil, "which", lambda _: None if failure == "missing" else "npm.cmd"
    )
    runner = MagicMock(
        side_effect=(
            subprocess.TimeoutExpired("PRIVATE", 10)
            if failure == "timeout"
            else OSError("PRIVATE")
        )
    )
    monkeypatch.setattr(subprocess, "run", runner)
    assert doctor.command(root, ["npm", "--version"]) == (
        127 if failure == "missing" else 1,
        "",
    )


def test_windows_command_resolution(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _: "C:/tools/npm.cmd")
    runner = MagicMock(
        return_value=subprocess.CompletedProcess([], 0, "11.19.0", "PRIVATE")
    )
    monkeypatch.setattr(subprocess, "run", runner)
    assert doctor.command(root, ["npm", "--version"]) == (0, "11.19.0")
    args, kwargs = runner.call_args
    assert args[0] == ["C:/tools/npm.cmd", "--version"]
    assert kwargs.get("shell", False) is False
    assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"


def test_fail_exit_status(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor, "tool_checks", lambda _: [("FAIL", "Missing tool")])
    monkeypatch.setattr(doctor, "repository_checks", lambda _: [])
    monkeypatch.setattr(doctor, "port_check", lambda _: ("PASS", "Available"))
    assert doctor.run(root) == 1


def test_requirements_drift(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (root / "package.json").write_text('{"engines":{"node":">=25"}}')
    monkeypatch.setattr(doctor, "command", lambda *_: (1, ""))
    assert (
        "FAIL",
        "Repository version requirements need doctor review",
    ) in doctor.tool_checks(root)


def test_unsupported_python(
    doctor: ModuleType, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    info = MagicMock(major=3, minor=13, micro=9)
    info.__getitem__.return_value = (3, 13)
    monkeypatch.setattr(doctor, "sys", MagicMock(version_info=info))
    monkeypatch.setattr(doctor, "command", lambda *_: (1, ""))
    assert ("FAIL", "Python 3.13.9 found; 3.14.x required") in doctor.tool_checks(root)
