"""Privileged local development console for ONE partial creation incident.

Never an API, AI tool or production mode. Starts the normal loopback backend
without reload. Use the normal UI first so this process owns a cached read
credential; the console never refreshes or exports one. All writers must be
stopped and CAD writes must be OFF. It performs GET reads only.

  inspect  read-only report of the sanitized current Part Studio evidence
  settle   one attempt to close the exact incident after a typed confirmation
"""

import sys
import time
from collections.abc import Callable
from getpass import getpass
from threading import Thread

import uvicorn
from fastapi import FastAPI
from pydantic import ValidationError

from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_create.settlement import (
    CONFIRMATION,
    Observation,
    SettlementDenied,
    SettlementReview,
    inspect_incident,
    settle_incident,
)
from forge_api.core.config import Settings
from forge_api.main import create_app


def show(observation: Observation, report: Callable[[str], None]) -> None:
    report(f"features_in_part_studio={observation.feature_count}")
    report(f"solid_bodies={observation.body_count}")
    report(f"captures_taken={observation.captures}")
    report(f"evidence_stable_two_consecutive_captures={observation.stable}")
    if observation.instability:
        report(f"evidence_instability={observation.instability}")
        if observation.instability_path:
            report("instability_path=" + ".".join(observation.instability_path))
    report(f"revision_advanced_since_approval={observation.revision_advanced}")
    report(
        f"expected_sketch_present_and_healthy={observation.sketch_named_and_healthy}"
    )
    report(f"acknowledgement_check_on_current_sketch={observation.ack_check or 'pass'}")
    if observation.ack_chain:
        report("acknowledgement_check_chain=" + ",".join(observation.ack_chain))
    if observation.ack_fields:
        report("unrecognized_provider_fields=" + ",".join(observation.ack_fields))
    report(f"settlement_blocker={observation.denial or 'none'}")


def operator_attempt(
    runtime: AuthRuntime,
    mode: str,
    ask: Callable[[str], str] = input,
    private: Callable[[str], str] = getpass,
    report: Callable[[str], None] = print,
) -> int:
    settings = runtime.settings
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        report("DENIED development_writes_off_required")
        return 1
    report("Confirm writers drained and Part Studio reviewed in Onshape by a human.")
    report("This console performs GET reads only and never edits CAD.")
    try:
        review = SettlementReview(
            operator_authorized=ask("Type AUTHORIZE to continue: ") == "AUTHORIZE",
            disposable_fixture=ask("Is the document disposable? (yes): ") == "yes",
            writers_drained=ask("All writers stopped/drained? (yes): ") == "yes",
            upstream_settled=ask("You reviewed the Onshape state? (yes): ") == "yes",
            acknowledgement="",
            settlement_review=private("Independent review note (private): "),
            stack=ask("Reviewed stack URL (exact): "),
            company_id=ask("Reviewed company ID (empty for personal stack): ") or None,
        )
        observation = inspect_incident(runtime, review)
        show(observation, report)
        if mode == "inspect":
            return 0
        if observation.denial is not None:
            report("DENIED " + observation.denial)
            return 1
        report("To close this exact incident, paste this statement exactly:")
        report(CONFIRMATION)
        review = review.model_copy(update={"acknowledgement": ask("> ")})
        settle_incident(runtime, review)
    except ValidationError:
        report("DENIED invalid_operator_review")
        return 1
    except SettlementDenied as error:
        report("DENIED " + str(error.args[0]))
        return 1
    except Exception:
        report("DENIED completion_unconfirmed_no_retry")
        return 1
    report("PASS incident_closed original_execution_outcome=execution_uncertain")
    return 0


def serve_operator(app: FastAPI, mode: str) -> int:
    """The console and the real lifespan runtime share one process and cache."""
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
        print("Use the normal UI now (read access) so this process caches a token.")
        return operator_attempt(runtime, mode)
    finally:
        server.should_exit = True
        worker.join(timeout=15)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in ("inspect", "settle"):
        print("usage: creation_incident_operator.py inspect|settle")
        return 2
    try:
        settings = Settings()
    except Exception:
        print("DENIED configuration_unavailable")
        return 1
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        print("DENIED development_writes_off_required")
        return 1
    try:
        return serve_operator(create_app(settings), mode)
    except EOFError, KeyboardInterrupt:
        print("DENIED operator_cancelled_no_retry")
        return 1
    except Exception:
        print("DENIED local_operator_failure_no_retry")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
