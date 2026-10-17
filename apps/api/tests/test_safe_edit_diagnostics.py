"""Synthetic structural diagnostics only; never copied real CAD payloads."""

import logging
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_safe_edit import M0, Provider, bodies, config, features

from forge_api.core.config import Settings
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.dev.safe_edit import probe
from forge_api.integrations.onshape.eligibility import (
    MISSING,
    Diagnostic,
    EligibilityRejected,
    Reason,
    primitive,
)
from forge_api.integrations.onshape.write_evidence import project_write_evidence


@pytest.mark.parametrize(
    "path,value,reason",
    [
        (("isComplete",), False, Reason.INCOMPLETE),
        (("isComplete",), MISSING, Reason.INCOMPLETE),
        (("microversionSkew",), True, Reason.SKEW),
        (("sourceMicroversion",), "f" * 24, Reason.REVISION),
        (("rollbackIndex",), 2, Reason.ROLLBACK),
        (("features",), [], Reason.COUNT),
        (("featureStates",), None, Reason.STATES),
        (("features", 2, "featureType"), "private-custom-feature", Reason.TYPE),
        (("features", 2, "btType"), "private-future-type", Reason.BT_TYPE),
        (("features", 2, "namespace"), None, Reason.NAMESPACE),
        (("features", 2, "namespace"), MISSING, Reason.NAMESPACE),
        (("features", 2, "subFeatures"), MISSING, Reason.SUBFEATURES),
        (("features", 2, "parentSuppressed"), MISSING, Reason.PARENT),
        (("features", 2, "suppressionConfigured"), True, Reason.CONFIGURED_SUPPRESSION),
        (("features", 2, "returnAfterSubfeatures"), MISSING, Reason.RETURN),
        (("features", 2, "suppressionState"), None, Reason.SUPPRESSION),
        (
            ("features", 2, "suppressionState", "btType"),
            "BTMSuppressionStateExpression-1811",
            Reason.SUPPRESSION,
        ),
        (
            ("features", 2, "suppressionState", "suppressionConfigured"),
            MISSING,
            Reason.CONFIGURED_SUPPRESSION,
        ),
        (
            ("features", 2, "suppressionState", "private-unknown-key"),
            "private-query",
            Reason.SUPPRESSION_FIELDS,
        ),
        (("features", 2, "suppressed"), True, Reason.SUPPRESSED),
        (
            ("featureStates", "synthetic-feature-2", "featureStatus"),
            "ERROR",
            Reason.STATUS,
        ),
        (
            ("featureStates", "synthetic-feature-2", "inactive"),
            MISSING,
            Reason.INACTIVE,
        ),
        (("serializationVersion",), None, Reason.SERIALIZATION),
        (("libraryVersion",), True, Reason.LIBRARY),
    ],
)
def test_exact_first_rejection_and_safe_projection(
    path: tuple[str | int, ...],
    value: Any,
    reason: Reason,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data = features()
    # These private-shaped strings must never enter diagnostics or exception text.
    data["features"][-1]["name"] = "private-name-never-log"
    data["features"][-1]["parameters"] = [{"query": "private-query-never-log"}]
    cursor: Any = data
    for part in path[:-1]:
        cursor = cursor[part]
    if value is MISSING:
        cursor.pop(path[-1])
    else:
        cursor[path[-1]] = value
    with caplog.at_level(logging.WARNING), pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    diagnostic = caught.value.diagnostic
    assert diagnostic.reason == reason
    assert str(caught.value) == "unsupported_target"
    assert diagnostic.actual_type in {
        "missing",
        "null",
        "boolean",
        "string",
        "integer",
        "array",
        "object",
    }
    for private in [
        "private-name-never-log",
        "private-query-never-log",
        "private-custom-feature",
        "private-future-type",
        "private-unknown-key",
        "private-query",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        M0,
        "synthetic-feature-2",
    ]:
        assert private not in caplog.text
        assert private not in diagnostic.model_dump_json()
    assert "safe_edit_reject reason=" + reason.value in caplog.text


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("configurationParameters", [{}], Reason.CONFIGURED),
        ("currentConfiguration", None, Reason.CONFIGURED),
        ("sourceMicroversion", "f" * 24, Reason.REVISION),
        ("microversionSkew", True, Reason.SKEW),
    ],
)
def test_configuration_checks_still_reject(
    field: str, value: Any, reason: Reason
) -> None:
    cfg = config()
    cfg[field] = value
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, features(), cfg, bodies())
    assert caught.value.diagnostic.reason == reason
    assert caught.value.diagnostic.field == field


