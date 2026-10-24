"""One bounded tutor turn. The model explains; the server owns every verified claim."""

import re
from collections.abc import AsyncIterator, Awaitable, Callable

from forge_api.ai import evidence as cad_evidence
from forge_api.ai.evidence import FRESHNESS, UNITS, project
from forge_api.ai.grounding import ORDER_SEMANTICS, GroundedCad
from forge_api.ai.models import AiError
from forge_api.ai.policy import REFUSAL, blocked
from forge_api.ai.presentation import GENERAL_REPLY_NOTE, mentions_model
from forge_api.integrations.onshape.inspector import CadInspector

from .catalog import CATALOG
from .context import build_context, context_message
from .evidence_token import VerifiedCheck
from .models import LatestCheck, Observed, TutorAnswer, TutorModelAnswer, TutorRequest
from .policy import boundary_response
from .providers import TutorProvider, TutorTask
from .relationships import relationship_question, unsafe_relationship_prose
from .structural import TERMINAL_UNKNOWN as TERMINAL_UNKNOWN
from .structural import structural_answer, terminal_answer, terminal_question

TOTAL_SECONDS = 120
STATUS_NOTE = (
    "Only Check my step can verify a step. This explanation doesn't change your result."
)
STALE_NOTE = (
    "Based on your last check. If you've changed your model since, press Check my "
    "step again."
)
DIMENSION_NOTE = (
    "Forge can't read your dimensions or units, so nothing here confirms a size."
)
STRENGTH_NOTE = "Forge doesn't verify strength, fit or safety."
RELATIONSHIP_EXPLANATION = (
    "In general CAD, a dependency means a feature uses another feature's profile "
    "or geometry as an input. Forge can describe captured feature order, but that "
    "does not establish dependency, ownership or other relationships in your model."
)
RELATIONSHIP_ACTION = (
    "Examine the feature's inputs in Onshape; use Check my step for a new step result."
)
CAD_OBSERVATIONS_ONLY = "Forge can't confirm more from the captured CAD evidence."
# Presentation guards, like the verdict guard below: the model may mention sizes or
# strength in teaching, but the learner is always told Forge has verified neither.
_DIMENSION = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mm|cm|millimet\w+|centimet\w+|inch(?:es)?|in)\b",
    re.IGNORECASE,
)
_STRENGTH = re.compile(
    r"\b(?:strong\s+enough|will\s+hold|sturdy|won't\s+break|structurally\s+sound|"
    r"safe\s+to\s+(?:use|print|build|ship))\b",
    re.IGNORECASE,
)
# The tutor claiming a verdict itself. Presentation guard only: the real authority
# is that nothing the model writes can set any status, resolution or completion.
_VERDICT = re.compile(
    r"\b(?:your|this|the)\s+(?:step|check|challenge|investigation)\s+"
    r"(?:is|has|was|now)\s+(?:passed|verified|complete|completed|resolved|done|correct)\b"
    r"|\byou(?:'ve|\s+have)?\s+(?:passed|completed|nailed|mastered)\b",
    re.IGNORECASE,
)


def latest(check: VerifiedCheck | None) -> LatestCheck | None:
    return (
        LatestCheck(outcome=check.outcome, captured_at=check.captured_at)
        if check
        else None
    )


def plain(text: str, check: VerifiedCheck | None) -> TutorAnswer:
    """A server-authored answer with no model involvement (refusals, boundaries)."""
    return TutorAnswer(
        explanation=text,
        reasoning_question=None,
        next_action=None,
        observed=[],
        unknowns=[],
        notes=[],
        latest_check=latest(check),
        used_cad=False,
        captured_at=None,
    )


