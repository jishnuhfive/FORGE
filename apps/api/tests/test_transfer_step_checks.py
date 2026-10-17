"""Phase 10 transfer challenge requirements, composed in the Phase 8 checker."""

from test_step_checks import body, feat, inspector

from forge_api.step_checks.bracket import STEPS, check_step

STEP = "transfer-single-profile"
ONE = [feat(1, "sketch"), feat(2, "extrude")]


def status(ins: object) -> dict[str, str]:
    return {
        r.requirement_id: r.outcome.status
        for r in check_step(STEP, ins).results  # type: ignore[arg-type]
    }


def test_the_step_is_part_of_the_server_owned_catalog() -> None:
    assert STEP in STEPS
    assert any(r.blocking for r in STEPS[STEP])
    assert not STEPS[STEP][-1].blocking  # dimensions are never blocking


def test_single_profile_with_one_extrusion_passes() -> None:
    result = check_step(STEP, inspector(ONE, [body(8)]))
    assert result.outcome == "verified"
    assert status(inspector(ONE, [body(8)])) == {
        "transfer.sketch": "PASS",
        "transfer.one_extrusion": "PASS",
        "transfer.solid_body": "PASS",
        "transfer.l_profile": "PASS",
        "transfer.dimensions": "UNVERIFIED",
    }


def test_two_extrusions_break_the_challenge_constraint() -> None:
    ins = inspector([*ONE, feat(3, "sketch"), feat(4, "extrude")], [body(8)])
    out = check_step(STEP, ins).results[1].outcome
    assert (out.status, out.reason) == ("FAIL", "constraint_not_met")
    assert out.finding == (
        "Forge sees 2 active extrusions; this challenge asks for exactly one."
    )
    assert check_step(STEP, ins).outcome == "not_met"


def test_a_suppressed_extra_extrusion_does_not_count() -> None:
    ins = inspector([*ONE, feat(3, "extrude", suppression="suppressed")], [body(8)])
    assert status(ins)["transfer.one_extrusion"] == "PASS"


def test_plain_block_fails_the_l_profile_signal_only() -> None:
    ins = inspector(ONE, [body(6)])
    assert status(ins)["transfer.l_profile"] == "FAIL"
    assert status(ins)["transfer.one_extrusion"] == "PASS"


def test_active_fillet_makes_the_signal_a_warning_not_a_pass() -> None:
    ins = inspector([*ONE, feat(3, "fillet")], [body(8)])
    out = check_step(STEP, ins)
    assert status(ins)["transfer.l_profile"] == "WARNING"
    assert out.outcome == "unverified"  # a blocking WARNING is not a PASS


def test_no_extrusion_is_missing_and_suppressed_is_reported() -> None:
    assert (
        status(inspector([feat(1, "sketch")], []))["transfer.one_extrusion"] == "FAIL"
    )
    ins = inspector(
        [feat(1, "sketch"), feat(2, "extrude", suppression="suppressed")], []
    )
    out = check_step(STEP, ins).results[1].outcome
    assert (out.status, out.reason) == ("FAIL", "suppressed")


def test_unknown_suppression_and_unknown_faces_stay_unverified() -> None:
    ins = inspector(
        [feat(1, "sketch"), feat(2, "extrude", suppression="unverified")],
        [body(None)],
    )
    assert status(ins)["transfer.one_extrusion"] == "UNVERIFIED"
    assert status(ins)["transfer.l_profile"] == "UNVERIFIED"


def test_stale_and_unreadable_evidence_never_decide() -> None:
    stale = inspector(ONE, [body(8)], consistency="mismatch")
    assert check_step(STEP, stale).outcome == "unverified"
    gone = inspector([], [], features_status="unavailable")
    assert status(gone)["transfer.one_extrusion"] == "UNVERIFIED"


def test_renamed_features_pass_and_no_dimension_claim_is_made() -> None:
    ins = inspector(
        [feat(1, "sketch", "Outline"), feat(2, "extrude", "Zzz")], [body(8)]
    )
    assert check_step(STEP, ins).outcome == "verified"
    dims = check_step(STEP, ins).results[-1].outcome
    assert (dims.status, dims.reason) == ("UNVERIFIED", "not_observable")
