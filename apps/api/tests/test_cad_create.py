import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import forge_api.cad_create.models as models_module
from forge_api.cad_create import (
    BriefError,
    CreationPlan,
    PlateWithHolesBrief,
    compile_brief,
)
from forge_api.cad_create.models import (
    BasePlaneRef,
    BlindExtent,
    CreateSketchCircle,
    CreationStep,
    ExtrudeNew,
)


def brief(**over: Any) -> PlateWithHolesBrief:
    data: dict[str, Any] = {
        "width": {"value": 60, "unit": "mm"},
        "length": {"value": 40, "unit": "mm"},
        "thickness": {"value": 10, "unit": "mm"},
        "holes": [
            {
                "diameter": {"value": 8, "unit": "mm"},
                "center_x": {"value": 0, "unit": "mm"},
                "center_y": {"value": 0, "unit": "mm"},
            }
        ],
    }
    data.update(over)
    return PlateWithHolesBrief.model_validate(data, strict=False)


def hole(d: float, x: float, y: float, unit: str = "mm") -> dict[str, Any]:
    return {
        "diameter": {"value": d, "unit": unit},
        "center_x": {"value": x, "unit": unit},
        "center_y": {"value": y, "unit": unit},
    }


def test_centered_hole_sequence() -> None:
    plan = compile_brief(brief())
    assert [s.op.operation for s in plan.steps] == [
        "CREATE_SKETCH_RECT",
        "EXTRUDE_NEW",
        "CREATE_SKETCH_CIRCLE",
        "EXTRUDE_REMOVE",
    ]
    assert [s.id for s in plan.steps] == ["s01", "s02", "s03", "s04"]
    assert [s.depends_on for s in plan.steps] == [
        (),
        ("s01",),
        ("s02",),
        ("s02", "s03"),
    ]
    assert [s.intent for s in plan.steps] == [
        "define_base_profile",
        "form_base_body",
        "define_cut_profile",
        "remove_material",
    ]


def test_equivalent_input_same_plan_and_digest() -> None:
    a = compile_brief(brief())
    b = compile_brief(
        brief(
            width={"value": 6, "unit": "cm"},
            length={"value": 40000, "unit": "mm"}
            if False
            else {"value": 4, "unit": "cm"},
            thickness={"value": 1, "unit": "cm"},
            holes=[hole(0.8, 0, 0, "cm")],
        )
    )
    assert a == b and a.digest == b.digest
    assert compile_brief(brief()).digest == a.digest


def test_hole_order_is_canonical() -> None:
    h1, h2 = hole(6, -15, 0), hole(6, 15, 0)
    assert compile_brief(brief(holes=[h1, h2])) == compile_brief(brief(holes=[h2, h1]))


def test_no_holes() -> None:
    plan = compile_brief(brief(holes=[]))
    assert [s.op.operation for s in plan.steps] == ["CREATE_SKETCH_RECT", "EXTRUDE_NEW"]


def test_four_holes() -> None:
    hs = [hole(6, x, y) for x in (-20, 20) for y in (-10, 10)]
    plan = compile_brief(brief(holes=hs))
    assert len(plan.steps) == 10
    assert [s.id for s in plan.steps][-1] == "s10"


