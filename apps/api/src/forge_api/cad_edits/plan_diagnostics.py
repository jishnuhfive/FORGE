"""Development-only closed verification stages; never accepts exception/data text."""

import logging
from typing import Literal

Stage = Literal["post_read", "operation_compare", "deadline", "authority"]
DispatchStage = Literal[
    "request_preflight",
    "provider_exchange",
    "ack_skew",
    "ack_feature_envelope",
    "ack_target_identity",
    "ack_fingerprint",
    "ack_marker_shape",
    "ack_marker_advance",
    "ack_journal",
]
logger = logging.getLogger("forge.modify.verification")


def emit(development: bool, stage: Stage, passed: bool) -> None:
    if development:
        logger.warning(
            "a2_verify stage=%s result=%s", stage, "pass" if passed else "fail"
        )


def emit_dispatch(development: bool, stage: DispatchStage, passed: bool) -> None:
    if development:
        logger.warning(
            "a2_dispatch stage=%s result=%s", stage, "pass" if passed else "fail"
        )
