"""Identity-preserving projection of existing normalized reads. Raw is never read."""

from typing import Literal

from pydantic import TypeAdapter

from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.models import (
    BodySummary,
    FeatureSummary,
    FeatureSummaryList,
    MassSummary,
    PartSummary,
    ProviderDocument,
    SectionState,
    Snapshot,
)
from forge_api.integrations.onshape.parameters import display_text

from .builder import build_graph
from .contracts import (
    MAX_BODIES,
    MAX_FEATURES,
    MAX_PARTS,
    BodyRecord,
    CaptureIdentity,
    EvidenceList,
    FeatureRecord,
    GraphEvidence,
    PartRecord,
    Provenance,
    ProviderId,
    SelectionObservation,
    SourceId,
)
from .graph import ForgeModelGraphV1


def capture_identity(
    snapshot: Snapshot,
    expected_context: WorkspaceReference,
    *,
    expected_captured_at: str | None = None,
    freshness: Literal["captured_unverified", "stale"] = "captured_unverified",
) -> CaptureIdentity:
    expected = WorkspaceReference.model_validate(expected_context.model_dump())
    context = WorkspaceReference.model_validate(snapshot.context.model_dump())
    if context != expected or freshness != "captured_unverified":
        raise ValueError("stale or mixed snapshot context")
    if (
        expected_captured_at is not None
        and snapshot.captured_at != expected_captured_at
    ):
        raise ValueError("unexpected snapshot capture")
    if snapshot.consistency != "unverified":
        raise ValueError("inconsistent snapshot")
    return CaptureIdentity(
        context=context,
        captured_at=snapshot.captured_at,
        provider_api_version=snapshot.provider_api_version,
        provider_schema_version=snapshot.provider_schema_version,
    )


def selection_from_category(
    capture: CaptureIdentity, category: Literal["none", "FACE", "EDGE", "unknown"]
) -> SelectionObservation:
    """The existing backend request carries a category, not an entity reference."""
    if category in ("FACE", "EDGE"):
        return SelectionObservation(
            capture=capture, state="selected", entity_type=category
        )
    if category not in ("none", "unknown"):
        raise ValueError("unsupported selection category")
    return SelectionObservation(
        capture=capture, state="clear" if category == "none" else "unknown"
    )


def _display(value: str | None) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("invalid normalized text")
    return display_text(value) or None


def _custom_namespace(value: bool) -> bool | None:
    if type(value) is not bool:
        raise ValueError("invalid normalized namespace flag")
    return True if value else None


