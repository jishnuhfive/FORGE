"""Opt-in inspector investigation: authenticated GET evidence, never a proposal."""

import logging
from typing import Literal

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.domain import EditError
from forge_api.core.config import Settings
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.eligibility import (
    MISSING,
    EligibilityRejected,
    Primitive,
    primitive,
)
from forge_api.integrations.onshape.service import read_permission
from forge_api.integrations.onshape.write_client import SafeEditClient

from .modify_representation import RepresentationCoverage, representation_coverage
from .standard_parameters import StandardCoverage, standard_parameter_coverage
from .standard_shape_failure import ShapeValidation, shape_validation_coverage

logger = logging.getLogger("forge.onshape.safe_edit")


def _diagnostics_enabled(settings: Settings) -> bool:
    return (
        settings.environment == "development"
        and settings.forge_safe_edit_diagnostics_enabled
        and not settings.forge_cad_writes_enabled
    )


class PositionCoverage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    position: int = Field(ge=1, le=20)
    category: Literal["sketch", "extrude", "fillet", "unsupported"]
    state_present: bool


class StateCoverage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    is_complete: bool | None
    features: int = Field(ge=0, le=20)
    states: int = Field(ge=0)
    positions: tuple[PositionCoverage, ...]
    unmatched_state_count: int = Field(ge=0)
    source_matches: bool
    response_bytes: int = Field(ge=0, le=2 * 1024 * 1024)


class BooleanCoverage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    present: bool
    actual_type: Primitive
    value: bool | None


