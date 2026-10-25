"""Internal eight-GET pinned capture. No mutation client, refresh, or retry path."""

from time import monotonic
from typing import Literal, NoReturn

import httpx2 as httpx
from pydantic import JsonValue, SecretStr, TypeAdapter

from forge_api.cad_edits.depth_baseline_diagnostics import (
    BaselineDifference,
    baseline_differences,
)
from forge_api.cad_edits.depth_contracts import (
    CAPTURE_SECONDS,
    DepthRecoveryDenied,
    DepthReference,
    ServerAttestedDepthReference,
    VerifiedDepthRecoveryEvidence,
    baseline_restoration_reviewed,
    reference_fingerprint,
)
from forge_api.cad_edits.depth_inventory_diagnostics import InventoryDifference
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import StoredPlan
from forge_api.cad_edits.quantity_recovery_evidence import (
    ComparisonFailure,
    DepthRecoveryCapture,
    approved_historical_baseline,
    check_depth_baseline_restored,
    check_depth_recovery_state,
    classify_depth_comparison,
    classify_depth_comparisons,
    classify_depth_inventory,
)

from .client import MAX_BYTES, bounded_json
from .contracts import ACCEPT, API_VERSION, CadId, WorkspaceReference, api_origin
from .eligibility import EligibilityRejected, Reason
from .modify_evidence import project_modify_evidence

ReadStage = Literal[
    "historical_features",
    "historical_configuration",
    "historical_body",
    "historical_projection",
    "current_head",
    "current_features",
    "current_configuration",
    "current_body",
    "current_projection",
    "current_feature_projection",
    "current_configuration_projection",
    "current_body_projection",
    "comparison",
    "final_head",
]
ReadCategory = Literal[
    "unavailable",
    "baseline_mismatch",
    "body_invalid",
    "changed",
    "deadline",
    "transport",
    "provider_response",
    "original_baseline_mismatch",
]


class DepthReadFailure(DepthRecoveryDenied):
    """Closed stage/category only. Never accepts provider/exception text."""

    def __init__(
        self,
        stage: ReadStage,
        category: ReadCategory | ComparisonFailure,
        differences: tuple[InventoryDifference, ...] = (),
    ) -> None:
        self.stage, self.category = stage, category
        suffix = ":" + ",".join(differences) if differences else ""
        super().__init__("depth_recovery:" + stage + ":" + category + suffix)


class DepthBaselineDiagnostic(DepthRecoveryDenied):
    """Unconditional denial, composed exclusively from closed diagnostic types."""

    def __init__(
        self,
        baseline: tuple[BaselineDifference, ...],
        comparisons: tuple[ComparisonFailure, ...] | None,
        inventory: tuple[InventoryDifference, ...],
        failure: DepthReadFailure | None = None,
    ) -> None:
        summary = "depth_recovery:diagnostic:historical_baseline_mismatch:" + ",".join(
            baseline
        )
        if comparisons is not None:
            summary += ";current_comparison:" + (",".join(comparisons) or "exact_match")
            if inventory:
                summary += ":" + ",".join(inventory)
        if failure is not None:
            summary += ";current_capture:" + failure.stage + ":" + failure.category
        super().__init__(summary)


