"""Minimize the Phase 5 inspector; all CAD text stays untrusted quoted data."""

import json

from forge_api.integrations.onshape.inspector import CadInspector

from .diagnostics import Reason
from .models import AiAnswer, AiError, Fact, ModelAnswer, Selection
from .presentation import (
    ASSUMPTIONS,
    PARAMETER_CAVEAT,
    QUESTIONS,
    SUGGESTIONS,
    ordinal,
    overview,
    overview_question,
)
from .selection import (
    SELECTION_IDS,
    selection_answer,
    selection_facts,
    selection_question,
)
from .writes import write_facts

MAX_EVIDENCE_BYTES = 65536
CAPABILITY = "Forge can analyze and propose designs, but cannot modify CAD in Phase 6."
VALIDATION = (
    "No deterministic engineering validator exists yet; validation is UNVERIFIED."
)
FRESHNESS = (
    "Evidence was read for this request using the default configuration and end of "
    "the feature list. Currentness and consistency across separate reads "
    "are unverified."
)
UNITS = (
    "Physical units are provider-native and unverified; "
    "exact mass and volume are not supplied."
)


def fact(identifier: str, statement: str, status: str = "verified") -> Fact:
    return Fact.model_validate(
        {"id": identifier, "statement": statement, "status": status}
    )


