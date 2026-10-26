"""Selection filter on query parameters, checked against the v17 provider contract.

OpenAPI 1.222.91980 declares BTMParameterQueryList-148.filter as a
BTQueryFilter-183: the entity-picker restriction the UI applies to a parameter
(a sketch plane, an Extrude's entities). The selection a feature evaluates is the
queries list, which Forge still verifies exactly; the filter only limits what a
person may pick, so it is accepted when it is a bounded tree whose every node is
declared by that schema:

* combinators BTAndFilter-110 / BTOrFilter-167 (operand1, operand2) and
  BTNotFilter-165 (operand);
* leaf filters whose ONLY fields are booleans or enums, with exactly their declared
  field names and literal values (UNKNOWN is never accepted).

Subtypes with free strings or vectors (a feature id or type, a plane normal) are not
in the table and are rejected. Unknown types, extra or missing keys, wrong scalar
types, and excess size or depth are rejected.
"""

import re
from typing import Any

_MAX_NODES = 128
_MAX_DEPTH = 12
_BOOL = (True, False)
# Generated from the public OpenAPI schemas above (scalar-only leaves).
_LEAVES: dict[str, dict[str, tuple[Any, ...]]] = {
    "BTActiveSheetMetalFilter-2944": {"isFromActiveSheetMetal": _BOOL},
    "BTAllowEdgePointFilter-2371": {"allowsEdgePoint": _BOOL},
    "BTAllowFlattenedGeometryFilter-2140": {"allowsFlattenedGeometry": _BOOL},
    "BTAllowMeshGeometryFilter-1026": {"allowsMeshGeometry": _BOOL},
    "BTAnnotationFilter-4841": {
        "annotationType": (
            "DATUM",
            "GTOL",
            "DIMENSION_POSITION",
            "DIMENSION",
            "WELD",
            "HOLE_CALLOUT",
            "HOLE_CALLOUT_POSITION",
            "CHAMFER_CALLOUT",
            "CHAMFER_CALLOUT_POSITION",
        )
    },
    "BTBodyTypeFilter-112": {
        "bodyType": ("SOLID", "SHEET", "WIRE", "POINT", "MATE_CONNECTOR", "COMPOSITE")
    },
    "BTCenterOfMassFilter-5569": {},
    "BTClosedCompositeConstituentFilter-2804": {},
    "BTClosedCurveFilter-1206": {"isClosed": _BOOL},
    "BTConstructionObjectFilter-113": {"isConstruction": _BOOL},
    "BTCurvedTextObjectFilter-5114": {"isCurvedText": _BOOL},
    "BTEdgeTopologyFilter-122": {
        "edgeTopology": ("WIRE", "ONE_SIDED", "TWO_SIDED", "LAMINAR"),
        "isInternalEdge": _BOOL,
    },
    "BTEntityTypeFilter-124": {
        "entityType": ("VERTEX", "EDGE", "FACE", "BODY", "DEGENERATE_EDGE")
    },
    "BTFlatSheetMetalFilter-3018": {
        "allows": ("MODEL_ONLY", "FLATTENED_ONLY", "MODEL_AND_FLATTENED")
    },
    "BTGeometryFilter-130": {
        "geometryType": (
            "LINE",
            "CIRCLE",
            "ARC",
            "PLANE",
            "CYLINDER",
            "CONE",
            "SPHERE",
            "TORUS",
            "SPLINE",
            "ELLIPSE",
            "MESH",
            "CONIC",
            "REVOLVED",
            "EXTRUDED",
            "ALL_MESH",
            "MIXED_MESH",
            "SPLINE_INTERNAL_POINT",
            "SPLINE_CONTROL_POLYGON",
            "ELLIPTICAL_ARC",
        )
    },
    "BTImageFilter-853": {"isImage": _BOOL},
    "BTInContextObjectFilter-3810": {"isInContext": _BOOL},
    "BTMateConnectorFilter-163": {
        "allowImplicitMateConnector": _BOOL,
        "isMateConnectorInferenceEnabledByDefault": _BOOL,
        "requiresOccurrence": _BOOL,
    },
    "BTMateFilter-162": {"requireMateQueryData": _BOOL, "topLevelMateOnly": _BOOL},
    "BTModifiableEntityOnlyFilter-1593": {"modifiableOnly": _BOOL},
    "BTOccurrenceFilter-166": {
        "excludeFlattenedParts": _BOOL,
        "excludeMirroredOrDeriveMirroredInstance": _BOOL,
        "excludeParametricPartStudioChildInstance": _BOOL,
        "excludeParametricPartStudioInstance": _BOOL,
        "excludePatternInstances": _BOOL,
        "excludeReplicatedInstances": _BOOL,
        "excludeSketch": _BOOL,
        "excludeStandardContent": _BOOL,
        "excludeStudioInserts": _BOOL,
        "excludeSubAssemblies": _BOOL,
        "excludeSuppressed": _BOOL,
        "includeAssemblyRoot": _BOOL,
        "includeParametricInstance": _BOOL,
        "includePatternOccurrence": _BOOL,
        "solidOrCompositeBodyOnly": _BOOL,
        "topLevelOnly": _BOOL,
    },
    "BTSMApplicationTypeFilter-4430": {
        "smApplicationType": ("SHEET_METAL", "FLEXIBLE_PCB", "NONE")
    },
    "BTSMDefinitionEntityTypeFilter-1651": {
        "smDefinitionEntityType": ("VERTEX", "EDGE", "FACE", "BODY", "DEGENERATE_EDGE")
    },
    "BTSectionGeometryFilter-4161": {"isSectionGeometry": _BOOL},
    "BTSketchObjectFilter-184": {
        "isSketchObject": _BOOL,
        "objectType": (
            "NOT_SKETCH_OBJECT",
            "ANY_SKETCH_OBJECT",
            "USER_ENTITY",
            "WHOLE_SKETCH",
        ),
    },
    "BTSketchSolveStatusFilter-3657": {
        "solveStatus": (
            "UNDER_DEFINED",
            "WELL_DEFINED",
            "FIXED",
            "OVER_DEFINED",
            "NOT_CONSISTENT",
        )
    },
    "BTSplineControlPolygonFilter-1130": {"allowsSplineControlPolygon": _BOOL},
    "BTSplineHandleFilter-2971": {"allowsSplineHandle": _BOOL},
    "BTSplineInternalPointFilter-4101": {"allowsSplineInternalPoint": _BOOL},
    "BTTextObjectFilter-1515": {"isText": _BOOL},
    "BTTextStrokeFilter-461": {"isStroke": _BOOL},
}

