"""Deterministic wording over captured evidence, never model-authored CAD claims."""

import json
import re

from forge_api.integrations.onshape.inspector import CadInspector

from .models import AssumptionId, QuestionId, SuggestionId

SUGGESTIONS: dict[SuggestionId, str] = {
    "check_constraints": (
        "Review sketch constraints in Onshape before changing dimensions."
    ),
    "check_material": "Check material and density in Onshape before relying on mass.",
    "confirm_units": "Confirm the document's units before using numeric dimensions.",
    "review_dimensions": (
        "Compare proposed dimensions against clearance and loading requirements "
        "before making changes."
    ),
    "define_requirements": (
        "Define loads, clearances and material requirements before comparing designs."
    ),
}
# These are optional hypothetical comparison cases, never assertions about CAD.
# Ownership hypotheses are deliberately absent, even for a unique part/body.
ASSUMPTIONS: dict[AssumptionId, str] = {
    "static_load_case": (
        "For a hypothetical comparison only, assume static loading; "
        "actual loads have not been verified."
    ),
    "room_temperature_case": (
        "For a hypothetical comparison only, assume room-temperature use; "
        "the actual environment has not been verified."
    ),
}
QUESTIONS: dict[QuestionId, str] = {
    "loads_and_clearances": "What loads and clearances should the design accommodate?",
    "intended_material": "What material are you considering for the design?",
    "proposed_dimensions": "What dimensions and units do you propose for the design?",
}
PARAMETER_CAVEAT = (
    "Parameter values are captured settings, not verified dimensions. Expressions "
    "are not evaluated, options may be inactive, and selection queries do not "
    "establish geometry ownership."
)


def overview_question(prompt: str) -> bool:
    """Only unambiguous inventory asks; specific questions keep fact selection."""
    value = prompt.strip().rstrip("?.!").lower()
    return bool(
        re.fullmatch(
            r"(?:what(?: is|'s) in|summari[sz]e|describe|give me an overview of) "
            r"(?:this|the|my) (?:part studio|model|design)",
            value,
        )
    )


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def ordinal(index: int) -> str:
    return {1: "first", 2: "second", 3: "third"}.get(index, f"number {index}")


def overview(inspector: CadInspector) -> str:
    """Only bounded observed counts, order, suppression and returned topology."""
    source = inspector.source
    count = source.features.count
    features = inspector.features.items[:3]
    if (
        features
        and count == len(features)
        and all(item.suppression == "active" for item in features)
    ):
        feature_text = (
            f"This Part Studio contains {count} active "
            f"{'feature' if count == 1 else 'features'}: "
            + ", followed by ".join(quoted(item.name) for item in features)
            + "."
        )
    else:
        feature_text = (
            f"This Part Studio contains {count} captured "
            f"{'feature' if count == 1 else 'features'}."
            if count is not None
            else "The total feature count is unknown."
        )
        if features:
            ordered = []
            for item in features:
                state = (
                    item.suppression
                    if item.suppression != "unverified"
                    else "activity unverified"
                )
                ordered.append(f"{quoted(item.name)} ({state})")
            feature_text += " Captured order: " + ", followed by ".join(ordered) + "."
    if len(inspector.features.items) > len(features):
        feature_text += " Additional captured features are available in the inspector."
    objects = []
    for name, singular in (("parts", "part"), ("bodies", "body")):
        section = getattr(inspector, name)
        count = getattr(source, name).count
        label = singular if count == 1 else name
        solid = (
            "solid "
            if (
                count == 1
                and len(section.items) == 1
                and section.items[0].body_type == "SOLID"
            )
            else ""
        )
        sentence = (
            f"{count} {solid}{label} {'is' if count == 1 else 'are'} reported"
            if count is not None
            else f"The total {singular} count is unknown"
        )
        if name == "parts" and section.items:
            # Names stay quoted data. Do not infer a part/body relationship.
            sentence += ": " + ", ".join(
                quoted(p.name) for p in inspector.parts.items[:2]
            )
            if len(inspector.parts.items) > 2:
                sentence += " (first two captured names)"
        objects.append(sentence + ".")
    if len(inspector.bodies.items) == 1:
        body = inspector.bodies.items[0]
        known, unknown = [], []
        for kind in ("face", "edge", "vertex"):
            value = getattr(body, kind + "_count")
            if value is None:
                unknown.append(kind)
            else:
                known.append(f"{value} {kind} {'entry' if value == 1 else 'entries'}")
        if known:
            objects.append(
                "Forge received " + ", ".join(known) + " for the captured body."
            )
        if unknown:
            objects.append(
                " and ".join(unknown).capitalize()
                + (" count remains" if len(unknown) == 1 else " counts remain")
                + " unverified."
            )
    paragraphs = [feature_text, " ".join(objects)]
    if any(
        section.completeness in ("partial", "unavailable", "unverified")
        for section in (inspector.features, inspector.parts, inspector.bodies)
    ):
        paragraphs.append(
            "Some details are only partially captured or remain unverified."
        )
    return "\n\n".join(paragraphs)


# Friendly replies for greetings and small talk. Written by the server, never by a
# model: no CAD is read and no provider is called, so nothing can be invented.
# Matching is deliberately strict (the whole message); anything else, including a
# greeting followed by a real question, takes the normal grounded path.
_SMALLTALK: tuple[tuple[str, str], ...] = (
    (
        r"(?:hi|hello|hey|hiya|howdy|yo|good (?:morning|afternoon|evening))"
        r"(?: (?:there|forge))?",
        "Hi! I'm Forge, a read-only engineering assistant for this Part Studio. "
        "I can read your model, explain what I find and point out what to check "
        "next. What would you like to look at?",
    ),
    (
        r"(?:thanks|thank you|thx|ty|cheers)(?: (?:so much|a lot|forge))?",
        "You're welcome! Ask me anything else about this Part Studio whenever "
        "you like.",
    ),
    (
        r"how are you(?: doing)?(?: today)?",
        "Doing well, thanks for asking! I'm ready to look at your Part Studio "
        "whenever you are.",
    ),
    (
        r"(?:who|what) are you",
        "I'm Forge, an engineering assistant inside Onshape. I read your Part "
        "Studio and explain what it contains. I can't change your model.",
    ),
    (
        r"help|what can you do|what do you do|how does this work",
        "I can read your current Part Studio and tell you what's in it: its "
        "features, parts and bodies, and what I could and couldn't verify. I can "
        "also suggest sensible things to check next. I can't edit your model, and "
        "I only state what I can actually see.",
    ),
)
SMALLTALK_FOLLOW_UPS = ["What features does my model have?", "Explain my model."]


def smalltalk(prompt: str) -> str | None:
    """A fixed friendly reply for a bare greeting or similar, else None."""
    value = re.sub(r"\s+", " ", prompt.strip().rstrip("?.!,").strip().lower())
    for pattern, reply in _SMALLTALK:
        if re.fullmatch(pattern, value):
            return reply
    return None
