"""DEV fixed GET-only investigation; no CAD write or recovery authority."""

import logging
from enum import StrEnum
from typing import Literal, Protocol

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.domain import Baseline, EditError, Proposal, fingerprint
from forge_api.core.config import Settings
from forge_api.db.database import make_engine
from forge_api.integrations.onshape.contracts import CadId
from forge_api.integrations.onshape.eligibility import EligibilityRejected, Reason
from forge_api.integrations.onshape.service import read_permission
from forge_api.integrations.onshape.write_client import SafeEditClient
from forge_api.integrations.onshape.write_evidence import project_write_evidence


class Category(StrEnum):
    SUPPRESSED = "suppressed"
    AUX = "suppressionState"
    CONFIGURED = "suppressionConfigured"
    PARENT = "parentSuppressed"
    RETURN = "returnAfterSubfeatures"
    STATUS = "featureStatus-related"
    NODE = "provider_node_bookkeeping"
    SERIALIZATION = "serialization_bookkeeping"
    PARAMETER = "parameter_definition"
    QUERY = "query_definition"
    IDENTITY = "feature_identity"
    TYPE = "feature_type"
    ORDER = "feature_order"
    UNKNOWN = "unknown_definition_field"


Check = Literal[
    "trusted_baseline",
    "ack_passed_runtime",
    "ack_details_available",
    "original_timing_available",
    "audit_window_within_deadline",
    "projection",
    "head_bracketing",
    "head_advanced",
    "feature_count",
    "feature_order",
    "target_identity",
    "terminal_fillet",
    "target_suppressed",
    "definitions",
    "parameters",
    "queries",
    "changed_field",
    "serialization",
    "library",
    "parent_suppression_evidence",
    "configured_suppression_evidence",
    "suppression_aux_evidence",
    "feature_state_evidence",
    "body_revision_evidence",
    "configuration",
    "one_solid",
    "body_error",
    "body_revision",
    "full_definition_snapshot",
    "evidence_modes_available",
]


class Entry(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", hide_input_in_errors=True
    )

    stage: Literal[
        "provider_ack",
        "baseline_read",
        "post_read",
        "final_compare",
        "structural",
        "timing",
    ]
    check: Check
    result: Literal["pass", "fail"]
    position: int | None = Field(default=None, ge=1, le=20)
    category: Category | None = None
    reason: Reason | None = None
    mode: (
        Literal[
            "COMPLETE",
            "UNAVAILABLE_EMPTY",
            "NULL_UNAVAILABLE",
            "ORDINARY_OBJECT",
            "EXPLICIT_FALSE",
            "STRUCTURALLY_NOT_APPLICABLE",
            "INDEPENDENTLY_PROVEN_UNCONFIGURED",
            "EXPLICIT_CLEAN_FLAGS",
            "EXACT_PINNED_ID_FLAGS_UNAVAILABLE",
        ]
        | None
    ) = None
    elapsed_ms: int | None = Field(default=None, ge=0, le=180000)


class Snapshot(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", hide_input_in_errors=True
    )

    microversion: CadId
    features: JsonValue
    configuration: JsonValue
    bodies: JsonValue


def _items(data: JsonValue) -> list[dict[str, JsonValue]]:
    raw = data.get("features") if isinstance(data, dict) else None
    if (
        not isinstance(raw, list)
        or len(raw) > 20
        or not all(isinstance(x, dict) for x in raw)
    ):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _differences(
    left: JsonValue, right: JsonValue, path: tuple[str, ...] = ()
) -> set[Category]:
    if (
        not isinstance(left, (dict, list))
        and type(left) is type(right)
        and left == right
    ):
        return set()
    if isinstance(left, dict) and isinstance(right, dict):
        result: set[Category] = set()
        for key in left.keys() | right.keys():
            if key not in left or key not in right:
                result.add(_category((*path, key)))
            else:
                result.update(_differences(left[key], right[key], (*path, key)))
        return result
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return set().union(
            *(_differences(a, b, path) for a, b in zip(left, right, strict=True))
        )
    return {_category(path)}