def evidence_from_snapshot(
    snapshot: Snapshot,
    expected_context: WorkspaceReference,
    *,
    selection: SelectionObservation | None = None,
    expected_captured_at: str | None = None,
    freshness: Literal["captured_unverified", "stale"] = "captured_unverified",
) -> GraphEvidence:
    capture = capture_identity(
        snapshot,
        expected_context,
        expected_captured_at=expected_captured_at,
        freshness=freshness,
    )
    names = {"features", "parts", "bodies", "mass"}
    if set(snapshot.sections) != names or not set(snapshot.documents) <= names:
        raise ValueError("invalid snapshot section coverage")
    sources: dict[SourceId, Provenance] = {}
    features: tuple[FeatureRecord, ...] = ()
    parts: tuple[PartRecord, ...] = ()
    bodies: tuple[BodyRecord, ...] = ()
    markers: set[str] = set()
    # Check bounds and outcome consistency before copying any collection.
    sections: tuple[Literal["features", "parts", "bodies", "mass"], ...] = (
        "features",
        "parts",
        "bodies",
        "mass",
    )
    for name in sections:
        state = SectionState.model_validate(snapshot.sections[name].model_dump())
        if state.status in ("unauthorized", "forbidden"):
            raise ValueError("unauthorized snapshot evidence")
        document = snapshot.documents.get(name)
        if (state.status == "success") != (document is not None) or (
            state.status == "success"
        ) != (state.code == "ok"):
            raise ValueError("inconsistent snapshot section")
        if document is None:
            if name != "mass":
                sources[name] = Provenance(
                    id=name,
                    capture=capture,
                    mode="normalized_workspace_read",
                    state="unavailable",
                    status=state.status,
                    code=state.code,
                )
            continue
        if (
            not isinstance(document, ProviderDocument)
            or not isinstance(document.microversions, list)
            or len(document.microversions) > 1
        ):
            raise ValueError("invalid normalized revision evidence")
        data = document.normalized
        common = {
            "capture": capture,
            "mode": "normalized_workspace_read",
            "status": state.status,
            "code": state.code,
            "microversions": tuple(document.microversions),
        }
        if name == "features":
            if (
                not isinstance(data, FeatureSummaryList)
                or not isinstance(data.items, list)
                or len(data.items) > MAX_FEATURES
            ):
                raise ValueError("invalid or oversized feature evidence")
            if not all(isinstance(item, FeatureSummary) for item in data.items):
                raise ValueError("invalid normalized feature")
            sources["features"] = Provenance.model_validate(
                dict(
                    id="features",
                    state="complete"
                    if data.complete is True
                    else "partial"
                    if data.complete is False
                    else "unknown",
                    returned_count=len(data.items),
                    list_complete=data.complete,
                    rollback_index=data.rollback_index,
                    serialization_version=data.serialization_version,
                    microversion_skew=data.microversion_skew,
                    **common,
                )
            )
            features = tuple(
                FeatureRecord(
                    provider_id=item.feature_id,
                    label=_display(item.name),
                    feature_type=_display(item.feature_type),
                    suppressed=item.suppressed,
                    custom_namespace=_custom_namespace(item.custom_namespace),
                )
                for item in data.items
            )
        else:
            limit = MAX_PARTS if name == "parts" else MAX_BODIES
            if not isinstance(data, list) or len(data) > limit:
                raise ValueError("invalid or oversized collection evidence")
            if name == "parts":
                if not all(isinstance(item, PartSummary) for item in data):
                    raise ValueError("invalid normalized part")
                parts = tuple(
                    PartRecord(
                        provider_id=item.part_id,
                        label=_display(item.name),
                        body_type=_display(item.body_type),
                        is_mesh=item.is_mesh,
                        microversion=item.microversion_id,
                    )
                    for item in data
                )
            elif name == "bodies":
                if not all(isinstance(item, BodySummary) for item in data):
                    raise ValueError("invalid normalized body")
                bodies = tuple(
                    BodyRecord(
                        provider_id=item.body_id,
                        body_type=_display(item.body_type),
                        face_count=item.face_count,
                        edge_count=item.edge_count,
                        vertex_count=item.vertex_count,
                    )
                    for item in data
                )
            elif not all(isinstance(item, MassSummary) for item in data):
                raise ValueError("invalid normalized mass section")
            if name != "mass":
                sources[name] = Provenance.model_validate(
                    dict(id=name, state="complete", returned_count=len(data), **common)
                )
        # Mass contributes only a conflict check, never facts or borrowed version IDs.
        for marker in document.microversions:
            markers.add(TypeAdapter(ProviderId).validate_python(marker, strict=True))
    if len(markers) > 1:
        raise ValueError("mixed snapshot revisions")
    observation = (
        selection
        if selection is not None
        else SelectionObservation(
            capture=capture, mode="unobserved_selection", state="unknown"
        )
    )
    return GraphEvidence(
        capture=capture,
        features=EvidenceList[FeatureRecord](
            source=sources["features"], items=features
        ),
        parts=EvidenceList[PartRecord](source=sources["parts"], items=parts),
        bodies=EvidenceList[BodyRecord](source=sources["bodies"], items=bodies),
        selection=observation,
    )


def graph_from_snapshot(
    snapshot: Snapshot,
    expected_context: WorkspaceReference,
    *,
    selection: SelectionObservation | None = None,
    expected_captured_at: str | None = None,
    freshness: Literal["captured_unverified", "stale"] = "captured_unverified",
) -> ForgeModelGraphV1:
    return build_graph(
        evidence_from_snapshot(
            snapshot,
            expected_context,
            selection=selection,
            expected_captured_at=expected_captured_at,
            freshness=freshness,
        )
    )
