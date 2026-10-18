"""Server-owned tutor lesson content. The model may explain it, never redefine it.

Mirrors the authored Learn lesson (`apps/web/src/learning/bracket.ts`) by stable
step id; a test fails if the two drift. Completion criteria live only in the
deterministic checker (`step_checks`), never here.
"""

from dataclasses import dataclass

from forge_api.step_checks.bracket import STEPS


@dataclass(frozen=True)
class CatalogStep:
    id: str
    title: str
    objective: str
    why: str
    concepts: tuple[str, ...]
    transfer: bool = False


LESSON_TITLE = "Mounting bracket"
CATALOG: dict[str, CatalogStep] = {
    step.id: step
    for step in (
        CatalogStep(
            "base-sketch",
            "Draw the base profile",
            "Sketch the outline of the bracket's foot.",
            "A sketch describes a 2D outline. Starting from a profile is the simplest "
            "way to describe a part whose cross-section stays the same through its "
            "thickness.",
            ("sketch", "closed profile"),
        ),
        CatalogStep(
            "base-solid",
            "Turn the profile into a solid",
            "Give the profile thickness.",
            "An extrusion fits because this portion keeps the same cross-section "
            "through its thickness. The sketch controls the outline and the extrusion "
            "controls the depth.",
            ("extrude", "solid body", "feature versus body"),
        ),
        CatalogStep(
            "second-portion",
            "Add the bracket's leg",
            "Make the bracket L-shaped.",
            "The leg also keeps one cross-section along its width, so a second "
            "extrusion or one L-shaped profile fits. A plain block cannot mount "
            "against a second surface.",
            ("add versus new", "single L-shaped profile", "second extrusion"),
        ),
        CatalogStep(
            "mounting-holes",
            "Add two mounting holes",
            "Give the bracket two places to attach.",
            "A hole is material removed through a constant depth, so a remove-extrude "
            "or a Hole feature both fit. Holes let the bracket attach to something.",
            ("remove", "through hole"),
        ),
        CatalogStep(
            "review",
            "Review what is and is not known",
            "Separate what Forge verified from what you still need to check.",
            "A model can have the right kinds of features and still be the wrong size. "
            "Separating checked facts from assumptions is part of engineering.",
            ("evidence versus assumption",),
        ),
        CatalogStep(
            "transfer-single-profile",
            "Build the L from one profile",
            "Make an L-shaped solid from one profile and one extrusion.",
            "Choosing between one profile and several extrusions is a design decision. "
            "One profile keeps the whole shape in a single sketch you can edit later, "
            "at the cost of a more complex outline.",
            ("profile", "single extrusion"),
            transfer=True,
        ),
    )
}
# A catalog step without a checker (review) is fine; a step the checker owns must
# exist here so the tutor never reasons about a step it has no content for.
assert set(STEPS) <= set(CATALOG), "tutor catalog is missing a checked step"
