"""Small strict provider projections and independent Forge read models.

Unknown JSON is retained only in a bounded, request-local ProviderDocument; it is
never serialized by the route. Missing optional provider fields remain unknown.
"""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from .contracts import API_VERSION, SCHEMA_VERSION, WorkspaceReference

Text = Annotated[str, Field(max_length=4096)]
Identifier = Annotated[str, Field(min_length=1, max_length=256)]
Number = Annotated[float, Field(allow_inf_nan=False)]


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)


class Parameter(ProviderModel):
    parameterId: Identifier | None = None
    btType: Text | None = None
    # Populated only by the allowlisted adapter, never from a provider-supplied
    # field with this name. Unknown parameter classes cannot inject summaries.
    summary: ParameterValue

    @model_validator(mode="before")
    @classmethod
    def project(cls, value: object) -> object:
        from .parameters import parameter_value

        if not isinstance(value, dict):
            return value
        return {
            "parameterId": value.get("parameterId"),
            "btType": value.get("btType"),
            "summary": parameter_value(value),
        }


class Feature(ProviderModel):
    featureId: Identifier
    featureType: Text | None = None
    name: Text | None = None
    suppressed: bool | None = None
    parameters: list[Parameter] | None = Field(default=None, max_length=512)
    namespace: Text | None = None


class Features(ProviderModel):
    features: list[Feature] = Field(max_length=2000)
    isComplete: bool | None = None
    rollbackIndex: int | None = Field(default=None, ge=-1)
    serializationVersion: Text | None = None
    sourceMicroversion: Identifier | None = None
    microversionSkew: bool | None = None


class Part(ProviderModel):
    partId: Identifier
    name: Text | None = None
    description: Text | None = None
    partNumber: Text | None = None
    bodyType: Text | None = None
    state: Text | None = None
    microversionId: Identifier | None = None
    isMesh: bool | None = None


class Microversion(ProviderModel):
    theId: Identifier | None = None
    ambiguous: bool | None = None
    deleted: bool | None = None


class Body(ProviderModel):
    id: Identifier
    type: Text | None = None
    faces: list[dict[str, JsonValue]] | None = Field(default=None, max_length=20000)
    edges: list[dict[str, JsonValue]] | None = Field(default=None, max_length=20000)
    vertices: list[dict[str, JsonValue]] | None = Field(default=None, max_length=20000)


class Bodies(ProviderModel):
    bodies: list[Body] = Field(max_length=2000)
    microversionId: Microversion | None = None
    errorEnum: Text | None = None


class MassBody(ProviderModel):
    hasMass: bool | None = None
    mass: list[Number] | None = Field(default=None, min_length=3, max_length=3)
    volume: list[Number] | None = Field(default=None, min_length=3, max_length=3)
    # Onshape defines periphery as surface area, also a physical scalar estimate.
    periphery: list[Number] | None = Field(default=None, min_length=3, max_length=3)
    centroid: list[Number] | None = Field(default=None, max_length=9)
    # Kept in provider order; do not invent an inertia frame or matrix convention.
    inertia: list[Number] | None = Field(default=None, max_length=27)
    principalInertia: list[Number] | None = Field(default=None, max_length=3)
    massMissingCount: int | None = Field(default=None, ge=0)

    @field_validator("mass", "volume", "periphery")
    @classmethod
    def physical_scalar_bounds(cls, values: list[float] | None) -> list[float] | None:
        if values is None:
            return None
        # Only these nonnegative physical quantities use [nominal, lower, upper].
        # A tolerance limit can cross zero; vectors/matrices are unrelated.
        nominal, lower, upper = values
        if nominal < 0:
            raise PydanticCustomError("negative_nominal", "Negative physical nominal")
        if not lower <= nominal <= upper:
            raise PydanticCustomError("bounds_order", "Invalid tolerance ordering")
        return values


class Mass(ProviderModel):
    bodies: dict[Identifier, MassBody] = Field(max_length=2000)
    microversionId: Identifier | None = None


class ReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class ParameterValue(ReadModel):
    kind: Literal[
        "boolean", "string", "enum", "expression", "query_count", "unsupported"
    ]
    state: Literal["available", "unavailable", "unsupported", "omitted"]
    text: Annotated[str, Field(max_length=256)] | None = None
    boolean: bool | None = None
    count: int | None = Field(default=None, ge=0, le=2000)


class ParameterSummary(ReadModel):
    parameter_id: str | None
    provider_type: str | None
    value: ParameterValue


class FeatureSummary(ReadModel):
    feature_id: str
    feature_type: str | None
    name: str | None
    suppressed: bool | None
    parameters: list[ParameterSummary] | None
    custom_namespace: bool = False


class FeatureSummaryList(ReadModel):
    items: list[FeatureSummary]
    complete: bool | None
    rollback_index: int | None
    serialization_version: str | None
    microversion_skew: bool | None


class PartSummary(ReadModel):
    part_id: str
    name: str | None
    description: str | None
    part_number: str | None
    body_type: str | None
    state: str | None
    microversion_id: str | None
    is_mesh: bool | None


class BodySummary(ReadModel):
    body_id: str
    body_type: str | None
    face_count: int | None
    edge_count: int | None
    vertex_count: int | None


class Estimate(ReadModel):
    nominal: Number
    lower: Number
    upper: Number


class MassSummary(ReadModel):
    body_id: str
    has_mass: bool | None
    mass: Estimate | None
    volume: Estimate | None
    mass_missing_count: int | None
    centroid_provider_values: list[float] | None
    inertia_provider_values: list[float] | None
    principal_inertia_provider_values: list[float] | None
    units: Literal["provider_native_unverified"] = "provider_native_unverified"


Status = Literal[
    "success",
    "unavailable",
    "unauthorized",
    "forbidden",
    "not_found",
    "rate_limited",
    "provider_failure",
]
Code = Literal[
    "ok",
    "connection_required",
    "read_permission_required",
    "permission_or_access_required",
    "document_forbidden",
    "not_found",
    "rate_limited",
    "quota_exceeded",
    "provider_unavailable",
    "invalid_response",
    "response_too_large",
    "redirect_rejected",
    "unsupported_provider",
    "request_in_progress",
    "provider_timeout",
]


class SectionState(ReadModel):
    status: Status
    code: Code
    retry_after_seconds: int | None = Field(default=None, ge=1, le=86400)


@dataclass(repr=False)
class ProviderDocument[T]:
    normalized: T
    microversions: list[str]
    raw: JsonValue = field(repr=False)


@dataclass(repr=False)
class Snapshot:
    context: WorkspaceReference
    sections: dict[str, SectionState]
    documents: dict[str, ProviderDocument[object]]
    captured_at: str
    consistency: Literal["unverified", "mismatch"]
    provider_api_version: str = API_VERSION
    provider_schema_version: str = SCHEMA_VERSION


class ProofSection(SectionState):
    count: int | None = Field(default=None, ge=0, le=2000)


class SnapshotProof(ReadModel):
    schema_version: Literal["forge-cad-read-v1"] = "forge-cad-read-v1"
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    captured_at: str
    consistency: Literal["unverified", "mismatch"]
    features: ProofSection
    parts: ProofSection
    bodies: ProofSection
    mass: ProofSection
    has_mass: bool | None
