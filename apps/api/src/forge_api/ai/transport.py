"""Bounded transport shared by reviewed providers; no content/error-body logging."""

import logging
import re
from contextlib import suppress
from typing import Final, Literal

import httpx2 as httpx
from pydantic import SecretStr

from forge_api.integrations.onshape.client import bounded_json, retry_after

from .diagnostics import Reason, provider_details
from .models import AiError

OPENAI_ENDPOINT: Final = "https://api.openai.com/v1/responses"
GROQ_ENDPOINT: Final = "https://api.groq.com/openai/v1/chat/completions"
Endpoint = Literal[
    "https://api.openai.com/v1/responses",
    "https://api.groq.com/openai/v1/chat/completions",
]
MAX_RESPONSE_BYTES = 262144
TIMEOUT = httpx.Timeout(connect=5, read=45, write=5, pool=2)
logger = logging.getLogger("forge.ai")


async def post_json(
    transport: httpx.AsyncClient,
    endpoint: Endpoint,
    key: SecretStr,
    payload: dict[str, object],
    request_id: str,
) -> object:
    if endpoint not in (OPENAI_ENDPOINT, GROQ_ENDPOINT):
        raise AiError("invalid_response")
    try:
        async with transport.stream(
            "POST",
            endpoint,
            json=payload,
            timeout=TIMEOUT,
            headers={
                "Authorization": "Bearer " + key.get_secret_value(),
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "X-Client-Request-Id": request_id,
            },
            follow_redirects=False,
        ) as response:
            provider_id = response.headers.get("x-request-id", "")
            logger.info(
                "ai_round_trip",
                extra={
                    "request_id": request_id,
                    "provider_request_id": provider_id
                    if re.fullmatch(r"[A-Za-z0-9_-]{1,200}", provider_id)
                    else None,
                    "status_class": response.status_code // 100,
                },
            )
            if response.status_code in (401, 403):
                raise AiError("authentication_failed")
            if response.headers.get("content-encoding", "identity") != "identity":
                raise AiError("invalid_response")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_RESPONSE_BYTES:
                    raise AiError("invalid_response")
            if endpoint == GROQ_ENDPOINT and response.status_code in (413, 429, 498):
                # Organization-wide RPM/TPM/RPD/TPD limits share this safe state.
                # No inference from private error prose, no paid-provider fallback.
                raise AiError(
                    "capacity_unavailable",
                    retry_after(response.headers.get("retry-after")) or 60,
                )
            if response.status_code == 429:
                quota = False
                try:
                    raw = bounded_json(bytes(content))
                    error = raw.get("error") if isinstance(raw, dict) else None
                    quota = (
                        isinstance(error, dict)
                        and error.get("code") == "insufficient_quota"
                    )
                except ValueError:
                    pass
                raise AiError(
                    "quota_unavailable" if quota else "rate_limited",
                    retry_after(response.headers.get("retry-after")) or 60,
                )
            if response.status_code >= 500:
                raise AiError(
                    "connection_unavailable", http_status=response.status_code
                )
            if (
                response.status_code != 200
                or "application/json" not in response.headers.get("content-type", "")
            ):
                code, kind, param = None, None, None
                if endpoint == GROQ_ENDPOINT:
                    with suppress(ValueError, UnicodeError):
                        code, kind, param = provider_details(
                            bounded_json(bytes(content))
                        )
                raise AiError(
                    "invalid_response",
                    reason=Reason.PROVIDER_TOOL_GENERATION_FAILED
                    if code == "tool_use_failed"
                    else Reason.PROVIDER_REQUEST_REJECTED,
                    http_status=response.status_code,
                    provider_error_code=code,
                    provider_error_type=kind,
                    provider_error_param=param,
                )
            try:
                return bounded_json(bytes(content))
            except ValueError, UnicodeError:
                raise AiError(
                    "invalid_response",
                    reason=Reason.PROVIDER_MALFORMED_JSON,
                    http_status=response.status_code,
                ) from None
    except httpx.TimeoutException:
        raise AiError("timeout") from None
    except httpx.HTTPError:
        raise AiError("connection_unavailable") from None
    except ValueError, UnicodeError:
        raise AiError("invalid_response") from None
