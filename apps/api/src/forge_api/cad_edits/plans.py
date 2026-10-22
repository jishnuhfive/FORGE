"""A1 semantic input and immutable server authority. No provider JSON in plans.

Only SemanticPlan/preview/result types are public contracts. Catalogs and resolved
plans are created by the authenticated resolver and loaded from trusted storage.
"""

import re
import unicodedata
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from .domain import Baseline, Binding, Closed, Digest, Handle, fingerprint

OperationType = Literal[
    "SET_SUPPRESSED",
    "SET_UNSUPPRESSED",
    "RENAME_FEATURE",
    "SET_EXTRUDE_DEPTH",
    "SET_FILLET_RADIUS",
]
FeatureType = Literal["extrude", "fillet"]


def valid_name(value: str) -> str:
    # Check before trim: tabs/newlines must reject, including at the edges.
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("invalid feature name")
    value = value.strip()
    if not value or len(value) > 128 or len(value.encode()) > 256:
        raise ValueError("invalid feature name")
    return value


def valid_quantity(value: str) -> str:
    # Fixed literal grammar, explicit units, positive and bounded. No evaluation,
    # inferred units, exponent notation, variables, aliases or normalization.
    match = re.fullmatch(r"([0-9]{1,6}(?:\.[0-9]{1,6})?) (mm|in)", value)
    if match is None:
        raise ValueError("unsupported quantity")
    number = Decimal(match[1])
    limit = Decimal("10000") if match[2] == "mm" else Decimal("393")
    if not number.is_finite() or not Decimal("0.001") <= number <= limit:
        raise ValueError("quantity outside supported bounds")
    return value


Name = Annotated[str, Field(min_length=1, max_length=256), AfterValidator(valid_name)]
Quantity = Annotated[
    str, Field(min_length=1, max_length=32), AfterValidator(valid_quantity)
]


class SetSuppressed(Closed):
    type: Literal["SET_SUPPRESSED"]
    target: Handle


class SetUnsuppressed(Closed):
    type: Literal["SET_UNSUPPRESSED"]
    target: Handle


class RenameFeature(Closed):
    type: Literal["RENAME_FEATURE"]
    target: Handle
    new_name: Name


class SetExtrudeDepth(Closed):
    type: Literal["SET_EXTRUDE_DEPTH"]
    target: Handle
    quantity: Quantity


class SetFilletRadius(Closed):
    type: Literal["SET_FILLET_RADIUS"]
    target: Handle
    quantity: Quantity


ModifyOperation = Annotated[
    SetSuppressed | SetUnsuppressed | RenameFeature | SetExtrudeDepth | SetFilletRadius,
    Field(discriminator="type"),
]


class SemanticPlan(Closed):
    target_catalog: Handle
    operations: Annotated[
        tuple[ModifyOperation, ...], Field(min_length=1, max_length=5)
    ]


class Target(Closed):
    """Private identity. Binding, revision and expiry belong to the owning catalog."""

    handle: Handle
    feature_id: Annotated[str, Field(min_length=1, max_length=256)]
    feature_type: FeatureType
    position: Annotated[int, Field(ge=1, le=20)]


class OwnedAuthority(Closed):
    proposal_id: Handle
    binding: Binding
    baseline: Baseline
    created_at: int
    expires_at: int

    @model_validator(mode="after")
    def bound(self) -> Self:
        if (
            self.binding.context != self.baseline.context
            or self.expires_at != self.created_at + 120
        ):
            raise ValueError("invalid authority binding")
        return self


class TargetCatalog(OwnedAuthority):
    schema_version: Literal["forge-modify-targets-a1"] = "forge-modify-targets-a1"
    targets: Annotated[tuple[Target, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({t.handle for t in self.targets}) != len(self.targets) or len(
            {t.feature_id for t in self.targets}
        ) != len(self.targets):
            raise ValueError("ambiguous targets")
        return self


class OperationPreview(Closed):
    type: OperationType
    label: Annotated[str, Field(min_length=1, max_length=256)]
    feature_type: FeatureType
    position: Annotated[int, Field(ge=1, le=20)]
    field: Literal["Suppression", "Name", "Depth", "Radius"]
    current: Annotated[str, Field(min_length=1, max_length=256)]
    proposed: Annotated[str, Field(min_length=1, max_length=256)]


class ResolvedOperation(Closed):
    operation: ModifyOperation
    target: Target
    preview: OperationPreview

    @model_validator(mode="after")
    def bound(self) -> Self:
        if (
            self.operation.target != self.target.handle
            or self.operation.type != self.preview.type
        ):
            raise ValueError("invalid operation binding")
        return self


class ModifyPlan(OwnedAuthority):
    schema_version: Literal["forge-modify-plan-a1"] = "forge-modify-plan-a1"
    policy_version: Literal["modify-a1-1"] = "modify-a1-1"
    operations: Annotated[
        tuple[ResolvedOperation, ...], Field(min_length=1, max_length=5)
    ]


class PlanPreview(Closed):
    proposal_id: Handle
    digest: Digest
    expires_at: int
    operations: Annotated[
        tuple[OperationPreview, ...], Field(min_length=1, max_length=5)
    ]


class TargetOption(Closed):
    handle: Handle
    label: Annotated[str, Field(min_length=1, max_length=256)]
    feature_type: FeatureType
    position: Annotated[int, Field(ge=1, le=20)]
    supported_operations: tuple[OperationType, ...]


class TargetPreview(Closed):
    target_catalog: Handle
    expires_at: int
    targets: tuple[TargetOption, ...]


OperationState = Literal[
    "pending",
    "checking",
    "executing",
    "verifying",
    "verified_success",
    "rejected_stale",
    "write_failed",
    "execution_uncertain",
    "skipped",
]
PlanState = Literal[
    "pending",
    "claimed",
    "verifying",
    "verified_success",
    "partial_failure",
    "rejected_stale",
    "write_failed",
    "execution_uncertain",
    "cancelled",
    "reconciled_current_state",
]


class PlanResult(Closed):
    state: PlanState
    operations: Annotated[tuple[OperationState, ...], Field(min_length=1, max_length=5)]


class StoredPlan(Closed):
    """Mutable lifecycle is outside the immutable, approval-digested plan."""

    plan: ModifyPlan
    result: PlanResult

    @model_validator(mode="after")
    def bound(self) -> Self:
        if len(self.plan.operations) != len(self.result.operations):
            raise ValueError("invalid operation journal")
        return self


def plan_preview(plan: ModifyPlan) -> PlanPreview:
    return PlanPreview(
        proposal_id=plan.proposal_id,
        digest=fingerprint(plan.model_dump(mode="json")),
        expires_at=plan.expires_at,
        operations=tuple(op.preview for op in plan.operations),
    )
