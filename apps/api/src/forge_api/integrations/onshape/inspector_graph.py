"""Graph inventory with same-Snapshot rich display evidence; no acquisition."""

from forge_api.model_graph import GraphQuery, graph_from_snapshot

from .contracts import WorkspaceReference
from .inspector import (
    MAX_FEATURES,
    CadInspector,
    _feature_evidence,
    _project,
    feature,
    inspect,
)
from .models import FeatureSummaryList, SectionState, Snapshot
from .parameters import display_text
from .service import proof


def inspect_graph(
    snapshot: Snapshot | SectionState,
    expected_context: WorkspaceReference,
    correlation: str,
) -> CadInspector:
    return _inspect_graph(snapshot, expected_context, correlation)[0]


def _inspect_graph(
    snapshot: Snapshot | SectionState,
    expected_context: WorkspaceReference,
    correlation: str,
) -> tuple[CadInspector, GraphQuery | None]:
    """Called only after acquisition's final session/grant validation.

    Failure discards evidence via the existing fixed-code unavailable response.
    Never fall back to legacy structural interpretation of a rejected Snapshot.
    """
    if isinstance(snapshot, SectionState):
        return inspect(snapshot, correlation), None
    # Preserve authorization failures, while discarding any earlier read evidence.
    denied = next(
        (
            state
            for state in snapshot.sections.values()
            if state.status in ("unauthorized", "forbidden")
        ),
        None,
    )
    if denied is not None:
        return inspect(denied, correlation), None
    try:
        graph = graph_from_snapshot(snapshot, expected_context)
        query = GraphQuery(graph)
        ordered = query.ordered_features()
        provenance = next(p for p in graph.provenance if p.id == "features")
        document = snapshot.documents.get("features")
        data = document.normalized if document else None
        items = data.items if isinstance(data, FeatureSummaryList) else []
        by_id = {item.feature_id: item for item in items}
        # Check the entire inventory before display truncation. Position checks
        # verify equivalence; rich evidence is resolved only by opaque provider ID.
        if (
            len(by_id) != len(items)
            or tuple(node.provider_id for node in ordered)
            != tuple(item.feature_id for item in items)
            or provenance.returned_count != (len(items) if document else None)
            or provenance.list_complete
            != (data.complete if isinstance(data, FeatureSummaryList) else None)
        ):
            raise ValueError("inconsistent feature inventory")
        views = []
        for ordinal, node in enumerate(ordered, 1):
            item = by_id[node.provider_id]
            if (
                node.index != ordinal
                or node.label != (display_text(item.name) or None)
                or node.feature_type != (display_text(item.feature_type) or None)
                or node.suppressed != item.suppressed
                or node.custom_namespace != (True if item.custom_namespace else None)
            ):
                raise ValueError("inconsistent feature metadata")
            if node.index <= MAX_FEATURES:
                # The unchanged display policy needs the normalized namespace
                # flag and exact provider type; null graph namespace is UNKNOWN.
                views.append(feature(item, node.index))
        source = proof(snapshot, correlation)
        inventory = _feature_evidence(
            views, len(ordered), provenance.list_complete, source
        )
    except ValueError:
        # Includes Pydantic validation errors. Do not log/serialize their inputs.
        return (
            inspect(
                SectionState(status="provider_failure", code="invalid_response"),
                correlation,
            ),
            None,
        )
    return _project(snapshot, source, inventory), query
