"""Privileged local development console; never an API, AI tool or production mode.

Starts the normal loopback backend without reload, preserving configured origins.
Use the normal UI to populate its read-token cache; this console never refreshes a
credential. All other writers must be stopped/drained before the single attempt.
"""

import time
from collections.abc import Callable
from getpass import getpass
from threading import Thread

import uvicorn
from fastapi import FastAPI
from pydantic import ValidationError

from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.depth_contracts import (
    DepthRecoveryDenied,
    DevelopmentIncidentReview,
)
from forge_api.cad_edits.depth_recovery import recover_development_depth_incident
from forge_api.core.config import Settings
from forge_api.main import create_app


def operator_attempt(
    runtime: AuthRuntime,
    ask: Callable[[str], str] = input,
    private: Callable[[str], str] = getpass,
    report: Callable[[str], None] = print,
) -> int:
    """Exactly one guarded invocation; no retries or private output."""
    settings = runtime.settings
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        report("DENIED development_writes_off_required")
        return 1
    report(
        "Review the unique owned disposable depth incident and server-attested policy."
    )
    report("Confirm all writers OFF/drained; independently review upstream settlement.")
    report("Use normal UI read access first; recovery cannot refresh a token.")
    if ask("Type DISPOSABLE SETTLED DRAINED AUTHORIZE to attempt once: ") != (
        "DISPOSABLE SETTLED DRAINED AUTHORIZE"
    ):
        report("DENIED operator_review_required")
        return 1
    try:
        review = DevelopmentIncidentReview(
            operator_authorized=True,
            server_attested_policy_accepted=True,
            disposable_fixture=True,
            writers_drained=True,
            upstream_settled=True,
            settlement_review=private("Independent settlement review (private): "),
            stack=ask("Reviewed stack URL (exact): "),
            company_id=ask("Reviewed company ID (empty for personal stack): ") or None,
        )
        recover_development_depth_incident(runtime, review)
    except ValidationError:
        report("DENIED invalid_operator_review")
        return 1
    except DepthRecoveryDenied as error:
        report("DENIED " + str(error.args[0]))
        return 1
    except Exception:
        report("DENIED completion_unconfirmed_no_retry")
        return 1
    report("PASS closure_confirmed original_execution_outcome=execution_uncertain")
    return 0


def serve_operator(app: FastAPI) -> int:
    """The console and actual lifespan runtime share one process/cache."""
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=8000, access_log=False)
    )
    worker = Thread(target=server.run, daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 15
        while worker.is_alive() and not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            print("DENIED local_backend_unavailable")
            return 1
        runtime = app.state.auth
        if not isinstance(runtime, AuthRuntime):
            print("DENIED local_runtime_unavailable")
            return 1
        return operator_attempt(runtime)
    finally:
        server.should_exit = True
        worker.join(timeout=15)


def main() -> int:
    try:
        settings = Settings()
    except Exception:
        print("DENIED configuration_unavailable")
        return 1
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        print("DENIED development_writes_off_required")
        return 1
    try:
        return serve_operator(create_app(settings))
    except EOFError, KeyboardInterrupt:
        print("DENIED operator_cancelled_no_retry")
        return 1
    except Exception:
        print("DENIED local_operator_failure_no_retry")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
