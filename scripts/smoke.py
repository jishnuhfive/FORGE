"""Check real native server startup, health/proxy responses, and shutdown."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PORTS = (5173, 8000)


def is_listening(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.25)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    if any(is_listening(port) for port in PORTS):
        print(
            "Smoke check requires free ports 5173 and 8000; "
            "existing services were left alone."
        )
        return 1
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/dev.py")],
        cwd=ROOT,
        creationflags=int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        if os.name == "nt"
        else 0,
    )
    try:
        deadline = time.monotonic() + 20
        while not all(is_listening(port) for port in PORTS):
            if process.poll() is not None:
                raise RuntimeError("Development servers exited during startup")
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Development servers did not start within 20 seconds"
                )
            time.sleep(0.2)
        expected = {"status": "ok", "service": "forge-api"}
        for url in (
            "http://127.0.0.1:8000/health",
            "http://127.0.0.1:5173/api/health",
        ):
            with urlopen(url, timeout=5) as response:
                if response.status != 200 or json.load(response) != expected:
                    raise RuntimeError("Health/proxy contract failed")
        with urlopen("http://127.0.0.1:5173", timeout=5) as response:
            if "Forge — AI engineering inside Onshape" not in response.read().decode():
                raise RuntimeError("Web HTML did not contain the expected title")
        print("PASS: real web/API startup, health response, and Vite API proxy.")
    except (RuntimeError, URLError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if process.poll() is None:
            process.send_signal(
                int(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM))
                if os.name == "nt"
                else signal.SIGTERM
            )
            process.wait(timeout=15)
    if any(is_listening(port) for port in PORTS):
        print("FAIL: development server remained after shutdown.", file=sys.stderr)
        return 1
    print("PASS: both development servers stopped cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
