"""Closed evidence for always-rejected filters; never a write validator.

Vocabulary/leaf types: current official OpenAPI, recorded in Phase 16. No runtime
schema fetching, type-prefix matching or raw provider strings in the projection.
"""

from dataclasses import dataclass
from typing import Literal, cast, get_args

from pydantic import Field, JsonValue, field_validator

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
    "query_filter",
    "active_sheet_metal",
    "allow_edge_point",
    "allow_flattened_geometry",
    "allow_mesh_geometry",
    "annotation",
    "center_of_mass",
    "closed_composite_constituent",
    "closed_curve",
    "curved_text",
    "feature",
    "feature_type",
    "flat_sheet_metal",
    "image",
    "in_context_object",
    "mate_connector",
    "mate",
    "modifiable_entity_only",
    "occurrence",
    "plane_orientation",
    "sheet_metal_application_type",
    "sheet_metal_definition_entity_type",
    "section_geometry",
    "sketch_object",
    "sketch_solve_status",
    "spline_control_polygon",
    "spline_handle",
    "spline_internal_point",
    "text_object",
    "text_stroke",
    "unknown",
]
CATEGORIES = cast(tuple[FilterCategory, ...], get_args(FilterCategory))
SignatureToken = FilterCategory | Literal["(", ",", ")"]
LeafField = Literal[
    "entity_type",
    "geometry",
    "body_type",
    "edge_topology",
    "internal_edge",
    "construction",
    "allow_flattened_geometry",
    "active_sheet_metal",
    "sheet_metal_definition_entity_type",
    "sketch_object",
    "sketch_object_type",
    "modifiable_entity_only",
    "allows",
]
LeafState = Literal[
    "all_mesh",
    "any_sketch_object",
    "arc",
    "body",
    "circle",
    "composite",
    "cone",
    "conic",
    "cylinder",
    "degenerate_edge",
    "edge",
    "ellipse",
    "elliptical_arc",
    "extruded",
    "face",
    "false",
    "flattened_only",
    "laminar",
    "line",
    "mate_connector",
    "mesh",
    "missing",
    "mixed_mesh",
    "model_and_flattened",
    "model_only",
    "not_sketch_object",
    "null",
    "one_sided",
    "plane",
    "point",
    "revolved",
    "sheet",
    "solid",
    "sphere",
    "spline",
    "spline_control_polygon",
    "spline_internal_point",
    "torus",
    "true",
    "two_sided",
    "unknown_enum",
    "unknown_value",
    "user_entity",
    "vertex",
    "whole_sketch",
    "wire",
    "wrong_type",
]
MAX_DEPTH = 8
MAX_NODES = 64
MAX_SIGNATURE_CHARS = 4096
# Derived from closed labels, <=64 nodes, <=2 fields per leaf. Includes the
# fixed DEV prefix/counts/flags; tests check both actual and schema maxima.
MAX_FILTER_LOG_CHARS = 16384