class SuppressionPosition(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    position: int = Field(ge=1, le=3)
    category: Literal["sketch", "extrude", "fillet", "unsupported"]
    shape: Literal["null", "object", "missing", "other"]
    bt_type: Literal["ordinary", "configured", "expression", "parent", "unknown"] | None
    suppressed: BooleanCoverage
    suppression_configured: BooleanCoverage
    parent_suppressed: BooleanCoverage


class SuppressionCoverage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    positions: tuple[SuppressionPosition, ...] = Field(max_length=3)


MarkerFlag = Literal["missing", "true", "false", "null", "wrong_type"]


class BodyCoverage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    the_id: Literal["present", "missing"]
    the_id_matches_requested: bool
    ambiguous: MarkerFlag
    deleted: MarkerFlag
    body_count: int | None = Field(ge=0, le=2000)
    body_type: Literal["SOLID", "other", "missing", "null", "wrong_type", "not_one"]
    error_enum: Literal["NO_ERROR", "other", "missing", "null", "wrong_type"]


def _marker_flag(value: object) -> MarkerFlag:
    return (
        "missing"
        if value is MISSING
        else "true"
        if value is True
        else "false"
        if value is False
        else "null"
        if value is None
        else "wrong_type"
    )


def body_coverage(data: JsonValue, marker: str) -> BodyCoverage:
    """Only fixed categories, a bounded count and exact-ID equality can escape."""
    raw = data if isinstance(data, dict) else {}
    revision = raw.get("microversionId")
    fields = revision if isinstance(revision, dict) else {}
    bodies = raw.get("bodies")
    count = len(bodies) if isinstance(bodies, list) and len(bodies) <= 2000 else None
    body = bodies[0] if isinstance(bodies, list) and count == 1 else None
    kind = body.get("type", MISSING) if isinstance(body, dict) else MISSING
    error = raw.get("errorEnum", MISSING)
    return BodyCoverage(
        the_id="present" if "theId" in fields else "missing",
        the_id_matches_requested=fields.get("theId", MISSING) == marker,
        ambiguous=_marker_flag(fields.get("ambiguous", MISSING)),
        deleted=_marker_flag(fields.get("deleted", MISSING)),
        body_count=count,
        body_type="not_one"
        if count != 1
        else "missing"
        if kind is MISSING
        else "null"
        if kind is None
        else "SOLID"
        if kind == "SOLID"
        else "other"
        if isinstance(kind, str)
        else "wrong_type",
        error_enum="missing"
        if error is MISSING
        else "null"
        if error is None
        else "NO_ERROR"
        if error == "NO_ERROR"
        else "other"
        if isinstance(error, str)
        else "wrong_type",
    )


def _boolean_coverage(feature: dict[str, JsonValue], field: str) -> BooleanCoverage:
    value = feature.get(field, MISSING)
    return BooleanCoverage(
        present=field in feature,
        actual_type=primitive(value),
        value=value if isinstance(value, bool) else None,
    )


def suppression_coverage(data: JsonValue, report: StateCoverage) -> SuppressionCoverage:
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise EditError("invalid_provider_response", 503)
    items = data["features"]
    assert isinstance(items, list)
    positions: list[SuppressionPosition] = []
    for item, summary in zip(items[:3], report.positions[:3], strict=True):
        if not isinstance(item, dict):
            raise EditError("invalid_provider_response", 503)
        raw = item.get("suppressionState", MISSING)
        bt_type = raw.get("btType") if isinstance(raw, dict) else None

        positions.append(
            SuppressionPosition(
                position=summary.position,
                category=summary.category,
                shape="missing"
                if raw is MISSING
                else "null"
                if raw is None
                else "object"
                if isinstance(raw, dict)
                else "other",
                bt_type=(
                    "ordinary"
                    if bt_type == "BTMSuppressionState-1924"
                    else "configured"
                    if bt_type == "BTMSuppressionStateConfigured-2598"
                    else "expression"
                    if bt_type == "BTMSuppressionStateExpression-1811"
                    else "parent"
                    if bt_type == "BTMSuppressionStateParentSuppressed-5404"
                    else "unknown"
                )
                if isinstance(raw, dict)
                else None,
                suppressed=_boolean_coverage(item, "suppressed"),
                suppression_configured=_boolean_coverage(item, "suppressionConfigured"),
                parent_suppressed=_boolean_coverage(item, "parentSuppressed"),
            )
        )
    return SuppressionCoverage(positions=tuple(positions))


def coverage(data: JsonValue, marker: str, response_bytes: int) -> StateCoverage:
    """Minimize request-local provider data before any diagnostic can escape."""
    if not isinstance(data, dict):
        raise EditError("invalid_provider_response", 503)
    items, states = data.get("features"), data.get("featureStates")
    if not isinstance(items, list) or len(items) > 20 or not isinstance(states, dict):
        raise EditError("invalid_provider_response", 503)
    positions: list[PositionCoverage] = []
    matched: set[str] = set()
    for position, feature in enumerate(items, 1):
        if not isinstance(feature, dict):
            raise EditError("invalid_provider_response", 503)
        identity, kind = feature.get("featureId"), feature.get("featureType")
        present = isinstance(identity, str) and identity in states
        if present and isinstance(identity, str):
            matched.add(identity)
        positions.append(
            PositionCoverage(
                position=position,
                category="sketch"
                if kind == "newSketch"
                else "extrude"
                if kind == "extrude"
                else "fillet"
                if kind == "fillet"
                else "unsupported",
                state_present=present,
            )
        )
    complete = data.get("isComplete")
    return StateCoverage(
        is_complete=complete if isinstance(complete, bool) else None,
        features=len(items),
        states=len(states),
        positions=tuple(positions),
        unmatched_state_count=len(states) - len(matched),
        source_matches=data.get("sourceMicroversion") == marker,
        response_bytes=response_bytes,
    )


class CoverageClient(SafeEditClient):
    def __init__(self, settings: Settings, transport: httpx.Client, token: str) -> None:
        super().__init__(settings, transport, token)
        self._diagnostic_settings = settings

    def _representation(
        self, data: JsonValue, *, source_matches: bool
    ) -> RepresentationCoverage | None:
        # Independent guard before projection, even for direct internal calls or
        # mutable Settings that bypassed startup/probe admission. No IO here.
        if not _diagnostics_enabled(self._diagnostic_settings):
            return None
        return representation_coverage(data, source_matches=source_matches)

    def _observe_body_evidence(self, bodies: JsonValue, microversion: str) -> None:
        logger.warning(
            "safe_edit_body_coverage metadata=%s",
            body_coverage(bodies, microversion).model_dump_json(),
        )

    def _standard_parameters(
        self, data: JsonValue, *, source_matches: bool
    ) -> StandardCoverage | None:
        if not _diagnostics_enabled(self._diagnostic_settings):
            return None
        return standard_parameter_coverage(data, source_matches=source_matches)

    def _shape_validation(
        self, data: JsonValue, *, source_matches: bool
    ) -> tuple[ShapeValidation, ...] | None:
        if (
            not _diagnostics_enabled(self._diagnostic_settings)
            or not source_matches
            or not isinstance(data, dict)
            or data.get("isComplete") is not True
        ):
            return None
        return shape_validation_coverage(data)

    """Development-only, two fixed GET variants; no raw results leave this call."""

    def compare(self, context: WorkspaceReference) -> None:
        marker = self.head(context)
        scope = f"d/{context.documentId}/m/{marker}/e/{context.elementId}"
        reports: list[
            tuple[
                str,
                StateCoverage,
                SuppressionCoverage,
                RepresentationCoverage | None,
                StandardCoverage | None,
                tuple[ShapeValidation, ...] | None,
            ]
        ] = []
        for mode in ("true", "false"):
            data, size = self._exchange_measured(
                "GET",
                f"/partstudios/{scope}/features?includeGeometryIds=false&noSketchGeometry={mode}&rollbackBarIndex=-1",
            )
            report = coverage(data, marker, size)
            reports.append(
                (
                    mode,
                    report,
                    suppression_coverage(data, report),
                    self._representation(data, source_matches=report.source_matches),
                    self._standard_parameters(
                        data, source_matches=report.source_matches
                    ),
                    self._shape_validation(data, source_matches=report.source_matches),
                )
            )
            del data
        if self.head(context) != marker:
            raise EditError("model_changed")
        for mode, report, suppression, representation, standard, shapes in reports:
            logger.warning(
                "safe_edit_state_coverage noSketchGeometry=%s metadata=%s",
                mode,
                report.model_dump_json(),
            )
            logger.warning(
                "safe_edit_suppression_coverage noSketchGeometry=%s metadata=%s",
                mode,
                suppression.model_dump_json(),
            )
            # Check again immediately before logging: an intervening flag change
            # cannot emit representation metadata from a now-disabled diagnostic.
            if representation is not None and _diagnostics_enabled(
                self._diagnostic_settings
            ):
                logger.warning(
                    "safe_edit_representation_coverage noSketchGeometry=%s metadata=%s",
                    mode,
                    representation.model_dump_json(),
                )
            if standard is not None and _diagnostics_enabled(self._diagnostic_settings):
                logger.warning(
                    "safe_edit_standard_parameter_coverage "
                    "noSketchGeometry=%s metadata=%s",
                    mode,
                    standard.model_dump_json(),
                )
            for shape in shapes or ():
                if not _diagnostics_enabled(self._diagnostic_settings):
                    break
                if shape.failure is None:
                    logger.warning(
                        "safe_edit_standard_shape_validation "
                        "category=%s outcome=exact_match",
                        shape.category,
                    )
                elif shape.common is not None:
                    logger.warning(
                        "safe_edit_standard_shape_failure "
                        "category=%s parameter=%s reason=%s "
                        "common_field=%s present=true state=%s",
                        shape.category,
                        shape.failure.parameter,
                        shape.failure.reason,
                        shape.common.field,
                        shape.common.state,
                    )
                else:
                    logger.warning(
                        "safe_edit_standard_shape_failure "
                        "category=%s parameter=%s reason=%s",
                        shape.category,
                        shape.failure.parameter,
                        shape.failure.reason,
                    )


def probe(
    auth: AuthRuntime,
    transport: httpx.Client,
    reference: WorkspaceReference,
    user_id: str,
) -> None:
    # Defense in depth if mutable test settings or a direct internal call bypass
    # startup validation. This never calls the mutation method or writes records.
    if not _diagnostics_enabled(auth.settings):
        return
    if read_permission(auth, user_id) is not True:
        logger.warning("safe_edit_probe outcome=read_permission_unknown_or_missing")
        return
    try:
        token = auth.tokens.get_valid_onshape_access_token(user_id)
        client = CoverageClient(auth.settings, transport, token)
        client.compare(reference)
        client.evidence(reference)
    except EligibilityRejected:
        # The projection already emitted only closed fixed metadata.
        return
    except EditError, ProviderError:
        logger.warning("safe_edit_probe outcome=read_unavailable")
        return
    logger.warning("safe_edit_probe outcome=eligible_no_proposal_no_write")
