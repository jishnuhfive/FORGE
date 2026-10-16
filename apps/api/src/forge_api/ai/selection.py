"""Selection evidence has no ownership join. Counts never participate here."""

import re

from .models import Fact, Selection

SELECTION_IDS = (
    "selection",
    "selection_ownership",
    "selection_part",
    "selection_body",
    "selection_feature",
    "selection_dimensions",
    "selection_type",
    "selection_geometry",
    "selection_capability",
)
SELECTION_CAPABILITY = (
    "Forge can currently confirm only the panel's selection category; "
    "selection-specific ownership and measurements are not available in Phase 6."
)


def selection_question(prompt: str) -> bool:
    return bool(
        re.search(
            r"\b(selected|selection|ownership|owns)\b|"
            r"\b(this|that|the|my)\s+(face|edge)\b",
            prompt,
            re.I,
        )
    )


def selection_facts(selection: Selection) -> list[Fact]:
    noun = selection.lower() if selection in ("FACE", "EDGE") else "geometry"
    state = (
        f"The panel reports one {noun} selected."
        if selection in ("FACE", "EDGE")
        else "The panel reports no selection."
        if selection == "none"
        else "Current selection is unknown."
    )
    unknown = {
        "selection_ownership": (
            "Selection ownership by a part, body or feature is unknown."
        ),
        "selection_part": f"The selected {noun}'s owning part is unknown.",
        "selection_body": f"The selected {noun}'s owning body is unknown.",
        "selection_feature": f"The selected {noun}'s owning feature is unknown.",
        "selection_dimensions": f"The selected {noun}'s dimensions are unknown.",
        "selection_type": (
            "The selected face's surface type is unknown."
            if selection == "FACE"
            else "The selected edge's curve type is unknown."
            if selection == "EDGE"
            else "Selected-geometry type is unknown."
        ),
        "selection_geometry": (
            "Selected-face geometry, including area and normal direction, is unknown."
            if selection == "FACE"
            else "Adjacent faces and edge-specific geometry are unknown."
            if selection == "EDGE"
            else "Selection-specific geometry is unknown."
        ),
    }
    return [
        Fact(
            id="selection",
            statement=state,
            status="unknown" if selection == "unknown" else "verified",
        ),
        *(
            Fact(id=key, statement=text, status="unknown")
            for key, text in unknown.items()
        ),
        Fact(
            id="selection_capability", statement=SELECTION_CAPABILITY, status="verified"
        ),
    ]


def selection_answer(selection: Selection) -> str:
    state = selection_facts(selection)[0].statement
    if selection == "FACE":
        unknown = (
            "Owning part, body and feature: unknown. Dimensions, surface type and "
            "face-specific geometry (including area and normal direction): unknown."
        )
    elif selection == "EDGE":
        unknown = (
            "Owning part, body and feature: unknown. Dimensions, curve type, "
            "adjacent faces and edge-specific geometry: unknown."
        )
    else:
        unknown = (
            "No selected geometry has been verified for ownership or measurements."
        )
    return "\n\n".join((state, unknown, SELECTION_CAPABILITY))
