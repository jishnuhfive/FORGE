"""Provider-independent CAD creation kernel (offline).

Engineering brief -> reusable semantic feature plan. Nothing here knows about
Onshape, the network, an AI model or any execution capability: a later,
separately proven provider layer is the only thing that may turn a plan into
provider calls.
"""

from forge_api.cad_create.compile import (
    BriefError,
    compile_brief,
    compile_plate_with_holes,
    plan_digest,
)
from forge_api.cad_create.explain import StepExplanation, explain_plan
from forge_api.cad_create.models import (
    CreationPlan,
    CreationStep,
    Dimension,
    PlateWithHolesBrief,
    ThroughHole,
)
from forge_api.cad_create.planner import (
    NeedsClarification,
    PlanReady,
    Rejected,
    Unsupported,
    plan_creation,
)

__all__ = [
    "BriefError",
    "CreationPlan",
    "NeedsClarification",
    "PlanReady",
    "Rejected",
    "StepExplanation",
    "Unsupported",
    "explain_plan",
    "plan_creation",
    "CreationStep",
    "Dimension",
    "PlateWithHolesBrief",
    "ThroughHole",
    "compile_brief",
    "compile_plate_with_holes",
    "plan_digest",
]
