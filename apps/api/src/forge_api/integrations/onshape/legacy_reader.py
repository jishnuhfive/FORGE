"""Distinct legacy evidence adapter over the unchanged fixed five-GET reader.

Only inherited GET primitives are used. No V1 receipt/reference/evidence is built,
no mutation-capable CAD client is imported, and settlement is never inferred here.
"""

from time import monotonic

import httpx2 as httpx

from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.legacy_contracts import (
    CAPTURE_SECONDS,
    LegacyContext,
    LegacyEnrollment,
    LegacyEvidence,
    LegacyRecoveryDenied,
    LegacyReview,
    enrollment_fingerprint,
    review_fingerprint,
)
from forge_api.cad_edits.retained_contracts import RetainedRecoveryDenied

from .modify_evidence import project_modify_evidence
from .retained_reader import RetainedEvidenceReader


class LegacyEvidenceReader(RetainedEvidenceReader):
    def capture_legacy(
        self, enrollment: LegacyEnrollment, review: LegacyReview, *, deadline: float
    ) -> LegacyEvidence:
        if (
            self._used
            or enrollment.binding.context.model_dump() != self._context.model_dump()
        ):
            self.close()
            raise LegacyRecoveryDenied("legacy_reader_reuse_or_context_mismatch")
        self._used = True
        started = monotonic()
        self._deadline = min(started + CAPTURE_SECONDS, deadline)
        try:
            marker = self._head()
            self._guard.pin(marker)
            features, configuration, bodies = self._get(), self._get(), self._get()
            baseline = project_modify_evidence(
                self._context, marker, features, configuration, bodies
            ).baseline
            final = self._head()
            finished = monotonic()
            if marker != final or finished > self._deadline:
                raise LegacyRecoveryDenied("legacy_capture_changed_or_expired")
            return LegacyEvidence(
                enrollment_fingerprint=enrollment_fingerprint(enrollment),
                review_fingerprint=review_fingerprint(review),
                context=LegacyContext.model_validate(self._context.model_dump()),
                baseline=baseline,
                head_before=marker,
                head_after=final,
                started_monotonic=started,
                finished_monotonic=finished,
            )
        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
            RecursionError,
            EditError,
            RetainedRecoveryDenied,
        ):
            raise LegacyRecoveryDenied("legacy_read_evidence_unavailable") from None
        finally:
            self.close()
