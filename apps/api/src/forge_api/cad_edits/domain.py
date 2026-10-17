"""Closed immutable authority records; no provider transport or model authority."""

import hashlib
import json
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from forge_api.integrations.onshape.contracts import CadId, WorkspaceReference

Handle = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
State = Literal[
    "candidate",
    "pending",
    "cancelled",
    "expired",
    "invalidated",
    "claimed",
    "rejected_stale",
    "write_failed",
    "verifying",
    "verified_success",
    "unverified_result",
    "execution_uncertain",
    "recovery_required",
]


class EditError(Exception):
    def __init__(self, code: str, status: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class Closed(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, hide_input_in_errors=True
    )


class Binding(Closed):
    user: str
    session: Digest
    generation: str
    context: WorkspaceReference
    workspace_key: Digest


class FeatureStateEvidence(StrEnum):
    COMPLETE = "COMPLETE"
    UNAVAILABLE_EMPTY = "UNAVAILABLE_EMPTY"


class SuppressionAuxEvidence(StrEnum):
    NULL_UNAVAILABLE = "NULL_UNAVAILABLE"
    ORDINARY_OBJECT = "ORDINARY_OBJECT"


class ParentSuppressionEvidence(StrEnum):
    EXPLICIT_FALSE = "EXPLICIT_FALSE"
    STRUCTURALLY_NOT_APPLICABLE = "STRUCTURALLY_NOT_APPLICABLE"


class ConfiguredSuppressionEvidence(StrEnum):
    EXPLICIT_FALSE = "EXPLICIT_FALSE"
    INDEPENDENTLY_PROVEN_UNCONFIGURED = "INDEPENDENTLY_PROVEN_UNCONFIGURED"


class BodyRevisionEvidence(StrEnum):
    EXPLICIT_CLEAN_FLAGS = "EXPLICIT_CLEAN_FLAGS"
    EXACT_PINNED_ID_FLAGS_UNAVAILABLE = "EXACT_PINNED_ID_FLAGS_UNAVAILABLE"


class Baseline(Closed):
    context: WorkspaceReference
    microversion: CadId
    feature_id: Annotated[str, Field(min_length=1, max_length=256)]
    label: Annotated[str, Field(min_length=1, max_length=256)]
    position: Annotated[int, Field(ge=1, le=20)]
    fingerprint: Digest
    definitions: Digest
    serialization: Annotated[str, Field(min_length=1, max_length=64)]
    library: Annotated[int, Field(ge=0, le=2147483647)]
    suppressed: bool
    body_revision_evidence: BodyRevisionEvidence
    feature_state_evidence: FeatureStateEvidence
    suppression_aux_evidence: Annotated[
        tuple[SuppressionAuxEvidence, ...], Field(min_length=3, max_length=20)
    ]
    parent_suppression_evidence: Annotated[
        tuple[ParentSuppressionEvidence, ...], Field(min_length=3, max_length=20)
    ]
    configured_suppression_evidence: Annotated[
        tuple[ConfiguredSuppressionEvidence, ...], Field(min_length=3, max_length=20)
    ]


class Proposal(Closed):
    schema_version: Literal["forge-write-proposal-v1"] = "forge-write-proposal-v1"
    policy_version: Literal["terminal-fillet-5"] = "terminal-fillet-5"
    operation_type: Literal["suppress_terminal_fillet_v1"] = (
        "suppress_terminal_fillet_v1"
    )
    proposal_id: Handle
    binding: Binding
    baseline: Baseline
    expected_suppressed: Literal[False] = False
    proposed_suppressed: Literal[True] = True
    created_at: int
    expires_at: int


class Preview(Closed):
    proposal_id: Handle
    digest: Digest
    operation_type: Literal["suppress_terminal_fillet_v1"] = (
        "suppress_terminal_fillet_v1"
    )
    label: str
    position: int
    current: Literal["Active"] = "Active"
    proposed: Literal["Suppressed"] = "Suppressed"
    expires_at: int


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def preview(proposal: Proposal) -> Preview:
    return Preview(
        proposal_id=proposal.proposal_id,
        digest=fingerprint(proposal.model_dump(mode="json")),
        label=proposal.baseline.label,
        position=proposal.baseline.position,
        expires_at=proposal.expires_at,
    )


def supported_intent(value: str) -> bool:
    # Deliberately closed grammar: discussion, plural/batch, IDs and embedded code
    # never turn into an operation. No hosted model call or prompt persistence.
    return bool(
        re.fullmatch(
            r"\s*(?:please\s+)?(?:suppress\s+(?:the\s+)?(?:final|last)\s+(?:edge\s+)?fillet|"
            r"turn\s+off\s+(?:the\s+)?(?:final|last)\s+fillet|"
            r"temporarily\s+remove\s+(?:the\s+)?(?:final|last)\s+(?:edge\s+)?fillet)[.!]?\s*",
            value,
            re.I,
        )
    )


def require_current(
    proposal: Proposal, binding: Binding, baseline: Baseline, at: int
) -> None:
    if at >= proposal.expires_at:
        raise EditError("proposal_expired")
    if proposal.binding != binding:
        raise EditError("context_changed")
    if proposal.baseline != baseline or baseline.suppressed:
        raise EditError("model_changed")
