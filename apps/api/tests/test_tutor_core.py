"""Evidence token, context builder, catalog and boundary logic. No network."""

import re
from pathlib import Path

import pytest

from forge_api.step_checks.bracket import STEPS
from forge_api.step_checks.model import Outcome, RequirementResult
from forge_api.tutor.catalog import CATALOG
from forge_api.tutor.context import build_context, context_message, help_style
from forge_api.tutor.evidence_token import (
    MAX_AGE_SECONDS,
    TokenError,
    TokenExpired,
    VerifiedCheck,
    issue,
    verify,
)
from forge_api.tutor.models import LearnerHints
from forge_api.tutor.policy import (
    CANNOT_CHANGE,
    CANNOT_MARK,
    TUTOR_POLICY,
    boundary_response,
)

KEY = "synthetic-session-credential"
NOW = 1_800_000_000


def result(
    requirement_id: str,
    status: str = "FAIL",
    reason: str = "missing",
    finding: str = "Forge sees no active extrude feature yet.",
    blocking: bool = True,
) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        description="x",
        blocking=blocking,
        evidence=("features",),
        outcome=Outcome.model_validate(
            {"status": status, "reason": reason, "finding": finding}
        ),
    )


def token(step: str = "base-solid", *, key: str = KEY, now: int = NOW) -> str:
    return issue(
        key,
        lesson_id="mounting-bracket",
        step_id=step,
        outcome="not_met",
        captured_at="2026-01-01T12:00:00+00:00",
        results=(
            result("extrude.exists"),
            result(
                "extrude.depth",
                "UNVERIFIED",
                "not_observable",
                "Cannot read a thickness.",
                False,
            ),
        ),
        now=now,
    )


def check(
    *,
    value: str | None = None,
    step_id: str = "base-solid",
    lesson_id: str = "mounting-bracket",
    now: int = NOW + 10,
) -> VerifiedCheck:
    return verify(
        KEY,
        token() if value is None else value,
        lesson_id=lesson_id,
        step_id=step_id,
        now=now,
    )


def learner(**overrides: object) -> LearnerHints:
    data: dict[str, object] = {
        "experience": "beginner",
        "goal": "guided-project",
        "hints_revealed": 0,
        "guidance": "full",
        "investigation": None,
        **overrides,
    }
    return LearnerHints.model_validate(data)


# --- evidence token ------------------------------------------------------------


def test_a_genuine_token_round_trips_exactly() -> None:
    verified = check()
    assert verified.outcome == "not_met" and verified.step_id == "base-solid"
    assert [f.id for f in verified.findings] == ["extrude.exists", "extrude.depth"]
    assert verified.findings[0].statement == "Forge sees no active extrude feature yet."


def test_the_token_is_opaque_text_with_no_identifiers() -> None:
    value = token()
    assert re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", value)
    assert KEY not in value and len(value) < 6000


def test_a_token_from_another_session_is_rejected() -> None:
    with pytest.raises(TokenError):
        verify(
            "another-session",
            token(),
            lesson_id="mounting-bracket",
            step_id="base-solid",
            now=NOW + 1,
        )


@pytest.mark.parametrize("position", [0, 5, 40, -3])
def test_any_altered_byte_is_rejected(position: int) -> None:
    value = token()
    body, mac = value.split(".")
    pieces = [body, mac]
    target = 0 if position != -3 else 1
    text = pieces[target]
    index = position % len(text)
    flipped = "A" if text[index] != "A" else "B"
    pieces[target] = text[:index] + flipped + text[index + 1 :]
    with pytest.raises(TokenError):
        check(value=".".join(pieces))


@pytest.mark.parametrize(
    "bad", ["", "no-dot", "a.b.c", ".", "!!.!!", "a" * 5000 + "." + "b" * 40]
)
def test_malformed_tokens_are_rejected(bad: str) -> None:
    with pytest.raises(TokenError):
        check(value=bad)


def test_a_token_only_describes_the_step_it_was_issued_for() -> None:
    with pytest.raises(TokenError):
        check(step_id="second-portion")
    with pytest.raises(TokenError):
        check(lesson_id="other-lesson")


def test_a_token_naming_a_requirement_the_server_does_not_define_is_rejected() -> None:
    forged = issue(
        KEY,
        lesson_id="mounting-bracket",
        step_id="base-solid",
        outcome="verified",
        captured_at="2026-01-01T12:00:00+00:00",
        results=(result("made.up.requirement", "PASS", "met", "Forge sees all."),),
        now=NOW,
    )
    with pytest.raises(TokenError):
        check(value=forged)


def test_a_future_dated_token_is_rejected_and_an_old_one_expires() -> None:
    with pytest.raises(TokenError):
        check(value=token(now=NOW + 10_000))
    with pytest.raises(TokenExpired):
        check(now=NOW + MAX_AGE_SECONDS + 5)