def _category(path: tuple[str, ...]) -> Category:
    if not path:
        return Category.UNKNOWN
    root = path[0]
    if (
        root == "suppressionState"
        and len(path) > 1
        and path[1] not in {"btType", "nodeId", "suppressionConfigured"}
    ):
        return Category.UNKNOWN
    if root == "parameters":
        return (
            Category.QUERY
            if set(path) & {"queries", "queryString", "deterministicIds", "query"}
            else Category.PARAMETER
        )
    return {
        "suppressed": Category.SUPPRESSED,
        "suppressionState": Category.AUX,
        "suppressionConfigured": Category.CONFIGURED,
        "parentSuppressed": Category.PARENT,
        "returnAfterSubfeatures": Category.RETURN,
        "featureStatus": Category.STATUS,
        "nodeId": Category.NODE,
        "serializationVersion": Category.SERIALIZATION,
        "featureId": Category.IDENTITY,
        "featureType": Category.TYPE,
        "btType": Category.TYPE,
        "namespace": Category.TYPE,
    }.get(root, Category.UNKNOWN)


def _query_nodes(value: JsonValue) -> list[JsonValue]:
    if isinstance(value, list):
        return [node for item in value for node in _query_nodes(item)]
    if not isinstance(value, dict):
        return []
    bt_type = value.get("btType")
    if isinstance(bt_type, str) and "Query" in bt_type:
        return [value]
    nodes: list[JsonValue] = []
    for key, item in value.items():
        if key in {"queries", "queryString", "deterministicIds", "query"}:
            nodes.append({key: item})
        else:
            nodes.extend(_query_nodes(item))
    return nodes