KINDS: dict[str, FilterCategory] = {
    "BTEntityTypeFilter-124": "entity_type",
    "BTGeometryFilter-130": "geometry",
    "BTBodyTypeFilter-112": "body_type",
    "BTEdgeTopologyFilter-122": "edge_topology",
    "BTConstructionObjectFilter-113": "construction",
    "BTAndFilter-110": "and",
    "BTOrFilter-167": "or",
    "BTNotFilter-165": "not",
    "BTQueryFilter-183": "query_filter",
    "BTActiveSheetMetalFilter-2944": "active_sheet_metal",
    "BTAllowEdgePointFilter-2371": "allow_edge_point",
    "BTAllowFlattenedGeometryFilter-2140": "allow_flattened_geometry",
    "BTAllowMeshGeometryFilter-1026": "allow_mesh_geometry",
    "BTAnnotationFilter-4841": "annotation",
    "BTCenterOfMassFilter-5569": "center_of_mass",
    "BTClosedCompositeConstituentFilter-2804": "closed_composite_constituent",
    "BTClosedCurveFilter-1206": "closed_curve",
    "BTCurvedTextObjectFilter-5114": "curved_text",
    "BTFeatureFilter-127": "feature",
    "BTFeatureTypeFilter-962": "feature_type",
    "BTFlatSheetMetalFilter-3018": "flat_sheet_metal",
    "BTImageFilter-853": "image",
    "BTInContextObjectFilter-3810": "in_context_object",
    "BTMateConnectorFilter-163": "mate_connector",
    "BTMateFilter-162": "mate",
    "BTModifiableEntityOnlyFilter-1593": "modifiable_entity_only",
    "BTOccurrenceFilter-166": "occurrence",
    "BTPlaneOrientationFilter-1700": "plane_orientation",
    "BTSMApplicationTypeFilter-4430": "sheet_metal_application_type",
    "BTSMDefinitionEntityTypeFilter-1651": "sheet_metal_definition_entity_type",
    "BTSectionGeometryFilter-4161": "section_geometry",
    "BTSketchObjectFilter-184": "sketch_object",
    "BTSketchSolveStatusFilter-3657": "sketch_solve_status",
    "BTSplineControlPolygonFilter-1130": "spline_control_polygon",
    "BTSplineHandleFilter-2971": "spline_handle",
    "BTSplineInternalPointFilter-4101": "spline_internal_point",
    "BTTextObjectFilter-1515": "text_object",
    "BTTextStrokeFilter-461": "text_stroke",
}
CHILDREN: dict[FilterCategory, tuple[str, ...]] = {
    "and": ("operand1", "operand2"),
    "or": ("operand1", "operand2"),
    "not": ("operand",),
}

GBTENTITYTYPE: dict[str, LeafState] = {
    "VERTEX": "vertex",
    "EDGE": "edge",
    "FACE": "face",
    "BODY": "body",
    "DEGENERATE_EDGE": "degenerate_edge",
    "UNKNOWN": "unknown_enum",
}
GBTGEOMETRYTYPE: dict[str, LeafState] = {
    "LINE": "line",
    "CIRCLE": "circle",
    "ARC": "arc",
    "PLANE": "plane",
    "CYLINDER": "cylinder",
    "CONE": "cone",
    "SPHERE": "sphere",
    "TORUS": "torus",
    "SPLINE": "spline",
    "ELLIPSE": "ellipse",
    "MESH": "mesh",
    "CONIC": "conic",
    "REVOLVED": "revolved",
    "EXTRUDED": "extruded",
    "ALL_MESH": "all_mesh",
    "MIXED_MESH": "mixed_mesh",
    "SPLINE_INTERNAL_POINT": "spline_internal_point",
    "SPLINE_CONTROL_POLYGON": "spline_control_polygon",
    "ELLIPTICAL_ARC": "elliptical_arc",
    "UNKNOWN": "unknown_enum",
}
GBTBODYTYPE: dict[str, LeafState] = {
    "SOLID": "solid",
    "SHEET": "sheet",
    "WIRE": "wire",
    "POINT": "point",
    "MATE_CONNECTOR": "mate_connector",
    "COMPOSITE": "composite",
    "UNKNOWN": "unknown_enum",
}
GBTEDGETOPOLOGY: dict[str, LeafState] = {
    "WIRE": "wire",
    "ONE_SIDED": "one_sided",
    "TWO_SIDED": "two_sided",
    "LAMINAR": "laminar",
    "UNKNOWN": "unknown_enum",
}
GBTSKETCHOBJECTTYPE: dict[str, LeafState] = {
    "NOT_SKETCH_OBJECT": "not_sketch_object",
    "ANY_SKETCH_OBJECT": "any_sketch_object",
    "USER_ENTITY": "user_entity",
    "WHOLE_SKETCH": "whole_sketch",
    "UNKNOWN": "unknown_enum",
}
GBTFILTERFLATTENEDGEOMETRYOPTIONS: dict[str, LeafState] = {
    "MODEL_ONLY": "model_only",
    "FLATTENED_ONLY": "flattened_only",
    "MODEL_AND_FLATTENED": "model_and_flattened",
    "UNKNOWN": "unknown_value",
}


