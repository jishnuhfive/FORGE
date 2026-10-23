"""Small deterministic queries. Absence of an edge is never a negative CAD fact."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .contracts import NodeKind, Relation
from .graph import (
    EntityReferenceNode,
    FeatureNode,
    ForgeModelGraphV1,
    GraphNode,
    SelectionNode,
)


@dataclass(frozen=True)
class GraphQuery:
    graph: ForgeModelGraphV1
    _nodes: Mapping[str, GraphNode] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        checked = ForgeModelGraphV1.model_validate(self.graph)
        object.__setattr__(self, "graph", checked)
        object.__setattr__(
            self, "_nodes", MappingProxyType({node.id: node for node in checked.nodes})
        )

    def get_node(self, identifier: str) -> GraphNode | None:
        return self._nodes.get(identifier)

    def nodes_of_type(self, kind: NodeKind) -> tuple[GraphNode, ...]:
        return tuple(node for node in self.graph.nodes if node.kind == kind)

    def ordered_features(self) -> tuple[FeatureNode, ...]:
        return tuple(node for node in self.graph.nodes if isinstance(node, FeatureNode))

    def terminal_feature(self) -> FeatureNode | None:
        source = next(
            source for source in self.graph.provenance if source.id == "features"
        )
        features = self.ordered_features()
        if source.list_complete is not True or source.rollback_index not in (
            -1,
            len(features),
        ):
            return None
        return features[-1] if features else None

    def selection(self) -> SelectionNode:
        return next(
            node for node in self.graph.nodes if isinstance(node, SelectionNode)
        )

    def selected_nodes(self) -> tuple[EntityReferenceNode, ...]:
        # Clear, missing reference, unknown and unavailable are distinguished by
        # selection().state/reference_state, not by inventing an ownership join.
        return tuple(
            node for node in self.graph.nodes if isinstance(node, EntityReferenceNode)
        )

    def neighbors(
        self, identifier: str, relation: Relation, *, incoming: bool = False
    ) -> tuple[GraphNode, ...]:
        adjacent = {
            edge.source if incoming else edge.target
            for edge in self.graph.edges
            if edge.kind == relation
            and (edge.target if incoming else edge.source) == identifier
        }
        return tuple(node for node in self.graph.nodes if node.id in adjacent)

    def has_fact(self, relation: Relation, source: str, target: str) -> bool:
        """Membership in this evidence graph only; False does not disprove CAD."""
        return any(
            edge.kind == relation and edge.source == source and edge.target == target
            for edge in self.graph.edges
        )
