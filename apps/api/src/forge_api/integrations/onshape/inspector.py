"""Bounded Forge evidence projected from the Phase 4 snapshot, never raw JSON."""

import re
from typing import Annotated, Literal

from pydantic import Field

from .models import (
    BodySummary,
    FeatureSummary,
    FeatureSummaryList,
    MassSummary,
    ParameterValue,
    PartSummary,
    ReadModel,
    SectionState,
    Snapshot,
    SnapshotProof,
)
from .parameters import display_text
from .service import failed_proof, proof

MAX_FEATURES = 100
MAX_PARTS = 200
MAX_BODIES = 200
MAX_PARAMETERS = 16
DisplayText = Annotated[str, Field(max_length=256)]
Completeness = Literal["complete", "partial", "unverified", "unavailable"]
Availability = Literal["available", "unavailable", "partial", "unverified"]
# Official feature-access examples establish these names. Nonempty namespaces
# denote custom Feature Studios and must not acquire a standard-feature meaning.
FeatureType = Literal["sketch", "extrude", "fillet", "chamfer", "unknown"]
FEATURE_TYPES: dict[str, FeatureType] = {
    "newSketch": "sketch",
    "extrude": "extrude",
    "fillet": "fillet",
    "chamfer": "chamfer",
}


class InspectorParameter(ParameterValue):
    label: DisplayText


class InspectorFeature(ReadModel):
    index: int = Field(ge=1, le=2000)
    name: DisplayText
    feature_type: FeatureType
    suppression: Literal["active", "suppressed", "unverified"]
    completeness: Completeness
    parameters: list[InspectorParameter] = Field(max_length=MAX_PARAMETERS)
    omitted_parameters: int = Field(ge=0, le=512)


class InspectorPart(ReadModel):
    index: int = Field(ge=1, le=2000)
    name: DisplayText
    description: DisplayText | None
    part_number: DisplayText | None
    body_type: DisplayText | None
    state: DisplayText | None
    is_mesh: bool | None
    # massAsGroup=true cannot establish any individual part's assigned mass.
    mass: Literal["unverified"] = "unverified"
    completeness: Completeness


class InspectorBody(ReadModel):
    index: int = Field(ge=1, le=2000)
    body_type: DisplayText | None
    face_count: int | None = Field(ge=0, le=20000)
    edge_count: int | None = Field(ge=0, le=20000)
    vertex_count: int | None = Field(ge=0, le=20000)


class EvidenceList[T](ReadModel):
    items: list[T] = Field(max_length=MAX_PARTS)
    completeness: Completeness
    returned_count: int = Field(ge=0, le=2000)
    omitted_count: int = Field(ge=0, le=2000)


class FeatureEvidence(EvidenceList[InspectorFeature]):
    items: list[InspectorFeature] = Field(max_length=MAX_FEATURES)


class PhysicalEvidence(ReadModel):
    mass: Availability
    volume: Literal["reported", "partial", "unavailable", "unverified"]
    missing_mass: bool | None
    units: Literal["provider_native_unverified"] = "provider_native_unverified"
    scope: Literal["aggregate"] = "aggregate"


class InspectorContext(ReadModel):
    kind: Literal["workspace_part_studio"] = "workspace_part_studio"
    configuration: Literal["default"] = "default"
    evaluation: Literal["end_of_list"] = "end_of_list"


class CadInspector(ReadModel):
    schema_version: Literal["forge-cad-inspector-v1"] = "forge-cad-inspector-v1"
    context: InspectorContext = Field(default_factory=InspectorContext)
    # Includes capture time, independent section outcomes, conservative counts,
    # consistency and a random reference. Also preserves the compact v1 projection.
    source: SnapshotProof
    freshness: Literal["captured_unverified", "stale"]
    features: FeatureEvidence
    parts: EvidenceList[InspectorPart]
    bodies: EvidenceList[InspectorBody]
    physical: PhysicalEvidence


def feature(item: FeatureSummary, index: int) -> InspectorFeature:
    parameters = []
    for ordinal, parameter in enumerate((item.parameters or [])[:MAX_PARAMETERS], 1):
        identifier = parameter.parameter_id or ""
        label = f"Parameter {ordinal}"
        # Parameter names like endDepth are useful; opaque node/feature IDs aren't.
        if re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_ ]{0,79}", identifier
        ) and not re.fullmatch(r"[a-fA-F0-9]{24,}", identifier):
            label = re.sub(r"([a-z])([A-Z])", r"\1 \2", identifier).replace("_", " ")
        parameters.append(
            InspectorParameter(label=label, **parameter.value.model_dump())
        )
    kind = (
        FEATURE_TYPES.get(item.feature_type or "")
        if not item.custom_namespace
        else None
    )
    name = display_text(item.name)
    omitted = max(0, len(item.parameters or []) - MAX_PARAMETERS)
    return InspectorFeature(
        index=index,
        name=name or f"Unnamed feature {index}",
        feature_type=kind or "unknown",
        suppression="unverified"
        if item.suppressed is None
        else "suppressed"
        if item.suppressed
        else "active",
        completeness="partial"
        if not name
        or not kind
        or omitted
        or any(p.state != "available" for p in parameters)
        else "unverified"
        if item.parameters is None or item.suppressed is None
        else "complete",
        parameters=parameters,
        omitted_parameters=omitted,
    )


