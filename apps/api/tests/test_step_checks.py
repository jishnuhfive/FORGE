"""Phase 8A: deterministic bracket requirements over synthetic, non-private evidence."""

import pytest

from forge_api.integrations.onshape.inspector import (
    CadInspector,
    EvidenceList,
    FeatureEvidence,
    InspectorBody,
    InspectorFeature,
    InspectorPart,
    PhysicalEvidence,
)
from forge_api.integrations.onshape.models import ProofSection, SnapshotProof
from forge_api.step_checks.bracket import STEPS, check_step


def feat(
    index: int, kind: str, name: str | None = None, suppression: str = "active"
) -> InspectorFeature:
    return InspectorFeature.model_validate(
        {
            "index": index,
            "name": name or f"Feature {index}",
            "feature_type": kind,
            "suppression": suppression,
            "completeness": "complete",
            "parameters": [],
            "omitted_parameters": 0,
        }
    )


def body(faces: int | None, body_type: str | None = "SOLID") -> InspectorBody:
    return InspectorBody(
        index=1,
        body_type=body_type,
        face_count=faces,
        edge_count=None,
        vertex_count=None,
    )


def inspector(
    features: list[InspectorFeature],
    bodies: list[InspectorBody],
    *,
    features_status: str = "success",
    bodies_status: str = "success",
    consistency: str = "unverified",
    mass: str = "unavailable",
) -> CadInspector:
    def section(state: str) -> ProofSection:
        return ProofSection.model_validate(
            {
                "status": state,
                "code": "ok" if state == "success" else "provider_unavailable",
            }
        )

    source = SnapshotProof.model_validate(
        {
            "request_id": "a" * 32,
            "captured_at": "2026-01-01T00:00:00Z",
            "consistency": consistency,
            "features": section(features_status),
            "parts": section("success"),
            "bodies": section(bodies_status),
            "mass": section("success"),
            "has_mass": None,
        }
    )
    return CadInspector.model_validate(
        {
            "source": source,
            "freshness": "stale"
            if consistency == "mismatch"
            else "captured_unverified",
            "features": FeatureEvidence(
                items=features,
                completeness="complete",
                returned_count=len(features),
                omitted_count=0,
            ),
            "parts": EvidenceList[InspectorPart](
                items=[], completeness="complete", returned_count=0, omitted_count=0
            ),
            "bodies": EvidenceList[InspectorBody](
                items=bodies,
                completeness="complete",
                returned_count=len(bodies),
                omitted_count=0,
            ),
            "physical": PhysicalEvidence.model_validate(
                {"mass": mass, "volume": "unverified", "missing_mass": None}
            ),
        }
    )


def status(step: str, ins: CadInspector) -> dict[str, str]:
    return {r.requirement_id: r.outcome.status for r in check_step(step, ins).results}


BASE = [feat(1, "sketch"), feat(2, "extrude")]
TWO_EXTRUDES = [*BASE, feat(3, "sketch"), feat(4, "extrude")]
FULL = [*TWO_EXTRUDES, feat(5, "sketch"), feat(6, "extrude")]


# Correct states ---------------------------------------------------------------


def test_correct_base_sketch_passes_and_profile_is_unverified() -> None:
    ins = inspector([feat(1, "sketch")], [])
    assert check_step("base-sketch", ins).outcome == "verified"
    assert status("base-sketch", ins) == {
        "sketch.exists": "PASS",
        "sketch.profile": "UNVERIFIED",
    }


def test_correct_base_solid() -> None:
    assert check_step("base-solid", inspector(BASE, [body(6)])).outcome == "verified"


def test_correct_second_portion_via_two_extrusions() -> None:
    ins = inspector(TWO_EXTRUDES, [body(8)])
    assert status("second-portion", ins)["bracket.second_portion"] == "PASS"


def test_correct_mounting_geometry() -> None:
    ins = inspector(FULL, [body(10)])
    assert check_step("mounting-holes", ins).outcome == "verified"


# Incomplete / empty -----------------------------------------------------------


def test_empty_part_studio_fails_sketch_and_solid() -> None:
    empty = inspector([], [])
    assert check_step("base-sketch", empty).outcome == "not_met"
    assert status("base-solid", empty)["body.solid"] == "FAIL"
    assert status("base-solid", empty)["extrude.exists"] == "FAIL"


