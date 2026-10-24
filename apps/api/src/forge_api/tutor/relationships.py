"""Conservative prose presentation checks, never a source of CAD relationships."""

import re

# Strong relationship vocabulary can identify intent without treating ordinary
# 'use', dialog 'input', or help 'references' as a relationship question.
_RELATIONSHIP = re.compile(
    r"\b(?:depend\w*|parent\w*|child\w*|ownership|owns|owned|owning|"
    r"consum\w*|driv\w*|driven|caus\w*|topolog\w*|relationship\w*|"
    r"relies|rely|belongs)\b|\bown\s+(?:this|that|the|an?|my|your)\b",
    re.IGNORECASE,
)
_RELATIONAL_USE = re.compile(
    r"\b(?:uses|references?|(?:is|are|was|were)\s+(?:using|connected|linked|based\s+on))\b|"
    r"\b(?:connected|linked)\s+to\b|"
    r"\bas\s+(?:(?:its|an?|the)\s+)?input\b|\binputs?\s+(?:of|to|for)\b",
    re.IGNORECASE,
)
_QUESTION_FORM = re.compile(r"^\s*(?:does|do|is|are|was|were)\b", re.I)
_PERSONAL_QUESTION = re.compile(
    r"^\s*(?:does|do|is|are|was|were)\s+(?:I|we|you|someone|people|learners?)\b", re.I
)
_QUESTION_LINK = re.compile(r"\b(?:references?|connected|linked|based\s+on)\b", re.I)
_GENERAL_QUESTION = re.compile(
    r"^\s*(?:what\s+(?:is|are)\s+(?:an?\s+)?(?:CAD\s+)?dependenc\w*|"
    r"what\s+does\s+(?:an?\s+)?dependenc\w*\s+mean|"
    r"how\s+do\s+(?:CAD\s+)?dependencies\s+work)\s*[?!.]?\s*$",
    re.IGNORECASE,
)
_GENERAL_TEACHING = re.compile(
    r"^\s*(?:in\s+general\b|generally\b|typically\b|commonly\b|in\s+CAD\b|"
    r"general\s+CAD\s+(?:knowledge|teaching)\s*:|"
    r"an?\s+(?:dependency|extrude|extrusion|sketch|fillet|feature)\b)",
    re.IGNORECASE,
)
_CURRENT_MODEL = re.compile(
    r"\b(?:your|this|that|these|those)\s+(?:\w+\s+){0,2}"
    r"(?:models?|features?|sketch(?:es)?|extrudes?|extrusions?|fillets?|profiles?|"
    r"parts?|faces?|edges?|body|bodies)\b|"
    r"\b(?:first|second|third|last)\s+(?:feature|sketch|extrude|fillet)\b|"
    r"\b(?:feature|face|edge|body)\s+\d+\b",
    re.IGNORECASE,
)
# Only closed lack-of-proof statements are exempt, never an arbitrary sentence
# that happens to include 'unknown' before an affirmative or negative CAD claim.
_LACK_OF_PROOF = re.compile(
    r"(?:that|this|the)\s+(?:relationship|dependency|ownership)\s+"
    r"(?:is|remains)\s+(?:unknown|unverified)(?:\s+(?:for|in)\s+this\s+model)?[.!?]?|"
    r"(?:returned\s+feature(?:-list|\s+list)?\s+order|feature\s+order|ordering)\s+"
    r"(?:alone\s+)?(?:does\s+not|doesn't|cannot|can't)\s+"
    r"(?:establish|prove|confirm)\s+(?:dependency|ownership|relationships?)"
    r"(?:\s+(?:or|and)\s+(?:dependency|ownership|relationships?))*"
    r"(?:\s+(?:for|in)\s+(?:this|your|the)\s+model)?[.!?]?",
    re.IGNORECASE,
)
_GENERIC_NAMES = frozenset(
    (
        "sketch",
        "extrude",
        "extrusion",
        "fillet",
        "feature",
        "part",
        "body",
        "face",
        "edge",
        "profile",
    )
)


def _named(text: str, name: str) -> bool:
    # A generic CAD noun used as a display name must not make all teaching
    # about that feature type model-specific. Quoting still identifies it.
    if name.casefold() in _GENERIC_NAMES:
        return (
            f'"{name.casefold()}"' in text.casefold()
            or f"'{name.casefold()}'" in text.casefold()
        )
    return bool(
        name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I)
    )


def _specific_model(text: str, cad_names: tuple[str, ...]) -> bool:
    return bool(_CURRENT_MODEL.search(text)) or any(
        _named(text, name) for name in cad_names
    )


def guard_relationships(
    question: str, prose: tuple[str, ...], cad_names: tuple[str, ...]
) -> bool:
    """Separate explicit relationship intent from claims in each model prose field.

    Known display names only identify model-specific prose; they never prove a
    join, grant authority, or become policy/regex syntax. Generic teaching scope
    cannot exempt a named/current-model claim later in the same paragraph.
    """
    specific_question = _specific_model(question, cad_names)
    if _RELATIONSHIP.search(question) and (
        specific_question or not _GENERAL_QUESTION.fullmatch(question)
    ):
        return True
    if (
        specific_question
        and _QUESTION_FORM.search(question)
        and not _PERSONAL_QUESTION.search(question)
        and (
            _RELATIONAL_USE.search(question)
            or _QUESTION_LINK.search(question)
            or (
                re.search(r"\buse\b", question, re.I)
                and len(_CURRENT_MODEL.findall(question))
                + sum(_named(question, name) for name in set(cad_names))
                >= 2
            )
        )
    ):
        return True
    for field in prose:
        for paragraph in field.splitlines():
            general = False
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph.strip()):
                general = general or bool(_GENERAL_TEACHING.search(sentence))
                if _LACK_OF_PROOF.fullmatch(sentence):
                    continue
                specific = _specific_model(sentence, cad_names)
                if _RELATIONSHIP.search(sentence) and (specific or not general):
                    return True
                if specific and _RELATIONAL_USE.search(sentence):
                    return True
    return False
