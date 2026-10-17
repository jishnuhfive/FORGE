"""Opt-in inspector investigation: authenticated GET evidence, never a proposal."""

import logging
from typing import Literal

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.domain import EditError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.eligibility import EligibilityRejected
from forge_api.integrations.onshape.service import read_permission
from forge_api.integrations.onshape.write_client import SafeEditClient

logger = logging.getLogger("forge.onshape.safe_edit")


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
    """Development-only, two fixed GET variants; no raw results leave this call."""

    def compare(self, context: WorkspaceReference) -> None:
        marker = self.head(context)
        scope = f"d/{context.documentId}/m/{marker}/e/{context.elementId}"
        reports: list[tuple[str, StateCoverage]] = []
        for mode in ("true", "false"):
            data, size = self._exchange_measured(
                "GET",
                f"/partstudios/{scope}/features?includeGeometryIds=false&noSketchGeometry={mode}&rollbackBarIndex=-1",
            )
            reports.append((mode, coverage(data, marker, size)))
            del data
        if self.head(context) != marker:
            raise EditError("model_changed")
        for mode, report in reports:
            logger.warning(
                "safe_edit_state_coverage noSketchGeometry=%s metadata=%s",
                mode,
                report.model_dump_json(),
            )


def probe(
    auth: AuthRuntime,
    transport: httpx.Client,
    reference: WorkspaceReference,
    user_id: str,
) -> None:
    # Defense in depth if mutable test settings or a direct internal call bypass
    # startup validation. This never calls the mutation method or writes records.
    if (
        auth.settings.environment != "development"
        or not auth.settings.forge_safe_edit_diagnostics_enabled
        or auth.settings.forge_cad_writes_enabled
    ):
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