def test_sketch_without_extrude_is_not_met() -> None:
    ins = inspector([feat(1, "sketch")], [])
    assert check_step("base-solid", ins).outcome == "not_met"


def test_plain_block_fails_second_portion() -> None:
    ins = inspector(BASE, [body(6)])
    assert status("second-portion", ins)["bracket.second_portion"] == "FAIL"


def test_too_few_faces_fails_mounting() -> None:
    ins = inspector(TWO_EXTRUDES, [body(8)])
    assert status("mounting-holes", ins)["bracket.mounting_faces"] == "FAIL"


# Names and alternatives -------------------------------------------------------


def test_renamed_features_still_pass() -> None:
    ins = inspector(
        [feat(1, "sketch", "Plate outline"), feat(2, "extrude", "Zzz")], [body(6)]
    )
    assert check_step("base-solid", ins).outcome == "verified"


def test_single_extruded_l_profile_is_an_accepted_alternative() -> None:
    # One L-shaped sketch extruded once: no second extrude, but an 8-face body.
    ins = inspector(BASE, [body(8)])
    outcome = check_step("second-portion", ins).results[0].outcome
    assert (outcome.status, outcome.reason) == ("PASS", "met_by_alternative")


def test_fillet_makes_face_count_route_a_warning() -> None:
    ins = inspector([*BASE, feat(3, "fillet")], [body(8)])
    assert status("second-portion", ins)["bracket.second_portion"] == "WARNING"


# Unverified -------------------------------------------------------------------


def test_unknown_face_count_is_unverified_not_zero() -> None:
    ins = inspector(BASE, [body(None)])
    assert status("second-portion", ins)["bracket.second_portion"] == "UNVERIFIED"
    assert status("mounting-holes", ins)["bracket.mounting_faces"] == "UNVERIFIED"


def test_unknown_body_type_is_unverified_not_missing() -> None:
    ins = inspector(BASE, [body(6, body_type=None)])
    assert status("base-solid", ins)["body.solid"] == "UNVERIFIED"


def test_unreadable_sections_are_unverified() -> None:
    ins = inspector([], [], features_status="unavailable", bodies_status="unavailable")
    assert check_step("base-sketch", ins).outcome == "unverified"
    assert status("base-solid", ins)["body.solid"] == "UNVERIFIED"


def test_stale_snapshot_is_unverified_everywhere() -> None:
    ins = inspector(FULL, [body(10)], consistency="mismatch")
    for step in ("base-sketch", "base-solid", "second-portion", "mounting-holes"):
        blocking = [r for r in check_step(step, ins).results if r.blocking]
        assert all(r.outcome.status == "UNVERIFIED" for r in blocking)


def test_suppressed_feature_does_not_count_and_is_reported() -> None:
    ins = inspector(
        [feat(1, "sketch"), feat(2, "extrude", suppression="suppressed")], []
    )
    out = check_step("base-solid", ins).results[0].outcome
    assert (out.status, out.reason) == ("FAIL", "suppressed")


def test_unknown_suppression_state_is_unverified_not_fail() -> None:
    ins = inspector(
        [feat(1, "sketch"), feat(2, "extrude", suppression="unverified")], [body(6)]
    )
    assert status("base-solid", ins)["extrude.exists"] == "UNVERIFIED"


def test_dimension_unit_mass_and_hole_expectations_never_pass() -> None:
    ins = inspector(FULL, [body(10)], mass="available")
    for step in STEPS:
        for r in check_step(step, ins).results:
            if not r.blocking:
                assert r.outcome.status == "UNVERIFIED"
                assert r.outcome.reason == "not_observable"


def test_review_step_is_never_forge_verified() -> None:
    assert check_step("review", inspector(FULL, [body(10)])).outcome == "unverified"


# Contract ---------------------------------------------------------------------


def test_every_requirement_names_its_evidence() -> None:
    for reqs in STEPS.values():
        for r in reqs:
            assert r.evidence and r.description and r.id


def test_results_are_immutable_and_exclude_provider_references() -> None:
    result = check_step("base-sketch", inspector([feat(1, "sketch")], []))
    with pytest.raises(ValueError):
        result.outcome = "not_met"  # type: ignore[misc]
    assert "request_id" not in result.model_dump_json()
