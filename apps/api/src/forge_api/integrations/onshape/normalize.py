"""Provider-specific parsing ends here; raw fields cannot enter domain logic."""

from pydantic import JsonValue, TypeAdapter

from .contracts import Operation
from .models import (
    Bodies,
    BodySummary,
    Estimate,
    Features,
    FeatureSummary,
    FeatureSummaryList,
    Mass,
    MassSummary,
    ParameterSummary,
    Part,
    PartSummary,
    ProviderDocument,
)


def normalize_provider_scalar_estimate(values: list[float] | None) -> Estimate | None:
    """Map validated Onshape mass/volume [nominal, lower, upper] arrays.

    The current v17 getPartStudioMassProperties contract specifies this order.
    Missing estimates stay unknown; present estimates are strict finite triples.
    Vector components and centroid/inertia arrays must not use this helper.
    """
    if values is None:
        return None
    nominal, lower, upper = values
    return Estimate(nominal=nominal, lower=lower, upper=upper)


def normalize(operation: Operation, raw: JsonValue) -> ProviderDocument[object]:
    versions: list[str] = []
    data: object
    match operation:
        case Operation.FEATURES:
            features = Features.model_validate(raw)
            data = FeatureSummaryList(
                items=[
                    FeatureSummary(
                        feature_id=f.featureId,
                        feature_type=f.featureType,
                        name=f.name,
                        suppressed=f.suppressed,
                        parameters=[
                            ParameterSummary(
                                parameter_id=p.parameterId, provider_type=p.btType
                            )
                            for p in f.parameters
                        ]
                        if f.parameters is not None
                        else None,
                    )
                    for f in features.features
                ],
                complete=features.isComplete,
                rollback_index=features.rollbackIndex,
                serialization_version=features.serializationVersion,
                microversion_skew=features.microversionSkew,
            )
            versions = (
                [features.sourceMicroversion] if features.sourceMicroversion else []
            )
        case Operation.PARTS:
            parts = TypeAdapter(list[Part]).validate_python(raw, strict=True)
            if len(parts) > 2000:
                raise ValueError("Too many parts")
            data = [
                PartSummary(
                    part_id=p.partId,
                    name=p.name,
                    description=p.description,
                    part_number=p.partNumber,
                    body_type=p.bodyType,
                    state=p.state,
                    microversion_id=p.microversionId,
                    is_mesh=p.isMesh,
                )
                for p in parts
            ]
            versions = list(
                dict.fromkeys(p.microversionId for p in parts if p.microversionId)
            )
        case Operation.BODIES:
            bodies = Bodies.model_validate(raw)
            if bodies.errorEnum not in (None, "NO_ERROR"):
                raise ValueError("Provider body evaluation failed")
            data = [
                BodySummary(
                    body_id=b.id,
                    body_type=b.type,
                    face_count=len(b.faces) if b.faces is not None else None,
                    edge_count=len(b.edges) if b.edges is not None else None,
                    vertex_count=len(b.vertices) if b.vertices is not None else None,
                )
                for b in bodies.bodies
            ]
            version = bodies.microversionId
            if (
                version
                and version.theId
                and not version.ambiguous
                and not version.deleted
            ):
                versions = [version.theId]
        case Operation.MASS:
            mass = Mass.model_validate(raw)
            data = [
                MassSummary(
                    body_id=key,
                    has_mass=value.hasMass,
                    # Unassigned provider mass is not a physical zero estimate.
                    mass=normalize_provider_scalar_estimate(value.mass)
                    if value.hasMass is not False
                    else None,
                    volume=normalize_provider_scalar_estimate(value.volume),
                    mass_missing_count=value.massMissingCount,
                    centroid_provider_values=value.centroid,
                    inertia_provider_values=value.inertia,
                    principal_inertia_provider_values=value.principalInertia,
                )
                for key, value in mass.bodies.items()
            ]
            versions = [mass.microversionId] if mass.microversionId else []
    return ProviderDocument(data, versions, raw)