_BODY_REASONS = frozenset(
    {
        Reason.BODY_SCHEMA,
        Reason.BODY_COUNT,
        Reason.BODY_TYPE,
        Reason.BODY_ERROR,
        Reason.BODY_REVISION_MISSING,
        Reason.BODY_REVISION,
        Reason.BODY_PINNING,
        Reason.BODY_AMBIGUOUS,
        Reason.BODY_DELETED,
    }
)


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
        self._diagnostic = False

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
                    if self._diagnostic and monotonic() >= self._deadline:
                        raise DepthRecoveryDenied("capture_deadline")
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
        diagnostic = isinstance(reference, ServerAttestedDepthReference)
        self._diagnostic = diagnostic
        stage: ReadStage = "historical_features"
        historical_mismatch = False
        historical_differences: tuple[BaselineDifference, ...] = ()
        comparisons: tuple[ComparisonFailure, ...] | None = None
        inventory_differences: tuple[InventoryDifference, ...] = ()

        def deny(failure: DepthReadFailure) -> NoReturn:
            if historical_mismatch:
                raise DepthBaselineDiagnostic(
                    historical_differences, comparisons, inventory_differences, failure
                ) from None
            raise failure from None

        try:
            if saved.plan.baseline.microversion != self._historical:
                raise DepthRecoveryDenied("historical_revision_mismatch")
            features = self._get()
            stage = "historical_configuration"
            configuration = self._get()
            stage = "historical_body"
            bodies = self._get()
            historical_capture = DepthRecoveryCapture(
                self._context, self._historical, features, configuration, bodies
            )
            stage = "historical_projection"
            # Stop independent recovery; latch development diagnostic denial.
            before = project_modify_evidence(
                self._context,
                self._historical,
                historical_capture.features,
                historical_capture.configuration,
                historical_capture.bodies,
            )
            approval_baseline = approved_historical_baseline(saved, historical_capture)
            if approval_baseline != saved.plan.baseline:
                if not diagnostic:
                    raise DepthRecoveryDenied("historical_baseline_mismatch")
                historical_mismatch = True
                historical_differences = baseline_differences(
                    saved.plan.baseline, approval_baseline
                )
            stage = "current_head"
            marker = self._head()
            self._guard.pin(marker)
            stage = "current_features"
            features = self._get()
            stage = "current_configuration"
            configuration = self._get()
            stage = "current_body"
            bodies = self._get()
            stage = "current_projection"
            after = project_modify_evidence(
                self._context, marker, features, configuration, bodies
            )
            baseline = after.baseline
            stage = "comparison"
            if historical_mismatch:
                comparisons = classify_depth_comparisons(
                    before, after, saved.plan.operations[0], marker
                )
                if "inventory_mismatch" in comparisons:
                    inventory_differences = classify_depth_inventory(
                        before, after, saved.plan.operations[0], marker
                    )
            else:
                try:
                    state_check = (
                        check_depth_baseline_restored
                        if baseline_restoration_reviewed(reference)
                        else check_depth_recovery_state
                    )
                    state_check(
                        saved,
                        historical_capture,
                        DepthRecoveryCapture(
                            self._context, marker, features, configuration, bodies
                        ),
                    )
                except EditError:
                    if baseline_restoration_reviewed(reference):
                        raise DepthReadFailure(
                            stage, "original_baseline_mismatch"
                        ) from None
                    if diagnostic:
                        comparison_category = (
                            classify_depth_comparison(
                                before, after, saved.plan.operations[0], marker
                            )
                            or "unavailable"
                        )
                        differences = (
                            classify_depth_inventory(
                                before, after, saved.plan.operations[0], marker
                            )
                            if comparison_category == "inventory_mismatch"
                            else ()
                        )
                        raise DepthReadFailure(
                            stage, comparison_category, differences
                        ) from None
                    raise
            stage = "final_head"
            final = self._head()
            finished = monotonic()
            if final != marker or finished > self._deadline:
                if diagnostic:
                    raise DepthReadFailure(
                        stage, "changed" if final != marker else "deadline"
                    )
                raise DepthRecoveryDenied("capture_changed_or_expired")
            if historical_mismatch:
                # Never construct evidence or reach release for mismatched history.
                raise DepthBaselineDiagnostic(
                    historical_differences, comparisons, inventory_differences
                )
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
        except DepthBaselineDiagnostic:
            raise
        except DepthReadFailure as error:
            deny(error)
        except DepthRecoveryDenied as error:
            if diagnostic and error.args[0] in (
                "capture_deadline",
                "read_response_rejected",
            ):
                deny(
                    DepthReadFailure(
                        stage,
                        "deadline"
                        if error.args[0] == "capture_deadline"
                        else "provider_response",
                    )
                )
            if historical_mismatch:
                deny(DepthReadFailure(stage, "unavailable"))
            raise
        except httpx.HTTPError:
            if diagnostic:
                deny(DepthReadFailure(stage, "transport"))
            raise DepthRecoveryDenied("read_evidence_unavailable") from None
        except (ValueError, TypeError, RecursionError, EditError) as error:
            if diagnostic:
                category: ReadCategory = "unavailable"
                if (
                    stage == "current_projection"
                    and isinstance(error, EligibilityRejected)
                    and error.diagnostic.reason in _BODY_REASONS
                ):
                    stage = "current_body_projection"
                    category = "body_invalid"
                elif stage == "current_projection":
                    stage = (
                        "current_configuration_projection"
                        if isinstance(error, EligibilityRejected)
                        and error.diagnostic.reason
                        in (Reason.CONFIGURATION_SHAPE, Reason.CONFIGURED)
                        else "current_feature_projection"
                    )
                elif stage not in (
                    "historical_projection",
                    "current_projection",
                    "comparison",
                ):
                    category = "provider_response"
                deny(DepthReadFailure(stage, category))
            raise DepthRecoveryDenied("read_evidence_unavailable") from None
        finally:
            self.close()
