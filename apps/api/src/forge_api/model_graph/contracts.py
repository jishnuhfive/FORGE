"""Closed, immutable read evidence. No credentials, provider JSON or authority."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.models import Code, Status
from forge_api.integrations.onshape.parameters import display_text

MAX_FEATURES = 2000
MAX_PARTS = 2000
MAX_BODIES = 2000
MAX_SELECTIONS = 1
MAX_NODES = MAX_FEATURES + MAX_PARTS + MAX_BODIES + 4
MAX_EDGES = 1 + MAX_FEATURES + MAX_PARTS + MAX_BODIES + MAX_FEATURES - 1 + 1
MAX_SERIALIZED_BYTES = 8 * 1024 * 1024


def opaque(value: str) -> str:
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid opaque identifier")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("invalid opaque identifier") from None
    return value


def display(value: str) -> str:
    if display_text(value) is None:
        raise ValueError("invalid display text")
    return value


def timestamp(value: str) -> str:
    try:
        if (
            re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
                value,
            )
            is None
        ):
            raise ValueError
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(UTC).isoformat()
    except ValueError, OverflowError:
        raise ValueError("invalid capture timestamp") from None


ProviderId = Annotated[str, Field(min_length=1, max_length=256), AfterValidator(opaque)]
SelectionReference = Annotated[
    str, Field(min_length=1, max_length=1024), AfterValidator(opaque)
]
DisplayText = Annotated[str, Field(max_length=256), AfterValidator(display)]
Timestamp = Annotated[
    str, Field(min_length=20, max_length=40), AfterValidator(timestamp)
]
NodeKind = Literal[
    "workspace",
    "part_studio",
    "feature",
    "part",
    "body",
    "selection",
    "entity_reference",
]
SourceId = Literal["context", "features", "parts", "bodies", "selection"]
EvidenceState = Literal["complete", "partial", "unavailable", "unknown"]
Availability = Literal["available", "unavailable", "unknown"]
Relation = Literal["CONTAINS", "PRECEDES", "REFERENCES"]
EntityType = Literal["FACE", "EDGE"]
NodeId = Annotated[
    str,
    Field(
        pattern=r"^fmg1:(workspace|part_studio|feature|part|body|selection|entity_reference):[a-f0-9]{64}$"
    ),
]
EdgeId = Annotated[str, Field(pattern=r"^fmg1:edge:[a-f0-9]{64}$")]
SOURCE_ORDER: tuple[SourceId, ...] = (
    "context",
    "features",
    "parts",
    "bodies",
    "selection",
)
NODE_ORDER: tuple[NodeKind, ...] = (
    "workspace",
    "part_studio",
    "feature",
    "part",
    "body",
    "selection",
    "entity_reference",
)


class Closed(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class CaptureIdentity(Closed):
    """Request-envelope binding, not a provider-echoed context or atomic snapshot."""

    context: WorkspaceReference
    captured_at: Timestamp
    provider_origin: Literal["https://cad.onshape.com"] = "https://cad.onshape.com"
    provider_api_version: Annotated[str, Field(min_length=1, max_length=64)]
    provider_schema_version: Annotated[str, Field(min_length=1, max_length=128)]
    configuration: Literal["default"] = "default"
    freshness: Literal["captured_unverified"] = "captured_unverified"
    consistency: Literal["unverified"] = "unverified"

    @field_validator("context", mode="before")
    @classmethod
    def recheck_context(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, WorkspaceReference) else value


class Provenance(Closed):
    id: SourceId
    capture: CaptureIdentity
    mode: Literal[
        "request_scope",
        "normalized_workspace_read",
        "browser_observation",
        "unobserved_selection",
    ]
    state: EvidenceState
    status: Status | None = None
    code: Code | None = None
    microversions: Annotated[tuple[ProviderId, ...], Field(max_length=1)] = ()
    returned_count: Annotated[int, Field(ge=0, le=2000)] | None = None
    # Only the feature endpoint reports these completeness/evaluation fields.
    list_complete: bool | None = None
    microversion_skew: bool | None = None
    rollback_index: Annotated[int, Field(ge=-1, le=2000)] | None = None
    serialization_version: Annotated[str, Field(max_length=4096)] | None = None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.microversion_skew is True:
            raise ValueError("skewed feature evidence")
        read = self.id in ("features", "parts", "bodies")
        if read:
            if (
                self.mode != "normalized_workspace_read"
                or self.status is None
                or self.code is None
            ):
                raise ValueError("invalid read provenance")
            if (self.status == "success") != (self.code == "ok"):
                raise ValueError("invalid section outcome")
            if self.status == "success":
                expected = (
                    "complete"
                    if self.id != "features" or self.list_complete is True
                    else "partial"
                    if self.list_complete is False
                    else "unknown"
                )
                if self.state != expected or self.returned_count is None:
                    raise ValueError("invalid read coverage")
            elif (
                self.state != "unavailable"
                or self.returned_count is not None
                or self.microversions
            ):
                raise ValueError("unavailable read contains evidence")
        elif (
            self.status is not None
            or self.code is not None
            or self.microversions
            or self.returned_count is not None
        ):
            raise ValueError("invalid observation provenance")
        if self.id == "context" and (
            self.mode != "request_scope" or self.state != "complete"
        ):
            raise ValueError("invalid context provenance")
        if self.id == "selection" and self.mode not in (
            "browser_observation",
            "unobserved_selection",
        ):
            raise ValueError("invalid selection provenance")
        if (self.id != "features" or self.status != "success") and (
            self.list_complete is not None
            or self.microversion_skew is not None
            or self.rollback_index is not None
            or self.serialization_version is not None
        ):
            raise ValueError("unexpected feature evidence")
        if (
            self.rollback_index is not None
            and self.returned_count is not None
            and self.rollback_index > self.returned_count
        ):
            raise ValueError("invalid rollback evidence")
        return self


class FeatureRecord(Closed):
    provider_id: ProviderId
    label: DisplayText | None = None
    feature_type: DisplayText | None = None
    suppressed: bool | None = None
    custom_namespace: bool | None = None

    @field_validator("custom_namespace")
    @classmethod
    def namespace_evidence(cls, value: bool | None) -> bool | None:
        # The existing summary collapses missing/empty namespaces to False.
        # It cannot establish a negative provider fact or standard eligibility.
        if value is False:
            raise ValueError("negative namespace evidence is unavailable")
        return value


class PartRecord(Closed):
    provider_id: ProviderId
    label: DisplayText | None = None
    body_type: DisplayText | None = None
    is_mesh: bool | None = None
    microversion: ProviderId | None = None


class BodyRecord(Closed):
    provider_id: ProviderId
    body_type: DisplayText | None = None
    face_count: Annotated[int, Field(ge=0, le=20000)] | None = None
    edge_count: Annotated[int, Field(ge=0, le=20000)] | None = None
    vertex_count: Annotated[int, Field(ge=0, le=20000)] | None = None


class EvidenceList[T](Closed):
    source: Provenance
    items: Annotated[tuple[T, ...], Field(max_length=2000)]


class SelectionObservation(Closed):
    """Association with one capture; never establishes CAD membership/ownership."""

    capture: CaptureIdentity
    mode: Literal["browser_observation", "unobserved_selection"] = "browser_observation"
    state: Literal["selected", "clear", "unknown", "unavailable", "stale"]
    entity_type: EntityType | None = None
    reference: SelectionReference | None = None

    @model_validator(mode="after")
    def bounded_selection(self) -> Self:
        if self.state == "selected":
            if self.entity_type is None:
                raise ValueError("selected entity type required")
        elif self.entity_type is not None or self.reference is not None:
            raise ValueError("nonselected observation contains an entity")
        if self.mode == "unobserved_selection" and self.state != "unknown":
            raise ValueError("unobserved selection must remain unknown")
        return self


def selection_provenance(observation: SelectionObservation) -> Provenance:
    state: EvidenceState = (
        "complete"
        if observation.state in ("selected", "clear")
        else "unavailable"
        if observation.state == "unavailable"
        else "unknown"
    )
    if observation.state == "selected" and observation.reference is None:
        state = "partial"
    return Provenance(
        id="selection", capture=observation.capture, mode=observation.mode, state=state
    )


class GraphEvidence(Closed):
    capture: CaptureIdentity
    features: EvidenceList[FeatureRecord]
    parts: EvidenceList[PartRecord]
    bodies: EvidenceList[BodyRecord]
    selection: SelectionObservation

    @model_validator(mode="after")
    def one_capture(self) -> Self:
        markers: set[str] = set()
        for name, section in (
            ("features", self.features),
            ("parts", self.parts),
            ("bodies", self.bodies),
        ):
            source = section.source
            if source.id != name or source.capture != self.capture:
                raise ValueError("mixed capture evidence")
            if source.status in ("unauthorized", "forbidden"):
                raise ValueError("unauthorized evidence")
            if len(section.items) != (source.returned_count or 0):
                raise ValueError("inconsistent collection evidence")
            ids = [item.provider_id for item in section.items]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate provider identity")
            markers.update(source.microversions)
        part_markers = {
            part.microversion
            for part in self.parts.items
            if part.microversion is not None
        }
        if part_markers != set(self.parts.source.microversions):
            raise ValueError("inconsistent part revision evidence")
        if len(markers) > 1:
            raise ValueError("mixed microversion evidence")
        if self.selection.capture != self.capture or self.selection.state == "stale":
            raise ValueError("stale or mixed selection evidence")
        return self


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def node_id(
    capture: CaptureIdentity,
    kind: NodeKind,
    provider_id: str | None = None,
    *,
    entity_type: EntityType | None = None,
) -> str:
    scope = [
        capture.provider_origin,
        capture.context.documentId,
        capture.context.workspaceId,
    ]
    if kind != "workspace":
        scope.append(capture.context.elementId)
    # Selection references have no established continuity across captures/edits.
    if kind == "entity_reference":
        scope.append(capture.captured_at)
        if entity_type is None:
            raise ValueError("selection entity type required for identity")
    return (
        f"fmg1:{kind}:"
        + hashlib.sha256(canonical([scope, kind, provider_id, entity_type])).hexdigest()
    )


def edge_id(kind: Relation, source: str, target: str) -> str:
    return "fmg1:edge:" + hashlib.sha256(canonical([kind, source, target])).hexdigest()
