"""Check local team setup with the standard library; never repair or show secrets."""

import argparse
import errno
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
Status = Literal["PASS", "WARN", "FAIL"]
Result = tuple[Status, str]
SETTINGS = (
    "ENVIRONMENT",
    "APP_BASE_URL",
    "DATABASE_URL",
    "ONSHAPE_REDIRECT_URI",
    "ONSHAPE_CLIENT_ID",
    "ONSHAPE_CLIENT_SECRET",
    "TOKEN_ENCRYPTION_KEY",
    "SESSION_SAMESITE",
    "FORGE_AI_PROVIDER",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
)


def command(root: Path, args: list[str]) -> tuple[int, str]:
    """Capture diagnostics privately. Callers may render fixed labels/numbers only."""
    executable = shutil.which(args[0])
    if executable is None:
        return 127, ""
    try:
        result = subprocess.run(
            [executable, *args[1:]],
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except OSError, subprocess.TimeoutExpired:
        return 1, ""
    return result.returncode, result.stdout


def version_check(label: str, code: int, output: str, major: int | None) -> Result:
    version = re.search(r"(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?\b", output)
    if code != 0 or version is None:
        return "FAIL", f"{label}: missing or version check unavailable"
    found = version.group(0)
    if major is not None and int(version[1]) != major:
        return "FAIL", f"{label} {found}: unsupported; major {major} required"
    return "PASS", f"{label} {found} found"


def tool_checks(root: Path) -> list[Result]:
    results: list[Result] = []
    try:
        engines = json.loads((root / "package.json").read_text())["engines"]
        python = tomllib.loads((root / "apps/api/pyproject.toml").read_text())[
            "project"
        ]["requires-python"]
        # Fail explicitly when the declared ranges change; don't guess compatibility.
        if engines != {"node": ">=24 <25", "npm": ">=11 <12"} or python != (
            ">=3.14,<3.15"
        ):
            raise ValueError
    except OSError, ValueError, KeyError, TypeError:
        results.append(("FAIL", "Repository version requirements need doctor review"))
    for label, args, major in (
        ("Git", ["git", "--version"], None),
        ("Node", ["node", "--version"], 24),
        ("npm", ["npm", "--version"], 11),
        ("uv", ["uv", "--version"], None),
        ("Docker CLI", ["docker", "--version"], None),
        ("Docker Compose", ["docker", "compose", "version"], None),
        ("mkcert", ["mkcert", "-version"], None),
    ):
        results.append(version_check(label, *command(root, args), major))
    compatible = sys.version_info[:2] == (3, 14)
    results.append(
        (
            "PASS" if compatible else "FAIL",
            f"Python {sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro} found; 3.14.x required",
        )
    )
    code, _ = command(root, ["docker", "info", "--format", "{{.ServerVersion}}"])
    results.append(
        ("PASS", "Docker daemon reachable")
        if code == 0
        else ("FAIL", "Docker daemon unavailable; check Docker Desktop")
    )
    return results


def repository_checks(root: Path) -> list[Result]:
    results: list[Result] = []
    code, output = command(root, ["git", "rev-parse", "--show-toplevel"])
    recognized = code == 0 and Path(output.strip()).resolve() == root.resolve()
    recognized = recognized and all(
        (root / name).is_file()
        for name in ("AGENTS.md", "package.json", "apps/api/pyproject.toml")
    )
    results.append(
        ("PASS", "Forge repository")
        if recognized
        else ("FAIL", "Forge repository root not recognized")
    )
    code, output = command(root, ["git", "branch", "--show-current"])
    if code != 0:
        results.append(("FAIL", "Current Git branch unavailable"))
    elif output.strip() == "main":
        results.append(("WARN", "Current branch: main; use a branch for team work"))
    elif output.strip():
        results.append(("PASS", "Current branch: named branch (name withheld)"))
    else:
        results.append(("WARN", "Current branch: detached HEAD"))
    code, output = command(root, ["git", "status", "--porcelain"])
    results.append(
        ("FAIL", "Working tree status unavailable")
        if code != 0
        else ("WARN", "Working tree has local changes")
        if output.strip()
        else ("PASS", "Working tree clean")
    )
    for name in (".env", ".certs/localhost.pem", ".certs/localhost-key.pem"):
        code, _ = command(root, ["git", "check-ignore", "--quiet", "--", name])
        results.append(
            ("PASS", f"{name}: ignored by Git")
            if code == 0
            else ("FAIL", f"{name}: not ignored or Git check unavailable")
        )
    return results


def local_settings(root: Path) -> dict[str, str]:
    """Read simple onboarding dotenv syntax without interpolation or execution.

    Deliberately rejects multiline/ambiguous syntax instead of claiming API parity.
    Process environment takes precedence, as in the API; empty entries are ignored.
    """
    settings: dict[str, str] = {}
    for line in (root / ".env").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name, value = name.strip().upper(), value.strip()
        if not separator:
            raise ValueError
        if value.startswith(("'", '"')):
            match = re.fullmatch(r"(['\"])(.*?)\1\s*(?:#.*)?", value)
            if match is None:
                raise ValueError
            value = match[2]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if name in SETTINGS:
            settings[name] = value
    for name in SETTINGS:
        if os.environ.get(name):
            settings[name] = os.environ[name]
    return settings


def integration_checks(root: Path) -> list[Result]:
    results: list[Result] = []
    for name in (".env", ".certs/localhost.pem", ".certs/localhost-key.pem"):
        results.append(
            ("PASS", f"{name}: present")
            if (root / name).is_file()
            else ("FAIL", f"{name}: missing")
        )
    try:
        settings = local_settings(root)
    except OSError, UnicodeError, ValueError:
        results.append(
            ("FAIL", ".env unreadable or unsupported syntax; inspect locally")
        )
        return results
    for name in (
        "DATABASE_URL",
        "ONSHAPE_CLIENT_ID",
        "ONSHAPE_CLIENT_SECRET",
        "TOKEN_ENCRYPTION_KEY",
    ):
        value = settings.get(name, "").strip()
        configured = bool(value) and not value.startswith("<")
        results.append(
            (
                "PASS" if configured else "FAIL",
                f"{name}: "
                + ("configured" if configured else "missing or placeholder"),
            )
        )
    for name, expected in (
        ("ENVIRONMENT", "development"),
        ("APP_BASE_URL", "https://localhost:5173"),
        ("ONSHAPE_REDIRECT_URI", "https://localhost:5173/auth/onshape/callback"),
        ("SESSION_SAMESITE", "lax"),
    ):
        matches = settings.get(name) == expected
        results.append(
            ("PASS", f"{name}: {expected}")
            if matches
            else ("WARN", f"{name}: differs from team guide or missing; value withheld")
        )
    provider = settings.get("FORGE_AI_PROVIDER", "")
    if provider not in ("groq", "openai"):
        results.append(("FAIL", "FORGE_AI_PROVIDER: missing or unsupported"))
    else:
        results.append(("PASS", f"FORGE_AI_PROVIDER: {provider}"))
        name = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
        value = settings.get(name, "").strip()
        configured = bool(value) and not value.startswith("<")
        results.append(
            (
                "PASS" if configured else "FAIL",
                f"{name}: "
                + ("configured" if configured else "missing or placeholder"),
            )
        )
    return results


def port_check(port: int) -> Result:
    """Connect on loopback without sending data; never bind or kill a process."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as connection:
                connection.settimeout(0.3)
                code = connection.connect_ex((host, port))
        except OSError:
            return "WARN", f"Port {port}: availability could not be verified"
        if code == 0:
            return "WARN", f"Port {port} is already in use."
        if code not in (errno.ECONNREFUSED, 10061):
            return "WARN", f"Port {port}: availability could not be verified"
    return "PASS", f"Port {port}: available (no loopback listener detected)"


def run(root: Path, integration: bool = False) -> int:
    system = platform.system()
    label = {"Darwin": "macOS", "Windows": "Windows"}.get(system, "other OS")
    sections: list[tuple[str, list[Result]]] = [
        (
            "Platform",
            [
                (
                    "PASS" if system == "Darwin" else "WARN",
                    label
                    + (
                        "; supported, less host verification"
                        if system == "Windows"
                        else "; outside primary team hosts"
                        if system != "Darwin"
                        else ""
                    ),
                )
            ],
        ),
        ("Core tools", tool_checks(root)),
        ("Repository", repository_checks(root)),
    ]
    if integration:
        sections.append(("Integration", integration_checks(root)))
    sections.append(("Ports", [port_check(port) for port in (5173, 8000, 5432)]))
    print("Forge team doctor")
    for title, results in sections:
        print(f"\n{title}")
        for status, message in results:
            print(f"  {status} {message}")
    print("\nPresence checks only; API validation and real login remain separate.")
    return int(
        any(status == "FAIL" for _, results in sections for status, _ in results)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--integration", action="store_true", help="also inspect local .env and HTTPS"
    )
    args = parser.parse_args()
    return run(ROOT, integration=args.integration)


if __name__ == "__main__":
    raise SystemExit(main())