def part(item: PartSummary, index: int) -> InspectorPart:
    values = {
        "name": display_text(item.name),
        "description": display_text(item.description),
        "part_number": display_text(item.part_number),
        "body_type": display_text(item.body_type),
        "state": display_text(item.state),
    }
    return InspectorPart(
        index=index,
        name=values["name"] or f"Unnamed part {index}",
        description=values["description"],
        part_number=values["part_number"],
        body_type=values["body_type"],
        state=values["state"],
        is_mesh=item.is_mesh,
        completeness="complete"
        if values["name"]
        and all(v is not None for v in values.values())
        and item.is_mesh is not None
        else "partial",
    )


def physical(items: list[MassSummary] | None) -> PhysicalEvidence:
    if items is None:
        return PhysicalEvidence(
            mass="unverified", volume="unverified", missing_mass=None
        )
    if not items:
        return PhysicalEvidence(
            mass="unavailable", volume="unavailable", missing_mass=None
        )
    missing = (
        True
        if any((i.mass_missing_count or 0) > 0 for i in items)
        else (False if all(i.mass_missing_count == 0 for i in items) else None)
    )
    available = [i.has_mass is True and i.mass is not None for i in items]
    mass: Availability = "unverified"
    if all(i.has_mass is False for i in items):
        mass = "unavailable"
    elif any(available) and (missing or any(i.has_mass is False for i in items)):
        mass = "partial"
    elif all(available):
        mass = "available"
    volume: Literal["reported", "partial", "unavailable", "unverified"] = (
        "reported"
        if all(i.volume is not None for i in items)
        else "partial"
        if any(i.volume is not None for i in items)
        else "unverified"
    )
    return PhysicalEvidence(mass=mass, volume=volume, missing_mass=missing)


def inspect(snapshot: Snapshot | SectionState, correlation: str) -> CadInspector:
    if isinstance(snapshot, SectionState):
        source = failed_proof(snapshot, correlation)
        documents = {}
    else:
        source = proof(snapshot, correlation)
        documents = snapshot.documents
    features = documents.get("features")
    feature_data = features.normalized if features else None
    feature_items = (
        feature_data.items if isinstance(feature_data, FeatureSummaryList) else []
    )
    parts = documents.get("parts")
    part_items = (
        [p for p in parts.normalized if isinstance(p, PartSummary)]
        if parts and isinstance(parts.normalized, list)
        else []
    )
    bodies = documents.get("bodies")
    body_items = (
        [b for b in bodies.normalized if isinstance(b, BodySummary)]
        if bodies and isinstance(bodies.normalized, list)
        else []
    )
    mass = documents.get("mass")
    mass_items = (
        [m for m in mass.normalized if isinstance(m, MassSummary)]
        if mass and isinstance(mass.normalized, list)
        else None
    )
    feature_views = [
        feature(f, n) for n, f in enumerate(feature_items[:MAX_FEATURES], 1)
    ]
    part_views = [part(p, n) for n, p in enumerate(part_items[:MAX_PARTS], 1)]
    body_views = [
        InspectorBody(
            index=n,
            body_type=display_text(b.body_type),
            face_count=b.face_count,
            edge_count=b.edge_count,
            vertex_count=b.vertex_count,
        )
        for n, b in enumerate(body_items[:MAX_BODIES], 1)
    ]
    return CadInspector(
        source=source,
        freshness="stale"
        if source.consistency == "mismatch"
        else "captured_unverified",
        features=FeatureEvidence(
            items=feature_views,
            returned_count=len(feature_items),
            omitted_count=max(0, len(feature_items) - MAX_FEATURES),
            completeness="unavailable"
            if source.features.status != "success"
            else "partial"
            if len(feature_items) > MAX_FEATURES
            or any(f.completeness == "partial" for f in feature_views)
            or (
                isinstance(feature_data, FeatureSummaryList)
                and feature_data.complete is False
            )
            else "unverified"
            if source.features.count is None
            or any(f.completeness == "unverified" for f in feature_views)
            else "complete",
        ),
        parts=EvidenceList[InspectorPart](
            items=part_views,
            returned_count=len(part_items),
            omitted_count=max(0, len(part_items) - MAX_PARTS),
            completeness="unavailable"
            if source.parts.status != "success"
            else "partial"
            if len(part_items) > MAX_PARTS
            or any(p.completeness != "complete" for p in part_views)
            else "complete",
        ),
        bodies=EvidenceList[InspectorBody](
            items=body_views,
            returned_count=len(body_items),
            omitted_count=max(0, len(body_items) - MAX_BODIES),
            completeness="unavailable"
            if source.bodies.status != "success"
            else "partial"
            if len(body_items) > MAX_BODIES
            or any(
                b.body_type is None
                or b.face_count is None
                or b.edge_count is None
                or b.vertex_count is None
                for b in body_views
            )
            else "complete",
        ),
        physical=physical(mass_items),
    )
