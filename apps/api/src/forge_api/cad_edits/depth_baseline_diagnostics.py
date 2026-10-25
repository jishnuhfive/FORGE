"""Closed field-level explanation only; never baseline or recovery authority."""

from typing import Literal

from .domain import Baseline

BaselineDifference = Literal[
    "context_mismatch",
    "microversion_mismatch",
    "terminal_identity_mismatch",
    "terminal_label_mismatch",
    "position_mismatch",
    "definitions_digest_mismatch",
    "full_evidence_digest_mismatch",
    "serialization_mismatch",
    "library_mismatch",
    "suppressed_state_mismatch",
    "body_revision_evidence_mismatch",
    "feature_state_evidence_mismatch",
    "suppression_aux_evidence_mismatch",
    "parent_suppression_evidence_mismatch",
    "configured_suppression_evidence_mismatch",
]
FIELDS: tuple[tuple[str, BaselineDifference], ...] = (
    ("context", "context_mismatch"),
    ("microversion", "microversion_mismatch"),
    ("feature_id", "terminal_identity_mismatch"),
    ("label", "terminal_label_mismatch"),
    ("position", "position_mismatch"),
    ("definitions", "definitions_digest_mismatch"),
    ("fingerprint", "full_evidence_digest_mismatch"),
    ("serialization", "serialization_mismatch"),
    ("library", "library_mismatch"),
    ("suppressed", "suppressed_state_mismatch"),
    ("body_revision_evidence", "body_revision_evidence_mismatch"),
    ("feature_state_evidence", "feature_state_evidence_mismatch"),
    ("suppression_aux_evidence", "suppression_aux_evidence_mismatch"),
    ("parent_suppression_evidence", "parent_suppression_evidence_mismatch"),
    ("configured_suppression_evidence", "configured_suppression_evidence_mismatch"),
)


def baseline_differences(
    saved: Baseline, fresh: Baseline
) -> tuple[BaselineDifference, ...]:
    """Match Baseline equality component by component, with no value output."""
    return tuple(
        code for field, code in FIELDS if getattr(saved, field) != getattr(fresh, field)
    )
