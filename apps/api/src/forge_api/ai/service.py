"""One bound read; model/tool flow for reads, server capability path for writes."""

from collections.abc import AsyncIterator, Awaitable, Callable

from forge_api.integrations.onshape.inspector import CadInspector

from .evidence import project, resolve, resolve_write
from .grounding import GroundedCad
from .models import AiAnswer, AiRequest
from .policy import REFUSAL, blocked
from .presentation import GENERAL_REPLY_NOTE, mentions_model
from .provider import AgentTask, AiProvider
from .writes import write_request

TOTAL_SECONDS = 150


async def run_agent(
    request: AiRequest,
    adapter: AiProvider,
    read: Callable[[], Awaitable[CadInspector | GroundedCad]],
    ensure_active: Callable[[], Awaitable[None]],
    request_id: str,
) -> AsyncIterator[dict[str, object]]:
    yield {"type": "progress", "stage": "understanding"}
    if blocked(request.prompt):
        yield {
            "type": "result",
            "result": AiAnswer(
                answer=REFUSAL,
                evidence=[],
                uncertainties=[],
                discussion="",
                assumptions=[],
                follow_up_questions=[],
                captured_at=None,
            ).model_dump(),
        }
        return
    await ensure_active()
    if write_request(request.prompt):
        # Unavailable actions must not force a provider to invent a tool call.
        # Still inspect through the same session/context-authorized read boundary.
        yield {"type": "progress", "stage": "inspecting"}
        acquired = await read()
        _, facts = project(acquired, request.selection)
        evidence = acquired.inspector if isinstance(acquired, GroundedCad) else acquired
        await ensure_active()
        yield {"type": "progress", "stage": "preparing"}
        answer = resolve_write(request.prompt, facts, evidence)
        yield {"type": "result", "result": answer.model_dump()}
        return
    chat = await adapter.request_inspection(
        AgentTask(request.prompt, tuple(request.history)), request_id=request_id
    )
    await ensure_active()
    if chat is not None:
        # The model judged this ordinary conversation: no CAD was read and nothing
        # here is a verified claim, so it carries no evidence.
        yield {
            "type": "result",
            "result": AiAnswer(
                answer=chat,
                evidence=[],
                uncertainties=[GENERAL_REPLY_NOTE] if mentions_model(chat) else [],
                discussion="",
                assumptions=[],
                follow_up_questions=[],
                captured_at=None,
            ).model_dump(),
        }
        return
    yield {"type": "progress", "stage": "inspecting"}
    acquired = await read()
    payload, facts = project(acquired, request.selection)
    evidence = acquired.inspector if isinstance(acquired, GroundedCad) else acquired
    await ensure_active()
    yield {"type": "progress", "stage": "reviewing"}
    final = await adapter.answer_with_evidence(payload, request_id=request_id)
    await ensure_active()
    yield {"type": "progress", "stage": "preparing"}
    if final.safety == "refuse":
        answer = AiAnswer(
            answer=REFUSAL,
            evidence=[],
            uncertainties=[],
            discussion="",
            assumptions=[],
            follow_up_questions=[],
            captured_at=None,
        )
    else:
        answer = resolve(
            final,
            facts,
            evidence.source.captured_at,
            prompt=request.prompt,
            inspector=evidence,
            selection=request.selection,
        )
    yield {"type": "result", "result": answer.model_dump()}