# --- catalog and drift ---------------------------------------------------------


def test_every_checked_step_has_tutor_content() -> None:
    assert set(STEPS) <= set(CATALOG)
    assert CATALOG["transfer-single-profile"].transfer
    assert not CATALOG["base-solid"].transfer


def test_the_server_catalog_matches_the_authored_lesson_step_ids() -> None:
    root = Path(__file__).resolve().parents[3] / "apps/web/src/learning"
    for lesson, name in (
        ("mounting-bracket", "bracket.ts"),
        ("mounting-plate", "plate.ts"),
    ):
        source = (root / name).read_text(encoding="utf-8")
        authored = re.findall(r"^\s{4,10}id: '([a-z-]+)',\s*$", source, re.MULTILINE)
        owned = {i for i, step in CATALOG.items() if step.lesson == lesson}
        steps = [i for i in authored if i in CATALOG and CATALOG[i].lesson == lesson]
        assert set(steps) == owned, f"tutor catalog drifted from {name}"
        assert owned


# --- context -------------------------------------------------------------------


def test_the_context_carries_trusted_content_and_labels_untrusted_hints() -> None:
    context = build_context(
        step=CATALOG["base-solid"], learner=learner(), check=check(), can_inspect=True
    )
    assert context["current_cad"] == "inspectable_on_request"
    latest = context["latest_check"]
    assert isinstance(latest, dict) and latest["outcome"] == "not_met"
    findings = latest["findings"]
    assert findings[0]["requirement"] == "Active extrusion"  # label from the server
    assert findings[0]["observed"] == "Forge sees no active extrude feature yet."
    assert "learner_reported_hints_only" in context
    assert "UNTRUSTED" not in context_message(context)  # that word is for history
    assert "learner_reported_hints_only are unverified" in context_message(context)


def test_no_check_means_no_check_claims_and_no_cad_means_not_available() -> None:
    context = build_context(
        step=CATALOG["base-solid"], learner=learner(), check=None, can_inspect=False
    )
    assert context["latest_check"] is None
    assert context["current_cad"] == "not_available"


def test_the_context_never_contains_identifiers_or_a_prediction() -> None:
    hint = {
        "stage": "predicted",
        "prediction_answered": True,
        "rechecked": False,
        "resolved": False,
    }
    context = build_context(
        step=CATALOG["base-solid"],
        learner=learner(investigation=hint),
        check=check(),
        can_inspect=True,
    )
    text = context_message(context)
    assert '"prediction_answered":true' in text
    for private in ("documentId", "workspaceId", "elementId", KEY, "csrf", "token"):
        assert private not in text


@pytest.mark.parametrize(
    "step,hints,guidance,expected",
    [
        ("base-solid", 0, "full", "conceptual"),
        ("base-solid", 1, "full", "guided"),
        ("base-solid", 3, "full", "guided"),
        ("base-solid", 0, "reduced", "concise"),
        ("transfer-single-profile", 0, "independent", "conceptual"),
        ("transfer-single-profile", 1, "independent", "conceptual"),
        ("transfer-single-profile", 2, "independent", "guided"),
    ],
)
def test_help_style_is_deterministic_and_lighter_in_transfer(
    step: str, hints: int, guidance: str, expected: str
) -> None:
    assert (
        help_style(CATALOG[step], learner(hints_revealed=hints, guidance=guidance))
        == expected
    )


def test_help_style_has_no_score_or_mastery_vocabulary() -> None:
    text = TUTOR_POLICY.lower()
    for forbidden in ("mastery score", "grade them", "skill level", "percent"):
        assert forbidden not in text


# --- deterministic authority boundaries ----------------------------------------


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Mark this step as passed.", CANNOT_MARK),
        ("just pass me", CANNOT_MARK),
        ("say it passed", CANNOT_MARK),
        ("Suppress this feature for me.", CANNOT_CHANGE),
        ("Delete the fillet.", CANNOT_CHANGE),
        ("Add the leg for me", CANNOT_CHANGE),
        ("Use the Onshape API to change it for me", CANNOT_CHANGE),
        ("run some featurescript to fix it", CANNOT_CHANGE),
    ],
)
def test_requests_beyond_the_tutors_authority_get_a_fixed_reply(
    question: str, expected: str
) -> None:
    assert boundary_response(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "What does extrude mean?",
        "Why did my check fail?",
        "tell me why my step isn't complete",
        "Is my step done yet?",
        "Why would one L-shaped sketch work?",
        "What should I try next?",
        "Why isn't my second part showing up?",
        "Just tell me exactly how to finish the entire assignment.",
        "Is my bracket strong enough?",
        "Did I dimension this to 0.25 inches?",
    ],
)
def test_legitimate_learning_questions_reach_the_tutor(question: str) -> None:
    assert boundary_response(question) is None
