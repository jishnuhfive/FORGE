"""Flat-sheet-metal evidence only; invented allows values never grant authority."""

import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from test_cad_read import REF
from test_modify_filter_signature import FIXTURES, SOURCE_TREES
from test_modify_representation import enabled_settings
from test_modify_ui_conformance import param, replacement_rejects, ui_inventory
from test_safe_edit import Provider

from forge_api.cad_edits.domain import fingerprint
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.query_filter_evidence import (
    MAX_FILTER_LOG_CHARS,
    LeafEvidence,
    LeafFieldState,
    LeafState,
    leaf_states_text,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import ShapeValidationError

FLAT_TYPE = "BTFlatSheetMetalFilter-3018"
HOSTILE = "private-provider-value\nreason=exact_match"
# Independent expectations from the current official SDK/OpenAPI, not LEAF_RULES.
ALLOWS_CASES: list[tuple[dict[str, Any], LeafState, bool]] = [
    ({"allows": "MODEL_ONLY"}, "model_only", False),
    ({"allows": "FLATTENED_ONLY"}, "flattened_only", False),
    ({"allows": "MODEL_AND_FLATTENED"}, "model_and_flattened", False),
    ({"allows": "UNKNOWN"}, "unknown_value", False),
    ({}, "missing", False),
    ({"allows": None}, "null", True),
    ({"allows": False}, "wrong_type", True),
    ({"allows": 1}, "wrong_type", True),
    ({"allows": []}, "wrong_type", True),
    ({"allows": {HOSTILE: HOSTILE}}, "wrong_type", True),
    ({"allows": "arbitrary-unknown-string"}, "unknown_value", False),
    ({"allows": HOSTILE}, "unknown_value", False),
]
EXTRUDE_SIGNATURE = (
    "and(or(and(and(flat_sheet_metal,sketch_object),entity_type),"
    "and(and(geometry,flat_sheet_metal),entity_type)),construction)"
)


def extrude_candidate(properties: dict[str, Any]) -> Any:
    # Synthetic reported topology plus invented allows inputs. No real capture or
    # inferred model/flattened equivalence; the real leaf values are still unknown.
    tree = deepcopy(SOURCE_TREES[0])
    union = tree["operand1"]
    union["operand1"]["operand1"]["operand1"] = {"btType": FLAT_TYPE, **properties}
    union["operand2"]["operand1"]["operand2"] = {"btType": FLAT_TYPE, **properties}
    union["operand1"]["operand1"]["operand2"]["objectType"] = "ANY_SKETCH_OBJECT"
    return tree


@pytest.mark.parametrize("properties,expected,malformed", ALLOWS_CASES)
def test_flat_leaf_states_are_explicit_closed_and_do_not_accept_filters(
    properties: dict[str, Any], expected: LeafState, malformed: bool
) -> None:
    tree = extrude_candidate(properties)
    original = deepcopy(tree)
    summary = unproven_filter_summary(tree)
    assert "".join(summary.signature) == EXTRUDE_SIGNATURE
    assert summary.node_count == 13 and summary.max_depth == 5
    assert summary.malformed is malformed
    assert not (
        summary.uninspected
        or summary.unexpected_fields
        or summary.missing_operand
        or summary.signature_truncated
        or summary.truncated
    )
    for visit in (5, 11):
        assert (
            LeafEvidence(
                visit=visit, fields=(LeafFieldState(field="allows", state=expected),)
            )
            in summary.leaf_states
        )
    assert tree == original
    data = ui_inventory()
    param(data, 2, "entities")["filter"] = tree
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(data["features"][1], "depth")
    assert caught.value.failure.reason == "query_filter_unproven"
    assert caught.value.query_filter == summary
    assert str(caught.value) == "unsupported_target"
    replacement_rejects(data, 2)


@pytest.mark.parametrize(
    "key",
    [
        "nodeId",
        "queryString",
        "featureId",
        "allowsFlattenedGeometry",
        "operand1",
        HOSTILE,
    ],
)
def test_flat_leaf_schema_envelope_flags_every_extra_field_without_walking_it(
    key: str,
) -> None:
    leaf: dict[str, Any] = {"btType": FLAT_TYPE, "allows": "MODEL_ONLY"}
    leaf[key] = leaf  # A cyclic unknown value must stay opaque.
    summary = unproven_filter_summary(leaf)
    assert summary.unexpected_fields and summary.uninspected
    assert summary.node_count == summary.max_depth == 1
    assert summary.signature == ("flat_sheet_metal",)
    assert not summary.signature_truncated and not summary.malformed
    assert leaf_states_text(summary) == "1:allows=model_only"
    assert (
        key not in summary.model_dump_json()
        and HOSTILE not in summary.model_dump_json()
    )


@pytest.mark.parametrize("properties,expected,malformed", ALLOWS_CASES)
@pytest.mark.parametrize("unexpected", [False, True])
def test_flat_leaf_logs_are_closed_with_four_existing_gets_and_no_writes(
    properties: dict[str, Any],
    expected: LeafState,
    malformed: bool,
    unexpected: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    fields = {**properties, **({HOSTILE: {HOSTILE: HOSTILE}} if unexpected else {})}
    tree = extrude_candidate(fields)
    param(provider.data, 2, "entities")["filter"] = tree
    # Keep the existing Fillet fixture byte-for-byte unchanged.
    param(provider.data, 3, "entities")["filter"] = deepcopy(SOURCE_TREES[1])
    original = deepcopy(provider.data)
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
        if r.message.startswith("safe_edit_standard_shape_failure")
    ]
    assert len(lines) == 4
    for line in lines:
        assert "reason=query_filter_unproven" in line
        assert "signature_truncated=false" in line and len(line) < MAX_FILTER_LOG_CHARS
        if "category=extrude " in line:
            assert f"signature={EXTRUDE_SIGNATURE} " in line
            assert f"malformed={str(malformed).lower()} " in line
            assert f"unexpected_fields={str(unexpected).lower()} " in line
            assert f"uninspected={str(unexpected).lower()} " in line
            assert f"5:allows={expected};" in line and f"11:allows={expected};" in line
        else:
            assert "category=fillet " in line
            assert f"signature={FIXTURES['fillet']['signature']} " in line
            assert f"leaf_states={FIXTURES['fillet']['leaf_states']}" in line
            assert "max_depth=8 node_count=17" in line and "uninspected=false" in line
    for forbidden in (
        "private-",
        "arbitrary-unknown-string",
        "MODEL_ONLY",
        "FLATTENED_ONLY",
        "MODEL_AND_FLATTENED",
        "UNKNOWN",
        "BTFlatSheetMetalFilter",
        "reason=exact_match",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        provider.marker,
    ):
        assert forbidden not in caplog.text
    assert len(provider.calls) == 4 and all(c.method == "GET" for c in provider.calls)
    assert provider.writes == 0
    assert fingerprint(provider.data) == fingerprint(original)
