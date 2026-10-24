"""Private, pure Ask Forge projection. Graphs and identities never leave here."""

from dataclasses import dataclass

from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.inspector import CadInspector
from forge_api.integrations.onshape.inspector_graph import _inspect_graph
from forge_api.integrations.onshape.models import SectionState, Snapshot
from forge_api.model_graph import GraphQuery
from forge_api.model_graph.graph import FeatureNode

from .models import AiError, Fact
from .presentation import ordinal, quoted

MAX_AI_FEATURES = 20
ORDER_SEMANTICS = (
    "Forge's feature ordering evidence describes returned feature-list order only. "
    "That ordering does not establish dependency, ownership, or parent-child "
    "relationships. Selection references do not establish ownership. Missing "
    "relationships prove nothing about CAD. A terminal feature is known only when "
    "complete feature-list and end-of-list rollback evidence establish one."
)


@dataclass(frozen=True)
class GroundedCad:
    """Request-local minimized evidence, never a public Inspector schema."""

    inspector: CadInspector
    structural_facts: tuple[Fact, ...]


def _name(node: FeatureNode) -> str:
    # Same checked display policy as Inspector, with no secondary rich-data join.
    return quoted(node.label or f"Unnamed feature {node.index}")


def _structural_facts(query: GraphQuery) -> tuple[Fact, ...]:
    visible = query.ordered_features()[:MAX_AI_FEATURES]
    facts = [Fact(id="order_semantics", statement=ORDER_SEMANTICS, status="verified")]
    for before, after in zip(visible, visible[1:], strict=False):
        if query.has_fact("PRECEDES", before.id, after.id):
            facts.append(
                Fact(
                    id=f"order_{before.index}_{after.index}",
                    statement=(
                        f"The {ordinal(before.index)} captured modeled feature, "
                        f"{_name(before)}, "
                        f"appears before the {ordinal(after.index)} captured modeled "
                        f"feature, {_name(after)}, "
                        "in the returned feature order."
                    ),
                    status="verified",
                )
            )
    terminal = query.terminal_feature()
    if terminal is not None and any(node.id == terminal.id for node in visible):
        facts.append(
            Fact(
                id="terminal_feature",
                statement=(
                    "The terminal feature in the complete captured feature list is "
                    f"the {ordinal(terminal.index)} feature, "
                    f"{_name(terminal)}."
                ),
                status="verified",
            )
        )
    return tuple(facts)


def ground(
    snapshot: Snapshot | SectionState,
    expected_context: WorkspaceReference,
    correlation: str,
) -> GroundedCad:
    """Only called after acquisition accepts the read and revalidates its owner."""
    inspector, query = _inspect_graph(snapshot, expected_context, correlation)
    try:
        return GroundedCad(
            inspector, _structural_facts(query) if query is not None else ()
        )
    except ValueError, KeyError:
        # No partial graph facts or legacy structural fallback on correspondence
        # or query validation failure. Never include private exception details.
        raise AiError("evidence_unavailable") from None
