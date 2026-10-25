"""Exact observed DEFAULT state; synthetic definitions and mock CAD transport."""

import json
import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from test_cad_read import REF
from test_modify_common_metadata import OPERATIONS, REPRESENTATIVES
from test_modify_conformance import operation_for, plan_for
from test_modify_plan import OP, PlanProvider, approve, target
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import CASES, param, ui_inventory
from test_safe_edit import M0, M1, Provider, bodies, config, running

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter


def all_families() -> dict[str, Any]:
    data = ui_inventory()
    for position, key in REPRESENTATIVES:
        param(data, position, key)["libraryRelationType"] = "DEFAULT"
    return data


@pytest.mark.parametrize("position,key", CASES)
@pytest.mark.parametrize("present", [False, True])
def test_only_absence_or_exact_default_is_supported_on_every_known_parameter(
    position: int, key: str, present: bool
) -> None:
    data = ui_inventory()
    item = param(data, position, key)
    item.update(parameterName="", valueString="", importMicroversion="")
    if present:
        item["libraryRelationType"] = "DEFAULT"
    else:
        item.pop("libraryRelationType", None)
    original = deepcopy(data)
    feature = data["features"][position - 1]
    assert ui_quantity_parameter(feature, "depth" if position == 2 else "radius")
    report = diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet")
    assert report.failure is None and report.common is None
    representation = metadata(data, position)
    assert representation["parameter_shape_matches_registry"] is True
    assert representation["replacement"] == representation["rename"] == "exact_match"
    assert data == original


@pytest.mark.parametrize("position,key", REPRESENTATIVES)
@pytest.mark.parametrize(
    "field,value",
    [
        ("importMicroversion", "private-import"),
        ("parameterName", "private-name"),
        ("valueString", "private-value"),
        ("libraryReference", "private-reference"),
        ("configuration", {"private-configuration": True}),
    ],
)
def test_default_never_overrides_other_common_or_configuration_checks(
    position: int, key: str, field: str, value: Any
) -> None:
    data = all_families()
    param(data, position, key)[field] = value
    with pytest.raises(EditError, match="unsupported_target"):
        ui_quantity_parameter(
            data["features"][position - 1], "depth" if position == 2 else "radius"
        )
    assert metadata(data, position)["replacement"] == "unsupported_shape"
    assert metadata(data, position)["rename"] == "unsupported_shape"


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_default_survives_the_full_copied_provider_payload_and_fresh_verification(
    harness: Harness, position: int, kind: str
) -> None:
    provider = PlanProvider()
    provider.data = all_families()
    original = deepcopy(provider.data)
    expected = deepcopy(original["features"][position - 1])
    if kind == "RENAME_FEATURE":
        expected["name"] = "Conformance renamed"
    else:
        key = "depth" if position == 2 else "radius"
        next(p for p in expected["parameters"] if p["parameterId"] == key)[
            "expression"
        ] = "25 mm" if position == 2 else "3 mm"
    with running(harness, provider):
        request, preview = plan_for(harness, position, kind)
        assert provider.writes == 0 and provider.data == original
        result = approve(harness, request, preview)
        assert result.state == "verified_success" and provider.writes == 1
        assert len(provider.payloads) == 1
        assert json.dumps(provider.payloads[0]["feature"]) == json.dumps(expected)
        assert fingerprint(provider.data["features"][position - 1]) == fingerprint(
            expected
        )
        for feature_position, key in REPRESENTATIVES:
            assert (
                param(provider.data, feature_position, key)["libraryRelationType"]
                == "DEFAULT"
            )
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, request, preview)
        assert provider.writes == 1


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("effect", ["remove", "change", "other_feature", "add_default"])
def test_any_unapproved_library_metadata_effect_fails_exact_verification(
    position: int, kind: str, effect: str
) -> None:
    data = all_families()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), operation)
    data["features"][position - 1] = updated
    metadata_position = 5 - position if effect == "other_feature" else position
    key = "domain" if metadata_position == 2 else "filletType"
    item = param(data, metadata_position, key)
    if effect in ("remove", "other_feature"):
        del item["libraryRelationType"]
    elif effect == "change":
        item["libraryRelationType"] = "IGNORE_LIBRARY_VALUES"
    else:
        param(data, position, "wallShape" if position == 2 else "otherRadius")[
            "libraryRelationType"
        ] = "DEFAULT"
    if effect != "change":
        assert metadata(data, position)["replacement"] == "exact_match"
    data["sourceMicroversion"] = M1
    after = project_modify_evidence(REF, M1, data, config(M1), bodies(M1))
    with pytest.raises(EditError, match="verification_failed"):
        verify_operation(
            before,
            after,
            ResolvedOperation(
                operation=operation, target=target(position), preview=preview
            ),
            M1,
        )


@pytest.mark.parametrize("later_failure", [None, "extrude", "fillet"])
def test_shared_diagnostic_moves_past_default_and_never_hides_the_next_failure(
    later_failure: str | None, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    provider.data = all_families()
    if later_failure == "extrude":
        param(provider.data, 2, "hasDraft")["value"] = True
    elif later_failure == "fillet":
        param(provider.data, 3, "crossSection")["value"] = "CONIC"
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    lines = [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_standard_shape_")
    ]
    expected = []
    for position, category in ((2, "extrude"), (3, "fillet")):
        if later_failure == category:
            key, reason = (
                ("hasDraft", "wrong_boolean")
                if category == "extrude"
                else ("crossSection", "wrong_enum_value")
            )
            expected.append(
                f"safe_edit_standard_shape_failure category={category} "
                f"parameter={key} reason={reason}"
            )
            assert (
                metadata(provider.data, position)["replacement"] == "unsupported_shape"
            )
        else:
            expected.append(
                f"safe_edit_standard_shape_validation category={category} "
                "outcome=exact_match"
            )
            assert metadata(provider.data, position)["replacement"] == "exact_match"
    assert lines == expected * 2
    assert "DEFAULT" not in caplog.text and "private-" not in caplog.text
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    assert provider.writes == 0


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "fault", ["configuration", "namespace", "configured_suppression"]
)
def test_default_does_not_prove_import_or_configuration_authority(
    position: int, fault: str
) -> None:
    data = all_families()
    configuration = config()
    if fault == "configuration":
        configuration["configurationParameters"] = [
            {"parameterId": "private-configuration"}
        ]
    elif fault == "namespace":
        data["features"][position - 1]["namespace"] = "private-import"
    else:
        data["features"][position - 1]["suppressionConfigured"] = True
    with pytest.raises(EditError):
        project_modify_evidence(REF, M0, data, configuration, bodies())


def test_parameter_default_metadata_does_not_expand_query_item_schema() -> None:
    data = all_families()
    param(data, 2, "entities")["queries"][0]["libraryRelationType"] = "DEFAULT"
    report = diagnose_ui_shape(data["features"][1], "extrude")
    assert report.failure and report.failure.reason == "query_item_unexpected_field"
    assert report.common is None
