"""Synthetic normalized evidence only. No captures, credentials or real calls."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from test_cad_inspector import snapshot
from test_cad_read import BODIES, FEATURES, PARTS, REF, VERSION, CadProvider

from forge_api.core.config import Settings
from forge_api.integrations.onshape.client import OnshapeReadClient
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.models import (
    BodySummary,
    FeatureSummaryList,
    PartSummary,
    SectionState,
    Snapshot,
)
from forge_api.model_graph import (
    ForgeModelGraphV1,
    GraphQuery,
    build_graph,
    evidence_from_snapshot,
    graph_from_snapshot,
)
from forge_api.model_graph.contracts import (
    MAX_BODIES,
    MAX_EDGES,
    MAX_FEATURES,
    MAX_NODES,
    MAX_PARTS,
    GraphEvidence,
    Relation,
    SelectionObservation,
    edge_id,
)
from forge_api.model_graph.graph import BodyNode, PartNode
from forge_api.model_graph.snapshot import capture_identity, selection_from_category


@pytest.fixture
def graph() -> ForgeModelGraphV1:
    return graph_from_snapshot(snapshot(), REF)


def observed(source: Snapshot, **values: object) -> SelectionObservation:
    return SelectionObservation.model_validate(
        {
            "capture": capture_identity(source, REF),
            "state": "selected",
            "entity_type": "FACE",
            "reference": "synthetic-face",
            **values,
        }
    )


def test_empty_part_studio() -> None:
    source = snapshot(
        features={"features": [], "isComplete": True, "rollbackIndex": -1},
        parts=[],
        bodies={"bodies": []},
        mass={"bodies": {}},
    )
    result = graph_from_snapshot(source, REF)
    query = GraphQuery(result)
    assert [n.kind for n in result.nodes] == ["workspace", "part_studio", "selection"]
    assert len(result.edges) == 1 and query.ordered_features() == ()
    assert query.terminal_feature() is None and query.selection().state == "unknown"
    assert query.selected_nodes() == ()
    assert [s.returned_count for s in result.provenance[1:4]] == [0, 0, 0]


def test_order_terminal_and_typed_queries(graph: ForgeModelGraphV1) -> None:
    query = GraphQuery(graph)
    features = query.ordered_features()
    assert [f.provider_id for f in features] == [
        "synthetic-sketch",
        "synthetic-extrude",
    ]
    assert [f.label for f in features] == ["Sketch 1", "Extrude 1"]
    assert [f.feature_type for f in features] == ["newSketch", "extrude"]
    assert [f.index for f in features] == [1, 2]
    assert query.terminal_feature() == features[-1]
    assert (
        query.get_node(features[0].id) == features[0]
        and query.get_node("missing") is None
    )
    assert query.neighbors(features[0].id, "PRECEDES") == (features[1],)
    assert query.neighbors(features[1].id, "PRECEDES", incoming=True) == (features[0],)
    assert query.has_fact("PRECEDES", features[0].id, features[1].id)
    assert not query.has_fact("PRECEDES", features[1].id, features[0].id)
    assert (
        len(query.neighbors(query.nodes_of_type("part_studio")[0].id, "CONTAINS")) == 4
    )
    assert query.neighbors("missing", "CONTAINS") == ()


def test_multiple_features_are_ordered_without_dependency_inference() -> None:
    raw = deepcopy(FEATURES)
    raw["features"] = [
        {
            "featureId": f"opaque-{i}",
            "name": "same name",
            "featureType": "futureType",
            "suppressed": i % 2 == 0,
        }
        for i in range(7)
    ]
    result = graph_from_snapshot(snapshot(features=raw), REF)
    features = GraphQuery(result).ordered_features()
    assert [f.provider_id for f in features] == [f"opaque-{i}" for i in range(7)]
    assert len({f.id for f in features}) == 7
    assert sum(e.kind == "PRECEDES" for e in result.edges) == 6
    assert {e.kind for e in result.edges} == {"CONTAINS", "PRECEDES"}
    assert GraphQuery(result).terminal_feature() == features[-1]


@pytest.mark.parametrize(
    "complete,rollback", [(False, -1), (None, -1), (True, None), (True, 0), (True, 1)]
)
def test_terminal_unknown_for_incomplete_or_rolled_back_inventory(
    complete: bool | None, rollback: int | None
) -> None:
    raw = deepcopy(FEATURES)
    raw.update(isComplete=complete, rollbackIndex=rollback)
    result = graph_from_snapshot(snapshot(features=raw), REF)
    assert len(GraphQuery(result).ordered_features()) == 2
    assert GraphQuery(result).terminal_feature() is None
    assert result.provenance[1].list_complete is complete
    assert result.provenance[1].state == (
        "complete"
        if complete is True
        else "partial"
        if complete is False
        else "unknown"
    )


def test_concrete_end_index() -> None:
    raw = deepcopy(FEATURES)
    raw["rollbackIndex"] = 2
    assert (
        GraphQuery(graph_from_snapshot(snapshot(features=raw), REF)).terminal_feature()
        is not None
    )


def test_parts_bodies_and_unknown_topology(graph: ForgeModelGraphV1) -> None:
    part = next(n for n in graph.nodes if isinstance(n, PartNode))
    body = next(n for n in graph.nodes if isinstance(n, BodyNode))
    assert (
        part.provider_id == body.provider_id == "synthetic-part" and part.id != body.id
    )
    assert (part.label, part.body_type, part.is_mesh, part.microversion) == (
        "Part 1",
        "SOLID",
        False,
        VERSION,
    )
    assert (body.face_count, body.edge_count, body.vertex_count) == (1, None, None)
    assert not any({e.source, e.target} == {part.id, body.id} for e in graph.edges)


@pytest.mark.parametrize("entity_type", ["FACE", "EDGE"])
def test_selection_reference_does_not_join_matching_part_or_body(
    entity_type: str,
) -> None:
    source = snapshot()
    result = graph_from_snapshot(
        source,
        REF,
        selection=observed(source, entity_type=entity_type, reference="synthetic-part"),
    )
    query = GraphQuery(result)
    selected = query.selected_nodes()
    assert len(selected) == 1 and selected[0].provider_id == "synthetic-part"
    assert selected[0].entity_type == entity_type
    assert query.selection().reference_state == "available"
    edges = [e for e in result.edges if e.kind == "REFERENCES"]
    assert (
        len(edges) == 1
        and edges[0].source == query.selection().id
        and edges[0].target == selected[0].id
    )
    assert query.neighbors(selected[0].id, "CONTAINS", incoming=True) == ()
    assert not any(e.source == selected[0].id for e in result.edges)
    assert result.provenance[-1].mode == "browser_observation"
    assert result.provenance[-1].microversions == ()


@pytest.mark.parametrize(
    "category,state",
    [
        ("none", "clear"),
        ("FACE", "selected"),
        ("EDGE", "selected"),
        ("unknown", "unknown"),
    ],
)
def test_existing_backend_category_has_no_invented_reference(
    category: Any, state: str
) -> None:
    source = snapshot()
    query = GraphQuery(
        graph_from_snapshot(
            source,
            REF,
            selection=selection_from_category(capture_identity(source, REF), category),
        )
    )
    assert query.selection().state == state and query.selected_nodes() == ()
    assert query.selection().reference_state == (
        "unavailable" if state == "clear" else "unknown"
    )


def test_selection_unavailable_is_not_clear() -> None:
    source = snapshot()
    query = GraphQuery(
        graph_from_snapshot(
            source,
            REF,
            selection=observed(
                source, state="unavailable", entity_type=None, reference=None
            ),
        )
    )
    assert query.selection().state == query.selection().availability == "unavailable"


@pytest.mark.parametrize(
    "values",
    [
        {"entity_type": "VERTEX"},
        {"entity_type": None},
        {"state": "clear"},
        {"state": "unknown"},
        {"reference": ["x", "y"]},
        {"reference": ""},
        {"reference": "x" * 1025},
        {"reference": "x\n"},
        {"reference": "x\x7f"},
        {"mode": "unobserved_selection"},
        {"occurrencePath": []},
    ],
)
def test_selection_rejects_unsupported_malformed_and_multiple(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        observed(snapshot(), **values)


def test_topology_reference_ids_do_not_claim_continuity_across_captures() -> None:
    before, after = snapshot(), snapshot()
    after.captured_at = "2026-10-13T12:01:00+00:00"
    a = GraphQuery(
        graph_from_snapshot(before, REF, selection=observed(before))
    ).selected_nodes()[0]
    b = GraphQuery(
        graph_from_snapshot(after, REF, selection=observed(after))
    ).selected_nodes()[0]
    assert a.provider_id == b.provider_id and a.id != b.id


def test_deterministic_bytes_roundtrip_and_hash_seed(graph: ForgeModelGraphV1) -> None:
    assert graph.to_bytes() == graph_from_snapshot(snapshot(), REF).to_bytes()
    assert (
        ForgeModelGraphV1.model_validate_json(graph.to_bytes()).to_bytes()
        == graph.to_bytes()
    )
    assert json.loads(graph.to_bytes())["schema_version"] == "forge-model-graph-v1"
    program = (
        "import sys; from forge_api.model_graph import ForgeModelGraphV1; "
        "sys.stdout.buffer.write(ForgeModelGraphV1.model_validate_json("
        "sys.stdin.buffer.read()).to_bytes())"
    )
    for seed in ("1", "999"):
        result = subprocess.run(
            [sys.executable, "-c", program],
            input=graph.to_bytes(),
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
        )
        assert result.stdout == graph.to_bytes()


def test_part_and_body_input_order_has_no_semantic_effect() -> None:
    parts = [*deepcopy(PARTS), {**PARTS[0], "partId": "another-part", "name": "Other"}]
    bodies: dict[str, Any] = deepcopy(BODIES)
    bodies["bodies"] = [*bodies["bodies"], {"id": "another-body", "type": "SHEET"}]
    before = graph_from_snapshot(snapshot(parts=parts, bodies=bodies), REF)
    parts.reverse()
    bodies["bodies"].reverse()
    assert (
        before.to_bytes()
        == graph_from_snapshot(snapshot(parts=parts, bodies=bodies), REF).to_bytes()
    )


def test_names_are_not_ids_and_ids_are_context_bound(graph: ForgeModelGraphV1) -> None:
    raw: dict[str, Any] = deepcopy(FEATURES)
    raw["features"][0]["name"] = "Renamed"
    renamed = graph_from_snapshot(snapshot(features=raw), REF)
    assert [n.id for n in graph.nodes] == [n.id for n in renamed.nodes]
    assert graph.to_bytes() != renamed.to_bytes()
    other = REF.model_copy(update={"elementId": "d" * 24})
    source = snapshot()
    source.context = other
    changed = graph_from_snapshot(source, other)
    assert graph.nodes[0].id == changed.nodes[0].id
    assert graph.nodes[1].id != changed.nodes[1].id
    assert (
        GraphQuery(graph).ordered_features()[0].id
        != GraphQuery(changed).ordered_features()[0].id
    )


def test_provenance_and_missing_metadata_are_honest(graph: ForgeModelGraphV1) -> None:
    assert graph.capture.context == REF and graph.capture.consistency == "unverified"
    assert graph.capture.freshness == "captured_unverified"
    assert graph.provenance[0].mode == "request_scope"
    assert graph.nodes[0].availability == graph.nodes[1].availability == "unknown"
    assert all(s.capture == graph.capture for s in graph.provenance)
    assert all(s.microversions == (VERSION,) for s in graph.provenance[1:4])
    raw = deepcopy(FEATURES)
    raw["features"] = [
        {"featureId": "opaque", "featureType": "custom type", "namespace": "custom"}
    ]
    node = GraphQuery(
        graph_from_snapshot(snapshot(features=raw), REF)
    ).ordered_features()[0]
    assert node.label is None and node.suppressed is None and node.custom_namespace
    assert node.feature_type == "custom type"


def test_missing_revision_not_borrowed() -> None:
    raw = deepcopy(BODIES)
    raw.pop("microversionId")
    result = graph_from_snapshot(snapshot(bodies=raw), REF)
    assert result.provenance[3].microversions == () and result.provenance[
        1
    ].microversions == (VERSION,)


def test_unavailable_section_is_not_empty_evidence() -> None:
    source = snapshot()
    source.sections["features"] = SectionState(
        status="provider_failure", code="provider_unavailable"
    )
    del source.documents["features"]
    result = graph_from_snapshot(source, REF)
    assert (
        GraphQuery(result).ordered_features() == ()
        and GraphQuery(result).terminal_feature() is None
    )
    assert (
        result.provenance[1].state == "unavailable"
        and result.provenance[1].returned_count is None
    )
    assert result.provenance[1].code == "provider_unavailable"


@pytest.mark.parametrize("field", ["documentId", "workspaceId", "elementId"])
def test_cross_context_snapshot_rejected(field: str) -> None:
    other = WorkspaceReference.model_validate({**REF.model_dump(), field: "f" * 24})
    with pytest.raises(ValueError, match="mixed snapshot context"):
        graph_from_snapshot(snapshot(), other)


@pytest.mark.parametrize(
    "change",
    [
        "stale",
        "capture_time",
        "consistency",
        "part_revision",
        "mass_revision",
        "skew",
        "source_context",
        "source_time",
        "selection_context",
        "selection_time",
        "selection_stale",
    ],
)
def test_stale_mixed_or_conflicting_evidence_rejected(change: str) -> None:
    source = snapshot()
    kwargs: dict[str, Any] = {}
    if change == "stale":
        kwargs["freshness"] = "stale"
    elif change == "capture_time":
        kwargs["expected_captured_at"] = "2026-10-13T12:01:00+00:00"
    elif change == "consistency":
        source.consistency = "mismatch"
    elif change in ("part_revision", "mass_revision"):
        source.documents[
            "parts" if change == "part_revision" else "mass"
        ].microversions = ["f" * 24]
    elif change == "skew":
        data = source.documents["features"].normalized
        assert isinstance(data, FeatureSummaryList)
        data.microversion_skew = True
    else:
        evidence = evidence_from_snapshot(source, REF)
        capture = evidence.capture
        if change.endswith("context"):
            capture = capture.model_copy(
                update={"context": REF.model_copy(update={"elementId": "f" * 24})}
            )
        elif change.endswith("time"):
            capture = capture.model_copy(
                update={"captured_at": "2026-10-13T12:01:00+00:00"}
            )
        if change.startswith("source_"):
            altered = evidence.features.model_copy(
                update={
                    "source": evidence.features.source.model_copy(
                        update={"capture": capture}
                    )
                }
            )
            with pytest.raises(ValidationError):
                build_graph(evidence.model_copy(update={"features": altered}))
            return
        kwargs["selection"] = SelectionObservation(
            capture=capture, state="stale" if change == "selection_stale" else "clear"
        )
    with pytest.raises(ValueError):
        graph_from_snapshot(source, REF, **kwargs)


@pytest.mark.parametrize("kind", ["features", "parts", "bodies"])
def test_duplicate_provider_ids_rejected_per_namespace(kind: str) -> None:
    source = snapshot()
    data = source.documents[kind].normalized
    if isinstance(data, FeatureSummaryList):
        data.items.append(data.items[0])
    else:
        assert isinstance(data, list)
        data.append(data[0])
    with pytest.raises(ValidationError, match="duplicate provider identity"):
        graph_from_snapshot(source, REF)


@pytest.mark.parametrize("kind", ["features", "parts", "bodies"])
@pytest.mark.parametrize("invalid", ["", "x" * 257, "x\n", "x\x7f", 12])
def test_malformed_provider_ids_rejected(kind: str, invalid: object) -> None:
    source = snapshot()
    data = source.documents[kind].normalized
    if isinstance(data, FeatureSummaryList):
        data.items[0] = data.items[0].model_copy(update={"feature_id": invalid})
    else:
        assert isinstance(data, list)
        data[0] = data[0].model_copy(
            update={"part_id" if kind == "parts" else "body_id": invalid}
        )
    with pytest.raises(ValidationError):
        graph_from_snapshot(source, REF)


@pytest.mark.parametrize(
    "change",
    [
        "extra_section",
        "extra_document",
        "failed_with_data",
        "success_without_data",
        "wrong_type",
        "wrong_item",
        "duplicate_revisions",
        "unauthorized",
        "forbidden",
        "invalid_boolean",
        "invalid_count",
        "bad_context",
        "bad_time",
    ],
)
def test_inconsistent_snapshot_rejected(change: str) -> None:
    source = snapshot()
    if change == "extra_section":
        source.sections["invented"] = SectionState(status="success", code="ok")
    elif change == "extra_document":
        source.documents["invented"] = source.documents["parts"]
    elif change in ("failed_with_data", "unauthorized", "forbidden"):
        source.sections["parts"] = SectionState(
            status="unauthorized"
            if change == "unauthorized"
            else "forbidden"
            if change == "forbidden"
            else "provider_failure",
            code="connection_required"
            if change == "unauthorized"
            else "document_forbidden"
            if change == "forbidden"
            else "invalid_response",
        )
    elif change == "success_without_data":
        del source.documents["parts"]
    elif change == "wrong_type":
        source.documents["features"].normalized = {}
    elif change == "wrong_item":
        source.documents["bodies"].normalized = [{}]
    elif change == "duplicate_revisions":
        source.documents["bodies"].microversions = [VERSION, VERSION]
    elif change == "invalid_boolean":
        data = source.documents["features"].normalized
        assert isinstance(data, FeatureSummaryList)
        data.items[0] = data.items[0].model_copy(update={"suppressed": 1})
    elif change == "invalid_count":
        data = source.documents["bodies"].normalized
        assert isinstance(data, list)
        data[0] = data[0].model_copy(update={"face_count": -1})
    elif change == "bad_context":
        source.context = WorkspaceReference.model_construct(
            documentId="bad",
            workspaceId=REF.workspaceId,
            elementId=REF.elementId,
            revisionKind="workspace",
        )
    else:
        source.captured_at = "2026-10-13T12:00:00"
    with pytest.raises(ValueError):
        graph_from_snapshot(source, REF)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_node",
        "duplicate_provider",
        "conflicting_provider",
        "dangling_edge",
        "wrong_relation",
        "impossible_types",
        "missing_edge",
        "duplicate_edge",
        "bad_edge_id",
        "bad_node_id",
        "bad_index",
        "mixed_provenance",
        "noncanonical_nodes",
        "noncanonical_edges",
        "extra_node_field",
        "extra_graph_field",
        "bad_version",
    ],
)
def test_graph_serialization_rejects_corruption(
    graph: ForgeModelGraphV1, change: str
) -> None:
    data = graph.model_dump()
    nodes, edges = data["nodes"], data["edges"]
    if change == "duplicate_node":
        data["nodes"] = (*nodes, nodes[-1])
    elif change in ("duplicate_provider", "conflicting_provider"):
        nodes[3]["provider_id"] = (
            nodes[2]["provider_id"] if change == "duplicate_provider" else "changed"
        )
    elif change == "dangling_edge":
        edges[0]["target"] = "fmg1:feature:" + "0" * 64
    elif change == "wrong_relation":
        edges[0]["kind"] = "OWNED_BY"
    elif change == "impossible_types":
        edges[0].update(
            kind="CONTAINS",
            source=nodes[2]["id"],
            target=nodes[4]["id"],
            id=edge_id("CONTAINS", nodes[2]["id"], nodes[4]["id"]),
        )
    elif change == "missing_edge":
        data["edges"] = edges[1:]
    elif change == "duplicate_edge":
        data["edges"] = (*edges, edges[0])
    elif change == "bad_edge_id":
        edges[0]["id"] = "fmg1:edge:" + "0" * 64
    elif change == "bad_node_id":
        nodes[2]["id"] = "bad"
    elif change == "bad_index":
        nodes[2]["index"] = 3
    elif change == "mixed_provenance":
        data["provenance"][1]["capture"]["captured_at"] = "2026-10-13T12:01:00+00:00"
    elif change == "noncanonical_nodes":
        data["nodes"] = tuple(reversed(nodes))
    elif change == "noncanonical_edges":
        data["edges"] = tuple(reversed(edges))
    elif change == "extra_node_field":
        nodes[2]["feature_health"] = "OK"
    elif change == "extra_graph_field":
        data["provider_payload"] = {"token": "synthetic-private"}
    else:
        data["schema_version"] = "future-graph"
    with pytest.raises(ValidationError):
        ForgeModelGraphV1.model_validate(data)


def test_constructed_models_cannot_skip_validation(graph: ForgeModelGraphV1) -> None:
    forged = graph.model_copy(update={"edges": ()})
    with pytest.raises(ValidationError):
        forged.to_bytes()
    with pytest.raises(ValidationError):
        GraphQuery(forged)
    source = evidence_from_snapshot(snapshot(), REF)
    forged_evidence = GraphEvidence.model_construct(
        **{
            **source.model_dump(),
            "selection": source.selection.model_copy(update={"state": "stale"}),
        }
    )
    with pytest.raises(ValidationError):
        build_graph(forged_evidence)


def test_graph_deeply_immutable(graph: ForgeModelGraphV1) -> None:
    for target, name, value in (
        (GraphQuery(graph).ordered_features()[0], "suppressed", True),
        (graph.capture.context, "elementId", "f" * 24),
        (graph, "nodes", ()),
    ):
        with pytest.raises(ValidationError):
            setattr(target, name, value)


@pytest.mark.parametrize(
    "kind,limit",
    [("features", MAX_FEATURES), ("parts", MAX_PARTS), ("bodies", MAX_BODIES)],
)
def test_oversized_evidence_rejected_before_projection(kind: str, limit: int) -> None:
    source = snapshot()
    data = source.documents[kind].normalized
    if isinstance(data, FeatureSummaryList):
        data.items = [data.items[0]] * (limit + 1)
    else:
        assert isinstance(data, list)
        source.documents[kind].normalized = [data[0]] * (limit + 1)
    with pytest.raises(ValueError, match="oversized"):
        graph_from_snapshot(source, REF)


def test_maximum_supported_model() -> None:
    source = snapshot()
    features, parts, bodies = (
        source.documents[k].normalized for k in ("features", "parts", "bodies")
    )
    assert (
        isinstance(features, FeatureSummaryList)
        and isinstance(parts, list)
        and isinstance(bodies, list)
    )
    assert isinstance(parts[0], PartSummary) and isinstance(bodies[0], BodySummary)
    features.items = [
        features.items[0].model_copy(update={"feature_id": f"f-{i}"})
        for i in range(MAX_FEATURES)
    ]
    source.documents["parts"].normalized = [
        parts[0].model_copy(update={"part_id": f"p-{i}"}) for i in range(MAX_PARTS)
    ]
    source.documents["bodies"].normalized = [
        bodies[0].model_copy(update={"body_id": f"b-{i}"}) for i in range(MAX_BODIES)
    ]
    result = graph_from_snapshot(source, REF, selection=observed(source))
    assert len(result.nodes) == MAX_NODES and len(result.edges) == MAX_EDGES
    assert (
        GraphQuery(result).terminal_feature() is not None
        and len(result.to_bytes()) < 8 * 1024 * 1024
    )


def test_serialization_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("forge_api.model_graph.graph.MAX_SERIALIZED_BYTES", 100)
    with pytest.raises(ValidationError, match="serialization limit"):
        graph_from_snapshot(snapshot(), REF)


def test_raw_payloads_and_unsafe_labels_do_not_escape() -> None:
    raw: dict[str, Any] = deepcopy(FEATURES)
    raw["features"][0]["name"] = "bad\nlabel"
    source = snapshot(features=raw)
    for document in source.documents.values():
        document.raw = {"access_token": "SYNTHETIC_PRIVATE_NOT_GRAPH_DATA"}
    result = graph_from_snapshot(source, REF)
    assert GraphQuery(result).ordered_features()[0].label is None
    assert not any(
        word in result.to_bytes()
        for word in (
            b"SYNTHETIC_PRIVATE",
            b"access_token",
            b"session",
            b"database_url",
            b"configuration_json",
            b"parameters",
            b"definitions",
            b"server-only-extra",
            b"server-only-custom",
        )
    )


def test_construction_has_no_io_or_model_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> Any:
        raise AssertionError("Graph construction attempted I/O")

    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
    monkeypatch.setattr(OnshapeReadClient, "_get", forbidden)
    monkeypatch.setattr(
        "forge_api.integrations.onshape.write_client.SafeEditClient.modify_evidence",
        forbidden,
    )
    monkeypatch.setattr(
        "forge_api.modify_planner.providers.create_planner_provider", forbidden
    )
    monkeypatch.delenv("FORGE_CAD_WRITES_ENABLED", raising=False)
    assert Settings(_env_file=None).forge_cad_writes_enabled is False
    assert graph_from_snapshot(snapshot(), REF).schema_version == "forge-model-graph-v1"


def test_model_generated_provenance_rejects() -> None:
    data = evidence_from_snapshot(snapshot(), REF).model_dump()
    data["features"]["source"]["mode"] = "ai_generated"
    with pytest.raises(ValidationError):
        GraphEvidence.model_validate(data)


def test_provider_ids_remain_opaque() -> None:
    source = snapshot()
    features = source.documents["features"].normalized
    assert isinstance(features, FeatureSummaryList)
    features.items[0] = features.items[0].model_copy(
        update={"feature_id": "opaque/reference + unicode-α"}
    )
    result = graph_from_snapshot(source, REF)
    assert (
        GraphQuery(result).ordered_features()[0].provider_id
        == "opaque/reference + unicode-α"
    )


def test_requested_context_containment_stays_unknown(graph: ForgeModelGraphV1) -> None:
    query = GraphQuery(graph)
    workspace = query.nodes_of_type("workspace")[0]
    studio = query.nodes_of_type("part_studio")[0]
    edge = next(e for e in graph.edges if e.provenance == "context")
    assert (edge.kind, edge.source, edge.target) == (
        "CONTAINS",
        workspace.id,
        studio.id,
    )
    assert edge.availability == "unknown"
    assert all(
        e.availability == "available" for e in graph.edges if e.provenance != "context"
    )
    # False means unproven here: the explicit unknown association remains recorded.
    assert not query.has_fact("CONTAINS", workspace.id, studio.id)
    assert query.neighbors(workspace.id, "CONTAINS") == ()
    assert query.neighbors(studio.id, "CONTAINS", incoming=True) == ()
    assert query.relationship_evidence("CONTAINS", workspace.id, studio.id) == (edge,)
    assert edge in query.graph.edges


@pytest.mark.parametrize("relation", ["CONTAINS", "PRECEDES", "REFERENCES"])
def test_available_relationship_queries_preserve_evidence(relation: Relation) -> None:
    source = snapshot()
    query = GraphQuery(graph_from_snapshot(source, REF, selection=observed(source)))
    before, after = query.ordered_features()
    source_node, target_node = {
        "CONTAINS": (query.nodes_of_type("part_studio")[0], before),
        "PRECEDES": (before, after),
        "REFERENCES": (query.selection(), query.selected_nodes()[0]),
    }[relation]
    edges = query.relationship_evidence(relation, source_node.id, target_node.id)
    assert len(edges) == 1 and edges[0].availability == "available"
    assert query.has_fact(relation, source_node.id, target_node.id)
    assert target_node in query.neighbors(source_node.id, relation)
    assert source_node in query.neighbors(target_node.id, relation, incoming=True)
    assert query.relationship_evidence(relation, target_node.id, source_node.id) == ()
    assert query.relationship_evidence(relation, "missing", target_node.id) == ()
    assert not query.has_fact(relation, "missing", target_node.id)


def test_existing_authenticated_capture_is_reused_without_extra_reads(
    harness: Harness,
) -> None:
    from forge_api.integrations.onshape.service import ReadGate, capture

    user = harness.login()
    provider = CadProvider()
    with httpx.Client(transport=httpx.MockTransport(provider.handle)) as client:
        source = capture(
            harness.runtime,
            OnshapeReadClient("https://cad.onshape.com/api", client),
            REF,
            user,
            "0" * 32,
            ReadGate(),
        )
        assert len(provider.calls) == 4
        result = graph_from_snapshot(source, REF)
        assert len(GraphQuery(result).ordered_features()) == 2
        assert len(provider.calls) == 4


def test_all_unavailable_sources_do_not_establish_existence() -> None:
    source = snapshot()
    source.sections = {
        name: SectionState(status="unavailable", code="request_in_progress")
        for name in source.sections
    }
    source.documents = {}
    result = graph_from_snapshot(source, REF)
    assert len(result.nodes) == 3
    assert all(node.availability == "unknown" for node in result.nodes)
    assert all(edge.availability == "unknown" for edge in result.edges)


@pytest.mark.parametrize("bad", ["", "x" * 257, "x\n", 12])
def test_malformed_mass_revision_rejects_even_without_structural_versions(
    bad: Any,
) -> None:
    source = snapshot()
    for name in ("features", "parts", "bodies"):
        source.documents[name].microversions = []
    parts = source.documents["parts"].normalized
    assert isinstance(parts, list)
    parts[0] = parts[0].model_copy(update={"microversion_id": None})
    source.documents["mass"].microversions = [bad]
    with pytest.raises(ValueError):
        graph_from_snapshot(source, REF)


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-13\n12:00:00+00:00",
        "2026-10-13x12:00:00+00:00",
        "2026-13-13T12:00:00+00:00",
        "2026-10-13T12:00:00",
        "2026-10-13T12:00:00+99:00",
    ],
)
def test_capture_timestamp_rejects_malformed_input(value: str) -> None:
    source = snapshot()
    source.captured_at = value
    with pytest.raises(ValidationError):
        graph_from_snapshot(source, REF)


def test_entity_type_is_part_of_reference_identity() -> None:
    source = snapshot()
    face = GraphQuery(
        graph_from_snapshot(source, REF, selection=observed(source, entity_type="FACE"))
    ).selected_nodes()[0]
    edge = GraphQuery(
        graph_from_snapshot(source, REF, selection=observed(source, entity_type="EDGE"))
    ).selected_nodes()[0]
    assert face.provider_id == edge.provider_id
    assert face.id != edge.id


@pytest.mark.parametrize("namespace", [None, ""])
def test_absent_or_empty_namespace_does_not_become_proven_standard(
    namespace: str | None,
) -> None:
    raw: dict[str, Any] = deepcopy(FEATURES)
    raw["features"][0]["namespace"] = namespace
    feature = GraphQuery(
        graph_from_snapshot(snapshot(features=raw), REF)
    ).ordered_features()[0]
    assert feature.custom_namespace is None


def test_negative_or_malformed_namespace_evidence_rejects() -> None:
    evidence = evidence_from_snapshot(snapshot(), REF).model_dump()
    evidence["features"]["items"][0]["custom_namespace"] = False
    with pytest.raises(ValidationError):
        GraphEvidence.model_validate(evidence)
    source = snapshot()
    features = source.documents["features"].normalized
    assert isinstance(features, FeatureSummaryList)
    features.items[0] = features.items[0].model_copy(update={"custom_namespace": 1})
    with pytest.raises(ValueError):
        graph_from_snapshot(source, REF)
