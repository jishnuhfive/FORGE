"""Run native development servers, and stop both when either exits or on Ctrl+C."""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType

ROOT = Path(__file__).resolve().parents[1]


def handle_shutdown(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(
                int(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM))
            )
        else:
            os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        process.wait()
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def main() -> int:
    signal.signal(signal.SIGTERM, handle_shutdown)
    if os.name == "nt":
        signal.signal(int(getattr(signal, "SIGBREAK", signal.SIGTERM)), handle_shutdown)
    npm = shutil.which("npm")
    uv = shutil.which("uv")
    if npm is None or uv is None:
        print(
            "Development requires npm and uv on PATH. Run setup first.", file=sys.stderr
        )
        return 1
    commands = [
        ([npm, "run", "dev:web"], ROOT),
        (
            [
                uv,
                "run",
                "--frozen",
                "uvicorn",
                "forge_api.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--no-access-log",
            ],
            ROOT / "apps/api",
        ),
    ]
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for command, cwd in commands:
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=cwd,
                    start_new_session=os.name != "nt",
                    creationflags=int(
                        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                    )
                    if os.name == "nt"
                    else 0,
                )
            )
        print(
            "Forge web: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/health",
            flush=True,
        )
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    return code if code != 0 else 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
