"""Pure, bounded construction of what the tutor model is told.

Trusted: authored lesson content (catalog) and deterministic check findings that
arrived through a verified evidence token. Untrusted: everything the browser says
about itself (`learner`), which is a closed set of enums that may only tune tone.
"""

import json

from forge_api.step_checks.bracket import STEPS

from .catalog import LESSON_TITLES, CatalogStep
from .evidence_token import VerifiedCheck
from .models import HelpStyle, LearnerHints


def help_style(step: CatalogStep, learner: LearnerHints) -> HelpStyle:
    """Deterministic and explainable; never a score or a mastery inference."""
    if step.transfer:
        # The challenge tests independence: stay conceptual until the learner has
        # deliberately opened the tool-specific hint themselves.
        return "conceptual" if learner.hints_revealed < 2 else "guided"
    if learner.guidance == "reduced":
        return "concise"
    return "conceptual" if learner.hints_revealed == 0 else "guided"


def build_context(
    *,
    step: CatalogStep,
    learner: LearnerHints,
    check: VerifiedCheck | None,
    can_inspect: bool,
) -> dict[str, object]:
    labels = {r.id: r.description for r in STEPS.get(step.id, ())}
    latest: dict[str, object] | None = None
    if check is not None:
        latest = {
            "outcome": check.outcome,
            "captured_at": check.captured_at,
            "note": "Reflects the model when the check ran; it may predate edits.",
            "findings": [
                {
                    "id": item.id,
                    "requirement": labels[item.id],
                    "blocking": item.blocking,
                    "status": item.status,
                    "reason": item.reason,
                    "observed": item.statement,
                }
                for item in check.findings
            ],
        }
    investigation: dict[str, object] | None = None
    if learner.investigation is not None:
        investigation = {
            # Whether the learner answered, never what they answered.
            "stage": learner.investigation.stage,
            "prediction_answered": learner.investigation.prediction_answered,
            "rechecked": learner.investigation.rechecked,
            "resolved_after_recheck": learner.investigation.resolved,
        }
    return {
        "lesson": {
            "title": LESSON_TITLES[step.lesson],
            "reference_dimensions": step.lesson == "mounting-plate",
            "is_transfer_challenge": step.transfer,
            "step": {
                "id": step.id,
                "title": step.title,
                "objective": step.objective,
                "why": step.why,
                "concepts": list(step.concepts),
            },
        },
        "learner_reported_hints_only": {
            "experience": learner.experience,
            "goal": learner.goal,
            "hints_revealed": learner.hints_revealed,
            "guidance": learner.guidance,
            "investigation": investigation,
        },
        "help_style": help_style(step, learner),
        "latest_check": latest,
        "current_cad": "inspectable_on_request" if can_inspect else "not_available",
    }


def context_message(context: dict[str, object]) -> str:
    return (
        "TRUSTED APPLICATION CONTEXT (authored lesson content and deterministic check "
        "results built by the server; learner_reported_hints_only are unverified):\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
