"""Bounded presentation of canonical CAD facts; no graph queries or new inference."""

import json
import re
from dataclasses import dataclass

from forge_api.ai.grounding import MAX_AI_FEATURES
from forge_api.ai.models import Fact
from forge_api.ai.presentation import ordinal, quoted

from .models import TutorAnswer

MAX_EXPLANATION_CHARS = int(
    TutorAnswer.model_json_schema()["properties"]["explanation"]["maxLength"]
)
INVENTORY_UNKNOWN = (
    "Forge can't establish a modeled-feature inventory from this evidence."
)
TERMINAL_UNKNOWN = (
    "Forge hasn't established a final feature from complete evidence. The last "
    "visible feature alone cannot prove the end of the feature list."
)
_INVENTORY = re.compile(
    r"(?:(?:what|which)\s+(?:modeled\s+)?features\s+are\s+(?:there\s+)?in|"
    r"(?:list|show(?:\s+me)?)\s+(?:the\s+)?(?:modeled\s+)?features\s+in)\s+"
    r"(?:my|this|the|our)\s+(?:current\s+)?(?:model|part\s+studio)"
    r"(?:\s+(?:and\s+)?(?:in\s+what\s+order|in\s+order))?",
    re.IGNORECASE,
)
_BEFORE = re.compile(r"what\s+(?:comes|appears)\s+before\s+(.+)", re.I)
_TERMINAL = re.compile(
    r"\b(?:final|last|terminal)\s+(?:captured\s+|modeled\s+)?feature\b|"
    r"\bfeature\b[^.?!]{0,60}\b(?:final|last|terminal)\b|"
    r"\bend\s+of\s+(?:the\s+)?feature\s+(?:list|tree)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Feature:
    index: int
    name: str


def _fact(facts: dict[str, object], identifier: str) -> Fact | None:
    value = facts.get(identifier)
    return value if isinstance(value, Fact) and value.id == identifier else None


def _features(facts: dict[str, object]) -> tuple[_Feature, ...] | None:
    """Decode only the closed server statement grammar, including JSON names.

    Any unmatched grammar fails conservative presentation. Names are data and
    cannot supply identities, delimiters, order facts or relationship semantics.
    """
    result = []
    for index in range(1, MAX_AI_FEATURES + 1):
        value = _fact(facts, f"feature_{index}")
        if value is None:
            if f"feature_{index}" in facts:
                return None
            continue
        prefix = f"The {ordinal(index)} captured feature is named "
        if value.status not in (
            "verified",
            "unverified",
        ) or not value.statement.startswith(prefix):
            return None
        try:
            name, end = json.JSONDecoder().raw_decode(value.statement[len(prefix) :])
        except ValueError:
            return None
        if not isinstance(name, str) or len(name) > 256:
            return None
        tail = value.statement[len(prefix) + end :]
        if (
            not re.fullmatch(
                r" \((?:sketch|extrude|fillet|chamfer|unknown); "
                r"(?:active|suppressed|unverified)\)\.",
                tail,
            )
            or value.statement != prefix + quoted(name) + tail
        ):
            return None
        result.append(_Feature(index, name))
    if [item.index for item in result] != list(range(1, len(result) + 1)):
        return None
    return tuple(result)


def _count(facts: dict[str, object]) -> int | None:
    value = _fact(facts, "features")
    if value is None or value.status != "verified":
        return None
    match = re.fullmatch(
        r"The captured Part Studio contains (\d+) features?\.", value.statement
    )
    if match is None:
        return None
    count = int(match[1])
    label = "feature" if count == 1 else "features"
    return (
        count
        if value.statement == f"The captured Part Studio contains {count} {label}."
        else None
    )


def _precedes(before: _Feature, after: _Feature, facts: dict[str, object]) -> bool:
    value = _fact(facts, f"order_{before.index}_{after.index}")
    return bool(
        after.index == before.index + 1
        and value is not None
        and value.status == "verified"
        and value.statement
        == (
            f"The {ordinal(before.index)} captured modeled feature, "
            f"{quoted(before.name)}, "
            f"appears before the {ordinal(after.index)} captured modeled feature, "
            f"{quoted(after.name)}, in the returned feature order."
        )
    )


def _label(item: _Feature, features: tuple[_Feature, ...]) -> str:
    duplicate = (
        sum(other.name.casefold() == item.name.casefold() for other in features) > 1
    )
    return quoted(item.name) + (
        f" (captured feature {item.index})" if duplicate else ""
    )


def _inventory(facts: dict[str, object], features: tuple[_Feature, ...]) -> str:
    count = _count(facts)
    if count is not None and count < len(features):
        return INVENTORY_UNKNOWN
    if count == 0:
        return "This Part Studio has no modeled features."
    if not features:
        return INVENTORY_UNKNOWN
    header = (
        f"The captured Part Studio has {count} modeled "
        f"{'feature' if count == 1 else 'features'}."
        if count is not None
        else f"Forge captured {len(features)} modeled features; "
        "the total feature count is unknown."
    )
    linked = all(
        _precedes(a, b, facts) for a, b in zip(features, features[1:], strict=False)
    )
    # Shorten by whole entries only, preserving quoted names and truthful limits.
    # Never enlarge the existing public prose bound or infer an omitted link.
    for shown in range(len(features), 0, -1):
        labels = [_label(item, features) for item in features[:shown]]
        body = (
            "Captured returned order:\n" + " → ".join(labels)
            if linked and shown > 1
            else "Captured features:\n- " + "\n- ".join(labels)
        )
        limits = []
        if not linked:
            limits.append("Returned-order links aren't fully established.")
        if shown < len(features) or (count is not None and shown < count):
            limits.append("Additional modeled features are not shown.")
        result = "\n\n".join([header, body, *limits])
        if len(result) <= MAX_EXPLANATION_CHARS:
            return result
    return INVENTORY_UNKNOWN


def structural_answer(question: str, facts: dict[str, object]) -> str | None:
    """Only simple inventory/before questions select these server-owned answers."""
    value = question.strip()
    if value.endswith(("?", "!")):
        value = value[:-1].rstrip()
    inventory = _INVENTORY.fullmatch(value.removesuffix("."))
    before = _BEFORE.fullmatch(value)
    if inventory is None and before is None:
        return None
    features = _features(facts)
    if features is None:
        return INVENTORY_UNKNOWN
    if inventory is not None:
        return _inventory(facts, features)
    assert before is not None
    target = before[1].strip()
    labels = {target.casefold()}
    try:
        decoded = json.loads(target)
    except ValueError:
        decoded = None
    if isinstance(decoded, str):
        labels.add(decoded.casefold())
    if len(target) >= 2 and target.startswith("'") and target.endswith("'"):
        labels.add(target[1:-1].casefold())
    matching = [item for item in features if item.name.casefold() in labels]
    if len(matching) != 1:
        return "Forge couldn't identify a unique captured feature for that question."
    after = matching[0]
    preceding = next((item for item in features if _precedes(item, after, facts)), None)
    if preceding is None:
        return (
            f"Forge hasn't established what comes before {quoted(after.name)} "
            "in the feature order."
        )
    return (
        f"{_label(preceding, features)} comes before {_label(after, features)} "
        "in the returned feature order."
    )


def terminal_question(text: str) -> bool:
    return bool(_TERMINAL.search(text))


def terminal_answer(facts: dict[str, object]) -> str:
    terminal = _fact(facts, "terminal_feature")
    return (
        terminal.statement
        if terminal is not None
        and terminal.status == "verified"
        and len(terminal.statement) <= MAX_EXPLANATION_CHARS
        else TERMINAL_UNKNOWN
    )
