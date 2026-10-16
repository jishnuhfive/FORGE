"""Operator selection only. No automatic fallback, shared state or dynamic endpoints."""

import httpx2 as httpx

from forge_api.core.config import Settings

from .adapter import ResponsesAdapter
from .groq import GroqProvider
from .models import AiError
from .provider import AiProvider


def create_provider(settings: Settings, transport: httpx.AsyncClient) -> AiProvider:
    if not settings.ai_configured:
        raise AiError("not_configured")
    match settings.forge_ai_provider:
        case "groq":
            return GroqProvider(settings, transport)
        case "openai":
            return ResponsesAdapter(settings, transport)
    raise AiError("not_configured")