_BINARY = ("BTAndFilter-110", "BTOrFilter-167")
_NOT = "BTNotFilter-165"


def _same(value: Any, allowed: tuple[Any, ...]) -> bool:
    # bool must never accept 0/1, and strings must be exact members.
    return any(type(value) is type(a) and value == a for a in allowed)


def valid_selection_filter(raw: Any) -> bool:
    stack: list[tuple[Any, int]] = [(raw, 1)]
    visits = 0
    while stack:
        node, level = stack.pop()
        visits += 1
        if visits > _MAX_NODES or level > _MAX_DEPTH or not isinstance(node, dict):
            return False
        bt_type = node.get("btType")
        if type(bt_type) is not str:
            return False
        if bt_type in _BINARY:
            if node.keys() != {"btType", "operand1", "operand2"}:
                return False
            stack.append((node["operand2"], level + 1))
            stack.append((node["operand1"], level + 1))
        elif bt_type == _NOT:
            if node.keys() != {"btType", "operand"}:
                return False
            stack.append((node["operand"], level + 1))
        else:
            fields = _LEAVES.get(bt_type)
            if fields is None or node.keys() != {"btType", *fields}:
                return False
            if not all(_same(node[k], allowed) for k, allowed in fields.items()):
                return False
    return True


_TYPE = re.compile(r"BT[A-Za-z]{1,60}-[0-9]{1,5}")
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]{0,39}")
_ENUM = re.compile(r"[A-Z][A-Z_]{0,39}")


def structure(raw: Any) -> str:
    """Single-line review label: type names, field names, booleans and enum words only.

    Works on any value (including a rejected filter) and never prints other strings,
    numbers or identities; bounded in size and depth.
    """
    budget = [96]

    def walk(node: Any, depth: int) -> str:
        budget[0] -= 1
        if budget[0] < 0 or depth > _MAX_DEPTH:
            return "..."
        if isinstance(node, bool):
            return "true" if node else "false"
        if isinstance(node, str):
            return node if _ENUM.fullmatch(node) else "<str>"
        if isinstance(node, dict):
            kind = node.get("btType")
            head = kind if isinstance(kind, str) and _TYPE.fullmatch(kind) else "<type>"
            rest = []
            for key in sorted(k for k in node if k != "btType"):
                name = key if _NAME.fullmatch(key) else "<key>"
                rest.append(f"{name}={walk(node[key], depth + 1)}")
            return f"{head}{{{','.join(rest)}}}"
        if isinstance(node, list):
            return "[" + ",".join(walk(x, depth + 1) for x in node[:8]) + "]"
        return "<value>"

    return walk(raw, 1)[:700]