def diagnose(
    settings: Settings,
    proposal: Proposal,
    before: Snapshot,
    after: Snapshot,
    *,
    head_bracketed: bool,
    acknowledged_at_runtime: bool,
    audit_elapsed_ms: int | None = None,
    definition_before: JsonValue | None = None,
    definition_after: JsonValue | None = None,
) -> tuple[Entry, ...]:
    """Report available comparisons without inferring missing original facts."""
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise EditError("invalid_request", 400)
    rows: list[Entry] = []

    def add(
        check: Check,
        passed: bool,
        stage: Literal[
            "provider_ack",
            "baseline_read",
            "post_read",
            "final_compare",
            "structural",
            "timing",
        ] = "final_compare",
        **extra: object,
    ) -> None:
        rows.append(
            Entry.model_validate(
                {
                    "stage": stage,
                    "check": check,
                    "result": "pass" if passed else "fail",
                    **extra,
                }
            )
        )

    add("ack_passed_runtime", acknowledged_at_runtime, "provider_ack")
    # Neither the original response/marker nor monotonic timing was durable.
    # Failure here is evidence availability, never an invented invariant failure.
    add("ack_details_available", False, "provider_ack")
    add("original_timing_available", False, "timing")
    if audit_elapsed_ms is not None:
        add(
            "audit_window_within_deadline",
            0 <= audit_elapsed_ms < 29000,
            "timing",
            elapsed_ms=audit_elapsed_ms,
        )
    projected: list[Baseline | None] = []
    for snapshot, is_after in ((before, False), (after, True)):
        stage: Literal["baseline_read", "post_read"] = (
            "post_read" if is_after else "baseline_read"
        )
        try:
            result = project_write_evidence(
                proposal.binding.context,
                snapshot.microversion,
                snapshot.features,
                snapshot.configuration,
                snapshot.bodies,
                after=is_after,
                pinned_body_microversion=snapshot.microversion,
            )
            add("projection", True, stage)
            projected.append(result)
        except EligibilityRejected as error:
            add("projection", False, stage, reason=error.diagnostic.reason)
            projected.append(None)
        except ValueError, TypeError, EditError:
            add("projection", False, stage)
            projected.append(None)
    for snapshot, full, is_after in (
        (before, definition_before, False),
        (after, definition_after, True),
    ):
        if full is None:
            continue
        full_stage: Literal["baseline_read", "post_read"] = (
            "post_read" if is_after else "baseline_read"
        )
        try:
            project_write_evidence(
                proposal.binding.context,
                snapshot.microversion,
                full,
                snapshot.configuration,
                snapshot.bodies,
                after=is_after,
                pinned_body_microversion=snapshot.microversion,
            )
            add("full_definition_snapshot", True, full_stage)
        except ValueError, TypeError, EditError:
            add("full_definition_snapshot", False, full_stage)
    add("trusted_baseline", projected[0] == proposal.baseline, "baseline_read")
    add("head_bracketing", head_bracketed, "post_read")
    add(
        "head_advanced",
        after.microversion != proposal.baseline.microversion,
        "post_read",
    )
    baseline = proposal.baseline
    current = projected[1]
    add("evidence_modes_available", current is not None, "post_read")
    if current is None:
        raw = after.features if isinstance(after.features, dict) else {}
        add("serialization", raw.get("serializationVersion") == baseline.serialization)
        library = raw.get("libraryVersion")
        add("library", type(library) is int and library == baseline.library)
        definitions = [dict(item) for item in _items(after.features)]
        if definitions:
            definitions[-1].pop("suppressed", None)
        add(
            "definitions",
            bool(definitions) and fingerprint(definitions) == baseline.definitions,
        )
    if current is not None:
        for field in (
            "serialization",
            "library",
            "definitions",
            "parent_suppression_evidence",
            "configured_suppression_evidence",
            "suppression_aux_evidence",
            "feature_state_evidence",
            "body_revision_evidence",
        ):
            # Closed check names only; model validation rejects accidental expansion.
            rows.append(
                Entry.model_validate(
                    {
                        "stage": "final_compare",
                        "check": field,
                        "result": "pass"
                        if getattr(current, field) == getattr(baseline, field)
                        else "fail",
                    }
                )
            )
            value = getattr(current, field)
            if isinstance(value, StrEnum):
                rows.append(
                    Entry.model_validate(
                        {
                            "stage": "post_read",
                            "check": field,
                            "result": "pass",
                            "mode": value.value,
                        }
                    )
                )
            elif isinstance(value, tuple):
                for position, mode in enumerate(value, 1):
                    rows.append(
                        Entry.model_validate(
                            {
                                "stage": "post_read",
                                "check": field,
                                "result": "pass",
                                "position": position,
                                "mode": mode.value,
                            }
                        )
                    )
    left = _items(before.features if definition_before is None else definition_before)
    right = _items(after.features if definition_after is None else definition_after)
    add("feature_count", len(left) == len(right) and 3 <= len(left) <= 20, "structural")
    add(
        "feature_order",
        [x.get("featureId") for x in left] == [x.get("featureId") for x in right]
        and bool(left),
        "structural",
    )
    add(
        "target_identity",
        bool(right) and right[-1].get("featureId") == baseline.feature_id,
        "structural",
    )
    add(
        "terminal_fillet",
        bool(right) and right[-1].get("featureType") == "fillet",
        "structural",
    )
    add(
        "target_suppressed",
        bool(right) and right[-1].get("suppressed") is True,
        "structural",
    )
    for index, (a, b) in enumerate(zip(left, right, strict=False)):
        position = index + 1
        differences = _differences(a, b)
        same_queries = fingerprint(_query_nodes(a.get("parameters"))) == fingerprint(
            _query_nodes(b.get("parameters"))
        )
        if not same_queries:
            differences.add(Category.QUERY)
        for category in sorted(differences):
            add(
                "changed_field",
                category == Category.SUPPRESSED
                and index == len(left) - 1
                and a.get("featureId") == b.get("featureId")
                and a.get("suppressed") is False
                and b.get("suppressed") is True,
                "structural",
                position=position,
                category=category,
            )
        structural_left, structural_right = dict(a), dict(b)
        if index == len(left) - 1 and a.get("featureId") == b.get("featureId"):
            structural_left.pop("suppressed", None)
            structural_right.pop("suppressed", None)
        add(
            "definitions",
            fingerprint(structural_left) == fingerprint(structural_right),
            "structural",
            position=position,
        )
        same_parameters = fingerprint(
            {k: v for k, v in a.items() if k == "parameters"}
        ) == fingerprint({k: v for k, v in b.items() if k == "parameters"})
        add("parameters", same_parameters, "structural", position=position)
        add(
            "queries",
            same_queries,
            "structural",
            position=position,
        )
    config = after.configuration if isinstance(after.configuration, dict) else {}
    add(
        "configuration",
        config.get("configurationParameters") == []
        and config.get("currentConfiguration") == []
        and config.get("sourceMicroversion") == after.microversion
        and config.get("microversionSkew") is False,
        "post_read",
    )
    body = after.bodies if isinstance(after.bodies, dict) else {}
    bodies = body.get("bodies")
    add(
        "one_solid",
        isinstance(bodies, list)
        and len(bodies) == 1
        and isinstance(bodies[0], dict)
        and bodies[0].get("type") == "SOLID",
        "post_read",
    )
    add("body_error", body.get("errorEnum") == "NO_ERROR", "post_read")
    marker = body.get("microversionId")
    add(
        "body_revision",
        isinstance(marker, dict) and marker.get("theId") == after.microversion,
        "post_read",
    )
    return tuple(rows)


