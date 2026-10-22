"""Local-only deployment gate. Own disposable DB/network; no integration calls."""

import argparse
import base64
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = (
    "postgres:18.6@sha256:"
    "5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722"
)
BLOCKED = {
    ".git",
    ".certs",
    "node_modules",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    ".DS_Store",
    "secrets",
    "data",
}
CREDENTIAL = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"(?:sk-(?:proj-)?|gsk_)[A-Za-z0-9_-]{24,}"
)


def forbidden(name: str) -> bool:
    return any(
        part in BLOCKED
        or part == ".env"
        or part.startswith((".env.", ".coverage"))
        or part.endswith(
            (".pem", ".key", ".p12", ".pfx", ".db", ".dump", ".sqlite", ".sqlite3")
        )
        for part in PurePosixPath(name).parts
    )


def run(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    source: str | None = None,
    timeout: int = 300,
) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        input=source,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        if args[:2] == ["make", "test"]:
            for node in re.findall(r"(?m)^FAILED ([^\s]+)", result.stdout):
                print("Failed test: " + node.split("[")[0], flush=True)
        # Captured Docker metadata/logs can contain env; never render them.
        raise RuntimeError(f"Deployment check command failed: {args[0]}")
    return result.stdout.strip()


def context_export(context: Path, destination: Path) -> None:
    run(
        [
            "docker",
            "build",
            "--file",
            "-",
            "--output",
            f"type=local,dest={destination}",
            str(context),
        ],
        source="FROM scratch\nCOPY . /context/\n",
    )