@pytest.mark.parametrize(
    "case,reason",
    [
        ("schema", Reason.BODY_SCHEMA),
        ("count", Reason.BODY_COUNT),
        ("type", Reason.BODY_TYPE),
        ("error", Reason.BODY_ERROR),
        ("missing", Reason.BODY_REVISION_MISSING),
        ("revision", Reason.BODY_REVISION),
        ("ambiguous", Reason.BODY_AMBIGUOUS),
        ("deleted", Reason.BODY_DELETED),
    ],
)
def test_body_evidence_remains_required(case: str, reason: Reason) -> None:
    body = bodies()
    if case == "schema":
        body["bodies"] = "private-invalid"
    if case == "count":
        body["bodies"] = []
    if case == "type":
        body["bodies"][0]["type"] = "SURFACE"
    if case == "error":
        body["errorEnum"] = "ERROR"
    if case == "missing":
        body.pop("microversionId")
    if case == "revision":
        body["microversionId"]["theId"] = "f" * 24
    if case == "ambiguous":
        body["microversionId"]["ambiguous"] = True
    if case == "deleted":
        body["microversionId"]["deleted"] = True
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, features(), config(), body)
    assert caught.value.diagnostic.reason == reason
    if case == "missing":
        assert caught.value.diagnostic.actual_type == "missing"


def test_diagnostic_schema_rejects_unreviewed_content() -> None:
    with pytest.raises(ValidationError):
        Diagnostic.model_validate(
            {
                "reason": "private-provider-string",
                "field": "private-key",
                "expected": "false",
                "actual_type": "object",
                "position": 21,
            }
        )
    assert primitive(MISSING) == "missing" and primitive(None) == "null"
    assert primitive("private-token") == "string" and primitive("") == "empty_string"


def test_opt_in_inspector_probe_writes_off_get_only_and_generic_response(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    settings = harness.runtime.settings
    settings.environment = "development"
    settings.forge_safe_edit_diagnostics_enabled = True
    assert not settings.forge_cad_writes_enabled
    safe = Provider()
    safe.data["features"][-1]["namespace"] = None
    normal = CadProvider()
    calls: list[httpx.Request] = []

    def read_only(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        calls.append(request)
        return (
            safe.handle(request)
            if "/m/" in request.url.path
            or request.url.path.endswith("currentmicroversion")
            else normal.handle(request)
        )

    with httpx.Client(transport=httpx.MockTransport(read_only)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        with caplog.at_level(logging.WARNING):
            response = harness.client.get(
                "/api/onshape/part-studio/inspector",
                params=REF.model_dump(),
                headers=harness.headers(),
            )
    assert response.status_code == 200 and len(calls) == 9
    assert "reason=unexpected_namespace position=3" in caplog.text
    assert "actual_type=null" in caplog.text
    assert "unexpected_namespace" not in response.text
    assert not any("Safe-Edit" in key for key in response.headers)
    assert safe.writes == 0
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0


@pytest.mark.parametrize(
    "enabled,environment,writes",
    [
        (False, "development", False),
        (True, "test", False),
        (True, "development", True),
    ],
)
def test_probe_runtime_guards_never_read_or_write(
    harness: Harness,
    enabled: bool,
    environment: str,
    writes: bool,
) -> None:
    settings = harness.runtime.settings
    settings.forge_safe_edit_diagnostics_enabled = enabled
    settings.environment = environment  # type: ignore[assignment]
    settings.forge_cad_writes_enabled = writes

    def never(_: httpx.Request) -> httpx.Response:
        raise AssertionError("guarded diagnostic made a provider request")

    with httpx.Client(transport=httpx.MockTransport(never)) as client:
        probe(harness.runtime, client, REF, "synthetic")


@pytest.mark.parametrize("environment,writes", [("test", False), ("development", True)])
def test_probe_configuration_requires_development_and_writes_off(
    environment: str, writes: bool
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment=environment,
            forge_safe_edit_diagnostics_enabled=True,
            forge_cad_writes_enabled=writes,
        )
