"""Frozen Phase 12 feature/public projection; test-only equivalence reference.

Copied from 6f7d147. Shared public models and unchanged part/physical display
helpers avoid a second production implementation or a runtime feature flag.
"""

import re

from forge_api.integrations.onshape.inspector import (
    FEATURE_TYPES,
    MAX_BODIES,
    MAX_FEATURES,
    MAX_PARAMETERS,
    MAX_PARTS,
    CadInspector,
    EvidenceList,
    FeatureEvidence,
    InspectorBody,
    InspectorFeature,
    InspectorParameter,
    InspectorPart,
    part,
    physical,
)
from forge_api.integrations.onshape.models import (
    BodySummary,
    FeatureSummary,
    FeatureSummaryList,
    MassSummary,
    PartSummary,
    SectionState,
    Snapshot,
)
from forge_api.integrations.onshape.parameters import display_text
from forge_api.integrations.onshape.service import failed_proof, proof


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