def check_context(work: Path) -> None:
    context_export(ROOT, work / "actual")
    actual = work / "actual/context"
    files = [path for path in actual.rglob("*") if path.is_file()]
    assert files and (actual / "package-lock.json").is_file()
    assert (actual / "apps/api/uv.lock").is_file()
    for path in files:
        name = path.relative_to(actual).as_posix()
        assert not forbidden(name), "Sensitive path entered Docker context"
        assert not path.is_symlink(), "Symlink entered Docker context"
        assert not CREDENTIAL.search(path.read_bytes()), (
            "Credential pattern in build context"
        )
    # Exercise Docker's actual ignore matcher, including allowed source subtrees.
    canary = work / "canary"
    canary.mkdir()
    (canary / ".dockerignore").write_bytes((ROOT / ".dockerignore").read_bytes())
    for prefix in (
        "",
        "apps/web/src/",
        "apps/api/src/forge_api/",
        "packages/design-system/src/",
    ):
        for name in (
            ".env",
            ".env.production",
            ".certs/local.pem",
            ".git/config",
            "node_modules/module.js",
            ".cache/private",
            ".pytest_cache/private",
            ".mypy_cache/private",
            ".ruff_cache/private",
            "test-results/private",
            "playwright-report/private",
            "private.sqlite3",
            "private.db",
            "secrets/token",
            "coverage/private",
            ".DS_Store",
        ):
            path = canary / (prefix + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("SYNTHETIC-DOCKER-EXCLUSION-CANARY")
    sentinel = canary / "apps/api/src/forge_api/sentinel.py"
    sentinel.write_text("# public synthetic source")
    context_export(canary, work / "canary-export")
    exported = work / "canary-export/context"
    assert [
        p.relative_to(exported).as_posix() for p in exported.rglob("*") if p.is_file()
    ] == ["apps/api/src/forge_api/sentinel.py"]
    print(
        "PASS Docker context: actual inputs and nested sensitive-path canaries",
        flush=True,
    )


def check_image(image: str, work: Path) -> None:
    config = json.loads(run(["docker", "image", "inspect", image]))[0]["Config"]
    assert config["User"] == "10001:10001"
    assert config["Cmd"] == ["python", "-m", "forge_api.serve"]
    assert not any(
        re.match(r"(?:DATABASE_URL|.*_KEY|.*_SECRET|ONSHAPE_CLIENT_ID)=", v)
        for v in config["Env"]
    )
    container = run(["docker", "create", image])
    try:
        archive = work / "image.tar"
        run(["docker", "export", "--output", str(archive), container])
        with tarfile.open(archive) as filesystem:
            names = set()
            for member in filesystem:
                names.add(member.name)
                parts = PurePosixPath(member.name).parts
                assert not any(
                    part in {".env", ".certs", ".git"} or part.startswith(".env.")
                    for part in parts
                ), "Local configuration in runtime filesystem"
                if member.name.startswith("app/"):
                    assert not forbidden(member.name), (
                        "Sensitive application path in runtime filesystem"
                    )
                if member.name.startswith(("app/api/", "app/web/")):
                    assert not any(
                        p in {"tests", "__fixtures__", "test-results"}
                        for p in PurePosixPath(member.name).parts
                    )
                    assert not member.name.endswith((".test.ts", ".test.tsx", ".map"))
                    if member.isfile():
                        content = filesystem.extractfile(member)
                        assert content is not None
                        assert not CREDENTIAL.search(content.read()), (
                            "Credential pattern in runtime application"
                        )
            assert {
                "app/web/index.html",
                "app/api/alembic.ini",
                "app/api/src/forge_api/main.py",
            } <= names
            assert not any(
                n.startswith(("usr/local/bin/node", "usr/local/bin/uv")) for n in names
            )
    finally:
        run(["docker", "rm", container])
    print(
        "PASS runtime image: non-root, metadata, filesystem, credentials/artifacts",
        flush=True,
    )


def wait_database(container: str) -> None:
    for _ in range(60):
        try:
            run(
                [
                    "docker",
                    "exec",
                    container,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "synthetic",
                    "-d",
                    "synthetic",
                ],
                timeout=5,
            )
            return
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError("Disposable database did not become healthy")


def smoke(image: str) -> None:
    suffix = uuid4().hex[:12]
    network, database, web = (
        f"forge-deploy-{role}-{suffix}" for role in ("net", "db", "web")
    )
    run(["docker", "network", "create", network])
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "APP_BASE_URL": "https://forge.example",
        "DATABASE_URL": f"postgresql://synthetic:synthetic-only@{database}:5432/synthetic",
        "TOKEN_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "TOKEN_ENCRYPTION_PREVIOUS_KEYS": "",
        "ONSHAPE_CLIENT_ID": "synthetic-client",
        "ONSHAPE_CLIENT_SECRET": "synthetic-only",
        "ONSHAPE_REDIRECT_URI": "https://forge.example/auth/onshape/callback",
        "SESSION_SAMESITE": "none",
        "FORGE_AI_PROVIDER": "groq",
        "GROQ_API_KEY": "",
        "OPENAI_API_KEY": "",
        "FORGE_CAD_WRITES_ENABLED": "false",
        "FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED": "false",
        "FORGE_CAD_WRITE_CONFORMANCE_PAUSE_SECONDS": "0",
        "PORT": "8765",
    }
    names = [
        "ENVIRONMENT",
        "APP_BASE_URL",
        "DATABASE_URL",
        "TOKEN_ENCRYPTION_KEY",
        "ONSHAPE_CLIENT_ID",
        "ONSHAPE_CLIENT_SECRET",
        "ONSHAPE_REDIRECT_URI",
        "SESSION_SAMESITE",
        "FORGE_CAD_WRITES_ENABLED",
        "FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED",
        "FORGE_CAD_WRITE_CONFORMANCE_PAUSE_SECONDS",
        "PORT",
    ]
    common = ["docker", "run", "--rm", "--network", network]
    for name in names:
        common.extend(["--env", name])
    try:
        run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                database,
                "--network",
                network,
                "--tmpfs",
                "/var/lib/postgresql",
                "--publish",
                "127.0.0.1::5432",
                "--env",
                "POSTGRES_USER=synthetic",
                "--env",
                "POSTGRES_PASSWORD=synthetic-only",
                "--env",
                "POSTGRES_DB=synthetic",
                POSTGRES_IMAGE,
            ]
        )
        wait_database(database)
        # The exact reviewed Railway pre-deploy operation, repeated for idempotence.
        config = json.loads((ROOT / "railway.json").read_text())
        migration = config["deploy"]["preDeployCommand"][0].split()
        for _ in range(2):
            run([*common, image, *migration], env=env)
        run(
            [*common, "--detach", "--name", web, "--publish", "127.0.0.1::8765", image],
            env=env,
        )
        binding = json.loads(run(["docker", "inspect", web]))[0]["NetworkSettings"][
            "Ports"
        ]["8765/tcp"][0]
        origin = f"http://127.0.0.1:{binding['HostPort']}"
        for _ in range(60):
            try:
                with urlopen(origin + "/health", timeout=2) as response:
                    assert json.load(response) == {
                        "status": "ok",
                        "service": "forge-api",
                    }
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("Production container startup failed")
        for path in (
            "/",
            "/extension",
            "/extension?documentId=synthetic&workspaceId=synthetic&elementId=synthetic",
        ):
            with urlopen(origin + path, timeout=5) as response:
                html = response.read().decode()
                assert 'id="root"' in html and response.status == 200
                assert (
                    response.headers["Content-Security-Policy"]
                    == "frame-ancestors https://cad.onshape.com"
                )
                assert response.headers["Referrer-Policy"] == "no-referrer"
                assert response.headers["X-Content-Type-Options"] == "nosniff"
                assert response.headers["X-Frame-Options"] is None
        asset = re.search(r'src="(/assets/[^" ]+\.js)"', html)
        assert asset
        with urlopen(origin + asset[1], timeout=5) as response:
            assert (
                response.status == 200
                and "javascript" in response.headers["Content-Type"]
            )
            bundle = response.read()
            assert not any(
                marker in bundle
                for marker in (
                    b"OnshapeSimulator",
                    b"UiLab",
                    b"SYNTHETIC-DOCKER-EXCLUSION-CANARY",
                )
            )
        for path in (
            "/docs",
            "/openapi.json",
            "/api/missing",
            "/auth/missing",
            "/.env",
        ):
            try:
                urlopen(origin + path, timeout=5).close()
            except URLError as error:
                assert getattr(error, "code", None) == 404
            else:
                raise AssertionError("Reserved path was served")
        print(
            "PASS production smoke: PORT 8765, health, SPA, assets, headers, docs/404s",
            flush=True,
        )
        # DATABASE_URL points only to this disposable DB; no integration is called.
        db_port = json.loads(run(["docker", "inspect", database]))[0][
            "NetworkSettings"
        ]["Ports"]["5432/tcp"][0]["HostPort"]
        local_url = f"postgresql+psycopg://synthetic:synthetic-only@127.0.0.1:{db_port}/synthetic"
        local_env = {
            **env,
            "DATABASE_URL": local_url,
            "WEB_BUILD_DIR": str(ROOT / "apps/web/dist"),
        }
        run(["make", "migration-check"], env=local_env)
        print("PASS make migration-check against disposable PostgreSQL", flush=True)
        test_env = {k: v for k, v in os.environ.items() if k not in names}
        test_env["FORGE_TEST_DATABASE_URL"] = local_url
        result = run(["make", "test"], env=test_env, timeout=600)
        # Test output is synthetic; show only summary lines.
        for line in result.splitlines():
            if " passed" in line or "Test Files" in line or "Tests " in line:
                print(line, flush=True)
        assert " skipped" not in result, "PostgreSQL tests must run, not skip"
        print("PASS make test including isolated real PostgreSQL tests", flush=True)
    finally:
        for container in (web, database):
            subprocess.run(
                ["docker", "rm", "--force", container], capture_output=True, check=False
            )
        run(["docker", "network", "rm", network])
        print(
            "Disposable services removed; existing services untouched",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="forge:railway-foundation")
    args = parser.parse_args()
    (ROOT / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="deployment-", dir=ROOT / ".cache"
    ) as temporary:
        work = Path(temporary)
        check_context(work)
        check_image(args.image, work)
        smoke(args.image)


if __name__ == "__main__":
    main()