def resolve_tutor(
    model: TutorModelAnswer,
    *,
    check: VerifiedCheck | None,
    facts: dict[str, object],
    used_cad: bool,
    captured_at: str | None,
    question: str = "",
    cad_names: tuple[str, ...] = (),
) -> TutorAnswer:
    from forge_api.ai.models import Fact

    findings = {item.id: item for item in (check.findings if check else ())}
    # The server only ever prints statements it owns, so an id the model invented or
    # repeated is simply not shown. Dropping it is safe; failing the whole answer
    # (as Design does) would throw away good teaching for a harmless slip.
    check_refs = [i for i in dict.fromkeys(model.check_refs) if i in findings]
    fact_ids = [i for i in dict.fromkeys(model.fact_ids) if i in facts]
    observed = [
        Observed(
            source="check",
            status=findings[i].status,
            statement=findings[i].statement,
        )
        for i in check_refs
    ]
    for identifier in fact_ids:
        fact = facts[identifier]
        assert isinstance(fact, Fact)
        observed.append(
            Observed(source="cad", status=fact.status, statement=fact.statement)
        )
    # Limitations never fade: every unverified finding is always shown, and a CAD
    # read always carries its freshness and units caveats.
    unknowns = list(
        dict.fromkeys(
            item.statement for item in findings.values() if item.status == "UNVERIFIED"
        )
    )
    if used_cad:
        unknowns += [UNITS, FRESHNESS]
        if "order_semantics" in facts:
            unknowns.append(ORDER_SEMANTICS)
    if len(unknowns) > 8:
        # Never discard a check limitation or structural caveat to fit the UI.
        raise AiError("evidence_unavailable")
    notes: list[str] = []
    if check is not None:
        notes.append(STALE_NOTE)
    if _VERDICT.search(model.explanation):
        notes.append(STATUS_NOTE)
    prose = model.explanation + " " + model.next_action + " " + model.reasoning_question
    if check is None and not used_cad and mentions_model(model.explanation):
        notes.append(GENERAL_REPLY_NOTE)
    if _DIMENSION.search(prose):
        notes.append(DIMENSION_NOTE)
    if _STRENGTH.search(prose):
        notes.append(STRENGTH_NOTE)
    explanation = model.explanation.strip()
    next_action = model.next_action.strip() or None
    reasoning_question = model.reasoning_question.strip() or None
    if "order_semantics" in facts:
        structural = structural_answer(question, facts)
        if structural is not None:
            # The question, never incidental model prose, selects this answer.
            explanation = structural
            next_action = None
            reasoning_question = None
        elif relationship_question(question, cad_names):
            explanation = RELATIONSHIP_EXPLANATION
            next_action = RELATIONSHIP_ACTION
            reasoning_question = None
        elif terminal_question(question):
            explanation = terminal_answer(facts)
            next_action = None
            reasoning_question = None
        else:
            # Discard an unsupported field without turning an unrelated question
            # into a relationship/terminal lesson. Other safe teaching can remain.
            def unsafe(text: str) -> bool:
                return unsafe_relationship_prose(text, cad_names) or terminal_question(
                    text
                )

            if unsafe(model.explanation):
                explanation = CAD_OBSERVATIONS_ONLY
            if unsafe(model.next_action):
                next_action = None
            if unsafe(model.reasoning_question):
                reasoning_question = None
    return TutorAnswer(
        explanation=explanation,
        reasoning_question=reasoning_question,
        next_action=next_action,
        observed=observed,
        unknowns=unknowns,
        notes=notes[:6],
        latest_check=latest(check),
        used_cad=used_cad,
        captured_at=captured_at,
    )


async def run_tutor(
    request: TutorRequest,
    check: VerifiedCheck | None,
    provider: TutorProvider,
    read: Callable[[], Awaitable[CadInspector | GroundedCad]],
    ensure_active: Callable[[], Awaitable[None]],
    request_id: str,
) -> AsyncIterator[dict[str, object]]:
    yield {"type": "progress", "stage": "understanding"}
    if blocked(request.question):
        yield {"type": "result", "result": plain(REFUSAL, check).model_dump()}
        return
    fixed = boundary_response(request.question)
    if fixed is not None:
        # Authority boundaries are deterministic: no model call, no CAD read.
        yield {"type": "result", "result": plain(fixed, check).model_dump()}
        return
    step = CATALOG[request.step_id]
    context = build_context(
        step=step,
        learner=request.learner,
        check=check,
        can_inspect=request.context is not None,
    )
    await ensure_active()
    wants_cad = await provider.decide(
        TutorTask(
            request.question,
            tuple(request.history),
            context,
            can_inspect=request.context is not None,
        ),
        request_id=request_id,
    )
    await ensure_active()
    payload: str | None = None
    facts: dict[str, object] = {}
    captured_at: str | None = None
    cad_names: tuple[str, ...] = ()
    if wants_cad:
        yield {"type": "progress", "stage": "inspecting"}
        evidence = await read()
        payload, projected = project(evidence, "none")
        if (
            len(payload.encode("utf-8")) + len(context_message(context).encode("utf-8"))
            > cad_evidence.MAX_EVIDENCE_BYTES
        ):
            raise AiError("evidence_unavailable")
        facts = dict(projected)
        inspector = (
            evidence.inspector if isinstance(evidence, GroundedCad) else evidence
        )
        captured_at = inspector.source.captured_at
        cad_names = tuple(
            item.name
            for item in inspector.features.items
            if f"feature_{item.index}" in facts
        )
        await ensure_active()
    yield {"type": "progress", "stage": "reviewing"}
    model = await provider.answer(payload, request_id=request_id)
    await ensure_active()
    yield {"type": "progress", "stage": "preparing"}
    if model.safety == "refuse":
        yield {"type": "result", "result": plain(REFUSAL, check).model_dump()}
        return
    yield {
        "type": "result",
        "result": resolve_tutor(
            model,
            check=check,
            facts=facts,
            used_cad=wants_cad,
            captured_at=captured_at,
            question=request.question,
            cad_names=cad_names,
        ).model_dump(),
    }
