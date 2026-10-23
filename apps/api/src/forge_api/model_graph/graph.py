"""Versioned graph contract and semantic integrity checks, independent of I/O."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .contracts import (
    MAX_EDGES,
    MAX_NODES,
    MAX_SERIALIZED_BYTES,
    NODE_ORDER,
    SOURCE_ORDER,
    Availability,
    BodyRecord,
    CaptureIdentity,
    Closed,
    DisplayText,
    EdgeId,
    EntityType,
    FeatureRecord,
    NodeId,
    NodeKind,
    PartRecord,
    Provenance,
    ProviderId,
    Relation,
    SelectionObservation,
    SelectionReference,
    SourceId,
    canonical,
    edge_id,
    node_id,
    selection_provenance,
)


class Node(Closed):
    id: NodeId
    label: DisplayText | None = None
    availability: Availability
    provenance: SourceId


class WorkspaceNode(Node):
    kind: Literal["workspace"] = "workspace"
    provider_id: ProviderId
    label: None = None
    availability: Literal["unknown"] = "unknown"
    provenance: Literal["context"] = "context"


class PartStudioNode(Node):
    kind: Literal["part_studio"] = "part_studio"
    provider_id: ProviderId
    label: None = None
    availability: Literal["unknown"] = "unknown"
    provenance: Literal["context"] = "context"


class FeatureNode(FeatureRecord, Node):
    kind: Literal["feature"] = "feature"
    index: Annotated[int, Field(ge=1, le=2000)]
    availability: Literal["available"] = "available"
    provenance: Literal["features"] = "features"


class PartNode(PartRecord, Node):
    kind: Literal["part"] = "part"
    availability: Literal["available"] = "available"
    provenance: Literal["parts"] = "parts"


class BodyNode(BodyRecord, Node):
    kind: Literal["body"] = "body"
    label: None = None
    availability: Literal["available"] = "available"
    provenance: Literal["bodies"] = "bodies"


class SelectionNode(Node):
    kind: Literal["selection"] = "selection"
    provider_id: None = None
    label: None = None
    provenance: Literal["selection"] = "selection"
    state: Literal["selected", "clear", "unknown", "unavailable"]
    entity_type: EntityType | None = None
    reference_state: Literal["available", "unknown", "unavailable"]


class EntityReferenceNode(Node):
    """An observed opaque reference, not an acquired/owned face or edge."""

    kind: Literal["entity_reference"] = "entity_reference"
    provider_id: SelectionReference
    label: None = None
    availability: Literal["available"] = "available"
    provenance: Literal["selection"] = "selection"
    entity_type: EntityType


GraphNode = Annotated[
    WorkspaceNode
    | PartStudioNode
    | FeatureNode
    | PartNode
    | BodyNode
    | SelectionNode
    | EntityReferenceNode,
    Field(discriminator="kind"),
]


class Edge(Closed):
    availability: Literal["available", "unknown"] = "available"
    id: EdgeId
    kind: Relation
    source: NodeId
    target: NodeId
    provenance: SourceId


def node_order(node: GraphNode) -> tuple[int, int, str]:
    return (
        NODE_ORDER.index(node.kind),
        node.index if isinstance(node, FeatureNode) else 0,
        node.provider_id or "",
    )


def edge_order(edge: Edge) -> tuple[str, str, str]:
    return edge.kind, edge.source, edge.target


def structural_edges(nodes: tuple[GraphNode, ...]) -> tuple[Edge, ...]:
    workspace = next(n for n in nodes if isinstance(n, WorkspaceNode))
    studio = next(n for n in nodes if isinstance(n, PartStudioNode))
    selection = next(n for n in nodes if isinstance(n, SelectionNode))
    edges: list[Edge] = []

    def add(
        kind: Relation, source: GraphNode, target: GraphNode, provenance: SourceId
    ) -> None:
        edges.append(
            Edge(
                id=edge_id(kind, source.id, target.id),
                kind=kind,
                source=source.id,
                target=target.id,
                provenance=provenance,
                availability="unknown" if provenance == "context" else "available",
            )
        )

    add("CONTAINS", workspace, studio, "context")
    features = []
    for node in nodes:
        if isinstance(node, FeatureNode | PartNode | BodyNode):
            add("CONTAINS", studio, node, node.provenance)
        if isinstance(node, FeatureNode):
            features.append(node)
        if isinstance(node, EntityReferenceNode):
            add("REFERENCES", selection, node, "selection")
    for before, after in zip(features, features[1:], strict=False):
        # Relative returned order only; never an immediate dependency/creation edge.
        add("PRECEDES", before, after, "features")
    return tuple(sorted(edges, key=edge_order))


class ForgeModelGraphV1(Closed):
    schema_version: Literal["forge-model-graph-v1"] = "forge-model-graph-v1"
    capture: CaptureIdentity
    provenance: Annotated[tuple[Provenance, ...], Field(min_length=5, max_length=5)]
    nodes: Annotated[tuple[GraphNode, ...], Field(min_length=3, max_length=MAX_NODES)]
    edges: Annotated[tuple[Edge, ...], Field(min_length=1, max_length=MAX_EDGES)]

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if tuple(source.id for source in self.provenance) != SOURCE_ORDER:
            raise ValueError("invalid provenance ordering or coverage")
        sources = {source.id: source for source in self.provenance}
        if any(source.capture != self.capture for source in self.provenance):
            raise ValueError("mixed graph context or capture")
        if any(
            source.status in ("unauthorized", "forbidden") for source in self.provenance
        ):
            raise ValueError("unauthorized graph evidence")
        markers = {
            marker for source in self.provenance for marker in source.microversions
        }
        if len(markers) > 1:
            raise ValueError("mixed graph revisions")
        if self.nodes != tuple(sorted(self.nodes, key=node_order)):
            raise ValueError("noncanonical node ordering")
        identities = [node.id for node in self.nodes]
        identity_set = set(identities)
        if len(identity_set) != len(identities):
            raise ValueError("duplicate graph identity")
        provider_keys = [
            (node.kind, node.provider_id)
            for node in self.nodes
            if node.provider_id is not None
        ]
        if len(set(provider_keys)) != len(provider_keys):
            raise ValueError("duplicate provider identity")
        for kind in ("workspace", "part_studio", "selection"):
            if sum(node.kind == kind for node in self.nodes) != 1:
                raise ValueError("invalid structural node coverage")
        for node in self.nodes:
            if node.id != node_id(
                self.capture,
                node.kind,
                node.provider_id,
                entity_type=node.entity_type
                if isinstance(node, EntityReferenceNode)
                else None,
            ):
                raise ValueError("invalid context-bound node identity")
            if (
                isinstance(node, WorkspaceNode)
                and node.provider_id != self.capture.context.workspaceId
            ):
                raise ValueError("conflicting workspace identity")
            if (
                isinstance(node, PartStudioNode)
                and node.provider_id != self.capture.context.elementId
            ):
                raise ValueError("conflicting Part Studio identity")
        collections: tuple[tuple[SourceId, NodeKind], ...] = (
            ("features", "feature"),
            ("parts", "part"),
            ("bodies", "body"),
        )
        for name, kind in collections:
            count = sum(node.kind == kind for node in self.nodes)
            if count != (sources[name].returned_count or 0):
                raise ValueError("graph collection coverage mismatch")
        features = [node for node in self.nodes if isinstance(node, FeatureNode)]
        if [node.index for node in features] != list(range(1, len(features) + 1)):
            raise ValueError("invalid feature ordering")
        parts = [node for node in self.nodes if isinstance(node, PartNode)]
        if {
            part.microversion for part in parts if part.microversion is not None
        } != set(sources["parts"].microversions):
            raise ValueError("inconsistent part revisions")
        selection = next(n for n in self.nodes if isinstance(n, SelectionNode))
        entities = [n for n in self.nodes if isinstance(n, EntityReferenceNode)]
        if len(entities) > 1 or (
            entities
            and (
                selection.state != "selected"
                or entities[0].entity_type != selection.entity_type
            )
        ):
            raise ValueError("invalid selection reference")
        reference = entities[0].provider_id if entities else None
        observation = SelectionObservation(
            capture=self.capture,
            mode="unobserved_selection"
            if sources["selection"].mode == "unobserved_selection"
            else "browser_observation",
            state=selection.state,
            entity_type=selection.entity_type,
            reference=reference,
        )
        if selection_provenance(observation) != sources["selection"]:
            raise ValueError("selection provenance mismatch")
        expected_availability = (
            "available" if selection.state in ("selected", "clear") else selection.state
        )
        expected_reference = (
            "available"
            if entities
            else "unavailable"
            if selection.state in ("clear", "unavailable")
            else "unknown"
        )
        if (
            selection.availability != expected_availability
            or selection.reference_state != expected_reference
        ):
            raise ValueError("selection availability mismatch")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids) or any(
            edge.source not in identity_set or edge.target not in identity_set
            for edge in self.edges
        ):
            raise ValueError("duplicate or dangling graph edge")
        if self.edges != structural_edges(self.nodes):
            raise ValueError("unsupported, missing or noncanonical graph relationship")
        if len(canonical(self.model_dump(mode="json"))) > MAX_SERIALIZED_BYTES:
            raise ValueError("graph serialization limit exceeded")
        return self

    def to_bytes(self) -> bytes:
        """Private deterministic JSON, not a browser/AI authorization boundary."""
        checked = type(self).model_validate(self)
        return canonical(checked.model_dump(mode="json"))
