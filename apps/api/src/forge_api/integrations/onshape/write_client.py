"""Private closed CAD transport. No generic public API authority or retry."""

import json
from time import monotonic
from urllib.parse import quote

import httpx2 as httpx
from pydantic import JsonValue, TypeAdapter

from forge_api.cad_edits import plan_diagnostics
from forge_api.cad_edits.domain import Baseline, EditError, Proposal, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.core.config import Settings

from .client import MAX_BYTES, bounded_json
from .contracts import ACCEPT, API_VERSION, CadId, WorkspaceReference, api_origin
from .edit_registry import change
from .modify_evidence import ModifyEvidence, project_modify_evidence
from .semantic_inventory import semantic_feature
from .write_evidence import project_write_evidence

MAX_REQUEST_BYTES = 8 * 1024
MAX_FEATURE_REPLACEMENT_BYTES = 24 * 1024


class SafeEditClient:
    def __init__(self, settings: Settings, transport: httpx.Client, token: str) -> None:
        self._origin = api_origin(str(settings.onshape_api_base_url))
        self._enabled = settings.forge_cad_writes_enabled
        self._development = settings.environment == "development"
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
        if content is not None and len(content) > MAX_REQUEST_BYTES:
            raise EditError("invalid_request", 400)
        return self._send_measured(method, path, content)

    def _exchange_replacement(self, path: str, body: dict[str, object]) -> JsonValue:
        """Only execute_operation's validated, fresh full-definition request.

        No request field, URL pattern or planner argument selects this budget.
        Suppression and ordinary exchanges keep their independent 8 KiB cap.
        """
        if not self._enabled:
            raise EditError("write_disabled", 403)
        content = json.dumps(body, allow_nan=False).encode()
        if len(content) > MAX_FEATURE_REPLACEMENT_BYTES:
            raise EditError("invalid_request", 400)
        return self._send_measured("POST", path, content)[0]

    def _send_measured(
        self, method: str, path: str, content: bytes | None
    ) -> tuple[JsonValue, int]:
        # Final absolute ceiling, even if an internal caller is added later.
        if content is not None and len(content) > MAX_FEATURE_REPLACEMENT_BYTES:
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
        microversion, features, configuration, bodies = self._read_evidence(context)
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

    def _read_evidence(
        self, context: WorkspaceReference
    ) -> tuple[str, JsonValue, JsonValue, JsonValue]:
        microversion = self.head(context)
        scope = f"d/{context.documentId}/m/{microversion}/e/{context.elementId}"
        features = self._exchange(
            "GET",
            f"/partstudios/{scope}/features?includeGeometryIds=false&noSketchGeometry=false&rollbackBarIndex=-1",
        )
        configuration = self._exchange("GET", f"/elements/{scope}/configuration")
        bodies = self._exchange(
            "GET", f"/partstudios/{scope}/bodydetails?includeGeometricData=false"
        )
        if self.head(context) != microversion:
            raise EditError("model_changed")
        self._observe_body_evidence(bodies, microversion)
        return microversion, features, configuration, bodies

    def modify_evidence(self, context: WorkspaceReference) -> ModifyEvidence:
        microversion, features, configuration, bodies = self._read_evidence(context)
        try:
            return project_modify_evidence(
                context, microversion, features, configuration, bodies
            )
        except ValueError, TypeError:
            raise EditError("unsupported_target", 422) from None

    def _observe_body_evidence(self, bodies: JsonValue, microversion: str) -> None:
        """DEV subclass hook after the bounded, pinned reads pass head bracketing."""

    def execute_operation(
        self, evidence: ModifyEvidence, operation: ResolvedOperation
    ) -> str:
        """Closed internal dispatch from a freshly checked, already-claimed plan.

        No caller-supplied path, method, parameter identifier or payload is accepted.
        The fixed executor is the sole caller; this is never a planner tool.
        """
        stage: plan_diagnostics.DispatchStage = "request_preflight"

        def passed() -> None:
            plan_diagnostics.emit_dispatch(self._development, stage, True)

        try:
            if not self._enabled:
                raise EditError("write_disabled", 403)
            baseline = evidence.baseline
            path, body, updated, suppression = self._operation_request(
                evidence, operation
            )
            passed()
            # The larger budget is reached only after change()/preview and payload
            # preflight. Both branches send exactly once, never retry.
            stage = "provider_exchange"
            data = (
                self._exchange("POST", path, body)
                if suppression
                else self._exchange_replacement(path, body)
            )
            passed()
            stage = "ack_skew"
            if not isinstance(data, dict) or data.get("microversionSkew") is not False:
                raise EditError("verification_failed")
            passed()
            stage = "ack_feature_envelope"
            if suppression:
                returned = data.get("features")
                if not isinstance(returned, list) or len(returned) != 1:
                    raise EditError("verification_failed")
                feature = returned[0]
            else:
                feature = data.get("feature")
            if not isinstance(feature, dict):
                raise EditError("verification_failed")
            passed()
            stage = "ack_target_identity"
            if feature.get("featureId") != operation.target.feature_id:
                raise EditError("verification_failed")
            passed()
            stage = "ack_fingerprint"
            if suppression and feature.get("suppressed") is not updated["suppressed"]:
                raise EditError("verification_failed")
            if not suppression and fingerprint(
                semantic_feature(feature)
            ) != fingerprint(semantic_feature(updated)):
                raise EditError("verification_failed")
            passed()
            stage = "ack_marker_shape"
            try:
                marker = TypeAdapter(CadId).validate_python(
                    data.get("sourceMicroversion"), strict=True
                )
            except ValueError:
                raise EditError("verification_failed") from None
            passed()
            stage = "ack_marker_advance"
            if marker == baseline.microversion:
                raise EditError("verification_failed")
            passed()
            return marker
        except Exception:
            # Closed labels only: no exception text, response, CAD or identifiers.
            plan_diagnostics.emit_dispatch(self._development, stage, False)
            raise

    def check_operation(
        self, evidence: ModifyEvidence, operation: ResolvedOperation
    ) -> None:
        """Local payload preflight before recording an operation dispatch boundary."""
        self._operation_request(evidence, operation)

    def _operation_request(
        self, evidence: ModifyEvidence, operation: ResolvedOperation
    ) -> tuple[str, dict[str, object], dict[str, JsonValue], bool]:
        baseline = evidence.baseline
        context = baseline.context
        updated, preview = change(
            evidence.features(), operation.target, operation.operation
        )
        if preview != operation.preview:
            raise EditError("model_changed")
        scope = (
            f"/partstudios/d/{context.documentId}/w/{context.workspaceId}"
            f"/e/{context.elementId}/features"
        )
        body: dict[str, object] = {
            "sourceMicroversion": baseline.microversion,
            "rejectMicroversionSkew": True,
            "serializationVersion": baseline.serialization,
            "libraryVersion": baseline.library,
        }
        suppression = operation.operation.type in ("SET_SUPPRESSED", "SET_UNSUPPRESSED")
        if suppression:
            path = scope + "/updates"
            body.update(
                {
                    "btType": "BTUpdateFeaturesCall-1748",
                    "updateSuppressionAttributes": True,
                    "features": [
                        {
                            "btType": "BTMFeature-134",
                            "featureId": operation.target.feature_id,
                            "suppressed": updated["suppressed"],
                        }
                    ],
                }
            )
        else:
            # updateFeatures documents parameter/suppression updates, not rename.
            # Use the documented full-definition replacement for name/quantity;
            # preserve every fresh unrelated field within the fixed 24 KiB cap.
            path = scope + "/featureid/" + quote(operation.target.feature_id, safe="")
            body.update({"btType": "BTFeatureDefinitionCall-1406", "feature": updated})
        limit = MAX_REQUEST_BYTES if suppression else MAX_FEATURE_REPLACEMENT_BYTES
        if len(json.dumps(body, allow_nan=False).encode()) > limit:
            raise EditError("unsupported_target", 422)
        return path, body, updated, suppression

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
