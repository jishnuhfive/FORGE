"""Conservative readers over CadInspector. None means 'cannot be established'."""

from dataclasses import dataclass

from ..integrations.onshape.inspector import CadInspector, FeatureType


@dataclass(frozen=True)
class FeatureCount:
    active: int
    # Features of the type whose suppression state is unknown: may be active.
    possibly_active: int
    suppressed: int
    # True only when the feature list is trustworthy enough to prove absence.
    absence_provable: bool


def trustworthy(inspector: CadInspector) -> str | None:
    """Return a reason code when no inference at all is safe."""
    if inspector.freshness == "stale" or inspector.source.consistency == "mismatch":
        return "evidence_stale"
    return None


def count_features(inspector: CadInspector, kind: FeatureType) -> FeatureCount | None:
    features = inspector.features
    if inspector.source.features.status != "success":
        return None
    items = [f for f in features.items if f.feature_type == kind]
    return FeatureCount(
        active=sum(f.suppression == "active" for f in items),
        possibly_active=sum(f.suppression == "unverified" for f in items),
        suppressed=sum(f.suppression == "suppressed" for f in items),
        # Truncated lists cannot prove absence. Provider isComplete=false is not
        # separately exposed today (documented Phase 8B blocker).
        absence_provable=features.omitted_count == 0
        and features.returned_count == len(features.items),
    )


@dataclass(frozen=True)
class SolidBodies:
    solid_count: int
    # Largest face count among SOLID bodies, if every SOLID body reports one.
    max_faces: int | None
    all_types_known: bool
    absence_provable: bool


def solid_bodies(inspector: CadInspector) -> SolidBodies | None:
    if inspector.source.bodies.status != "success":
        return None
    bodies = inspector.bodies
    solids = [b for b in bodies.items if b.body_type == "SOLID"]
    faces = [b.face_count for b in solids]
    return SolidBodies(
        solid_count=len(solids),
        max_faces=max((f for f in faces if f is not None), default=None)
        if faces and all(f is not None for f in faces)
        else None,
        all_types_known=all(b.body_type is not None for b in bodies.items),
        absence_provable=bodies.omitted_count == 0
        and bodies.returned_count == len(bodies.items),
    )
