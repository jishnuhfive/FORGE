import json
from typing import Any, get_args

import pytest

from forge_api.cad_create import (
    NeedsClarification,
    PlanReady,
    Rejected,
    Unsupported,
    compile_brief,
    explain_plan,
    plan_creation,
)
from forge_api.cad_create.explain import INTENT_KEYS, RATIONALE
from forge_api.cad_create.models import IntentKey
from forge_api.cad_create.wire import CLARIFY_FIELDS


def dim(v: float, unit: str = "mm") -> dict[str, Any]:
    return {"value": v, "unit": unit}


def centered_hole(d: dict[str, Any]) -> dict[str, Any]:
    return {"diameter": d, "placement": {"mode": "center"}}


def brief_wire(
    w: dict[str, Any], length: dict[str, Any], t: dict[str, Any], holes: list[Any]
) -> dict[str, Any]:
    return {
        "outcome": "brief",
        "design": {
            "kind": "rect_plate_with_through_holes",
            "width": w,
            "length": length,
            "thickness": t,
            "holes": holes,
        },
    }


# Synthetic model outputs for "Make a 60 by 40 by 10 mm plate with an 8 mm hole in
# the center." and "Create a 6 cm x 4 cm plate, 1 cm thick, with one centered 8 mm
# through-hole." No model is called.
MM = brief_wire(dim(60), dim(40), dim(10), [centered_hole(dim(8))])
CM = brief_wire(
    dim(6, "cm"), dim(4, "cm"), dim(1, "cm"), [centered_hole(dim(0.8, "cm"))]
)


def ready(raw: Any) -> PlanReady:
    result = plan_creation(raw)
    assert isinstance(result, PlanReady)
    return result


def test_ready_matches_compiler_output() -> None:
    r = ready(MM)
    assert r.plan == compile_brief(r.brief)
    assert [s.op.operation for s in r.plan.steps] == [
        "CREATE_SKETCH_RECT",
        "EXTRUDE_NEW",
        "CREATE_SKETCH_CIRCLE",
        "EXTRUDE_REMOVE",
    ]


def test_paraphrases_normalize_to_same_brief_and_digest() -> None:
    inch = brief_wire(
        dim(60 / 25.4, "in"),
        dim(40 / 25.4, "in"),
        dim(10 / 25.4, "in"),
        [centered_hole(dim(8 / 25.4, "in"))],
    )
    a, b, c = ready(MM), ready(CM), ready(inch)
    assert a.brief == b.brief == c.brief
    assert a.plan.digest == b.plan.digest == c.plan.digest
    # explicit zero offset is the same intent as "centered"
    explicit = brief_wire(
        dim(60),
        dim(40),
        dim(10),
        [
            {
                "diameter": dim(8),
                "placement": {"mode": "offset_from_center", "x": dim(0), "y": dim(0)},
            }
        ],
    )
    assert ready(explicit).plan.digest == a.plan.digest


def test_accepts_json_text_and_offsets() -> None:
    raw = brief_wire(
        dim(60),
        dim(40),
        dim(10),
        [
            {
                "diameter": dim(6),
                "placement": {"mode": "offset_from_center", "x": dim(-15), "y": dim(0)},
            }
        ],
    )
    r = ready(json.dumps(raw))
    assert r.plan.steps[2].op.model_dump()["center_x_um"] == -15_000


def test_plate_without_holes_and_hole_order() -> None:
    assert len(ready(brief_wire(dim(60), dim(40), dim(10), [])).plan.steps) == 2

    def h(x: float) -> dict[str, Any]:
        return {
            "diameter": dim(6),
            "placement": {"mode": "offset_from_center", "x": dim(x), "y": dim(0)},
        }

    a = ready(brief_wire(dim(60), dim(40), dim(10), [h(-15), h(15)]))
    b = ready(brief_wire(dim(60), dim(40), dim(10), [h(15), h(-15)]))
    assert a.plan.digest == b.plan.digest


def test_clarification_is_server_worded_and_sorted() -> None:
    r = plan_creation(
        {
            "outcome": "clarification",
            "reason": "missing_dimension",
            "fields": ["thickness", "width", "width"],
        }
    )
    assert isinstance(r, NeedsClarification)
    assert r.fields == ("width", "thickness")
    assert r.questions == ("What is the width?", "What is the thickness?")
    r2 = plan_creation(
        {
            "outcome": "clarification",
            "reason": "ambiguous_intent",
            "fields": ["object_kind"],
        }
    )
    assert isinstance(r2, NeedsClarification)
    assert r2.reason == "ambiguous_intent"


