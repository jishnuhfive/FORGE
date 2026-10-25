"""Request-local query-role evidence, independent of replacement eligibility.

Only source-catalog role names and existing closed filter labels may escape.
Unknown identities, ambiguous duplicates and clipping prevent completeness.
No query item contents, provider IO, mutation, persistence or acceptance here.
"""

from pydantic import Field, JsonValue, field_validator

from forge_api.cad_edits.domain import Closed, EditError

from ..query_filter_evidence import (
    MAX_FILTER_LOG_CHARS,
    QueryFilterSummary,
    leaf_states_text,
    unproven_filter_summary,
)
from ..standard_edit_shapes import BASE_FIELDS
from ..standard_shape_contract import ShapeCategory, StandardId
from .standard_parameters import VOCABULARY, State

MAX_PARAMETERS = 100
MAX_ROLES = max(len(vocabulary) for vocabulary in VOCABULARY.values())
MAX_ROLE_PREFIX_CHARS = 1024
MAX_LOG_HEADER_CHARS = 128
MAX_ROLE_LOG_CHARS = MAX_FILTER_LOG_CHARS + MAX_ROLE_PREFIX_CHARS
MAX_FEATURE_LOG_CHARS = 128 * 1024


class QueryRole(Closed):
    parameter: StandardId
    occurrences: int = Field(ge=1, le=MAX_PARAMETERS)
    query_state: State | None
    query_item_count: int | None = Field(ge=0, le=2000)
    query_count_capped: bool
    filter_present: bool
    query_filter: QueryFilterSummary | None
    malformed: bool
    unexpected_fields: bool
    uninspected: bool
    truncated: bool

    @field_validator("query_filter", mode="before")
    @classmethod
    def closed_filter(cls, value: object) -> QueryFilterSummary | None:
        # The projector supplies an already closed summary, never a provider
        # mapping whose arbitrary keys could appear in validation-error paths.
        if value is not None and not isinstance(value, QueryFilterSummary):
            raise ValueError("closed_filter_projection_required")
        return value


class QueryRoleSummary(Closed):
    position: int = Field(ge=1, le=20)
    category: ShapeCategory
    total_query_roles_discovered: int = Field(ge=0, le=MAX_PARAMETERS)
    total_query_roles_inspected: int = Field(ge=0, le=MAX_ROLES)
    all_roles_inspected: bool
    unrecognized_query_parameters: int = Field(ge=0, le=MAX_PARAMETERS)
    parameter_count_capped: bool
    any_malformed: bool
    any_unexpected_fields: bool
    any_uninspected: bool
    any_truncated: bool


class FeatureQueryRoles(Closed):
    summary: QueryRoleSummary
    roles: tuple[QueryRole, ...] = Field(max_length=MAX_ROLES)


def _query_bearing(param: dict[str, JsonValue]) -> bool:
    # Include malformed query-looking envelopes as well as the exact provider
    # query-list type. This never turns representation recognition into authority.
    return (
        param.get("btType") == "BTMParameterQueryList-148"
        or "queries" in param
        or "filter" in param
    )


def _role(
    key: StandardId, source_query: bool, matches: list[dict[str, JsonValue]]
) -> QueryRole:
    if len(matches) != 1:
        # Never choose one duplicate's evidence and present it as the whole role.
        return QueryRole(
            parameter=key,
            occurrences=len(matches),
            query_state=None,
            query_item_count=None,
            query_count_capped=False,
            filter_present=any("filter" in item for item in matches),
            query_filter=None,
            malformed=True,
            unexpected_fields=False,
            uninspected=True,
            truncated=True,
        )
    param = matches[0]
    queries = param.get("queries")
    state: State = (
        "missing"
        if "queries" not in param
        else "null"
        if queries is None
        else "wrong_type"
        if not isinstance(queries, list)
        else "nonempty"
        if queries
        else "empty"
    )
    count = len(queries) if isinstance(queries, list) else None
    present = "filter" in param
    evidence = unproven_filter_summary(param["filter"]) if present else None
    allowed = BASE_FIELDS | {"queries", "filter"}
    extra = len(param) > len(allowed) or any(key not in allowed for key in param)
    return QueryRole(
        parameter=key,
        occurrences=1,
        query_state=state,
        query_item_count=min(count, 2000) if count is not None else None,
        query_count_capped=count is not None and count > 2000,
        filter_present=present,
        query_filter=evidence,
        malformed=(
            not source_query
            or param.get("btType") != "BTMParameterQueryList-148"
            or state in ("missing", "null", "wrong_type")
            or bool(evidence and (evidence.malformed or evidence.missing_operand))
        ),
        unexpected_fields=extra or bool(evidence and evidence.unexpected_fields),
        uninspected=extra or bool(evidence and evidence.uninspected),
        truncated=(count is not None and count > 2000)
        or bool(evidence and (evidence.truncated or evidence.signature_truncated)),
    )


