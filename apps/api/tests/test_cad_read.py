"""Invented contract fixtures only; never a capture of the user's CAD document."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import cast

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import JsonValue, SecretStr, ValidationError
from sqlalchemy import select

from forge_api.auth.provider import TokenResponse
from forge_api.db.models import OnshapeAuthorization, Session, now
from forge_api.integrations.onshape.client import (
    MAX_BYTES,
    OnshapeReadClient,
    ReadError,
    bounded_json,
    retry_after,
)
from forge_api.integrations.onshape.contracts import (
    ACCEPT,
    API_VERSION,
    Operation,
    WorkspaceReference,
    endpoint,
    provider_origin,
)
from forge_api.integrations.onshape.models import FeatureSummaryList, MassSummary
from forge_api.integrations.onshape.normalize import normalize
from forge_api.integrations.onshape.service import ReadGate, capture, proof

REF = WorkspaceReference(
    documentId="a" * 24,
    workspaceId="b" * 24,
    elementId="c" * 24,
    revisionKind="workspace",
)
PATH = "/api/onshape/part-studio/snapshot"
VERSION = "d" * 24
FEATURES: dict[str, object] = {
    "features": [
        {
            "featureId": "synthetic-sketch",
            "featureType": "newSketch",
            "name": "Sketch 1",
            "suppressed": False,
            "parameters": [
                {
                    "parameterId": "plane",
                    "btType": "BTMParameterQueryList-148",
                    "queries": [{"unknownFutureField": "server-only-parameter"}],
                }
            ],
        },
        {
            "featureId": "synthetic-extrude",
            "featureType": "extrude",
            "name": "Extrude 1",
            "suppressed": False,
            "parameters": [],
        },
    ],
    "isComplete": True,
    "rollbackIndex": -1,
    "sourceMicroversion": VERSION,
    "serializationVersion": "1.2.4",
    "unknownFutureField": {"secret": "server-only-extra"},
}
PARTS = [
    {
        "partId": "synthetic-part",
        "name": "Part 1",
        "bodyType": "SOLID",
        "isMesh": False,
        "microversionId": VERSION,
        "description": "Synthetic part",
        "partNumber": "TEST",
        "state": "IN_PROGRESS",
        "customProperties": {"private": "server-only-custom"},
    }
]
BODIES = {
    "bodies": [
        {
            "id": "synthetic-part",
            "type": "SOLID",
            "faces": [{"id": "synthetic-face"}],
            "edges": [],
            "vertices": [],
        }
    ],
    "errorEnum": "NO_ERROR",
    "microversionId": {"theId": VERSION, "ambiguous": False, "deleted": False},
}
MASS = {
    "bodies": {
        "-all-": {
            "hasMass": True,
            "mass": [2.0, 1.9, 2.1],
            "volume": [1.0, 0.9, 1.1],
            "centroid": [0.0] * 9,
            "inertia": [0.0] * 27,
            "principalInertia": [0.0] * 3,
            "massMissingCount": 0,
        }
    },
    "microversionId": VERSION,
}


@dataclass
class CadProvider:
    responses: dict[str, object] = field(
        default_factory=lambda: {
            "features": FEATURES,
            "parts": PARTS,
            "bodies": BODIES,
            "mass": MASS,
        }
    )
    statuses: dict[str, int] = field(default_factory=dict)
    calls: list[httpx.Request] = field(default_factory=list, repr=False)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        name = (
            "parts"
            if "/parts/" in path
            else (
                "bodies"
                if path.endswith("bodydetails")
                else "mass"
                if path.endswith("massproperties")
                else "features"
            )
        )
        return httpx.Response(
            self.statuses.get(name, 200),
            json=self.responses[name],
            headers={"Retry-After": "120"},
        )


@contextmanager
def transport(harness: Harness, provider: CadProvider) -> Iterator[None]:
    with httpx.Client(transport=httpx.MockTransport(provider.handle)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        yield


def fetch(harness: Harness) -> httpx.Response:
    return harness.client.get(PATH, params=REF.model_dump(), headers=harness.headers())


def set_scope(harness: Harness, user_id: str, scope: str | None) -> None:
    with harness.runtime.sessions.begin() as db:
        grant = db.get(OnshapeAuthorization, user_id)
        assert grant
        grant.granted_scope = scope


@pytest.mark.parametrize(
    "value",
    [
        "https://cad.onshape.com",
        "https://CAD.onshape.com/",
        "https://cad.onshape.com:443",
    ],
)
def test_approved_origin(value: str) -> None:
    assert provider_origin(value) == "https://cad.onshape.com"


@pytest.mark.parametrize(
    "value",
    [
        "http://cad.onshape.com",
        "https://evil.example",
        "https://cad.onshape.com.evil.example",
        "https://localhost",
        "https://127.0.0.1",
        "https://10.0.0.1",
        "https://[::1]",
        "https://192.168.1.1",
        "https://user@cad.onshape.com",
        "https://:pass@cad.onshape.com",
        "https://cad.onshape.com:8443",
        "https://cad.onshape.com/api",
        "https://cad.onshape.com#x",
        "https://cad.onshape.com?",
        "https://cad.onshape.com#",
        "https://cad.onshape.com\\evil",
        "https://cad.onshape.com\n",
        "not a URL",
        "\x00https://cad.onshape.com",
        "https://cad.onshape.com\x7f",
        "https://enterprise.onshape.com",
    ],
)
def test_unapproved_origins(value: str) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        provider_origin(value)


@pytest.mark.parametrize("field", ["documentId", "workspaceId", "elementId"])
@pytest.mark.parametrize(
    "bad",
    [
        "",
        "a" * 23,
        "a" * 25,
        "../etc/passwd",
        "https://evil.example",
        "x" * 24,
        "a" * 23 + "\n",
    ],
)
def test_invalid_ids(field: str, bad: str) -> None:
    with pytest.raises(ValidationError):
        WorkspaceReference.model_validate({**REF.model_dump(), field: bad})


def test_version_is_not_a_workspace() -> None:
    with pytest.raises(ValidationError):
        WorkspaceReference.model_validate(
            {**REF.model_dump(), "revisionKind": "version"}
        )


@pytest.mark.parametrize("operation", list(Operation))
def test_each_documented_get(operation: Operation) -> None:
    provider = CadProvider()
    with httpx.Client(
        transport=httpx.MockTransport(provider.handle)
    ) as transport_client:
        client = OnshapeReadClient("https://cad.onshape.com/api", transport_client)
        method = {
            Operation.FEATURES: client.features,
            Operation.PARTS: client.parts,
            Operation.BODIES: client.bodies,
            Operation.MASS: client.mass,
        }[operation]
        result = method(REF, "synthetic-token", "0" * 32)
    assert result.microversions == [VERSION]
    request = provider.calls[0]
    path, params = endpoint(operation, REF)
    assert request.method == "GET"
    assert str(request.url).startswith(
        "https://cad.onshape.com/api/" + API_VERSION + path
    )
    assert dict(request.url.params) == params
    assert request.headers["accept"] == ACCEPT
    assert request.headers["authorization"] == "Bearer synthetic-token"
    assert request.extensions["timeout"] == {
        "connect": 3,
        "read": 8,
        "write": 3,
        "pool": 2,
    }
    assert not hasattr(client, "request")
    assert not any(hasattr(client, name) for name in ("post", "put", "patch", "delete"))


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "connection_required"),
        (403, "document_forbidden"),
        (404, "not_found"),
        (429, "rate_limited"),
        (402, "quota_exceeded"),
        (500, "provider_unavailable"),
        (503, "provider_unavailable"),
        (307, "redirect_rejected"),
    ],
)
def test_errors_no_retries_or_redirects(
    status: int, code: str, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            status,
            json={"token": "private-error-text"},
            headers={"Location": "http://127.0.0.1/private", "Retry-After": "120"},
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as transport_client,
        caplog.at_level(logging.INFO, logger="forge.onshape.read"),
        pytest.raises(ReadError) as error,
    ):
        OnshapeReadClient("https://cad.onshape.com/api", transport_client).features(
            REF, "synthetic-token", "0" * 32
        )
    assert error.value.state.code == code
    assert len(calls) == 1
    assert "private-error-text" not in str(error.value)
    serialized_logs = str([record.__dict__ for record in caplog.records])
    for value in (
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        "synthetic-token",
        "private-error-text",
    ):
        assert value not in serialized_logs
    assert caplog.records[-1].__dict__["request_id"] == "0" * 32


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("120", 120),
        ("0", 1),
        ("99999999", 86400),
        ("-1", None),
        ("NaN", None),
        ("1.5", None),
        ("9" * 50, None),
        ("１２", None),
        ("Wed, 21 Oct 2026", None),
    ],
)
def test_retry_after(value: str | None, expected: int | None) -> None:
    assert retry_after(value) == expected


@pytest.mark.parametrize(
    "case,code",
    [
        ("timeout", "provider_timeout"),
        ("network", "provider_unavailable"),
        ("json", "invalid_response"),
        ("shape", "invalid_response"),
        ("html", "invalid_response"),
        ("compressed", "invalid_response"),
        ("large", "response_too_large"),
        ("stream_large", "response_too_large"),
    ],
)
def test_bad_transport_responses(case: str, code: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if case == "timeout":
            raise httpx.ReadTimeout("private timeout URL", request=request)
        if case == "network":
            raise httpx.ConnectError("private network URL", request=request)
        headers = {"Content-Type": "application/json"}
        content = json.dumps(FEATURES).encode()
        if case == "json":
            content = b"invalid-json"
        if case == "shape":
            content = b'{"features":"invalid"}'
        if case == "html":
            headers["Content-Type"] = "text/html"
        if case == "compressed":
            headers["Content-Encoding"] = "br"
        if case == "large":
            headers["Content-Length"] = str(MAX_BYTES + 1)
        if case == "stream_large":
            content = b" " * (MAX_BYTES + 1)
        return httpx.Response(200, stream=httpx.ByteStream(content), headers=headers)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as transport_client,
        pytest.raises(ReadError) as error,
    ):
        OnshapeReadClient("https://cad.onshape.com/api", transport_client).features(
            REF, "synthetic", "0" * 32
        )
    assert error.value.state.code == code


@pytest.mark.parametrize(
    "content",
    [
        b'{"a":NaN}',
        b'{"a":1e9999}',
        b'{"a":1,"a":2}',
        b"[" * 35 + b"0" + b"]" * 35,
        json.dumps({"s": "x" * 65537}).encode(),
        b"[0," * 5,
    ],
)
def test_bounded_json(content: bytes) -> None:
    with pytest.raises(ValueError):
        bounded_json(content)


def test_normalization_preserves_unknown_only_server_side() -> None:
    result = normalize(Operation.FEATURES, cast(JsonValue, FEATURES))
    features = cast(FeatureSummaryList, result.normalized)
    assert features.items[0].feature_type == "newSketch"
    assert (
        features.items[0].parameters
        and features.items[0].parameters[0].parameter_id == "plane"
    )
    assert "server-only-extra" in json.dumps(result.raw)
    assert "server-only-extra" not in features.model_dump_json()
    result = normalize(Operation.MASS, cast(JsonValue, MASS))
    mass = cast(list[MassSummary], result.normalized)[0]
    assert mass.mass and (mass.mass.nominal) == 2
    assert mass.mass.lower == 1.9 and mass.mass.upper == 2.1
    assert mass.volume and mass.volume.lower == 0.9 and mass.volume.upper == 1.1
    assert mass.units == "provider_native_unverified"
    assert len(mass.centroid_provider_values or []) == 9


@pytest.mark.parametrize(
    "values", [[1.0, 2.0], [1.0, 2.0, 3.0], [-1.0], [float("inf")]]
)
def test_invalid_mass(values: list[float]) -> None:
    with pytest.raises(ValueError):
        normalize(
            Operation.MASS, cast(JsonValue, {"bodies": {"-all-": {"mass": values}}})
        )


def test_signed_out_cannot_read(harness: Harness) -> None:
    assert harness.client.get(PATH, params=REF.model_dump()).status_code == 401
    assert not harness.provider.calls


def test_success_snapshot_is_minimized_and_uncached(harness: Harness) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        result = fetch(harness)
        again = fetch(harness)
    assert result.status_code == 200
    data = result.json()
    assert data["features"]["count"] == 2 and data["parts"]["count"] == 1
    assert data["bodies"]["count"] == 1 and data["has_mass"] is True
    assert data["consistency"] == "unverified"
    assert result.headers["cache-control"] == "no-store"
    assert data["request_id"] == result.headers["x-forge-request-id"]
    assert again.json()["features"]["code"] == "rate_limited"
    assert len(provider.calls) == 4
    for private in (
        REF.documentId,
        VERSION,
        "synthetic-part",
        "Sketch 1",
        "server-only",
        "synthetic-access",
    ):
        assert private not in result.text


@pytest.mark.parametrize(
    "scope,status,expected",
    [
        ("OAuth2ReadPII", 200, "read_permission_required"),
        (None, 403, "permission_or_access_required"),
        ("onshape_bitmask:3", 403, "permission_or_access_required"),
        ("OAuth2Read OAuth2ReadPII", 403, "document_forbidden"),
        (None, 401, "connection_required"),
    ],
)
def test_permissions_are_not_invented(
    harness: Harness, scope: str | None, status: int, expected: str
) -> None:
    user = harness.login()
    set_scope(harness, user, scope)
    provider = CadProvider(statuses={"features": status})
    with transport(harness, provider):
        result = fetch(harness)
    assert result.json()["features"]["code"] == expected
    assert len(provider.calls) == (0 if expected == "read_permission_required" else 1)
    with harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, user)
        assert grant and grant.status == "connected" and grant.encrypted_refresh_token


@pytest.mark.parametrize("failure", ["expired", "revoked", "transient", "disconnected"])
def test_token_lifecycle(harness: Harness, failure: str) -> None:
    user = harness.login()
    if failure == "expired":
        harness.runtime.tokens._cache[user].expires_at = now() - 1
    else:
        harness.runtime.tokens.forget(user)
    if failure == "revoked":
        harness.provider.refresh_status = 400
    if failure == "transient":
        harness.provider.refresh_status = 503
    if failure == "disconnected":
        harness.client.post("/api/onshape/disconnect", headers=harness.headers())
    provider = CadProvider()
    with transport(harness, provider):
        result = fetch(harness)
    assert result.status_code == 200
    assert result.json()["features"]["status"] == (
        "success"
        if failure == "expired"
        else "provider_failure"
        if failure == "transient"
        else "unauthorized"
    )
    if failure == "expired":
        assert len(provider.calls) == 4
        assert (
            provider.calls[0].headers["authorization"]
            == "Bearer synthetic-refreshed-access"
        )
    else:
        assert not provider.calls


@pytest.mark.parametrize(
    "params,code",
    [
        ({"workspaceId": "bad-private-id"}, 400),
        ({"server": "https://evil.example"}, 400),
        ({"url": "https://cad.onshape.com/api"}, 400),
        ({"user_id": "another-user"}, 400),
        ({"revisionKind": "version"}, 422),
        ({"versionId": "b" * 24}, 422),
        ({"revisionKind": "microversion"}, 422),
    ],
)
def test_reference_boundary(
    harness: Harness, params: dict[str, str], code: int
) -> None:
    harness.login()
    result = harness.client.get(
        PATH, params={**REF.model_dump(), **params}, headers=harness.headers()
    )
    assert result.status_code == code
    assert "bad-private-id" not in result.text
    assert REF.documentId not in result.text


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "csrf", "origin", "cross_site", "body"]
)
def test_request_shape_and_csrf(harness: Harness, case: str) -> None:
    harness.login()
    headers = harness.headers()
    params = REF.model_dump()
    if case == "missing":
        del params["documentId"]
    if case == "csrf":
        headers["X-CSRF-Token"] = "0" * 64
    if case == "origin":
        headers["Origin"] = "https://cad.onshape.com"
    if case == "cross_site":
        headers["Sec-Fetch-Site"] = "cross-site"
    result = harness.client.request(
        "GET",
        PATH,
        params=list(params.items())
        + ([("documentId", "d" * 24)] if case == "duplicate" else []),
        headers=headers,
        content="private body" if case == "body" else None,
    )
    assert result.status_code in (400, 403)


@pytest.mark.parametrize(
    "statuses", [{"bodies": 500}, {"bodies": 500, "mass": 404}, {"features": 429}]
)
def test_partial_success_and_limit_stops_remaining_calls(
    harness: Harness, statuses: dict[str, int]
) -> None:
    harness.login()
    provider = CadProvider(statuses=statuses)
    with transport(harness, provider):
        result = fetch(harness).json()
    if "features" in statuses:
        assert len(provider.calls) == 1
        assert all(
            result[name]["status"] == "rate_limited"
            for name in ("features", "parts", "bodies", "mass")
        )
        assert result["features"]["retry_after_seconds"] == 120
    else:
        assert len(provider.calls) == 4 and result["features"]["count"] == 2
        assert (
            result["parts"]["count"] == 1
            and result["bodies"]["status"] == "provider_failure"
        )


def test_changed_microversion_and_incomplete_features(harness: Harness) -> None:
    user = harness.login()
    provider = CadProvider()
    provider.responses["features"] = {
        **FEATURES,
        "isComplete": False,
        "sourceMicroversion": "e" * 24,
    }
    with httpx.Client(
        transport=httpx.MockTransport(provider.handle)
    ) as transport_client:
        result = capture(
            harness.runtime,
            OnshapeReadClient("https://cad.onshape.com/api", transport_client),
            REF,
            user,
            "0" * 32,
            ReadGate(),
        )
    assert result.consistency == "mismatch"
    assert proof(result, "0" * 32).features.count is None


def test_users_never_share_authorization_or_read_results(harness: Harness) -> None:
    first_user = harness.login()
    first_cookie = harness.client.cookies.get("forge_session")
    provider = CadProvider()
    with transport(harness, provider):
        first = fetch(harness)
        harness.provider.identity_payload = {
            "id": "second-synthetic-user",
            "name": "Second Engineer",
        }
        harness.client.cookies.clear()
        harness.callback(harness.start(), code="synthetic-code")
        with harness.runtime.sessions() as db:
            second_grant = db.scalar(
                select(OnshapeAuthorization).where(
                    OnshapeAuthorization.user_id != first_user
                )
            )
            assert second_grant
            harness.runtime.tokens.remember(
                second_grant.user_id,
                second_grant.generation,
                TokenResponse(
                    access_token=SecretStr("synthetic-second-access"),
                    expires_in=3600,
                    token_type="Bearer",
                ),
            )
        provider.responses["parts"] = []
        second = fetch(harness)
        assert first.json()["parts"]["count"] == 1
        assert second.json()["parts"]["count"] == 0
        assert provider.calls[0].headers["authorization"] == "Bearer synthetic-access"
        assert (
            provider.calls[4].headers["authorization"]
            == "Bearer synthetic-second-access"
        )
        with harness.runtime.sessions() as db:
            session = db.scalar(select(Session).where(Session.user_id != first_user))
            assert session and session.user_id != first_user
        assert len(provider.calls) == 8
        assert first.json()["request_id"] != second.json()["request_id"]
        # Revoked first session cannot be supplied through query parameters.
        denied = harness.client.get(
            PATH,
            params={**REF.model_dump(), "session": first_cookie},
            headers=harness.headers(),
        )
        assert denied.status_code == 400 and len(provider.calls) == 8


def test_gate_prevents_concurrency_and_is_user_scoped() -> None:
    gate = ReadGate()
    with gate.enter("user-a"):
        with (
            pytest.raises(ReadError, match="request_in_progress"),
            gate.enter("user-a"),
        ):
            pass
        with gate.enter("user-b"):
            pass
        gate.defer("user-a", 120)
    with pytest.raises(ReadError) as error, gate.enter("user-a"):
        pass
    assert (
        error.value.state.retry_after_seconds
        and error.value.state.retry_after_seconds >= 119
    )


def test_read_routes_expose_no_cad_mutations(harness: Harness) -> None:
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert harness.client.request(method, PATH).status_code == 405


def test_session_expiry_prevents_read(harness: Harness) -> None:
    harness.login()
    with harness.runtime.sessions.begin() as db:
        session = db.scalar(select(Session))
        assert session
        session.expires_at = now() - 1
    assert harness.client.get(PATH, params=REF.model_dump()).status_code == 401


def test_get_without_origin_still_requires_session_csrf(harness: Harness) -> None:
    harness.login()
    headers = {"X-CSRF-Token": harness.headers()["X-CSRF-Token"]}
    provider = CadProvider()
    with transport(harness, provider):
        assert (
            harness.client.get(PATH, params=REF.model_dump(), headers=headers).json()[
                "features"
            ]["status"]
            == "success"
        )
    assert harness.client.get(PATH, params=REF.model_dump()).status_code == 403


def test_disconnect_during_read_discards_result(harness: Harness) -> None:
    user = harness.login()
    provider = CadProvider()

    def handle(request: httpx.Request) -> httpx.Response:
        result = provider.handle(request)
        with harness.runtime.sessions.begin() as db:
            grant = db.get(OnshapeAuthorization, user)
            assert grant
            grant.status = "disconnected"
            grant.encrypted_refresh_token = None
        return result

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        result = fetch(harness)
    assert len(provider.calls) == 1
    assert result.json()["features"]["status"] == "unauthorized"
    assert result.json()["features"]["count"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"features": [None]},
        {"features": [{"featureId": 3}]},
        {"features": [], "isComplete": "true"},
    ],
)
def test_invalid_provider_feature_shape(payload: object) -> None:
    with pytest.raises(ValueError):
        normalize(Operation.FEATURES, cast(JsonValue, payload))


@pytest.mark.parametrize(
    "base",
    [
        "http://cad.onshape.com/api",
        "https://evil.example/api",
        "https://127.0.0.1/api",
        "https://cad.onshape.com/api/other",
        "https://cad.onshape.com/api?url=evil",
        "https://enterprise.onshape.com/api",
    ],
)
def test_client_rejects_unreviewed_provider_base(base: str) -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(500))
        ) as client,
        pytest.raises(ReadError, match="unsupported_provider"),
    ):
        OnshapeReadClient(base, client)


def test_empty_part_studio_is_valid(harness: Harness) -> None:
    harness.login()
    provider = CadProvider(
        responses={
            "features": {"features": [], "isComplete": True},
            "parts": [],
            "bodies": {"bodies": []},
            "mass": {"bodies": {}},
        }
    )
    with transport(harness, provider):
        result = fetch(harness).json()
    assert result["features"]["count"] == 0 and result["parts"]["count"] == 0
    assert result["has_mass"] is None and result["consistency"] == "unverified"


def test_gate_reserves_capacity_for_active_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "forge_api.integrations.onshape.service.monotonic", lambda: 1000
    )
    gate = ReadGate()
    with gate.enter("active"):
        for index in range(1023):
            with gate.enter(f"user-{index}"):
                pass
        with pytest.raises(ReadError, match="rate_limited"), gate.enter("over-limit"):
            pass


def test_mass_flag_without_values_does_not_claim_availability(harness: Harness) -> None:
    harness.login()
    provider = CadProvider()
    provider.responses["mass"] = {"bodies": {"-all-": {"hasMass": True}}}
    with transport(harness, provider):
        result = fetch(harness).json()
    assert result["mass"]["status"] == "success"
    assert result["has_mass"] is None
