"""Fixed internal rejection diagnostics; never provider strings or public details."""

import logging
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from forge_api.cad_edits.domain import EditError

logger = logging.getLogger("forge.onshape.safe_edit")


class Reason(StrEnum):
    INVENTORY_SHAPE = "feature_inventory_invalid"
    CONFIGURATION_SHAPE = "configuration_invalid"
    INCOMPLETE = "feature_inventory_incomplete"
    SKEW = "microversion_skew"
    REVISION = "source_microversion_mismatch"
    ROLLBACK = "rollback_active"
    CONFIGURED = "configured_part_studio"
    COUNT = "feature_count_out_of_range"
    FEATURE_SHAPE = "feature_invalid"
    ID = "feature_identity_invalid"
    DUPLICATE = "duplicate_feature_id"
    STATES = "feature_states_invalid"
    STATE_COVERAGE = "feature_state_coverage_invalid"
    STATE = "feature_state_missing_or_invalid"
    TYPE = "unsupported_feature_type"
    BT_TYPE = "unexpected_bt_type"
    NAMESPACE = "unexpected_namespace"
    SUBFEATURES = "subfeatures_present"
    PARENT = "parent_suppressed"
    CONFIGURED_SUPPRESSION = "suppression_configured"
    RETURN = "unexpected_return_after_subfeatures"
    SUPPRESSION = "unsupported_suppression_state"
    SUPPRESSION_FIELDS = "suppression_state_extra_fields"
    SUPPRESSED = "unexpected_suppressed_value"
    STATUS = "feature_status_not_ok"
    INACTIVE = "unexpected_inactive_value"
    TERMINAL = "terminal_feature_not_fillet"
    SKETCH = "missing_sketch"
    EXTRUDE = "missing_extrude"
    BODY_SCHEMA = "body_schema_invalid"
    BODY_COUNT = "body_count_not_one"
    BODY_TYPE = "body_not_solid"
    BODY_ERROR = "body_error_not_clear"
    BODY_REVISION_MISSING = "body_microversion_missing"
    BODY_REVISION = "body_microversion_mismatch"
    BODY_PINNING = "body_pinned_read_unproven"
    BODY_AMBIGUOUS = "body_microversion_ambiguous"
    BODY_DELETED = "body_microversion_deleted"
    SERIALIZATION = "serialization_version_invalid"
    LIBRARY = "library_version_invalid"


FieldName = Literal[
    "inventory",
    "configuration",
    "isComplete",
    "microversionSkew",
    "sourceMicroversion",
    "rollbackIndex",
    "configurationParameters",
    "currentConfiguration",
    "features",
    "feature",
    "featureId",
    "featureStates",
    "featureState",
    "featureType",
    "btType",
    "namespace",
    "subFeatures",
    "parentSuppressed",
    "suppressionConfigured",
    "returnAfterSubfeatures",
    "suppressionState",
    "suppressed",
    "featureStatus",
    "inactive",
    "bodies",
    "bodyType",
    "errorEnum",
    "microversionId",
    "ambiguous",
    "deleted",
    "serializationVersion",
    "libraryVersion",
]
Expected = Literal[
    "object",
    "true",
    "false",
    "matching_revision",
    "end_of_list",
    "empty_array",
    "three_to_twenty",
    "bounded_identity",
    "unique_identity",
    "exact_feature_coverage",
    "standard_feature",
    "standard_bt_type",
    "empty_namespace",
    "ordinary_suppression",
    "known_fields",
    "OK",
    "fillet",
    "sketch",
    "extrude",
    "one",
    "SOLID",
    "NO_ERROR",
    "bounded_string",
    "nonnegative_int32",
]
Primitive = Literal[
    "missing",
    "null",
    "boolean",
    "integer",
    "number",
    "string",
    "empty_string",
    "array",
    "object",
    "invalid",
]
MISSING = object()


class Diagnostic(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    reason: Reason
    field: FieldName
    expected: Expected
    actual_type: Primitive
    position: Annotated[int, Field(ge=1, le=20)] | None = None
    actual_boolean: bool | None = None


def primitive(value: object) -> Primitive:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "empty_string" if value == "" else "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "invalid"


class EligibilityRejected(EditError):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(
            "ambiguous_target"
            if diagnostic.reason == Reason.DUPLICATE
            else "unsupported_target",
            409 if diagnostic.reason == Reason.DUPLICATE else 422,
        )
        self.diagnostic = diagnostic
        # Only closed enums, bounded position and a Boolean enter the log. Never
        # interpolate the raw evidence, exception, label, identity or unknown key.
        logger.warning(
            "safe_edit_reject reason=%s position=%s field=%s expected=%s "
            "actual_type=%s actual_boolean=%s",
            diagnostic.reason.value,
            diagnostic.position,
            diagnostic.field,
            diagnostic.expected,
            diagnostic.actual_type,
            diagnostic.actual_boolean,
        )


def require(
    condition: bool,
    reason: Reason,
    field: FieldName,
    expected: Expected,
    actual: object,
    position: int | None = None,
) -> None:
    if not condition:
        raise EligibilityRejected(
            Diagnostic(
                reason=reason,
                field=field,
                expected=expected,
                actual_type=primitive(actual),
                position=position,
                actual_boolean=actual if isinstance(actual, bool) else None,
            )
        )