def project(
    inspector: CadInspector, selection: Selection
) -> tuple[str, dict[str, Fact]]:
    if inspector.freshness == "stale" or inspector.source.consistency == "mismatch":
        raise AiError("evidence_unavailable")
    sections = [
        inspector.source.features,
        inspector.source.parts,
        inspector.source.bodies,
        inspector.source.mass,
    ]
    if any(
        s.code
        in (
            "connection_required",
            "read_permission_required",
            "permission_or_access_required",
            "document_forbidden",
        )
        for s in sections
    ):
        raise AiError("read_permission_required")
    if not any(s.status == "success" for s in sections):
        raise AiError("evidence_unavailable")
    # Keep the actual Phase 5 schema/semantics. Omit even random source identifiers.
    data = inspector.model_dump(mode="json", exclude={"source": {"request_id"}})
    for name, limit in (("features", 20), ("parts", 20), ("bodies", 20)):
        section = data[name]
        original = len(section["items"])
        section["items"] = section["items"][:limit]
        if original > limit:
            section["omitted_count"] += original - limit
            section["completeness"] = "partial"
    for feature in data["features"]["items"]:
        original = len(feature["parameters"])
        feature["parameters"] = feature["parameters"][:4]
        if original > 4:
            feature["omitted_parameters"] += original - 4
            feature["completeness"] = "partial"
            data["features"]["completeness"] = "partial"
    facts = [
        fact("capability", CAPABILITY),
        fact("validation", VALIDATION, "unverified"),
        fact("units", UNITS, "unverified"),
    ]
    facts.extend(selection_facts(selection))
    physical = inspector.physical
    facts.append(
        fact(
            "mass",
            (
                "Mass is unavailable; material or density may be missing. "
                "No exact mass can be verified."
                if physical.mass == "unavailable"
                else f"Aggregate mass availability is {physical.mass}; "
                "no exact numeric mass is supplied."
            ),
            "unknown" if physical.mass == "unavailable" else "unverified",
        )
    )
    facts.append(
        fact(
            "volume",
            f"Aggregate volume availability is {physical.volume}; "
            "numeric volume and units are unverified.",
            "unverified",
        )
    )
    for name in ("features", "parts", "bodies"):
        section = data[name]
        count = getattr(inspector.source, name).count
        status = getattr(inspector.source, name).status
        label = (
            {"features": "feature", "parts": "part", "bodies": "body"}[name]
            if count == 1
            else name
        )
        statement = (
            f"The captured Part Studio contains {count} {label}."
            if count is not None
            else f"The total number of {name} is unknown; "
            f"{section['returned_count']} entries were returned."
        )
        facts.append(
            fact(
                name,
                statement,
                "verified" if status == "success" and count is not None else "unknown",
            )
        )
        facts.append(
            fact(
                f"{name}_completeness",
                f"{name.capitalize()} evidence is {section['completeness']}; "
                f"{section['omitted_count']} entries omitted.",
                "unverified",
            )
        )
    # Quote names/values as JSON so malicious names cannot masquerade as prose.
    for feature in data["features"]["items"]:
        index = feature["index"]
        facts.append(
            fact(
                f"feature_{index}",
                f"The {ordinal(index)} captured feature is named "
                f"{json.dumps(feature['name'], ensure_ascii=False)} "
                f"({feature['feature_type']}; {feature['suppression']}).",
                "unverified"
                if feature["feature_type"] == "unknown"
                or feature["suppression"] == "unverified"
                else "verified",
            )
        )
        for parameter_index, parameter in enumerate(feature["parameters"], 1):
            value = parameter.get("text")
            if value is None:
                value = parameter.get("boolean")
            if value is None:
                value = parameter.get("count")
            rendered = (
                json.dumps(value, ensure_ascii=False)
                if value is not None
                else "unknown"
            )
            if parameter["kind"] == "query_count":
                rendered = (
                    f"selection query returned {rendered} entries; ownership unverified"
                )
            facts.append(
                fact(
                    f"parameter_{index}_{parameter_index}",
                    f"Feature {index}, {parameter['label']}: "
                    f"{rendered} "
                    f"({parameter['state']}).",
                    "unverified",
                )
            )
    for part in data["parts"]["items"]:
        body_type = json.dumps(part["body_type"]) if part["body_type"] else "unknown"
        facts.append(
            fact(
                f"part_{part['index']}",
                f"Part {part['index']}: name "
                f"{json.dumps(part['name'], ensure_ascii=False)}, "
                f"reported body type {body_type}.",
            )
        )
    for body in data["bodies"]["items"]:
        body_type = json.dumps(body["body_type"]) if body["body_type"] else "unknown"
        counts = ", ".join(
            f"{kind}: {value if value is not None else 'unknown'}"
            for kind in ("face", "edge", "vertex")
            for value in [body[kind + "_count"]]
        )
        facts.append(
            fact(
                f"body_{body['index']}",
                f"Body {body['index']}: reported type "
                f"{body_type}; "
                f"returned topology counts — {counts}.",
            )
        )
    # Large records fail safely rather than silently truncate semantics or JSON.
    indexed = {f.id: f for f in facts}
    payload = json.dumps(
        {
            "trust": "UNTRUSTED_QUOTED_CAD_EVIDENCE",
            "cad_evidence": data,
            "selection": {
                "kind": selection,
                "source": "validated_browser_panel",
                "ownership": "unknown",
            },
            "freshness_caveat": FRESHNESS,
            "facts": [f.model_dump() for f in facts],
            "optional_next_steps": SUGGESTIONS,
            "hypothetical_cases": ASSUMPTIONS,
            "requirements_questions": QUESTIONS,
        },
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(payload.encode("utf-8")) > MAX_EVIDENCE_BYTES:
        raise AiError("evidence_unavailable")
    return payload, indexed


def resolve(
    answer: ModelAnswer,
    facts: dict[str, Fact],
    captured_at: str,
    *,
    prompt: str = "",
    inspector: CadInspector | None = None,
    selection: Selection = "unknown",
) -> AiAnswer:
    if any(i not in facts for i in answer.fact_ids):
        raise AiError("invalid_response", reason=Reason.UNKNOWN_FACT_ID)
    for identifiers in (
        answer.fact_ids,
        answer.suggestion_ids,
        answer.assumption_ids,
        answer.question_ids,
    ):
        if len(set(identifiers)) != len(identifiers):
            raise AiError("invalid_response", reason=Reason.DUPLICATE_CANONICAL_ID)
    if not answer.fact_ids and not answer.suggestion_ids:
        raise AiError("invalid_response", reason=Reason.EMPTY_CANONICAL_ANSWER)
    ids = answer.fact_ids
    broad = overview_question(prompt) and inspector is not None
    selected_question = not broad and (
        selection_question(prompt)
        or (selection in ("FACE", "EDGE") and any(i in SELECTION_IDS for i in ids))
    )
    if selected_question:
        # No CAD inventory or model-written sidecar can infer an ownership join.
        ids = list(SELECTION_IDS)
    if broad and inspector is not None:
        # Server-owned presentation routing, not model freedom to summarize CAD.
        core = (
            ["features"]
            + [f"feature_{item.index}" for item in inspector.features.items[:3]]
            + ["parts"]
            + [f"part_{item.index}" for item in inspector.parts.items[:1]]
            + ["bodies"]
            + [f"body_{item.index}" for item in inspector.bodies.items[:1]]
        )
        chosen = [
            i
            for i in ids
            if not i.startswith("parameter_") and not i.endswith("_completeness")
        ]
        ids = list(dict.fromkeys(chosen + core))[:12]
    selected = [facts[i] for i in ids]
    # Revalidate the public contract even if an internal caller constructed a Fact
    # without normal Pydantic validation. Never allow a blank evidence row through.
    try:
        selected = [Fact.model_validate(f.model_dump()) for f in selected]
    except ValueError:
        raise AiError(
            "invalid_response", reason=Reason.CANONICAL_RESPONSE_VALIDATION_FAILED
        ) from None
    uncertainties = [FRESHNESS, UNITS, VALIDATION]
    if any(i.startswith("parameter_") for i in ids):
        uncertainties.append(PARAMETER_CAVEAT)
    try:
        return AiAnswer(
            answer=overview(inspector)
            if broad and inspector is not None
            else selection_answer(selection)
            if selected_question
            else "\n\n".join(f.statement for f in selected),
            evidence=selected,
            uncertainties=uncertainties,
            discussion=""
            if broad or selected_question
            else " ".join(SUGGESTIONS[i] for i in answer.suggestion_ids),
            assumptions=[]
            if selected_question
            else [ASSUMPTIONS[i] for i in answer.assumption_ids],
            follow_up_questions=[]
            if selected_question
            else [QUESTIONS[i] for i in answer.question_ids],
            captured_at=captured_at,
        )
    except ValueError:
        raise AiError(
            "invalid_response", reason=Reason.CANONICAL_RESPONSE_VALIDATION_FAILED
        ) from None


def resolve_write(
    prompt: str, facts: dict[str, Fact], inspector: CadInspector
) -> AiAnswer:
    """No model output or fabricated tool call is needed for a capability answer."""
    selected = write_facts(prompt) + [
        facts[f"feature_{item.index}"] for item in inspector.features.items[:2]
    ]
    try:
        selected = [Fact.model_validate(item.model_dump()) for item in selected]
        return AiAnswer(
            answer="\n\n".join(item.statement for item in selected),
            evidence=selected,
            uncertainties=[FRESHNESS, UNITS, VALIDATION],
            discussion="",
            assumptions=[],
            follow_up_questions=[],
            captured_at=inspector.source.captured_at,
        )
    except ValueError:
        raise AiError(
            "invalid_response", reason=Reason.CANONICAL_RESPONSE_VALIDATION_FAILED
        ) from None
