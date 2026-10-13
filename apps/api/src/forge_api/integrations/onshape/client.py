"""Four GET operations only. Transport is private; errors and telemetry are fixed."""

import json
import logging
import math
from collections.abc import Callable
from time import monotonic

import httpx2 as httpx
from pydantic import JsonValue, TypeAdapter

from .contracts import (
    ACCEPT,
    API_VERSION,
    Operation,
    WorkspaceReference,
    api_origin,
    endpoint,
)
from .models import Code, ProviderDocument, SectionState, Status
from .normalize import normalize

logger = logging.getLogger("forge.onshape.read")
MAX_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 20
TIMEOUT = httpx.Timeout(connect=3, read=8, write=3, pool=2)


class ReadError(Exception):
    def __init__(
        self, status: Status, code: Code, retry_after: int | None = None
    ) -> None:
        super().__init__(code)
        self.state = SectionState(
            status=status, code=code, retry_after_seconds=retry_after
        )


def retry_after(value: str | None) -> int | None:
    # Onshape documents delta-seconds. Dates, signs and arbitrary text are ignored.
    if value is None or len(value) > 10 or not value.isascii() or not value.isdecimal():
        return None
    return min(86400, max(1, int(value)))


def bounded_json(content: bytes) -> JsonValue:
    def invalid_constant(_: str) -> None:
        raise ValueError("Nonfinite JSON")

    def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    raw = json.loads(
        content, parse_constant=invalid_constant, object_pairs_hook=unique_keys
    )
    pending: list[tuple[object, int]] = [(raw, 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if nodes > 100000 or depth > 32:
            raise ValueError("JSON structure limit")
        if isinstance(value, dict):
            if any(len(key) > 256 for key in value):
                raise ValueError("JSON key limit")
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value)
        elif isinstance(value, str) and len(value) > 65536:
            raise ValueError("JSON string limit")
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Nonfinite JSON")
    return TypeAdapter(JsonValue).validate_python(raw, strict=True)


class OnshapeReadClient:
    def __init__(
        self,
        api_base: str,
        transport: httpx.Client,
        *,
        mass_diagnostic: Callable[[JsonValue, ValueError | None], str] | None = None,
    ) -> None:
        try:
            self._origin = api_origin(api_base)
        except ValueError:
            raise ReadError("unavailable", "unsupported_provider") from None
        self._transport = transport
        self._mass_diagnostic = mass_diagnostic
        self.mass_structure: str | None = None

    def features(
        self, reference: WorkspaceReference, token: str, correlation: str
    ) -> ProviderDocument[object]:
        return self._get(Operation.FEATURES, reference, token, correlation)

    def parts(
        self, reference: WorkspaceReference, token: str, correlation: str
    ) -> ProviderDocument[object]:
        return self._get(Operation.PARTS, reference, token, correlation)

    def bodies(
        self, reference: WorkspaceReference, token: str, correlation: str
    ) -> ProviderDocument[object]:
        return self._get(Operation.BODIES, reference, token, correlation)

    def mass(
        self, reference: WorkspaceReference, token: str, correlation: str
    ) -> ProviderDocument[object]:
        return self._get(Operation.MASS, reference, token, correlation)

    def _get(
        self,
        operation: Operation,
        reference: WorkspaceReference,
        token: str,
        correlation: str,
    ) -> ProviderDocument[object]:
        path, params = endpoint(operation, reference)
        started = monotonic()
        status_code: int | None = None
        outcome = "provider_failure"
        raw: JsonValue = None
        if operation is Operation.MASS:
            self.mass_structure = None
        try:
            # Stream bounds response size; identity avoids decompression bombs.
            with self._transport.stream(
                "GET",
                self._origin + "/api/" + API_VERSION + path,
                params=params,
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": ACCEPT,
                    "Accept-Encoding": "identity",
                    "User-Agent": "Forge/0.4 CAD-Read",
                },
                timeout=TIMEOUT,
                follow_redirects=False,
            ) as response:
                status_code = response.status_code
                if status_code == 401:
                    raise ReadError("unauthorized", "connection_required")
                if status_code == 403:
                    raise ReadError("forbidden", "document_forbidden")
                if status_code == 404:
                    raise ReadError("not_found", "not_found")
                if status_code in (402, 429):
                    raise ReadError(
                        "rate_limited",
                        "quota_exceeded" if status_code == 402 else "rate_limited",
                        retry_after(response.headers.get("retry-after")),
                    )
                if 300 <= status_code < 400:
                    raise ReadError("provider_failure", "redirect_rejected")
                if status_code != 200:
                    raise ReadError("provider_failure", "provider_unavailable")
                if (
                    response.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                    != "application/json"
                    or response.headers.get("content-encoding", "identity")
                    != "identity"
                ):
                    raise ReadError("provider_failure", "invalid_response")
                declared = response.headers.get("content-length")
                if declared and (
                    not declared.isdecimal()
                    or len(declared) > 10
                    or int(declared) > MAX_BYTES
                ):
                    raise ReadError("unavailable", "response_too_large")
                content = bytearray()
                for chunk in response.iter_bytes():
                    if monotonic() - started > MAX_SECONDS:
                        raise ReadError("provider_failure", "provider_timeout")
                    if len(content) + len(chunk) > MAX_BYTES:
                        raise ReadError("unavailable", "response_too_large")
                    content.extend(chunk)
                raw = bounded_json(bytes(content))
                document = normalize(operation, raw)
                outcome = "success"
                return document
        except ReadError as error:
            if (
                operation is Operation.MASS
                and error.state.code == "invalid_response"
                and self._mass_diagnostic
            ):
                self.mass_structure = self._mass_diagnostic(None, None)
            outcome = error.state.code
            raise
        except httpx.TimeoutException:
            outcome = "provider_timeout"
            raise ReadError("provider_failure", "provider_timeout") from None
        except httpx.HTTPError:
            outcome = "provider_unavailable"
            raise ReadError("provider_failure", "provider_unavailable") from None
        except (ValueError, RecursionError) as error:
            if operation is Operation.MASS and self._mass_diagnostic:
                self.mass_structure = self._mass_diagnostic(
                    raw, error if isinstance(error, ValueError) else ValueError()
                )
            outcome = "invalid_response"
            raise ReadError("provider_failure", "invalid_response") from None
        finally:
            # No provider URLs, IDs, payloads, request objects or exceptions here.
            logger.info(
                "onshape_read",
                extra={
                    "operation": operation.value,
                    "outcome": outcome,
                    "status_class": status_code // 100 if status_code else None,
                    "duration_ms": round((monotonic() - started) * 1000),
                    "retry_count": 0,
                    "request_id": correlation,
                },
            )
