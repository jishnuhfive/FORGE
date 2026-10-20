"""Human-only generalized approval transport; A1 retains all CAD authority."""

import asyncio
import re
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from forge_api.auth.routes import Runtime
from forge_api.integrations.onshape.contracts import WorkspaceReference

from . import plan_recovery, plan_service
from .domain import Closed, EditError
from .plan_events import (
    MAX_EVENT_BYTES,
    MAX_EVENTS,
    MAX_STREAM_BYTES,
    ErrorEvent,
    Progress,
    ResultEvent,
    StreamEvent,
)
from .routes import Approve, enabled, error_response, guard

router = APIRouter()


def valid_handle(handle: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", handle):
        raise EditError("proposal_unavailable", 404)


class EventBuffer:
    """Event-loop owned, bounded and nonblocking even after a disconnect.

    Reserve one event/line for the real final result (or a conservative error).
    Dropping a presentation event must never alter execution or fill a worker's
    queue indefinitely. Only validated server-created closed models enter here.
    """

    def __init__(self) -> None:
        self.queue: asyncio.Queue[str | EditError] = asyncio.Queue(MAX_EVENTS)
        self.count = 0
        self.size = 0

    def put(self, event: StreamEvent) -> None:
        line = event.model_dump_json() + "\n"
        size = len(line.encode())
        terminal = isinstance(event, ResultEvent | ErrorEvent)
        reserve = 0 if terminal else 1
        if (
            size > MAX_EVENT_BYTES
            or self.count >= MAX_EVENTS - reserve
            or self.size + size > MAX_STREAM_BYTES - reserve * MAX_EVENT_BYTES
        ):
            return
        self.count += 1
        self.size += size
        self.queue.put_nowait(line)


@router.post("/api/modify/plans/{handle}/approve", response_model=None)
async def approve(
    request: Request, auth: Runtime, handle: str
) -> JSONResponse | StreamingResponse:
    raw = await guard(request, auth)
    try:
        valid_handle(handle)
        enabled(auth)
        value = Approve.model_validate(raw)
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)

    loop = asyncio.get_running_loop()
    buffer = EventBuffer()

    def progress(event: Progress) -> None:
        loop.call_soon_threadsafe(buffer.put, event)

    async def run() -> None:
        try:
            result = await asyncio.to_thread(
                plan_service.approve, request, auth, handle, value.digest, progress
            )
            buffer.put(ResultEvent(**result.model_dump()))
        except EditError as error:
            # A1 raises admission/claim errors before emitting any progress.
            # After claim, never assert that a potentially dispatched write failed.
            if buffer.count == 0:
                buffer.queue.put_nowait(error)
            else:
                buffer.put(ErrorEvent())
        except Exception:
            if buffer.count == 0:
                buffer.queue.put_nowait(EditError("execution_uncertain", 503))
            else:
                buffer.put(ErrorEvent())

    task = asyncio.create_task(run())
    # Strong application-owned reference, independent of the stream consumer.
    tasks = cast(set[asyncio.Task[None]], request.app.state.plan_executions)
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    # Claim/digest/ownership errors must retain normal HTTP status codes. Waiting
    # for the first presentation event does not own/cancel the execution task.
    first = await buffer.queue.get()
    if isinstance(first, EditError):
        return error_response(first)

    async def events() -> AsyncIterator[str]:
        line = first
        try:
            while True:
                yield line
                if task.done() and buffer.queue.empty():
                    break
                item = await buffer.queue.get()
                assert isinstance(item, str)
                line = item
        finally:
            # Never re-enter approve on cancellation, lost ack or stream failure.
            await asyncio.shield(task)

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


@router.post("/api/modify/plans/{handle}/cancel")
async def cancel(request: Request, auth: Runtime, handle: str) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        valid_handle(handle)
        Closed.model_validate(raw)
        result = await asyncio.to_thread(plan_service.cancel, request, auth, handle)
        return JSONResponse(result.model_dump(mode="json"))
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)


@router.get("/api/modify/plans/{handle}")
async def status(request: Request, auth: Runtime, handle: str) -> JSONResponse:
    await guard(request, auth)
    try:
        valid_handle(handle)
        result = await asyncio.to_thread(plan_service.status, request, auth, handle)
        return JSONResponse(result.model_dump(mode="json"))
    except EditError as error:
        return error_response(error)


class RecoveryRequest(Closed):
    context: WorkspaceReference


@router.post("/api/modify/recovery")
async def recovery(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        value = RecoveryRequest.model_validate(raw)
        result = await asyncio.to_thread(
            plan_recovery.discover, request, auth, value.context
        )
        return JSONResponse(
            result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)


@router.post("/api/modify/plans/{handle}/reconcile")
async def reconcile(request: Request, auth: Runtime, handle: str) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        valid_handle(handle)
        Closed.model_validate(raw)
        result = await asyncio.to_thread(plan_recovery.reconcile, request, auth, handle)
        return JSONResponse(
            result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)