def test_every_clarify_field_has_a_question() -> None:
    from forge_api.cad_create.planner import QUESTIONS

    assert set(QUESTIONS) == set(CLARIFY_FIELDS)


@pytest.mark.parametrize(
    "reason", ["unsupported_object", "unsupported_feature", "not_a_creation_request"]
)
def test_unsupported_is_closed(reason: str) -> None:
    r = plan_creation({"outcome": "unsupported", "reason": reason})
    assert isinstance(r, Unsupported) and r.reason == reason and r.message


def test_unsupported_ignores_model_prose() -> None:
    r = plan_creation(
        {"outcome": "unsupported", "reason": "unsupported_object", "message": "hi"}
    )
    assert r == Rejected(code="invalid_model_output")


def test_no_defaults_for_missing_dimensions_or_units() -> None:
    no_thickness = brief_wire(dim(60), dim(40), dim(10), [])
    del no_thickness["design"]["thickness"]
    no_unit = brief_wire({"value": 60}, dim(40), dim(10), [])
    no_holes_key = brief_wire(dim(60), dim(40), dim(10), [])
    del no_holes_key["design"]["holes"]
    no_placement = brief_wire(dim(60), dim(40), dim(10), [{"diameter": dim(8)}])
    for raw in (no_thickness, no_unit, no_holes_key, no_placement):
        assert plan_creation(raw) == Rejected(code="invalid_model_output")


def test_malformed_and_extra_fields_rejected() -> None:
    cases: list[Any] = [
        "not json",
        "",
        "[]",
        {"outcome": "approve"},
        {},
        {"outcome": "clarification", "reason": "missing_dimension", "fields": []},
        {
            "outcome": "clarification",
            "reason": "missing_dimension",
            "fields": ["colour"],
        },
        brief_wire(dim("60"), dim(40), dim(10), []),  # type: ignore[arg-type]
        brief_wire(dim(0), dim(40), dim(10), []),
        brief_wire(dim(-1), dim(40), dim(10), []),
        brief_wire(dim(60, "ft"), dim(40), dim(10), []),
        brief_wire(dim(0.0001), dim(40), dim(10), []),  # rounds to 0 um
        brief_wire(dim(60), dim(40), dim(10), [centered_hole(dim(2))] * 5),
        {"outcome": "brief", "design": {"kind": "sphere"}},
    ]
    for raw in cases:
        assert plan_creation(raw) == Rejected(code="invalid_model_output"), raw
    assert plan_creation({"x": float("nan")}) == Rejected(code="invalid_model_output")
    for key, value in (
        ("feature_id", "abc"),
        ("query", "q"),
        ("microversion", "m"),
        ("approved", True),
        ("payload", {}),
    ):
        top = {**MM, key: value}
        design = {**MM, "design": {**MM["design"], key: value}}
        assert plan_creation(top) == Rejected(code="invalid_model_output")
        assert plan_creation(design) == Rejected(code="invalid_model_output")


def test_compiler_remains_geometry_authority() -> None:
    outside = brief_wire(
        dim(60),
        dim(40),
        dim(10),
        [
            {
                "diameter": dim(8),
                "placement": {"mode": "offset_from_center", "x": dim(28), "y": dim(0)},
            }
        ],
    )
    assert plan_creation(outside) == Rejected(code="hole_outside_plate")
    big = brief_wire(dim(60), dim(40), dim(10), [centered_hole(dim(39))])
    assert plan_creation(big) == Rejected(code="insufficient_wall")
    tiny = brief_wire(dim(60), dim(40), dim(10), [centered_hole(dim(0.5))])
    assert plan_creation(tiny) == Rejected(code="hole_too_small")


def test_ready_result_has_no_provider_data() -> None:
    text = ready(MM).model_dump_json().lower()
    for word in ("onshape", "microversion", "feature_id", "http", "query"):
        assert word not in text


def test_explanations_are_server_owned_and_authority_free() -> None:
    assert set(RATIONALE) == set(get_args(IntentKey)) == set(INTENT_KEYS)
    plan = ready(brief_wire(dim(60), dim(40), dim(10), [centered_hole(dim(8))])).plan
    notes = explain_plan(plan)
    assert [n.step_id for n in notes] == [s.id for s in plan.steps]
    assert [n.intent for n in notes] == [s.intent for s in plan.steps]
    for n in notes:
        assert n.authority == "none"
        assert n.text == RATIONALE[n.intent]
        assert not any(ch.isdigit() for ch in n.text)
        assert n.rationale_key == f"creation.rationale.{n.intent}"
