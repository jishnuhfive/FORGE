"""Pure graph construction; no transport, clock, cache, persistence or model calls."""

from .contracts import GraphEvidence, Provenance, node_id, selection_provenance
from .graph import (
    BodyNode,
    EntityReferenceNode,
    FeatureNode,
    ForgeModelGraphV1,
    GraphNode,
    PartNode,
    PartStudioNode,
    SelectionNode,
    WorkspaceNode,
    node_order,
    structural_edges,
)


def build_graph(evidence: GraphEvidence) -> ForgeModelGraphV1:
    # Revalidate even model_construct/model_copy inputs and nested frozen instances.
    evidence = GraphEvidence.model_validate(evidence)
    capture = evidence.capture
    workspace = WorkspaceNode(
        id=node_id(capture, "workspace", capture.context.workspaceId),
        provider_id=capture.context.workspaceId,
    )
    studio = PartStudioNode(
        id=node_id(capture, "part_studio", capture.context.elementId),
        provider_id=capture.context.elementId,
    )
    nodes: list[GraphNode] = [workspace, studio]
    for index, feature in enumerate(evidence.features.items, 1):
        nodes.append(
            FeatureNode(
                id=node_id(capture, "feature", feature.provider_id),
                index=index,
                **feature.model_dump(),
            )
        )
    for part in evidence.parts.items:
        nodes.append(
            PartNode(id=node_id(capture, "part", part.provider_id), **part.model_dump())
        )
    for body in evidence.bodies.items:
        nodes.append(
            BodyNode(id=node_id(capture, "body", body.provider_id), **body.model_dump())
        )
    observation = evidence.selection
    # GraphEvidence has already rejected stale observations.
    if observation.state == "stale":
        raise ValueError("stale selection")
    nodes.append(
        SelectionNode(
            id=node_id(capture, "selection"),
            state=observation.state,
            entity_type=observation.entity_type,
            availability="unknown"
            if observation.state == "unknown"
            else "unavailable"
            if observation.state == "unavailable"
            else "available",
            reference_state="available"
            if observation.reference is not None
            else "unavailable"
            if observation.state in ("clear", "unavailable")
            else "unknown",
        )
    )
    if observation.reference is not None:
        assert observation.entity_type is not None
        nodes.append(
            EntityReferenceNode(
                id=node_id(
                    capture,
                    "entity_reference",
                    observation.reference,
                    entity_type=observation.entity_type,
                ),
                provider_id=observation.reference,
                entity_type=observation.entity_type,
            )
        )
    ordered = tuple(sorted(nodes, key=node_order))
    return ForgeModelGraphV1(
        capture=capture,
        provenance=(
            Provenance(
                id="context", capture=capture, mode="request_scope", state="complete"
            ),
            evidence.features.source,
            evidence.parts.source,
            evidence.bodies.source,
            selection_provenance(observation),
        ),
        nodes=ordered,
        edges=structural_edges(ordered),
    )
