"""Learn-facing explanations of plan steps.

Derived only from a step's closed ``intent`` key via server-owned text. Contains
no model output and no CAD facts (no numbers, names or ids), and carries no
authority: it cannot approve, edit or execute anything.
"""

from typing import Literal, get_args

from forge_api.ai.models import StrictModel
from forge_api.cad_create.models import CreationPlan, IntentKey

RATIONALE: dict[str, str] = {
    "define_base_profile": "Sketch the outline that gives the part its basic shape.",
    "form_base_body": "Extrude the outline into a solid so there is material to cut.",
    "define_cut_profile": "Sketch the shape of material to remove on an existing face.",
    "remove_material": "Cut the sketched shape out of the solid.",
}
INTENT_KEYS: tuple[str, ...] = get_args(IntentKey)


class StepExplanation(StrictModel):
    step_id: str
    intent: IntentKey
    rationale_key: str
    text: str
    authority: Literal["none"] = "none"


def explain_plan(plan: CreationPlan) -> tuple[StepExplanation, ...]:
    return tuple(
        StepExplanation(
            step_id=s.id,
            intent=s.intent,
            rationale_key=f"creation.rationale.{s.intent}",
            text=RATIONALE[s.intent],
        )
        for s in plan.steps
    )
