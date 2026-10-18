"""Deterministic validation of planner output. The model is never trusted.

Everything the model emits is checked against the server's own catalog and then
converted into A1's strict operation types, reusing A1's quantity and name
validators. Ambiguity and contradiction are answered by clarifying, never guessing.
"""

import re
from collections.abc import Iterable

from pydantic import TypeAdapter, ValidationError

from forge_api.cad_edits.plans import ModifyOperation, TargetOption

from .models import (
    MAX_CANDIDATES,
    Choice,
    PlannerClarification,
    PlannerPlan,
    PlannerResult,
    WireOperation,
    WirePlan,
)

OPERATION: TypeAdapter[ModifyOperation] = TypeAdapter(ModifyOperation)
# Operations that change the same field of the same target conflict.
FIELD = {
    "SET_SUPPRESSED": "suppression",
    "SET_UNSUPPRESSED": "suppression",
    "RENAME_FEATURE": "name",
    "SET_EXTRUDE_DEPTH": "depth",
    "SET_FILLET_RADIUS": "radius",
}
ORDINALS = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
    "last": -1,
    "final": -1,
}
_ORDINAL = re.compile(
    r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|last|final)\b",
    re.IGNORECASE,
)
_POSITION = re.compile(r"\bposition\s*\d+|#\s*\d+", re.IGNORECASE)


class PlannerError(Exception):
    """The model's output was not a valid plan. Carries no model content."""


def choices(options: Iterable[TargetOption]) -> tuple[Choice, ...]:
    unique = {o.handle: o for o in options}.values()
    return tuple(
        Choice(label=o.label, feature_type=o.feature_type, position=o.position)
        for o in list(unique)[:MAX_CANDIDATES]
    )


def _typed(item: WireOperation) -> ModifyOperation:
    """Shape-check the flat wire operation, then let A1 validate every value."""
    payload: dict[str, str] = {"type": item.type, "target": item.target}
    if item.type == "RENAME_FEATURE":
        if item.quantity or not item.new_name:
            raise PlannerError
        payload["new_name"] = item.new_name
    elif item.type in ("SET_EXTRUDE_DEPTH", "SET_FILLET_RADIUS"):
        if item.new_name or not item.quantity:
            raise PlannerError
        payload["quantity"] = item.quantity
    elif item.quantity or item.new_name:
        raise PlannerError
    try:
        return OPERATION.validate_python(payload)
    except ValidationError:
        raise PlannerError from None


def _conflicts(
    pairs: list[tuple[TargetOption, ModifyOperation]],
) -> tuple[list[tuple[TargetOption, ModifyOperation]], bool]:
    seen: dict[tuple[str, str], ModifyOperation] = {}
    kept: list[tuple[TargetOption, ModifyOperation]] = []
    for target, operation in pairs:
        key = (target.handle, FIELD[operation.type])
        prior = seen.get(key)
        if prior is None:
            seen[key] = operation
            kept.append((target, operation))
        elif prior != operation:
            # Two different requests for the same field: never pick one silently.
            return kept, True
        # An exact repeat is dropped, consistently, preserving order.
    return kept, False


def _ambiguity(
    pairs: list[tuple[TargetOption, ModifyOperation]],
    options: tuple[TargetOption, ...],
    request: str,
) -> PlannerClarification | None:
    """Conservative checks only where they add safety; A1 still revalidates."""
    spoken = [m.group(1).casefold() for m in _ORDINAL.finditer(request)]
    positional = bool(_POSITION.search(request))
    for target, operation in pairs:
        same_label = [o for o in options if o.label == target.label]
        same_type = [
            o
            for o in options
            if o.feature_type == target.feature_type
            and operation.type in o.supported_operations
        ]
        named = target.label.casefold() in request.casefold()
        located = bool(spoken) or positional
        if len(same_label) >= 2 and not located:
            return PlannerClarification(
                reason="ambiguous_target", choices=choices(same_label)
            )
        if len(same_type) >= 2 and not named and not located:
            return PlannerClarification(
                reason="ambiguous_target", choices=choices(same_type)
            )
        if not named and len(set(spoken)) == 1 and not positional:
            ordered = sorted(same_type, key=lambda o: o.position)
            index = ORDINALS[spoken[0]]
            try:
                expected = ordered[index]
            except IndexError:
                expected = None
            if len(ordered) >= 2 and (
                expected is None or expected.handle != target.handle
            ):
                # The chosen target contradicts the ordinal the user spoke.
                return PlannerClarification(
                    reason="ambiguous_target", choices=choices(ordered)
                )
    return None


def to_result(
    wire: WirePlan, options: tuple[TargetOption, ...], request: str
) -> PlannerResult:
    by_handle = {o.handle: o for o in options}
    if wire.outcome == "clarification":
        if wire.reason == "none" or wire.operations:
            raise PlannerError
        if any(c not in by_handle for c in wire.candidates):
            raise PlannerError
        return PlannerClarification(
            reason=wire.reason,
            choices=choices(by_handle[c] for c in wire.candidates),
        )
    if wire.reason != "none" or wire.candidates or not wire.operations:
        raise PlannerError
    pairs: list[tuple[TargetOption, ModifyOperation]] = []
    for item in wire.operations:
        target = by_handle.get(item.target)
        # An unknown handle or an operation the target does not support is a model
        # error, not a plan. Neither is ever forwarded to A1.
        if target is None or item.type not in target.supported_operations:
            raise PlannerError
        pairs.append((target, _typed(item)))
    kept, conflict = _conflicts(pairs)
    if conflict:
        return PlannerClarification(reason="contradictory_request")
    ambiguous = _ambiguity(kept, options, request)
    if ambiguous is not None:
        return ambiguous
    return PlannerPlan(operations=tuple(operation for _, operation in kept))
