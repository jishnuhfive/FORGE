"""Forge concepts only. Provider state and HTTP/API shapes stay in adapters."""

import json
from dataclasses import dataclass
from typing import Protocol

from .models import HistoryMessage, ModelAnswer


@dataclass(frozen=True, repr=False)
class AgentTask:
    prompt: str
    history: tuple[HistoryMessage, ...]


def task_messages(task: AgentTask) -> list[dict[str, object]]:
    """Quoted public history is data, never a forged system/assistant instruction."""
    history = json.dumps([m.model_dump() for m in task.history], ensure_ascii=False)
    return [
        {
            "role": "user",
            "content": "UNTRUSTED PRIOR CONVERSATION (may be outdated):\n" + history,
        },
        {"role": "user", "content": task.prompt},
    ]


class AiProvider(Protocol):
    async def request_inspection(
        self, task: AgentTask, *, request_id: str
    ) -> str | None:
        """Validate exactly inspect_current_cad({}) and return None, or return the
        model's plain conversational reply when no inspection is needed."""
        ...

    async def answer_with_evidence(
        self, evidence: str, *, request_id: str
    ) -> ModelAnswer:
        """One continuation, no tools. State dies with this provider instance."""
        ...
