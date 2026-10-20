"""Closed explicit-command fast path over safe catalog options only.

Unknown language returns None for the existing planner. Recognized ambiguity,
invalid values and conflicts produce server-owned clarification, never a guess.
Feature labels are compared as text; no dynamic patterns, evaluation or CAD IDs.
"""

import re

from forge_api.cad_edits.plans import TargetOption

from .models import PlannerClarification, PlannerPlan, PlannerResult
from .screen import screen
from .validate import FIELD, OPERATION, ORDINALS, choices

# Patterns capture whole values; the A1 validator alone owns quantity grammar.
_PATTERNS = (
    (r"(un)?suppress (.+)", "suppression"),
    (r"set the depth of (.+?) to (.+)", "SET_EXTRUDE_DEPTH"),
    (r"set the radius of (.+?) to (.+)", "SET_FILLET_RADIUS"),
    (r"set (.+?) radius to (.+)", "SET_FILLET_RADIUS"),
    (r"set (.+?) to (.+)", "quantity"),
    (r"make (.+) (\S+ \S+) deep", "SET_EXTRUDE_DEPTH"),
    (r"(?:make )?(.+?) radius (.+)", "SET_FILLET_RADIUS"),
    (r"rename (.+?) to (.+)", "RENAME_FEATURE"),
)


def _resolve(text: str, options: tuple[TargetOption, ...]) -> tuple[TargetOption, ...]:
    value = re.sub(r"^the ", "", text, flags=re.I).casefold()
    named = tuple(o for o in options if o.label.casefold() == value)
    # A label matching a structural selector cannot silently override it.
    selector = re.fullmatch(r"(?:(\w+) )?(extrude|fillet)", value)
    selected: tuple[TargetOption, ...] = ()
    if selector:
        ordinal, kind = selector.groups()
        same = tuple(
            sorted(
                (o for o in options if o.feature_type == kind), key=lambda o: o.position
            )
        )
        if ordinal is None:
            selected = same
        elif ordinal in ORDINALS:
            index = ORDINALS[ordinal]
            if -len(same) <= index < len(same):
                selected = (same[index],)
    by_handle = {o.handle: o for o in (*named, *selected)}
    return tuple(by_handle.values())


def parse(text: str, options: tuple[TargetOption, ...]) -> PlannerResult | None:
    if screen(text) != "ok":
        return PlannerClarification(reason="unsupported_request")
    # Do not split decimal points or absorb trailing free-form instructions.
    clauses = [
        c.strip()
        for c in re.split(r"[.;](?=\s|$)|\n+|\s+and\s+", text.strip())
        if c.strip()
    ]
    if len(clauses) > 5:
        return PlannerClarification(reason="unsupported_request")
    operations = []
    seen: set[tuple[str, str]] = set()
    for clause in clauses:
        match = None
        kind = ""
        for pattern, candidate in _PATTERNS:
            match = re.fullmatch(pattern, clause, re.I)
            if match:
                kind = candidate
                break
        if match is None:
            return None
        if kind == "suppression":
            prefix, target_text = match.groups()
            kind = "SET_UNSUPPRESSED" if prefix else "SET_SUPPRESSED"
            value = ""
        else:
            target_text, value = match.groups()
        matches = _resolve(target_text.strip(), options)
        if not matches:
            return PlannerClarification(reason="no_matching_target")
        if len(matches) != 1:
            return PlannerClarification(
                reason="ambiguous_target", choices=choices(matches)
            )
        target = matches[0]
        if kind == "quantity":
            kind = (
                "SET_EXTRUDE_DEPTH"
                if target.feature_type == "extrude"
                else "SET_FILLET_RADIUS"
            )
        if kind not in target.supported_operations:
            return PlannerClarification(reason="unsupported_request")
        key = (target.handle, FIELD[kind])
        if key in seen:
            return PlannerClarification(reason="contradictory_request")
        seen.add(key)
        payload = {"type": kind, "target": target.handle}
        if kind == "RENAME_FEATURE":
            payload["new_name"] = value
        elif kind in ("SET_EXTRUDE_DEPTH", "SET_FILLET_RADIUS"):
            payload["quantity"] = value
        try:
            # A1 owns quantity/name validation; prepare rechecks applicability.
            operations.append(OPERATION.validate_python(payload))
        except ValueError:
            return PlannerClarification(reason="missing_value")
    return PlannerPlan(operations=tuple(operations)) if operations else None
