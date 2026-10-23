"""Run existing Inspector fixtures/assertions through the graph and frozen reference."""

import hashlib
import json
from copy import deepcopy

import pytest
import test_body_topology as topology_cases
import test_cad_inspector as inspector_cases
from inspector_reference import inspect as legacy_inspect
from test_cad_inspector import snapshot
from test_cad_read import BODIES, FEATURES, PARTS, REF

from forge_api.integrations.onshape.inspector import CadInspector
from forge_api.integrations.onshape.inspector_graph import inspect_graph
from forge_api.integrations.onshape.models import SectionState, Snapshot

# Reuse every parameterized case and the original public assertions. The fixture
# below adds byte equivalence without editing or weakening the original tests.
test_normal_equivalence = inspector_cases.test_order_types_names_parts_and_topology
test_metadata_equivalence = inspector_cases.test_incomplete_features
test_parameters_equivalence = inspector_cases.test_parameter_adapters
test_empty_equivalence = inspector_cases.test_empty_and_provider_completeness
test_missing_metadata_equivalence = (
    inspector_cases.test_missing_topology_and_metadata_not_zero
)
test_physical_equivalence = (
    inspector_cases.test_physical_evidence_no_units_or_estimates_invented
)
test_topology_equivalence = (
    topology_cases.test_topology_evidence_survives_every_projection
)


def equivalent(source: Snapshot, correlation: str = "a" * 32) -> CadInspector:
    expected = legacy_inspect(source, correlation)
    result = inspect_graph(source, REF, correlation)
    assert result.model_dump_json() == expected.model_dump_json()
    return result


@pytest.fixture(autouse=True)
def compare_existing_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inspector_cases, "inspect", equivalent)
    monkeypatch.setattr(topology_cases, "inspect", equivalent)


@pytest.mark.parametrize("complete", [None, False, True])
@pytest.mark.parametrize("rollback", [None, -1, 0, 2, 4])
def test_multiple_order_completeness_and_rollback(
    complete: bool | None, rollback: int | None
) -> None:
    raw = deepcopy(FEATURES)
    raw["features"] = [
        {
            "featureId": identifier,
            "featureType": kind,
            "name": "Repeated name",
            "suppressed": suppressed,
            "parameters": [],
        }
        for identifier, kind, suppressed in (
            ("z opaque", "newSketch", False),
            ("a/opaque", "extrude", True),
            ("m:opaque", "fillet", None),
            ("b opaque", "chamfer", False),
        )
    ]
    raw.update(isComplete=complete, rollbackIndex=rollback)
    result = equivalent(snapshot(features=raw))
    assert [f.index for f in result.features.items] == [1, 2, 3, 4]
    assert [f.feature_type for f in result.features.items] == [
        "sketch",
        "extrude",
        "fillet",
        "chamfer",
    ]


@pytest.mark.parametrize("section", ["features", "parts", "bodies", "mass"])
def test_unavailable_section_equivalence(section: str) -> None:
    source = snapshot()
    del source.documents[section]
    source.sections[section] = SectionState(
        status="provider_failure", code="provider_timeout"
    )
    result = equivalent(source)
    if section == "features":
        assert result.features.completeness == "unavailable"
        assert result.source.features.count is None


def test_limits_and_provider_part_body_order_are_unchanged() -> None:
    # Unique identities are valid graph inputs, even past display truncation.
    source = snapshot(
        features={
            "features": [
                {
                    "featureId": f"feature-{101 - n}",
                    "featureType": "extrude",
                    "name": f"Feature {n}",
                    "suppressed": False,
                    "parameters": [
                        {
                            "parameterId": "endDepth",
                            "btType": "BTMParameterQuantity-147",
                            "expression": f"{n} mm",
                        }
                    ]
                    * 19,
                }
                for n in range(101)
            ],
            "isComplete": True,
        },
        parts=[
            {
                **PARTS[0],
                "partId": f"p-{201 - n}",
                "name": f"Part {n}",
            }
            for n in range(201)
        ],
        bodies={
            "bodies": [{"id": f"b-{201 - n}", "type": f"Type {n}"} for n in range(201)],
            "microversionId": BODIES["microversionId"],
        },
    )
    result = equivalent(source)
    assert result.features.omitted_count == 1
    assert result.features.items[-1].name == "Feature 99"
    assert result.features.items[0].omitted_parameters == 3
    assert result.features.items[99].parameters[0].text == "99 mm"
    assert result.parts.omitted_count == result.bodies.omitted_count == 1
    assert [p.name for p in result.parts.items] == [f"Part {n}" for n in range(200)]
    assert [b.body_type for b in result.bodies.items] == [
        f"Type {n}" for n in range(200)
    ]


def test_public_schema_is_frozen() -> None:
    schema = json.dumps(CadInspector.model_json_schema(), sort_keys=True).encode()
    assert (
        hashlib.sha256(schema).hexdigest()
        == "274a91b1c8ee280ec3fd41f87b579d398d4dc4001281f5f86ec2244465e151ca"
    )
