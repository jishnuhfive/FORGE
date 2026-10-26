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
    lesson: str = "mounting-bracket"


LESSON_TITLE = "Mounting bracket"
LESSON_TITLES = {
    "mounting-bracket": LESSON_TITLE,
    "mounting-plate": "Mounting plate",
}
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

# Mirrors apps/web/src/learning/plate.ts by stable step id (a test fails on drift).
# None of these steps has a deterministic checker: nothing here can be "verified".
# Dimensions are authored reference values for the lesson's example plate, never
# measurements of the learner's model.
_PLATE = "mounting-plate"
PLATE_STEPS: tuple[CatalogStep, ...] = (
    CatalogStep(
        "plate-sketch",
        "Sketch the plate outline",
        "Draw the flat outline the plate is built from.",
        "A sketch is a flat 2D drawing. A closed outline (a profile) says what shape "
        "the part has seen from above. It has no thickness yet.",
        ("sketch", "closed profile"),
        lesson=_PLATE,
    ),
    CatalogStep(
        "plate-extrude",
        "Extrude the outline into a plate",
        "Give the outline thickness so it becomes a solid.",
        "Extrude pushes a closed profile along one direction. The sketch decides the "
        "outline; the Extrude decides how thick the solid is.",
        ("extrude", "solid body", "depth versus outline"),
        lesson=_PLATE,
    ),
    CatalogStep(
        "plate-hole-sketch",
        "Sketch where the holes go",
        "Mark the hole positions and size on the plate.",
        "A second sketch on the plate's face records where the holes go and how big "
        "they are. Sketching alone removes no material.",
        ("sketch on a face", "hole position"),
        lesson=_PLATE,
    ),
    CatalogStep(
        "plate-remove",
        "Cut the holes with Extrude Remove",
        "Remove material through the plate using the circles.",
        "A hole is missing material. Remove cuts the sketch shape out of the existing "
        "solid, while Add or New would build material instead.",
        ("remove", "through all", "add versus remove"),
        lesson=_PLATE,
    ),
    CatalogStep(
        "plate-fillet",
        "Round the top edges with a Fillet",
        "Soften the sharp outer top edges.",
        "A fillet rounds an edge. It is the last feature, so suppressing it (turning "
        "it off without deleting it) brings back the sharp edges without changing "
        "the plate or its holes.",
        ("fillet", "suppress", "feature order"),
        lesson=_PLATE,
    ),
    CatalogStep(
        "plate-review",
        "Read the feature tree as a story",
        "See how the five operations build on one another.",
        "Each feature uses what came before: a sketch feeds an Extrude and later "
        "features refine the shape. Knowing the order shows which feature to edit; "
        "thickness is the first Extrude's depth.",
        ("feature order", "which feature controls what"),
        lesson=_PLATE,
    ),
)
CATALOG.update({step.id: step for step in PLATE_STEPS})
# A catalog step without a checker (review) is fine; a step the checker owns must
# exist here so the tutor never reasons about a step it has no content for.
assert set(STEPS) <= set(CATALOG), "tutor catalog is missing a checked step"
