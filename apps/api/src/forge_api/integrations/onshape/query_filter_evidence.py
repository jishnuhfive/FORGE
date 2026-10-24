"""Bounded structure-only evidence for rejected filters; no acceptance contract."""

from typing import Literal

from pydantic import Field, JsonValue

from forge_api.cad_edits.domain import Closed

FilterCategory = Literal[
    "entity_type",
    "geometry",
    "body_type",
    "edge_topology",
    "construction",
    "and",
    "or",
    "not",
    "other_known",
    "unknown",
]
CATEGORIES: tuple[FilterCategory, ...] = (
    "entity_type",
    "geometry",
    "body_type",
    "edge_topology",
    "construction",
    "and",
    "or",
    "not",
    "other_known",
    "unknown",
)
MAX_DEPTH = 8
MAX_NODES = 64

# Exact current /api/openapi discriminator vocabulary, never a prefix match or
# a write allowlist. No payload field values (including enum values) are read.
KINDS: dict[str, FilterCategory] = {
    "BTEntityTypeFilter-124": "entity_type",
    "BTGeometryFilter-130": "geometry",
    "BTBodyTypeFilter-112": "body_type",
    "BTEdgeTopologyFilter-122": "edge_topology",
    "BTConstructionObjectFilter-113": "construction",
    "BTAndFilter-110": "and",
    "BTOrFilter-167": "or",
    "BTNotFilter-165": "not",
    **dict.fromkeys(
        (
            "BTQueryFilter-183",
            "BTActiveSheetMetalFilter-2944",
            "BTAllowEdgePointFilter-2371",
            "BTAllowFlattenedGeometryFilter-2140",
            "BTAllowMeshGeometryFilter-1026",
            "BTAnnotationFilter-4841",
            "BTCenterOfMassFilter-5569",
            "BTClosedCompositeConstituentFilter-2804",
            "BTClosedCurveFilter-1206",
            "BTCurvedTextObjectFilter-5114",
            "BTFeatureFilter-127",
            "BTFeatureTypeFilter-962",
            "BTFlatSheetMetalFilter-3018",
            "BTImageFilter-853",
            "BTInContextObjectFilter-3810",
            "BTMateConnectorFilter-163",
            "BTMateFilter-162",
            "BTModifiableEntityOnlyFilter-1593",
            "BTOccurrenceFilter-166",
            "BTPlaneOrientationFilter-1700",
            "BTSMApplicationTypeFilter-4430",
            "BTSMDefinitionEntityTypeFilter-1651",
            "BTSectionGeometryFilter-4161",
            "BTSketchObjectFilter-184",
            "BTSketchSolveStatusFilter-3657",
            "BTSplineControlPolygonFilter-1130",
            "BTSplineHandleFilter-2971",
            "BTSplineInternalPointFilter-4101",
            "BTTextObjectFilter-1515",
            "BTTextStrokeFilter-461",
        ),
        "other_known",
    ),
}
CHILDREN = {
    "and": ("operand1", "operand2"),
    "or": ("operand1", "operand2"),
    "not": ("operand",),
}
LEAF_FIELDS = {
    "entity_type": frozenset({"btType", "entityType"}),
    "geometry": frozenset({"btType", "geometryType"}),
    "body_type": frozenset({"btType", "bodyType"}),
    "edge_topology": frozenset({"btType", "edgeTopology", "isInternalEdge"}),
    "construction": frozenset({"btType", "isConstruction"}),
}


class QueryFilterSummary(Closed):
    root: FilterCategory
    root_state: Literal["object", "null", "wrong_type"]
    root_child_count: int = Field(ge=0, le=2)
    max_depth: int = Field(ge=1, le=MAX_DEPTH)
    node_count: int = Field(ge=1, le=MAX_NODES)
    categories: tuple[FilterCategory, ...] = Field(max_length=10)
    malformed: bool
    missing_operand: bool
    unexpected_fields: bool
    uninspected: bool
    truncated: bool


def _category(raw: JsonValue) -> FilterCategory:
    bt = raw.get("btType") if isinstance(raw, dict) else None
    return KINDS.get(bt, "unknown") if isinstance(bt, str) else "unknown"


def unproven_filter_summary(raw: JsonValue) -> QueryFilterSummary:
    """Not validation: every present filter still rejects in the calling predicate.

    Only fixed binary/unary SDK operand slots are traversed. Unknown/other-known
    payloads, arrays and leaf values are opaque; no raw data enters the result.
    Iteration is bounded even for deep, wide or cyclic synthetic Python objects.
    """
    stack = [(raw, 1)]
    categories: set[FilterCategory] = set()
    nodes, depth, root_children = 0, 1, 0
    malformed = missing = unexpected = uninspected = truncated = False
    while stack and nodes < MAX_NODES:
        node, level = stack.pop()
        nodes += 1
        depth = max(depth, level)
        category = _category(node)
        categories.add(category)
        if not isinstance(node, dict) or not isinstance(node.get("btType"), str):
            malformed = True
            continue
        slots = CHILDREN.get(category, ())
        allowed = frozenset({"btType", *slots}) if slots else LEAF_FIELDS.get(category)
        if allowed is None:
            # Recognition of another SDK family says nothing about its payload.
            uninspected = True
        elif len(node) > len(allowed) or any(k not in allowed for k in node):
            unexpected = True
        if nodes == 1:
            root_children = sum(k in node for k in slots)
        for key in reversed(slots):
            if key not in node:
                missing = True
            elif level == MAX_DEPTH:
                truncated = True
            else:
                stack.append((node[key], level + 1))
    truncated = truncated or bool(stack)
    return QueryFilterSummary(
        root=_category(raw),
        root_state="object"
        if isinstance(raw, dict)
        else "null"
        if raw is None
        else "wrong_type",
        root_child_count=root_children,
        max_depth=depth,
        node_count=nodes,
        categories=tuple(c for c in CATEGORIES if c in categories),
        malformed=malformed,
        missing_operand=missing,
        unexpected_fields=unexpected,
        uninspected=uninspected,
        truncated=truncated,
    )