@pytest.mark.parametrize("field", ["width", "length", "thickness"])
@pytest.mark.parametrize("value", [0, -5, float("nan"), float("inf")])
def test_invalid_dimensions(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        brief(**{field: {"value": value, "unit": "mm"}})


@pytest.mark.parametrize("unit", ["ft", "", "MM", "yd"])
def test_unsupported_units(unit: str) -> None:
    with pytest.raises(ValidationError):
        brief(width={"value": 60, "unit": unit})
    with pytest.raises(ValidationError):
        brief(width={"value": 60})


def test_more_than_four_holes() -> None:
    with pytest.raises(ValidationError):
        brief(holes=[hole(2, i * 5 - 20, 0) for i in range(5)])


def test_hole_outside_bounds() -> None:
    with pytest.raises(BriefError) as e:
        compile_brief(brief(holes=[hole(8, 28, 0)]))
    assert e.value.code == "hole_outside_plate"


def test_insufficient_wall_to_edge() -> None:
    # Hole fits (edge gap 1 mm) but wall is under the 2 mm minimum.
    with pytest.raises(BriefError) as e:
        compile_brief(brief(holes=[hole(8, 0, 15)]))
    assert e.value.code == "insufficient_wall"
    compile_brief(brief(holes=[hole(8, 0, 14)]))  # exactly 2 mm wall is allowed


def test_hole_too_small() -> None:
    with pytest.raises(BriefError) as e:
        compile_brief(brief(holes=[hole(0.5, 0, 0)]))
    assert e.value.code == "hole_too_small"


def test_overlapping_and_thin_web_holes() -> None:
    with pytest.raises(BriefError) as e:
        compile_brief(brief(holes=[hole(8, -3, 0), hole(8, 3, 0)]))
    assert e.value.code == "holes_overlap"
    with pytest.raises(BriefError) as e:
        compile_brief(brief(holes=[hole(8, -4.5, 0), hole(8, 4.5, 0)]))
    assert e.value.code == "insufficient_wall"


def test_malformed_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        brief(color="red")
    with pytest.raises(ValidationError):
        brief(width={"value": 60, "unit": "mm", "extra": 1})
    with pytest.raises(ValidationError):
        PlateWithHolesBrief.model_validate_json(
            '{"width":{"value":"60","unit":"mm"},"length":{"value":4,"unit":"cm"},'
            '"thickness":{"value":1,"unit":"cm"}}'
        )
    with pytest.raises(ValidationError):
        brief(kind="sphere")
    with pytest.raises(ValidationError):
        brief(holes=[{"diameter": {"value": 8, "unit": "mm"}}])


def plan_data() -> dict[str, Any]:
    return compile_brief(brief()).model_dump(mode="json")


def test_plan_round_trips() -> None:
    plan = compile_brief(brief())
    assert (
        CreationPlan.model_validate(plan.model_dump(mode="json"), strict=False) == plan
    )


def test_tampering_breaks_digest() -> None:
    data = plan_data()
    data["steps"][1]["op"]["extent"]["depth_um"] = 11_000
    with pytest.raises(ValidationError):
        CreationPlan.model_validate(data, strict=False)


def test_invalid_dependencies_rejected() -> None:
    from forge_api.cad_create.compile import plan_digest

    def build(steps: list[CreationStep]) -> CreationPlan:
        return CreationPlan(
            capability="demo_cap",
            steps=tuple(steps),
            digest=plan_digest("demo_cap", steps),
        )

    circle = CreationStep(
        id="s01",
        intent="define_base_profile",
        depends_on=(),
        op=CreateSketchCircle(
            target=BasePlaneRef(plane="TOP"),
            center_x_um=0,
            center_y_um=0,
            diameter_um=5_000,
        ),
    )

    def extrude(sid: str, profile: str, deps: tuple[str, ...]) -> CreationStep:
        return CreationStep(
            id=sid,
            intent="form_base_body",
            depends_on=deps,
            op=ExtrudeNew(profile=profile, extent=BlindExtent(depth_um=1_000)),
        )

    build([circle, extrude("s02", "s01", ("s01",))])  # generic, non-plate plan ok
    with pytest.raises(ValidationError):  # forward / missing reference
        build(
            [extrude("s01", "s02", ("s02",)), circle.model_copy(update={"id": "s02"})]
        )
    with pytest.raises(ValidationError):  # undeclared dependency
        build([circle, extrude("s02", "s01", ())])
    with pytest.raises(ValidationError):  # self reference
        build([extrude("s01", "s01", ("s01",))])
    with pytest.raises(ValidationError):  # duplicate id
        build([circle, circle])
    with pytest.raises(ValidationError):  # extrude of a non-sketch
        build(
            [circle, extrude("s02", "s01", ("s01",)), extrude("s03", "s02", ("s02",))]
        )
    with pytest.raises(ValidationError):  # bad step id / empty plan
        CreationStep.model_validate({**circle.model_dump(mode="json"), "id": "x1"})
    with pytest.raises(ValidationError):
        build([])


def test_plan_has_no_provider_data() -> None:
    text = json.dumps(plan_data())

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key.lower() not in {"query", "microversion", "payload", "json"}
                assert not key.endswith(("_id", "Id"))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            assert "http" not in node and "?" not in node and "=" not in node

    walk(json.loads(text))
    for word in ("onshape", "microversion", "feature_id", "deterministic_id"):
        assert word not in text.lower()


def test_core_plan_layer_is_not_plate_specific() -> None:
    source = Path(models_module.__file__).read_text()
    core = source.split("# --- the first constrained capability's brief")[0]
    assert "plate" not in core.lower().replace("plane", "")
    assert "hole" not in core.lower()
    assert "capability" in CreationPlan.model_fields
