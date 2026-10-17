"""Mounting-bracket lesson requirements (Phase 8A, not wired to any runtime).

Requirements describe observable model outcomes, never feature names. Only what
the Phase 5 evidence can prove is blocking; everything else is informational and
reported UNVERIFIED with a fixed reason.
"""

from ..integrations.onshape.inspector import CadInspector
from .evidence import count_features, solid_bodies, trustworthy
from .model import Outcome, Reason, Requirement, StepCheckResult, evaluate

LESSON_ID = "mounting-bracket"
# Faces of a prismatic L-shaped body; two simple through holes add one each.
L_BRACKET_FACES = 8
HOLED_BRACKET_FACES = 10


def _out(status: str, reason: Reason, finding: str) -> Outcome:
    return Outcome.model_validate(
        {"status": status, "reason": reason, "finding": finding}
    )


def _unverified(reason: Reason, finding: str) -> Outcome:
    return _out("UNVERIFIED", reason, finding)


def _stale() -> Outcome:
    return _unverified(
        "evidence_stale", "Forge could not confirm this model snapshot is current."
    )


def _feature_needed(
    inspector: CadInspector, kind: str, noun: str, minimum: int = 1
) -> Outcome:
    if trustworthy(inspector):
        return _stale()
    counts = count_features(inspector, kind)  # type: ignore[arg-type]
    if counts is None:
        return _unverified(
            "evidence_unavailable", f"The feature list could not be read, so {noun}."
        )
    if counts.active >= minimum:
        return _out("PASS", "met", f"Forge sees {counts.active} active {noun}.")
    if counts.active + counts.possibly_active >= minimum:
        return _unverified(
            "evidence_incomplete", f"Forge cannot tell whether {noun} is active."
        )
    if not counts.absence_provable:
        return _unverified(
            "evidence_incomplete", f"The feature list is incomplete; {noun} not proven."
        )
    if counts.suppressed:
        return _out(
            "FAIL", "suppressed", "A matching feature exists but is suppressed."
        )
    return _out("FAIL", "missing", f"Forge sees no active {noun} yet.")


def sketch_exists(inspector: CadInspector) -> Outcome:
    return _feature_needed(inspector, "sketch", "sketch")


def extrude_exists(inspector: CadInspector) -> Outcome:
    return _feature_needed(inspector, "extrude", "extrude feature")


def solid_body_exists(inspector: CadInspector) -> Outcome:
    if trustworthy(inspector):
        return _stale()
    bodies = solid_bodies(inspector)
    if bodies is None:
        return _unverified("evidence_unavailable", "Body evidence could not be read.")
    if bodies.solid_count >= 1:
        return _out("PASS", "met", "Forge sees a solid body.")
    if not (bodies.all_types_known and bodies.absence_provable):
        return _unverified("evidence_incomplete", "Body types are not fully known.")
    return _out("FAIL", "missing", "Forge sees no solid body yet.")


def second_portion(inspector: CadInspector) -> Outcome:
    """Two extrusions, or a single body more complex than a plain box (L profile)."""
    if trustworthy(inspector):
        return _stale()
    extrudes = count_features(inspector, "extrude")
    bodies = solid_bodies(inspector)
    if extrudes is None or bodies is None:
        return _unverified("evidence_unavailable", "Model evidence could not be read.")
    if extrudes.active >= 2:
        return _out("PASS", "met", "Forge sees two or more active extrusions.")
    if bodies.max_faces is not None and bodies.max_faces >= L_BRACKET_FACES:
        fillets = count_features(inspector, "fillet")
        chamfers = count_features(inspector, "chamfer")
        edge_features = (fillets.active if fillets else 0) + (
            chamfers.active if chamfers else 0
        )
        if edge_features:
            return _out(
                "WARNING",
                "ambiguous_signal",
                "The face count fits a second portion, but fillets or chamfers "
                "can also raise it.",
            )
        return _out(
            "PASS",
            "met_by_alternative",
            "Forge sees a single body with more faces than a plain block.",
        )
    if bodies.max_faces is None or not (extrudes.absence_provable):
        return _unverified("evidence_incomplete", "Face counts are not fully known.")
    return _out("FAIL", "missing", "Forge sees only a plain block so far.")


def mounting_geometry(inspector: CadInspector) -> Outcome:
    """Face count only: Forge cannot tell holes from other face-adding features."""
    if trustworthy(inspector):
        return _stale()
    bodies = solid_bodies(inspector)
    if bodies is None:
        return _unverified("evidence_unavailable", "Body evidence could not be read.")
    if bodies.max_faces is None:
        return _unverified("evidence_incomplete", "Face counts are not fully known.")
    if bodies.max_faces >= HOLED_BRACKET_FACES:
        return _out(
            "PASS",
            "met",
            "The body has added faces beyond a plain L-shaped bracket.",
        )
    return _out("FAIL", "missing", "The body shows no added mounting faces yet.")


def not_observable(what: str) -> Outcome:
    return _unverified(
        "not_observable", f"Forge's current evidence cannot read {what}."
    )


def _fixed(what: str):  # type: ignore[no-untyped-def]
    return lambda _inspector: not_observable(what)


STEPS: dict[str, tuple[Requirement, ...]] = {
    "base-sketch": (
        Requirement(
            "sketch.exists", "A sketch exists", ("features",), True, sketch_exists
        ),
        Requirement(
            "sketch.profile",
            "The sketch is a closed, dimensioned profile",
            ("sketch geometry",),
            False,
            _fixed("sketch geometry, constraints or dimensions"),
        ),
    ),
    "base-solid": (
        Requirement(
            "extrude.exists", "An extrusion exists", ("features",), True, extrude_exists
        ),
        Requirement(
            "body.solid", "A solid body exists", ("bodies",), True, solid_body_exists
        ),
        Requirement(
            "extrude.depth",
            "The thickness is as intended",
            ("parameter units",),
            False,
            _fixed("a trustworthy thickness value with verified units"),
        ),
    ),
    "second-portion": (
        Requirement(
            "bracket.second_portion",
            "The bracket has a second portion",
            ("features", "bodies"),
            True,
            second_portion,
        ),
        Requirement(
            "bracket.dimensions",
            "The leg is the intended size",
            ("parameter units",),
            False,
            _fixed("dimensions with verified units"),
        ),
    ),
    "mounting-holes": (
        Requirement(
            "bracket.mounting_faces",
            "Mounting features add geometry",
            ("bodies",),
            True,
            mounting_geometry,
        ),
        Requirement(
            "holes.placement",
            "Two holes are placed and sized correctly",
            ("hole geometry",),
            False,
            _fixed("hole count, size or position"),
        ),
    ),
    "review": (
        Requirement(
            "review.mass",
            "Mass is reported",
            ("physical",),
            False,
            _fixed("mass or material"),
        ),
        Requirement(
            "review.fit",
            "Fit, strength and manufacturability",
            ("none",),
            False,
            _fixed("fit, strength or manufacturability"),
        ),
    ),
}


def check_step(step_id: str, inspector: CadInspector) -> StepCheckResult:
    return evaluate(step_id, STEPS[step_id], inspector)