class Preserved(Protocol):
    proposal: Proposal
    before: dict[str, JsonValue]
    after: dict[str, JsonValue]
    after_heads: list[JsonValue]
    audit: list[tuple[str, int]]
    full_before: JsonValue
    full_after: JsonValue


def read_definition_pair(
    settings: Settings, proposal: Proposal, expected_after: str
) -> tuple[JsonValue, JsonValue]:
    """Fixed GET-only reads for a trusted decoded operation; never accepts a URL."""
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise EditError("invalid_request", 400)
    context = proposal.binding.context
    expected_after = TypeAdapter(CadId).validate_python(expected_after, strict=True)
    # Internal harnesses need the same privacy boundary as application startup.
    for name in ("httpx2", "httpcore2", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)
    engine = make_engine(settings)

    def get_only(request: httpx.Request) -> None:
        if request.method != "GET":
            raise EditError("write_disabled", 403)

    try:
        with (
            httpx.Client(follow_redirects=False, trust_env=False) as oauth,
            httpx.Client(
                follow_redirects=False,
                trust_env=False,
                event_hooks={"request": [get_only]},
            ) as transport,
        ):
            auth = AuthRuntime.create(settings, engine, oauth)
            if read_permission(auth, proposal.binding.user) is not True:
                raise EditError("permission_or_access_required", 403)
            token = auth.tokens.get_valid_onshape_access_token(proposal.binding.user)
            client = SafeEditClient(settings, transport, token)
            if client.head(context) != expected_after:
                raise EditError("model_changed")
            results = []
            for marker in (proposal.baseline.microversion, expected_after):
                scope = f"d/{context.documentId}/m/{marker}/e/{context.elementId}"
                data = client._exchange(
                    "GET",
                    f"/partstudios/{scope}/features?includeGeometryIds=false&noSketchGeometry=false&rollbackBarIndex=-1",
                )
                if (
                    not isinstance(data, dict)
                    or data.get("sourceMicroversion") != marker
                    or data.get("microversionSkew") is not False
                    or data.get("isComplete") is not True
                ):
                    raise EditError("invalid_provider_response", 503)
                results.append(data)
            if client.head(context) != expected_after:
                raise EditError("model_changed")
            return results[0], results[1]
    finally:
        engine.dispose()


def report_preserved(state: Preserved) -> None:
    """Internal harness adapter; prints validated minimized records only."""
    first, last = state.after_heads[0], state.after_heads[-1]
    if not isinstance(first, dict) or not isinstance(last, dict):
        raise EditError("invalid_provider_response", 503)
    before = Snapshot(
        microversion=state.proposal.baseline.microversion,
        features=state.before["features"],
        configuration=state.before["configuration"],
        bodies=state.before["bodydetails"],
    )
    after = Snapshot.model_validate(
        {
            "microversion": first.get("microversion"),
            "features": state.after["features"],
            "configuration": state.after["configuration"],
            "bodies": state.after["bodydetails"],
        }
    )
    if not hasattr(state, "full_before"):
        state.full_before, state.full_after = read_definition_pair(
            Settings(), state.proposal, after.microversion
        )
    claimed = [t for k, t in state.audit if k == "write_proposal_claimed"]
    ended = [t for k, t in state.audit if k == "write_uncertain"]
    elapsed = (
        (ended[0] - claimed[0]) * 1000 if len(claimed) == len(ended) == 1 else None
    )
    entries = diagnose(
        Settings(),
        state.proposal,
        before,
        after,
        head_bracketed=len(state.after_heads) == 2 and first == last,
        acknowledged_at_runtime=any(
            k == "write_provider_acknowledged" for k, _ in state.audit
        ),
        audit_elapsed_ms=elapsed,
        definition_before=state.full_before,
        definition_after=state.full_after,
    )
    for row in entries:
        print(
            "safe_edit_verify "
            + " ".join(
                f"{key}={value}"
                for key, value in row.model_dump(mode="json", exclude_none=True).items()
            ),
            flush=True,
        )