@dataclass(frozen=True)
class LeafRule:
    provider_field: str
    field: LeafField
    values: dict[str, LeafState] | None = None


# Only these identity-free enum/Boolean fields are inspected. Other recognized
# families remain opaque category-only leaves, even if their SDK has fields.
LEAF_RULES: dict[FilterCategory, tuple[LeafRule, ...]] = {
    "entity_type": (LeafRule("entityType", "entity_type", GBTENTITYTYPE),),
    "geometry": (LeafRule("geometryType", "geometry", GBTGEOMETRYTYPE),),
    "body_type": (LeafRule("bodyType", "body_type", GBTBODYTYPE),),
    "edge_topology": (
        LeafRule("edgeTopology", "edge_topology", GBTEDGETOPOLOGY),
        LeafRule("isInternalEdge", "internal_edge"),
    ),
    "construction": (LeafRule("isConstruction", "construction"),),
    "allow_flattened_geometry": (
        LeafRule("allowsFlattenedGeometry", "allow_flattened_geometry"),
    ),
    "active_sheet_metal": (LeafRule("isFromActiveSheetMetal", "active_sheet_metal"),),
    "sheet_metal_definition_entity_type": (
        LeafRule(
            "smDefinitionEntityType",
            "sheet_metal_definition_entity_type",
            GBTENTITYTYPE,
        ),
    ),
    "sketch_object": (
        LeafRule("isSketchObject", "sketch_object"),
        LeafRule("objectType", "sketch_object_type", GBTSKETCHOBJECTTYPE),
    ),
    "modifiable_entity_only": (LeafRule("modifiableOnly", "modifiable_entity_only"),),
    # The base schema contributes only btType; this subtype adds only allows.
    "flat_sheet_metal": (
        LeafRule("allows", "allows", GBTFILTERFLATTENEDGEOMETRYOPTIONS),
    ),
}


class LeafFieldState(Closed):
    field: LeafField
    state: LeafState


class LeafEvidence(Closed):
    # Preorder visit number within this filter, never a provider identity.
    visit: int = Field(ge=1, le=MAX_NODES)
    fields: tuple[LeafFieldState, ...] = Field(min_length=1, max_length=2)


class QueryFilterSummary(Closed):
    root: FilterCategory
    root_state: Literal["object", "null", "wrong_type"]
    root_child_count: int = Field(ge=0, le=2)
    max_depth: int = Field(ge=1, le=MAX_DEPTH)
    node_count: int = Field(ge=1, le=MAX_NODES)
    categories: tuple[FilterCategory, ...] = Field(max_length=len(CATEGORIES))
    signature: tuple[SignatureToken, ...] = Field(max_length=3 * MAX_NODES)
    signature_truncated: bool
    leaf_states: tuple[LeafEvidence, ...] = Field(max_length=MAX_NODES)
    malformed: bool
    missing_operand: bool
    unexpected_fields: bool
    uninspected: bool
    truncated: bool

    @field_validator("signature")
    @classmethod
    def bounded_signature(
        cls, value: tuple[SignatureToken, ...]
    ) -> tuple[SignatureToken, ...]:
        if sum(map(len, value)) > MAX_SIGNATURE_CHARS:
            raise ValueError("filter_signature_bound")
        return value


def _category(raw: JsonValue) -> FilterCategory:
    bt = raw.get("btType") if isinstance(raw, dict) else None
    return KINDS.get(bt, "unknown") if isinstance(bt, str) else "unknown"


