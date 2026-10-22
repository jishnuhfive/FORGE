"""Request -> fresh discover -> model -> server validation -> A1 prepare().

This is the only place the planner touches A1, and it touches exactly two functions:
``discover`` and ``prepare``. It never imports or calls ``approve``, the write
client, the edit registry or any provider identity. The result is a preview.
"""

import asyncio
from typing import cast

from fastapi import Request

from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import SemanticPlan
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.service import ReadGate

from .deterministic import parse
from .models import PlannerClarification, PlannerPlan
from .providers import PlannerProvider
from .screen import screen
from .validate import PlannerError, to_result

MODEL_SECONDS = 25
# The shared CAD gate enforces a short cooldown after each CAD read. Wait it out
# (bounded) rather than fail a plan the user already waited for.
MAX_SETTLE_SECONDS = 6.0


class Unplannable(Exception):
    """The model output could not become a safe plan. Carries no model content."""


async def settle(gate: ReadGate, user_id: str) -> None:
    wait = gate.remaining(user_id)
    if wait > MAX_SETTLE_SECONDS:
        raise EditError("rate_limited", 429)
    if wait > 0:
        await asyncio.sleep(wait + 0.05)


async def plan(
    request: Request,
    auth: AuthRuntime,
    user_id: str,
    context: WorkspaceReference,
    text: str,
    provider: PlannerProvider | None,
    request_id: str,
) -> dict[str, object]:
    verdict = screen(text)
    if verdict != "ok":
        # Decided locally: no CAD read, no model call, no quota.
        return PlannerClarification(reason="unsupported_request").model_dump(
            mode="json"
        )
    targets = await asyncio.to_thread(plan_service.discover, request, auth, context)
    options = targets.targets
    result = parse(text, options)
    if result is None:
        if provider is None:
            from forge_api.ai.models import AiError

            raise AiError("not_configured")
        async with asyncio.timeout(MODEL_SECONDS):
            wire = await provider.plan(text, options, request_id=request_id)
        try:
            result = to_result(wire, options, text)
        except PlannerError:
            raise Unplannable from None
    if isinstance(result, PlannerClarification):
        return result.model_dump(mode="json")
    assert isinstance(result, PlannerPlan)
    # The catalog identity is server-owned: the model never sees or supplies it.
    semantic = SemanticPlan(
        target_catalog=targets.target_catalog, operations=result.operations
    )
    await settle(cast(ReadGate, request.app.state.cad_gate), user_id)
    preview = await asyncio.to_thread(plan_service.prepare, request, auth, semantic)
    return {"outcome": "plan", "preview": preview.model_dump(mode="json")}
