"""Private fixed transport for one operation. No generic API authority or retry."""

import json
from time import monotonic

import httpx2 as httpx
from pydantic import JsonValue, TypeAdapter

from forge_api.cad_edits.domain import Baseline, EditError, Proposal
from forge_api.core.config import Settings

from .client import MAX_BYTES, bounded_json
from .contracts import ACCEPT, API_VERSION, CadId, WorkspaceReference, api_origin
from .write_evidence import project_write_evidence


class SafeEditClient:
    def __init__(self, settings: Settings, transport: httpx.Client, token: str) -> None:
        self._origin = api_origin(str(settings.onshape_api_base_url))
        self._enabled = settings.forge_cad_writes_enabled
        self._transport = transport
        self._token = token
        self._deadline = monotonic() + 30

    def _exchange(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> JsonValue:
        return self._exchange_measured(method, path, body)[0]

    def _exchange_measured(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> tuple[JsonValue, int]:
        content = (
            json.dumps(body, allow_nan=False).encode() if body is not None else None
        )
        if content is not None and len(content) > 8192:
            raise EditError("invalid_request", 400)
        started = monotonic()
        remaining = self._deadline - started
        if remaining <= 0:
            raise EditError("onshape_unavailable", 503)
        timeout = httpx.Timeout(
            connect=min(3, remaining),
            read=min(8, remaining),
            write=min(3, remaining),
            pool=min(2, remaining),
        )
        try:
            with self._transport.stream(
                method,
                self._origin + "/api/" + API_VERSION + path,
                content=content,
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Accept": ACCEPT,
                    "Accept-Encoding": "identity",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise EditError(
                        "permission_or_access_required"
                        if response.status_code in (401, 403)
                        else "rate_limited"
                        if response.status_code in (402, 429)
                        else "onshape_unavailable",
                        503,
                    )
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    raise EditError("invalid_provider_response", 503)
                declared = response.headers.get("content-length")
                if declared and (
                    not declared.isdecimal()
                    or len(declared) > 10
                    or int(declared) > MAX_BYTES
                ):
                    raise EditError("invalid_provider_response", 503)
                payload = bytearray()
                for chunk in response.iter_bytes():
                    payload.extend(chunk)
                    if len(payload) > MAX_BYTES or monotonic() >= self._deadline:
                        raise EditError("invalid_provider_response", 503)
                return bounded_json(bytes(payload)), len(payload)
        except httpx.HTTPError, ValueError, RecursionError:
            raise EditError("onshape_unavailable", 503) from None

    def head(self, context: WorkspaceReference) -> str:
        data = self._exchange(
            "GET",
            f"/documents/d/{context.documentId}/w/{context.workspaceId}/currentmicroversion",
        )
        if not isinstance(data, dict):
            raise EditError("invalid_provider_response", 503)
        try:
            return TypeAdapter(CadId).validate_python(
                data.get("microversion"), strict=True
            )
        except ValueError:
            raise EditError("invalid_provider_response", 503) from None

    def evidence(self, context: WorkspaceReference, *, after: bool = False) -> Baseline:
        microversion = self.head(context)
        scope = f"d/{context.documentId}/m/{microversion}/e/{context.elementId}"
        features = self._exchange(
            "GET",
            f"/partstudios/{scope}/features?includeGeometryIds=false&noSketchGeometry=true&rollbackBarIndex=-1",
        )
        configuration = self._exchange("GET", f"/elements/{scope}/configuration")
        bodies = self._exchange(
            "GET", f"/partstudios/{scope}/bodydetails?includeGeometricData=false"
        )
        if self.head(context) != microversion:
            raise EditError("model_changed")
        self._observe_body_evidence(bodies, microversion)
        try:
            return project_write_evidence(
                context,
                microversion,
                features,
                configuration,
                bodies,
                after=after,
                pinned_body_microversion=microversion,
            )
        except ValueError, TypeError:
            raise EditError("unsupported_target", 422) from None

    def _observe_body_evidence(self, bodies: JsonValue, microversion: str) -> None:
        """DEV subclass hook after the bounded, pinned reads pass head bracketing."""

    def suppress_terminal_fillet(self, proposal: Proposal) -> str:
        if not self._enabled:
            raise EditError("write_disabled", 403)
        if (
            proposal.baseline.suppressed
            or proposal.expected_suppressed is not False
            or proposal.proposed_suppressed is not True
            or proposal.binding.context != proposal.baseline.context
        ):
            raise EditError("invalid_request", 400)
        baseline = proposal.baseline
        context = proposal.binding.context
        data = self._exchange(
            "POST",
            f"/partstudios/d/{context.documentId}/w/{context.workspaceId}/e/{context.elementId}/features/updates",
            {
                "btType": "BTUpdateFeaturesCall-1748",
                "sourceMicroversion": baseline.microversion,
                "rejectMicroversionSkew": True,
                "serializationVersion": baseline.serialization,
                "libraryVersion": baseline.library,
                "updateSuppressionAttributes": True,
                "features": [
                    {
                        "btType": "BTMFeature-134",
                        "featureId": baseline.feature_id,
                        "suppressed": True,
                    }
                ],
            },
        )
        if not isinstance(data, dict) or data.get("microversionSkew") is not False:
            raise EditError("verification_failed")
        features = data.get("features")
        if (
            not isinstance(features, list)
            or len(features) != 1
            or not isinstance(features[0], dict)
            or features[0].get("featureId") != baseline.feature_id
            or features[0].get("suppressed") is not True
        ):
            raise EditError("verification_failed")
        try:
            marker = TypeAdapter(CadId).validate_python(
                data.get("sourceMicroversion"), strict=True
            )
        except ValueError:
            raise EditError("verification_failed") from None
        if marker == baseline.microversion:
            raise EditError("verification_failed")
        return marker
