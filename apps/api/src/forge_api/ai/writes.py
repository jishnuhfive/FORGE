"""Server-owned Phase 6 capability statements, never CAD edit instructions."""

import re

from .models import Fact

READ_ONLY = "Forge is currently read-only and can't modify CAD yet."
WRITE_LIMITATION = (
    READ_ONLY + " I can inspect the current model and explain or propose how "
    "a change could be made."
)
NO_WRITES = "Forge performed no CAD writes for this request."
WIDTH_UNKNOWN = (
    "The captured evidence does not identify a verified width-driving dimension, "
    "so I cannot safely identify which parameter to edit."
)
DIMENSION_UNKNOWN = (
    "The captured evidence does not identify a verified controlling dimension "
    "or edit target, so I cannot safely identify which parameter to edit."
)


def write_request(prompt: str) -> bool:
    # Explicit request routing, never permission. Anchor the action so discussing
    # an Extrude feature or a possible change stays on the normal read/tool path.
    return bool(
        re.search(
            r"^\s*(?:(?:please|forge)[,\s]+)?"
            r"(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?|"
            r"i\s+(?:want|need|would\s+like)\s+you\s+to\s+|"
            r"use\s+(?:post|put|patch|delete)\s+to\s+)?"
            r"(?:make(?!\s+sense\b)|modify|change|edit|resize|widen|increase|"
            r"decrease|delete|remove|create|add|extrude|fillet|chamfer|move|"
            r"rotate|scale|set|adjust)\b",
            prompt,
            re.I,
        )
        and re.search(
            r"\b(cad|model|design|part|body|solid|sketch|feature|face|edge|hole|"
            r"width|wider|height|length|dimension|diameter|thickness|extrusion)\b",
            prompt,
            re.I,
        )
    )


def write_facts(prompt: str) -> list[Fact]:
    return [
        Fact(id="write_capability", statement=WRITE_LIMITATION, status="verified"),
        Fact(id="no_cad_writes", statement=NO_WRITES, status="verified"),
        Fact(
            id="write_target_unknown",
            statement=WIDTH_UNKNOWN
            if re.search(r"\b(width|wider|widen)\b", prompt, re.I)
            else DIMENSION_UNKNOWN,
            status="unknown",
        ),
    ]
