"""Complete fixed final checks; no relaxed definitions or inferred provider state."""

import logging
from typing import Literal

from forge_api.auth.security import AuditOutcome

from .domain import Baseline

FinalCheck = Literal[
    "serialization",
    "library",
    "target_identity",
    "acknowledged_revision",
    "definitions",
    "parent_suppression",
    "configured_suppression",
    "deadline",
]
Stage = Literal["provider_ack", "post_read", "final_compare", "final_authority"]
Failure = Literal[
    "verify_serialization",
    "verify_library",
    "verify_target_identity",
    "verify_ack_revision",
    "verify_definitions",
    "verify_parent",
    "verify_configured",
    "verify_deadline",
    "verify_provider_ack",
    "verify_post_read",
    "verify_authority",
    "verify_internal",
]

logger = logging.getLogger("forge.onshape.safe_edit")


def final_checks(
    baseline: Baseline, after: Baseline, marker: str, elapsed: float
) -> dict[FinalCheck, bool]:
    # Evaluate every comparison before deciding, rather than losing later failures
    # behind a short-circuiting expression. Keep all existing semantic requirements.
    return {
        "serialization": after.serialization == baseline.serialization,
        "library": after.library == baseline.library,
        "target_identity": after.feature_id == baseline.feature_id,
        "acknowledged_revision": after.microversion == marker,
        "definitions": after.definitions == baseline.definitions,
        "parent_suppression": after.parent_suppression_evidence
        == baseline.parent_suppression_evidence,
        "configured_suppression": after.configured_suppression_evidence
        == baseline.configured_suppression_evidence,
        "deadline": 0 <= elapsed <= 30,
    }


def failures(checks: dict[FinalCheck, bool]) -> tuple[Failure, ...]:
    codes: dict[FinalCheck, Failure] = {
        "serialization": "verify_serialization",
        "library": "verify_library",
        "target_identity": "verify_target_identity",
        "acknowledged_revision": "verify_ack_revision",
        "definitions": "verify_definitions",
        "parent_suppression": "verify_parent",
        "configured_suppression": "verify_configured",
        "deadline": "verify_deadline",
    }
    return tuple(codes[name] for name, passed in checks.items() if not passed)


def stage_failure(stage: Stage) -> Failure:
    codes: dict[Stage, Failure] = {
        "provider_ack": "verify_provider_ack",
        "post_read": "verify_post_read",
        "final_compare": "verify_internal",
        "final_authority": "verify_authority",
    }
    return codes[stage]


def emit(
    development: bool,
    stage: Stage,
    check: Literal["validation", "projection", "authority", "internal"] | FinalCheck,
    passed: bool,
) -> None:
    if development:
        logger.warning(
            "safe_edit_verify stage=%s check=%s result=%s",
            stage,
            check,
            "pass" if passed else "fail",
        )


def audit_outcome(failure: Failure) -> AuditOutcome:
    return failure