def query_role_text(role: QueryRole) -> str:
    """Finite labels/counters only; caller supplies guarded fixed log metadata."""

    def flag(value: bool) -> str:
        return "true" if value else "false"

    f = role.query_filter
    count = (
        role.query_item_count if role.query_item_count is not None else "unavailable"
    )
    signature_truncated = f.signature_truncated if f else role.filter_present
    return (
        f"parameter={role.parameter} occurrences={role.occurrences} "
        f"query_state={role.query_state or 'unavailable'} "
        f"query_item_count={count} "
        f"query_count_capped={flag(role.query_count_capped)} "
        f"filter_present={flag(role.filter_present)} "
        f"filter_root={f.root if f else 'unknown'} "
        f"child_count={f.root_child_count if f else 0} "
        f"max_depth={f.max_depth if f else 0} node_count={f.node_count if f else 0} "
        f"categories={','.join(f.categories) if f else 'none'} "
        f"malformed={flag(role.malformed)} "
        f"missing_operand={flag(bool(f and f.missing_operand))} "
        f"unexpected_fields={flag(role.unexpected_fields)} "
        f"uninspected={flag(role.uninspected)} truncated={flag(role.truncated)} "
        f"signature={(''.join(f.signature) or 'unavailable') if f else 'unavailable'} "
        f"signature_truncated={flag(signature_truncated)} "
        f"leaf_states={leaf_states_text(f) if f else 'none'}"
    )


def _feature(
    feature: dict[str, JsonValue], position: int, category: ShapeCategory
) -> FeatureQueryRoles:
    vocabulary = VOCABULARY[category]
    params = feature.get("parameters")
    malformed = not isinstance(params, list)
    capped = isinstance(params, list) and len(params) > MAX_PARAMETERS
    uninspected = malformed or capped
    unexpected = False
    unknown_queries = 0
    matches: dict[StandardId, list[dict[str, JsonValue]]] = {}
    for item in params[:MAX_PARAMETERS] if isinstance(params, list) else []:
        if not isinstance(item, dict):
            malformed = uninspected = True
            continue
        key = next((key for key in vocabulary if key == item.get("parameterId")), None)
        if key is None:
            # Count but never emit an unknown/malformed role identity. It might
            # hide a query role, so completeness cannot be asserted either way.
            unknown_queries += int(_query_bearing(item))
            unexpected = uninspected = True
            malformed = malformed or not isinstance(item.get("parameterId"), str)
        else:
            matches.setdefault(key, []).append(item)
    roles = [
        _role(key, kind == "query", matches[key])
        for key, kind in vocabulary.items()
        if key in matches
        and (kind == "query" or any(_query_bearing(p) for p in matches[key]))
    ]
    # Reserve a fixed prefix for every catalog role plus a summary. Pathological
    # filters lose their payload explicitly, never a role record or completeness flag.
    budget = MAX_FEATURE_LOG_CHARS - (MAX_ROLES + 1) * MAX_ROLE_PREFIX_CHARS
    bounded = []
    for role in roles:
        size = len(query_role_text(role)) + MAX_LOG_HEADER_CHARS
        extra = max(0, size - MAX_ROLE_PREFIX_CHARS)
        if size > MAX_ROLE_LOG_CHARS or extra > budget:
            role = role.model_copy(
                update={"query_filter": None, "uninspected": True, "truncated": True}
            )
        else:
            budget -= extra
        bounded.append(role)
    inspected = sum(not (role.uninspected or role.truncated) for role in bounded)
    discovered = len(roles) + unknown_queries
    return FeatureQueryRoles(
        roles=tuple(bounded),
        summary=QueryRoleSummary(
            position=position,
            category=category,
            total_query_roles_discovered=discovered,
            total_query_roles_inspected=inspected,
            all_roles_inspected=not uninspected and inspected == discovered,
            unrecognized_query_parameters=unknown_queries,
            parameter_count_capped=capped,
            any_malformed=malformed or any(role.malformed for role in bounded),
            any_unexpected_fields=unexpected
            or any(role.unexpected_fields for role in bounded),
            any_uninspected=uninspected or any(role.uninspected for role in bounded),
            any_truncated=capped or any(role.truncated for role in bounded),
        ),
    )


def query_role_inventory(data: JsonValue) -> tuple[FeatureQueryRoles, ...]:
    """All present source-query or provider-query roles, in catalog order."""
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise EditError("invalid_provider_response", 503)
    features = data["features"]
    assert isinstance(features, list)
    if len(features) > 20:
        raise EditError("invalid_provider_response", 503)
    result: list[FeatureQueryRoles] = []
    for position, feature in enumerate(features, 1):
        if not isinstance(feature, dict):
            continue
        if feature.get("featureType") == "extrude":
            result.append(_feature(feature, position, "extrude"))
        elif feature.get("featureType") == "fillet":
            result.append(_feature(feature, position, "fillet"))
    return tuple(result)
