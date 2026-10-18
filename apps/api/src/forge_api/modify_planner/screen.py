"""Deterministic pre-screen: refuse or reject obvious non-plans before any model call.

This saves provider quota and keeps unsupported work out of the planner entirely.
It is intentionally conservative: when it cannot tell, the request goes on to the
model and then to the same server-side validation.
"""

import re
from typing import Literal

from forge_api.ai.policy import blocked

Screen = Literal["ok", "unsupported", "refused"]
# Anything other than the five A1 operations, plus attempts at API/script access.
_UNSUPPORTED = re.compile(
    r"\b(?:delete|remove\s+the\s+(?:feature|extrude|fillet|sketch)|loft|sweep|"
    r"revolve|assembl\w*|mates?|featurescript|"
    r"(?:create|add|make|draw|drill|insert)\s+(?:me\s+)?(?:a\s+|an\s+|the\s+)?"
    r"(?:new\s+)?(?:sketch|hole|pocket|rib|boss|pattern|mate|assembly|loft|sweep|"
    r"feature|part|body)|"
    r"stronger|aerodynamic|lighter|optimi[sz]e|"
    r"(?:fix|repair|redo|redesign)\s+(?:the\s+)?(?:whole|entire|model)|"
    r"(?:post|put|patch)\s+(?:this|the|a)\b|\bapi\b|\bpayload\b|\burl\b|\bcurl\b)",
    re.IGNORECASE,
)


def screen(request: str) -> Screen:
    if blocked(request):
        return "refused"
    if _UNSUPPORTED.search(request):
        return "unsupported"
    return "ok"
