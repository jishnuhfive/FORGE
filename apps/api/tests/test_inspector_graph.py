"""Phase 13 rejection, authenticated-route and authority regressions; synthetic only."""

from collections.abc import Callable
from typing import cast

import httpx2 as httpx
import pytest
from conftest import Harness
from inspector_reference import inspect as legacy_inspect
from sqlalchemy import Engine, event, select
from test_cad_inspector import PATH, snapshot
from test_cad_read import REF, CadProvider, transport

from forge_api.db.models import OnshapeAuthorization, Session, now
from forge_api.integrations.onshape import inspector_graph, routes
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.inspector import CadInspector
from forge_api.integrations.onshape.inspector_graph import inspect_graph
from forge_api.integrations.onshape.models import (
    FeatureSummaryList,
    SectionState,
    Snapshot,
)
from forge_api.integrations.onshape.service import capture
from forge_api.model_graph import ForgeModelGraphV1, GraphQuery, graph_from_snapshot
from forge_api.model_graph.graph import FeatureNode


def unavailable(result: CadInspector, code: str = "invalid_response") -> None:
    assert result.features.items == []
    assert result.parts.items == []
    assert result.bodies.items == []
    assert result.features.completeness == "unavailable"
    assert result.features.returned_count == 0
    assert result.source.features.count is None
    assert all(
        getattr(result.source, name).code == code
        for name in ("features", "parts", "bodies", "mass")
    )
    assert result.physical.mass == "unverified"


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-features",
        "duplicate-parts",
        "duplicate-bodies",
        "documentId",
        "workspaceId",
        "elementId",
        "revision-conflict",
        "stale",
        "skew",
        "oversized",
        "serialization-budget",
    ],
)
def test_invalid_evidence_fails_closed(
    fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = snapshot()
    if fault.startswith("duplicate-"):
        section = fault.removeprefix("duplicate-")
        data = source.documents[section].normalized
        if isinstance(data, FeatureSummaryList):
            data.items.append(data.items[0])
        else:
            collection = cast(list[object], data)
            collection.append(collection[0])
    elif fault in ("documentId", "workspaceId", "elementId"):
        source.context = REF.model_copy(update={fault: "f" * 24})
    elif fault == "revision-conflict":
        source.documents["mass"].microversions = ["e" * 24]
    elif fault == "stale":
        source.consistency = "mismatch"
    elif fault == "skew":
        cast(
            FeatureSummaryList, source.documents["features"].normalized
        ).microversion_skew = True
    elif fault == "oversized":
        data = cast(FeatureSummaryList, source.documents["features"].normalized)
        data.items = [data.items[0]] * 2001
    elif fault == "serialization-budget":
        monkeypatch.setattr("forge_api.model_graph.graph.MAX_SERIALIZED_BYTES", 1)
    result = inspect_graph(source, REF, "0123456789abcdef" * 2)
    unavailable(result)
    assert result.source.request_id == "0123456789abcdef" * 2
    for private in (
        *REF.model_dump().values(),
        "synthetic-",
        "fmg1:",
        "ValidationError",
    ):
        # "workspace" is an intentional public context-kind substring.
        if private != "workspace":
            assert private not in result.model_dump_json()


@pytest.mark.parametrize(
    "fault", ["order", "missing", "name", "type", "suppression", "namespace", "index"]
)
def test_query_snapshot_correspondence_checked_before_truncation(
    fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = GraphQuery.ordered_features

    def changed(query: GraphQuery) -> tuple[FeatureNode, ...]:
        nodes = original(query)
        if fault == "order":
            return tuple(reversed(nodes))
        if fault == "missing":
            return nodes[:-1]
        field, value = {
            "name": ("label", "Different"),
            "type": ("feature_type", "fillet"),
            "suppression": ("suppressed", True),
            "namespace": ("custom_namespace", True),
            "index": ("index", 2),
        }[fault]
        return (nodes[0].model_copy(update={field: value}), *nodes[1:])

    monkeypatch.setattr(GraphQuery, "ordered_features", changed)
    unavailable(inspect_graph(snapshot(), REF, "a" * 32))


def test_omitted_feature_identity_still_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = snapshot()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items = [
        data.items[0].model_copy(update={"feature_id": f"opaque-{n}"})
        for n in range(101)
    ]
    original = GraphQuery.ordered_features

    def changed(query: GraphQuery) -> tuple[FeatureNode, ...]:
        nodes = original(query)
        return (*nodes[:100], nodes[-1].model_copy(update={"provider_id": "other"}))

    monkeypatch.setattr(GraphQuery, "ordered_features", changed)
    unavailable(inspect_graph(source, REF, "a" * 32))


def test_unknown_relationships_remain_unknown() -> None:
    query = GraphQuery(graph_from_snapshot(snapshot(), REF))
    workspace = query.nodes_of_type("workspace")[0]
    studio = query.nodes_of_type("part_studio")[0]
    assert (
        query.relationship_evidence("CONTAINS", workspace.id, studio.id)[0].availability
        == "unknown"
    )
    assert not query.has_fact("CONTAINS", workspace.id, studio.id)
    assert query.neighbors(workspace.id, "CONTAINS") == ()
    assert query.neighbors(studio.id, "CONTAINS", incoming=True) == ()
    before, after = query.ordered_features()
    assert query.has_fact("PRECEDES", before.id, after.id)
    assert not query.has_fact("PRECEDES", after.id, before.id)


@pytest.mark.parametrize("fail_graph", [False, True])
def test_route_context_four_reads_no_ai_write_or_database_mutation(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    fail_graph: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    harness.login()
    headers = harness.headers()
    provider = CadProvider()
    calls: list[WorkspaceReference] = []
    sources: list[Snapshot] = []
    statements: list[str] = []
    ai_calls: list[httpx.Request] = []

    def build(source: Snapshot, expected: WorkspaceReference) -> ForgeModelGraphV1:
        calls.append(expected)
        sources.append(source)
        assert expected == REF
        assert len(provider.calls) == 4
        if fail_graph:
            raise ValueError("private-sentinel " + REF.documentId)
        return graph_from_snapshot(source, expected)

    def record_sql(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(statement.split()[0].upper())

    async def ai_handler(
        client: httpx.AsyncClient, request: httpx.Request, **kwargs: object
    ) -> httpx.Response:
        ai_calls.append(request)
        raise AssertionError("Inspector cannot invoke AI")

    monkeypatch.setattr(inspector_graph, "graph_from_snapshot", build)
    engine = cast(Engine, harness.runtime.sessions.kw["bind"])
    event.listen(engine, "before_cursor_execute", record_sql)
    monkeypatch.setattr(httpx.AsyncClient, "send", ai_handler)
    with transport(harness, provider):
        response = harness.client.get(PATH, params=REF.model_dump(), headers=headers)
    event.remove(engine, "before_cursor_execute", record_sql)
    assert response.status_code == 200
    assert calls == [REF]
    assert len(provider.calls) == 4
    assert all(call.method == "GET" for call in provider.calls)
    assert statements and set(statements) == {"SELECT"}
    assert not ai_calls
    assert not harness.runtime.settings.forge_cad_writes_enabled
    assert response.headers["cache-control"] == "no-store"
    result = CadInspector.model_validate(response.json())
    assert result.source.request_id == response.headers["x-forge-request-id"]
    if fail_graph:
        unavailable(result)
    else:
        assert len(result.features.items) == 2
        assert (
            result.model_dump_json()
            == legacy_inspect(sources[0], result.source.request_id).model_dump_json()
        )
    for private in (
        "private-sentinel",
        REF.documentId,
        "fmg1:",
        "provenance",
        "featureId",
        "synthetic-sketch",
    ):
        assert private not in response.text + caplog.text


@pytest.mark.parametrize("ending", ["logout", "disconnected", "revoked"])
def test_final_lifecycle_check_precedes_graph(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, ending: str
) -> None:
    user = harness.login()
    headers = harness.headers()
    provider = CadProvider()

    def forbidden_graph(*args: object, **kwargs: object) -> ForgeModelGraphV1:
        raise AssertionError("Discarded evidence must never reach graph construction")

    def handle(request: httpx.Request) -> httpx.Response:
        result = provider.handle(request)
        if request.url.path.endswith("massproperties"):
            with harness.runtime.sessions.begin() as db:
                if ending == "logout":
                    session = db.scalar(select(Session))
                    assert session
                    session.revoked_at = now()
                else:
                    grant = db.get(OnshapeAuthorization, user)
                    assert grant
                    grant.status = ending
                    grant.encrypted_refresh_token = None
        return result

    monkeypatch.setattr(inspector_graph, "graph_from_snapshot", forbidden_graph)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        response = harness.client.get(PATH, params=REF.model_dump(), headers=headers)
    assert len(provider.calls) == 4
    unavailable(CadInspector.model_validate(response.json()), "connection_required")


def test_request_context_is_independent_of_acquired_snapshot(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness.login()
    original = capture

    def mixed(*args: object, **kwargs: object) -> Snapshot:
        source = cast(Callable[..., Snapshot], original)(*args, **kwargs)
        source.context = REF.model_copy(update={"elementId": "f" * 24})
        return source

    monkeypatch.setattr(routes, "capture", mixed)
    provider = CadProvider()
    with transport(harness, provider):
        response = harness.client.get(
            PATH, params=REF.model_dump(), headers=harness.headers()
        )
    unavailable(CadInspector.model_validate(response.json()))
    assert len(provider.calls) == 4


@pytest.mark.parametrize(
    "failure",
    [
        "microversion",
        "version-id",
        "microversion-id",
        "body",
        "duplicate-csrf",
        "duplicate-origin",
        "cross-site",
        "invalid-context",
    ],
)
def test_additional_route_security_boundaries(harness: Harness, failure: str) -> None:
    harness.login()
    headers = list(harness.headers().items())
    params = list(REF.model_dump().items())
    content = None
    if failure == "microversion":
        params = [(k, "microversion" if k == "revisionKind" else v) for k, v in params]
    elif failure in ("version-id", "microversion-id"):
        params.append(
            ("versionId" if failure == "version-id" else "microversionId", "f" * 24)
        )
    elif failure == "body":
        content = "private-sentinel"
    elif failure == "duplicate-csrf":
        headers.append(("X-CSRF-Token", headers[-1][1]))
    elif failure == "duplicate-origin":
        headers.append(("Origin", harness.runtime.settings.origin))
    elif failure == "cross-site":
        headers.append(("Sec-Fetch-Site", "cross-site"))
    elif failure == "invalid-context":
        params = [
            (k, "private-sentinel" if k == "workspaceId" else v) for k, v in params
        ]
    provider = CadProvider()
    with transport(harness, provider):
        response = harness.client.request(
            "GET", PATH, params=params, headers=headers, content=content
        )
    assert response.status_code in (400, 403, 422)
    assert response.headers["cache-control"] == "no-store"
    assert not provider.calls
    assert (
        "private-sentinel" not in response.text and REF.documentId not in response.text
    )


def test_authorization_stop_preserves_fixed_error() -> None:
    source = snapshot()
    del source.documents["parts"]
    source.sections["parts"] = SectionState(
        status="forbidden", code="document_forbidden"
    )
    unavailable(inspect_graph(source, REF, "a" * 32), "document_forbidden")
