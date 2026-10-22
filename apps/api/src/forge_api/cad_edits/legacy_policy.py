"""ONE fixed historical case. Remove after retirement or sunset; never extend.

The read-only enrollment review did not persist private candidate pins. Accordingly
the shipped policy is UNENROLLED and cannot contact CAD or release anything. A
separately reviewed private static enrollment is required before any live use.
There is no environment/file/CLI loader, DB enrollment builder, or runtime setter.
Tests replace this private slot with invented pins in their isolated process only.
"""

from forge_api.core.config import Settings
from forge_api.db.models import now

from .domain import fingerprint
from .legacy_contracts import (
    REVIEW_SECONDS,
    LegacyCasePolicy,
    LegacyContext,
    LegacyEnrollment,
    LegacyRecoveryDenied,
    LegacyReview,
    enrollment_fingerprint,
)

CASE = LegacyCasePolicy(
    context=LegacyContext(
        documentId="616f4c98dfb6deed0a0c40e6",
        workspaceId="75018163dba1b8c05d651a5b",
        elementId="6dfea845bb52ec251a31af43",
        revisionKind="workspace",
    )
)
_ENROLLMENT: LegacyEnrollment | None = None


def require_enrollment(settings: Settings, review: LegacyReview) -> LegacyEnrollment:
    at = now()
    if settings.environment != CASE.environment or settings.forge_cad_writes_enabled:
        raise LegacyRecoveryDenied("development_writes_off_required")
    if not CASE.adoption_boundary <= at < CASE.sunset:
        raise LegacyRecoveryDenied("legacy_policy_inactive_or_sunset")
    enrollment = _ENROLLMENT
    if enrollment is None:
        raise LegacyRecoveryDenied("legacy_case_not_enrolled")
    # Revalidate even in-process inputs; no arbitrary dictionaries/extra fields.
    try:
        checked = LegacyEnrollment.model_validate_json(enrollment.model_dump_json())
        proofs = LegacyReview.model_validate_json(review.model_dump_json())
    except ValueError, TypeError, AttributeError:
        raise LegacyRecoveryDenied("legacy_review_invalid") from None
    if (
        checked != enrollment
        or proofs != review
        or enrollment.binding.context.model_dump() != CASE.context.model_dump()
        or enrollment.reviewed_at > at
        or enrollment.stack != str(settings.onshape_api_base_url)
        or enrollment.company_id != settings.onshape_company_id
    ):
        raise LegacyRecoveryDenied("legacy_enrollment_mismatch")
    pin = enrollment_fingerprint(enrollment)
    for proof in (review.settlement, review.quiescence):
        if (
            proof.enrollment_fingerprint != pin
            or not enrollment.reviewed_at <= proof.reviewed_at <= at < proof.valid_until
            or proof.valid_until > proof.reviewed_at + REVIEW_SECONDS
            or proof.valid_until > CASE.sunset
        ):
            raise LegacyRecoveryDenied("legacy_review_expired_or_mismatched")
    evidence = review.settlement.evidence
    if (
        evidence.user != enrollment.binding.user
        or evidence.context != CASE.context
        or evidence.issued_at > review.settlement.reviewed_at
        or evidence.execution_start != CASE.execution_start
        or evidence.execution_end_exclusive != CASE.execution_end_exclusive
    ):
        raise LegacyRecoveryDenied("legacy_settlement_mismatch")
    # Canonical policy fingerprint is available for tests/review, not a credential.
    if fingerprint(CASE.model_dump(mode="json")) != fingerprint(
        LegacyCasePolicy.model_validate_json(CASE.model_dump_json()).model_dump(
            mode="json"
        )
    ):
        raise LegacyRecoveryDenied("legacy_policy_invalid")
    return enrollment
