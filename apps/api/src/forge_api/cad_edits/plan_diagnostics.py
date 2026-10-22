"""Development-only closed verification stages; never accepts exception/data text."""

import logging
from typing import Literal

Stage = Literal["post_read", "operation_compare", "deadline", "authority"]
logger = logging.getLogger("forge.modify.verification")


def emit(development: bool, stage: Stage, passed: bool) -> None:
    if development:
        logger.warning(
            "a2_verify stage=%s result=%s", stage, "pass" if passed else "fail"
        )
