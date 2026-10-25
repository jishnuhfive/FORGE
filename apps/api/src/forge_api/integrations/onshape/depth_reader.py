"""Internal eight-GET pinned capture. No mutation client, refresh, or retry path."""

from time import monotonic

import httpx2 as httpx
from pydantic import JsonValue, SecretStr, TypeAdapter

from forge_api.cad_edits.depth_contracts import (
    CAPTURE_SECONDS,
    DepthRecoveryDenied,
    DepthReference,
    VerifiedDepthRecoveryEvidence,
    reference_fingerprint,
)
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import StoredPlan
from forge_api.cad_edits.quantity_recovery_evidence import (
    DepthRecoveryCapture,
    check_depth_recovery_state,
)

from .client import MAX_BYTES, bounded_json
from .contracts import ACCEPT, API_VERSION, CadId, WorkspaceReference, api_origin
from .modify_evidence import project_modify_evidence


class _PinnedGetTransport(httpx.BaseTransport):
    """Enforce method, exact origin/path/query/body and sequence before any I/O."""

    def __init__(
        self,
        origin: str,
        context: WorkspaceReference,
        historical: str,
        inner: httpx.BaseTransport,
    ) -> None:
        self._base = origin + "/api/" + API_VERSION
        self._context = context
        self._inner = inner
        self._head = self._base + (
            f"/documents/d/{context.documentId}/w/{context.workspaceId}"
            "/currentmicroversion"
        )
        historical = TypeAdapter(CadId).validate_python(historical, strict=True)
        scope = f"d/{context.documentId}/m/{historical}/e/{context.elementId}"
        self.urls = [
            self._base + f"/partstudios/{scope}/features?"
            "includeGeometryIds=false&noSketchGeometry=false&rollbackBarIndex=-1",
            self._base + f"/elements/{scope}/configuration",
            self._base + f"/partstudios/{scope}/bodydetails?includeGeometricData=false",
            self._head,
        ]
        self.index = 0
        self.closed = False

    def pin(self, marker: str) -> None:
        marker = TypeAdapter(CadId).validate_python(marker, strict=True)
        if self.index != 4 or len(self.urls) != 4:
            raise DepthRecoveryDenied("reader_sequence_invalid")
        context = self._context
        scope = f"d/{context.documentId}/m/{marker}/e/{context.elementId}"
        self.urls.extend(
            [
                self._base + f"/partstudios/{scope}/features?"
                "includeGeometryIds=false&noSketchGeometry=false&rollbackBarIndex=-1",
                self._base + f"/elements/{scope}/configuration",
                self._base + f"/partstudios/{scope}/bodydetails?"
                "includeGeometricData=false",
                self._head,
            ]
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if (
            self.closed
            or self.index >= len(self.urls)
            or request.method != "GET"
            or str(request.url) != self.urls[self.index]
            or request.read() != b""
        ):
            raise DepthRecoveryDenied("reader_request_rejected")
        self.index += 1
        return self._inner.handle_request(request)

    def close(self) -> None:
        self.closed = True
        self._inner.close()


class DepthEvidenceReader:
    """An owned, disposable GET capability, never imported by DB release logic."""

    def __init__(
        self,
        api_base: str,
        context: WorkspaceReference,
        credential: SecretStr,
        historical: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        try:
            origin = api_origin(api_base)
        except ValueError:
            raise DepthRecoveryDenied("unsupported_read_origin") from None
        self._context = context
        self._historical = historical
        self._credential: SecretStr | None = credential
        self._guard = _PinnedGetTransport(
            origin,
            context,
            historical,
            transport
            if transport is not None
            else httpx.HTTPTransport(retries=0, trust_env=False),
        )
        self._client = httpx.Client(
            transport=self._guard, follow_redirects=False, trust_env=False
        )
        self._deadline = 0.0
        self._used = False

    def close(self) -> None:
        self._credential = None
        self._client.close()

    def _get(self) -> JsonValue:
        remaining = self._deadline - monotonic()
        if remaining <= 0 or self._credential is None:
            raise DepthRecoveryDenied("capture_deadline")
        url = self._guard.urls[self._guard.index]
        timeout = httpx.Timeout(
            connect=min(3, remaining),
            read=min(8, remaining),
            write=min(3, remaining),
            pool=min(2, remaining),
        )
        with self._client.stream(
            "GET",
            url,
            headers={
                "Authorization": "Bearer " + self._credential.get_secret_value(),
                "Accept": ACCEPT,
                "Accept-Encoding": "identity",
            },
            timeout=timeout,
            follow_redirects=False,
        ) as response:
            if (
                response.status_code != 200
                or response.headers.get("content-encoding", "identity") != "identity"
                or response.headers.get("content-type", "").split(";", 1)[0]
                != "application/json"
            ):
                raise DepthRecoveryDenied("read_response_rejected")
            declared = response.headers.get("content-length")
            if declared and (
                not declared.isascii()
                or not declared.isdecimal()
                or len(declared) > 10
                or int(declared) > MAX_BYTES
            ):
                raise DepthRecoveryDenied("read_response_rejected")
            content = bytearray()
            for chunk in response.iter_bytes():
                if (
                    len(content) + len(chunk) > MAX_BYTES
                    or monotonic() >= self._deadline
                ):
                    raise DepthRecoveryDenied("read_response_rejected")
                content.extend(chunk)
            if monotonic() >= self._deadline:
                raise DepthRecoveryDenied("capture_deadline")
            return bounded_json(bytes(content))

    def _head(self) -> str:
        value = self._get()
        if not isinstance(value, dict):
            raise DepthRecoveryDenied("read_response_rejected")
        return TypeAdapter(CadId).validate_python(
            value.get("microversion"), strict=True
        )

    def capture(
        self,
        reference: DepthReference,
        saved: StoredPlan,
        *,
        deadline: float | None = None,
    ) -> VerifiedDepthRecoveryEvidence:
        if self._used or reference.approval.context != self._context:
            self.close()
            raise DepthRecoveryDenied("reader_reuse_or_context_mismatch")
        self._used = True
        started = monotonic()
        self._deadline = (
            min(started + CAPTURE_SECONDS, deadline)
            if deadline is not None
            else started + CAPTURE_SECONDS
        )
        try:
            if saved.plan.baseline.microversion != self._historical:
                raise DepthRecoveryDenied("historical_revision_mismatch")
            historical_capture = DepthRecoveryCapture(
                self._context, self._historical, self._get(), self._get(), self._get()
            )
            # Reject bad history before spending the current-read quota.
            if (
                project_modify_evidence(
                    self._context,
                    self._historical,
                    historical_capture.features,
                    historical_capture.configuration,
                    historical_capture.bodies,
                ).baseline
                != saved.plan.baseline
            ):
                raise DepthRecoveryDenied("historical_baseline_mismatch")
            marker = self._head()
            self._guard.pin(marker)
            features, configuration, bodies = self._get(), self._get(), self._get()
            baseline = project_modify_evidence(
                self._context, marker, features, configuration, bodies
            ).baseline
            check_depth_recovery_state(
                saved,
                historical_capture,
                DepthRecoveryCapture(
                    self._context, marker, features, configuration, bodies
                ),
            )
            final = self._head()
            finished = monotonic()
            if final != marker or finished > self._deadline:
                raise DepthRecoveryDenied("capture_changed_or_expired")
            historical = reference.historical
            return VerifiedDepthRecoveryEvidence(
                reference_fingerprint=reference_fingerprint(reference),
                record_id=historical.record_id,
                plan_digest=historical.plan_digest,
                payload_fingerprint=historical.payload_fingerprint,
                user=reference.approval.user,
                current_generation=reference.review.current_generation,
                context=self._context,
                baseline=baseline,
                head_before=marker,
                head_after=final,
                started_monotonic=started,
                finished_monotonic=finished,
            )
        except httpx.HTTPError, ValueError, TypeError, RecursionError, EditError:
            raise DepthRecoveryDenied("read_evidence_unavailable") from None
        finally:
            self.close()