def _state(node: dict[str, JsonValue], rule: LeafRule) -> LeafFieldState:
    state: LeafState
    if rule.provider_field not in node:
        state = "missing"
    else:
        value = node[rule.provider_field]
        if value is None:
            state = "null"
        elif rule.values is None:
            state = (
                ("true" if value else "false") if type(value) is bool else "wrong_type"
            )
        else:
            state = (
                rule.values.get(value, "unknown_value")
                if isinstance(value, str)
                else "wrong_type"
            )
    return LeafFieldState(field=rule.field, state=state)


def leaf_states_text(summary: QueryFilterSummary) -> str:
    """Serialize only schema-closed labels and bounded local visit numbers."""
    return (
        ";".join(
            f"{leaf.visit}:" + ",".join(f"{p.field}={p.state}" for p in leaf.fields)
            for leaf in summary.leaf_states
        )
        or "none"
    )


def unproven_filter_summary(raw: JsonValue) -> QueryFilterSummary:
    """Not acceptance: every present filter still rejects in the caller.

    Iterative raw visits <=64, depth <=8, fixed SDK operand slots only. Unknown
    payloads are opaque. Only finite enum/Boolean states may leave known leaves.
    Token events never examine provider data or consume another raw-node visit.
    Invalid operator arity or clipping clears the signature, never invents nodes.
    """
    stack: list[tuple[JsonValue, int] | SignatureToken] = [(raw, 1)]
    categories: set[FilterCategory] = set()
    parts: list[SignatureToken] = []
    leaves: list[LeafEvidence] = []
    nodes, depth, root_children = 0, 1, 0
    root: FilterCategory = "unknown"
    malformed = missing = unexpected = uninspected = truncated = False
    invalid_operator = False
    while stack:
        event = stack.pop()
        if isinstance(event, str):
            parts.append(event)
            continue
        if nodes == MAX_NODES:
            truncated = True
            break
        node, level = event
        nodes += 1
        depth = max(depth, level)
        category = _category(node)
        if nodes == 1:
            root = category
        categories.add(category)
        parts.append(category)
        if not isinstance(node, dict) or not isinstance(node.get("btType"), str):
            malformed = True
            continue
        slots = CHILDREN.get(category, ())
        rules = LEAF_RULES.get(category)
        allowed = (
            {"btType", *slots}
            if slots
            else {"btType", *(r.provider_field for r in rules)}
            if rules
            else None
        )
        if allowed is None:
            uninspected = True
        elif len(node) > len(allowed) or any(k not in allowed for k in node):
            # Do not walk unknown keys/values, including extra operand trees.
            unexpected = uninspected = True
            invalid_operator = invalid_operator or bool(slots)
        if rules:
            leaves.append(
                LeafEvidence(visit=nodes, fields=tuple(_state(node, r) for r in rules))
            )
            malformed = malformed or any(
                p.state in ("null", "wrong_type") for p in leaves[-1].fields
            )
        if nodes == 1:
            root_children = sum(k in node for k in slots)
        if slots:
            parts.append("(")
            stack.append(")")
            for index, key in reversed(tuple(enumerate(slots))):
                if key not in node:
                    missing = True
                elif level == MAX_DEPTH:
                    truncated = True
                else:
                    stack.append((node[key], level + 1))
                if index:
                    stack.append(",")
    signature_truncated = (
        truncated
        or missing
        or invalid_operator
        or sum(map(len, parts)) > MAX_SIGNATURE_CHARS
    )
    return QueryFilterSummary(
        root=root,
        root_state="object"
        if isinstance(raw, dict)
        else "null"
        if raw is None
        else "wrong_type",
        root_child_count=root_children,
        max_depth=depth,
        node_count=nodes,
        categories=tuple(c for c in CATEGORIES if c in categories),
        signature=() if signature_truncated else tuple(parts),
        signature_truncated=signature_truncated,
        leaf_states=tuple(leaves),
        malformed=malformed,
        missing_operand=missing,
        unexpected_fields=unexpected,
        uninspected=uninspected,
        truncated=truncated,
    )
