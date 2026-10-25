"""Exact role contracts from complete human writes-OFF Phase 16 evidence.

These private immutable shapes are acceptance authority, not diagnostic tokens.
No known-node allowlist, tree rewriting, Boolean equivalence or default inference.
Feature category and parameter identity remain mandatory, even for equal trees.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from pydantic import JsonValue

LeafType = Literal[
    "BTFlatSheetMetalFilter-3018",
    "BTSketchObjectFilter-184",
    "BTEntityTypeFilter-124",
    "BTGeometryFilter-130",
    "BTConstructionObjectFilter-113",
    "BTActiveSheetMetalFilter-2944",
    "BTEdgeTopologyFilter-122",
    "BTSMDefinitionEntityTypeFilter-1651",
    "BTModifiableEntityOnlyFilter-1593",
    "BTBodyTypeFilter-112",
    "BTAllowMeshGeometryFilter-1026",
    "BTMateConnectorFilter-163",
]
LeafField = Literal[
    "allows",
    "isSketchObject",
    "objectType",
    "entityType",
    "geometryType",
    "isConstruction",
    "isFromActiveSheetMetal",
    "edgeTopology",
    "isInternalEdge",
    "smDefinitionEntityType",
    "modifiableOnly",
    "bodyType",
    "allowsMeshGeometry",
    "allowImplicitMateConnector",
    "isMateConnectorInferenceEnabledByDefault",
    "requiresOccurrence",
]
LeafValue = Literal[
    True,
    False,
    "MODEL_AND_FLATTENED",
    "MODEL_ONLY",
    "ANY_SKETCH_OBJECT",
    "NOT_SKETCH_OBJECT",
    "FACE",
    "EDGE",
    "VERTEX",
    "PLANE",
    "TWO_SIDED",
    "BODY",
    "SOLID",
    "SHEET",
    "MATE_CONNECTOR",
    "LINE",
    "CIRCLE",
    "ARC",
    "CYLINDER",
    "CONE",
    "REVOLVED",
]


@dataclass(frozen=True)
class _Leaf:
    bt_type: LeafType
    fields: tuple[tuple[LeafField, LeafValue], ...]


@dataclass(frozen=True)
class _Binary:
    bt_type: Literal["BTAndFilter-110", "BTOrFilter-167"]
    operand1: _Binary | _Leaf
    operand2: _Binary | _Leaf


_EXTRUDE = _Binary(
    "BTAndFilter-110",
    _Binary(
        "BTOrFilter-167",
        _Binary(
            "BTAndFilter-110",
            _Binary(
                "BTAndFilter-110",
                _Leaf(
                    "BTFlatSheetMetalFilter-3018", (("allows", "MODEL_AND_FLATTENED"),)
                ),
                _Leaf(
                    "BTSketchObjectFilter-184",
                    (("isSketchObject", True), ("objectType", "ANY_SKETCH_OBJECT")),
                ),
            ),
            _Leaf("BTEntityTypeFilter-124", (("entityType", "FACE"),)),
        ),
        _Binary(
            "BTAndFilter-110",
            _Binary(
                "BTAndFilter-110",
                _Leaf("BTGeometryFilter-130", (("geometryType", "PLANE"),)),
                _Leaf("BTFlatSheetMetalFilter-3018", (("allows", "MODEL_ONLY"),)),
            ),
            _Leaf("BTEntityTypeFilter-124", (("entityType", "FACE"),)),
        ),
    ),
    _Leaf("BTConstructionObjectFilter-113", (("isConstruction", False),)),
)
_FILLET = _Binary(
    "BTAndFilter-110",
    _Binary(
        "BTAndFilter-110",
        _Binary(
            "BTAndFilter-110",
            _Binary(
                "BTOrFilter-167",
                _Binary(
                    "BTAndFilter-110",
                    _Leaf(
                        "BTActiveSheetMetalFilter-2944",
                        (("isFromActiveSheetMetal", False),),
                    ),
                    _Binary(
                        "BTOrFilter-167",
                        _Binary(
                            "BTAndFilter-110",
                            _Leaf("BTEntityTypeFilter-124", (("entityType", "EDGE"),)),
                            _Leaf(
                                "BTEdgeTopologyFilter-122",
                                (
                                    ("edgeTopology", "TWO_SIDED"),
                                    ("isInternalEdge", True),
                                ),
                            ),
                        ),
                        _Leaf("BTEntityTypeFilter-124", (("entityType", "FACE"),)),
                    ),
                ),
                _Binary(
                    "BTAndFilter-110",
                    _Leaf("BTEntityTypeFilter-124", (("entityType", "EDGE"),)),
                    _Leaf(
                        "BTSMDefinitionEntityTypeFilter-1651",
                        (("smDefinitionEntityType", "VERTEX"),),
                    ),
                ),
            ),
            _Leaf("BTConstructionObjectFilter-113", (("isConstruction", False),)),
        ),
        _Leaf(
            "BTSketchObjectFilter-184",
            (("isSketchObject", False), ("objectType", "NOT_SKETCH_OBJECT")),
        ),
    ),
    _Leaf("BTModifiableEntityOnlyFilter-1593", (("modifiableOnly", True),)),
)


def _matches(
    raw: JsonValue,
    expected: _Binary,
    *,
    nodes: int,
    depth: int,
    depth_limit: Literal[8, 9] = 8,
) -> bool:
    # Walk only the fixed expected operand slots. Extra/missing keys reject before
    # examining values. Work is bounded even for cyclic/deep synthetic inputs.
    stack: list[tuple[JsonValue, _Binary | _Leaf, int]] = [(raw, expected, 1)]
    visits = max_depth = 0
    while stack:
        node, shape, level = stack.pop()
        visits += 1
        max_depth = max(max_depth, level)
        if visits > 64 or level > depth_limit or not isinstance(node, dict):
            return False
        bt_type = node.get("btType")
        if type(bt_type) is not str or bt_type != shape.bt_type:
            return False
        if isinstance(shape, _Binary):
            if len(node) != 3 or node.keys() != {"btType", "operand1", "operand2"}:
                return False
            stack.append((node["operand2"], shape.operand2, level + 1))
            stack.append((node["operand1"], shape.operand1, level + 1))
        else:
            if len(node) != 1 + len(shape.fields) or node.keys() != {
                "btType",
                *(field for field, _ in shape.fields),
            }:
                return False
            for field, expected_value in shape.fields:
                value = node[field]
                # In particular, bool must never accept 0/1 or string coercion.
                if type(value) is not type(expected_value) or value != expected_value:
                    return False
    return visits == nodes and max_depth == depth


def matches_extrude_entities_filter(raw: JsonValue) -> bool:
    return _matches(raw, _EXTRUDE, nodes=13, depth=5)


def matches_fillet_entities_filter(raw: JsonValue) -> bool:
    return _matches(raw, _FILLET, nodes=17, depth=8)


# Constructors build immutable expected shapes only, never provider payloads.
def _and(left: _Binary | _Leaf, right: _Binary | _Leaf) -> _Binary:
    return _Binary("BTAndFilter-110", left, right)


def _or(left: _Binary | _Leaf, right: _Binary | _Leaf) -> _Binary:
    return _Binary("BTOrFilter-167", left, right)


def _entity(value: Literal["FACE", "EDGE", "VERTEX", "BODY"]) -> _Leaf:
    return _Leaf("BTEntityTypeFilter-124", (("entityType", value),))


def _geometry(
    value: Literal["PLANE", "LINE", "CIRCLE", "ARC", "CYLINDER", "CONE", "REVOLVED"],
) -> _Leaf:
    return _Leaf("BTGeometryFilter-130", (("geometryType", value),))


def _body(value: Literal["SOLID", "SHEET", "MATE_CONNECTOR"]) -> _Leaf:
    return _Leaf("BTBodyTypeFilter-112", (("bodyType", value),))


def _sketch(value: bool = False) -> _Leaf:
    return _Leaf(
        "BTSketchObjectFilter-184",
        (
            ("isSketchObject", value),
            ("objectType", "ANY_SKETCH_OBJECT" if value else "NOT_SKETCH_OBJECT"),
        ),
    )


def _modifiable(value: bool = True) -> _Leaf:
    return _Leaf("BTModifiableEntityOnlyFilter-1593", (("modifiableOnly", value),))


_CONSTRUCTION = _Leaf("BTConstructionObjectFilter-113", (("isConstruction", False),))
_MESH = _Leaf("BTAllowMeshGeometryFilter-1026", (("allowsMeshGeometry", True),))
_MATE = _Leaf(
    "BTMateConnectorFilter-163",
    (
        ("allowImplicitMateConnector", False),
        ("isMateConnectorInferenceEnabledByDefault", False),
        ("requiresOccurrence", False),
    ),
)
_SURFACE = _and(
    _and(_and(_entity("EDGE"), _sketch(True)), _modifiable()), _CONSTRUCTION
)
_WALL = _or(
    _and(
        _and(_and(_entity("FACE"), _geometry("PLANE")), _CONSTRUCTION),
        _modifiable(False),
    ),
    _and(_and(_and(_entity("EDGE"), _sketch(True)), _CONSTRUCTION), _modifiable()),
)
_BOUND_FACE = _or(
    _and(_and(_entity("FACE"), _sketch()), _MESH), _body("MATE_CONNECTOR")
)
_BOUND_BODY = _and(
    _and(_and(_entity("BODY"), _or(_body("SOLID"), _body("SHEET"))), _sketch()), _MESH
)
_BOUND_VERTEX = _or(_entity("VERTEX"), _MATE)
_DIRECTION = _or(
    _or(
        _or(
            _or(
                _geometry("LINE"),
                _or(
                    _geometry("CIRCLE"),
                    _or(
                        _geometry("ARC"),
                        _or(
                            _geometry("CYLINDER"),
                            _or(_geometry("CONE"), _geometry("REVOLVED")),
                        ),
                    ),
                ),
            ),
            _MATE,
        ),
        _geometry("PLANE"),
    ),
    _body("MATE_CONNECTOR"),
)
_START_OFFSET = _or(
    _or(
        _or(_and(_geometry("PLANE"), _entity("FACE")), _entity("EDGE")),
        _entity("VERTEX"),
    ),
    _body("MATE_CONNECTOR"),
)
_SCOPE = _and(_and(_and(_entity("BODY"), _body("SOLID")), _modifiable()), _MESH)
_SURFACE_SCOPE = _and(
    _and(_and(_and(_entity("BODY"), _body("SHEET")), _modifiable()), _MESH), _sketch()
)
_FILLET_FACE = _and(
    _and(_and(_and(_entity("FACE"), _CONSTRUCTION), _sketch()), _modifiable()),
    _Leaf("BTActiveSheetMetalFilter-2944", (("isFromActiveSheetMetal", False),)),
)
_PARTIAL = _or(_and(_entity("FACE"), _MESH), _or(_entity("VERTEX"), _MATE))
_KEEP_EDGES = _and(
    _and(
        _and(
            _and(
                _entity("EDGE"),
                _Leaf(
                    "BTEdgeTopologyFilter-122",
                    (("edgeTopology", "TWO_SIDED"), ("isInternalEdge", True)),
                ),
            ),
            _CONSTRUCTION,
        ),
        _sketch(),
    ),
    _modifiable(),
)
_CORNERS = _and(_and(_and(_entity("VERTEX"), _CONSTRUCTION), _sketch()), _modifiable())


@dataclass(frozen=True)
class _RoleContract:
    shape: _Binary
    nodes: int
    depth: int
    depth_limit: Literal[8, 9] = 8


_DORMANT_ROLES: Mapping[tuple[str, str], _RoleContract] = MappingProxyType(
    {
        ("extrude", "surfaceEntities"): _RoleContract(_SURFACE, 7, 4),
        ("extrude", "wallShape"): _RoleContract(_WALL, 15, 5),
        ("extrude", "endBoundEntityFace"): _RoleContract(_BOUND_FACE, 7, 4),
        ("extrude", "secondDirectionBoundEntityFace"): _RoleContract(_BOUND_FACE, 7, 4),
        ("extrude", "endBoundEntityBody"): _RoleContract(_BOUND_BODY, 9, 5),
        ("extrude", "secondDirectionBoundEntityBody"): _RoleContract(_BOUND_BODY, 9, 5),
        ("extrude", "endBoundEntityVertex"): _RoleContract(_BOUND_VERTEX, 3, 2),
        ("extrude", "secondDirectionBoundEntityVertex"): _RoleContract(
            _BOUND_VERTEX, 3, 2
        ),
        ("extrude", "extrudeDirection"): _RoleContract(
            _DIRECTION, 17, 9, depth_limit=9
        ),
        ("extrude", "startOffsetEntity"): _RoleContract(_START_OFFSET, 9, 5),
        ("extrude", "booleanScope"): _RoleContract(_SCOPE, 7, 4),
        ("extrude", "booleanSurfaceScope"): _RoleContract(_SURFACE_SCOPE, 9, 5),
        ("fillet", "side1Face"): _RoleContract(_FILLET_FACE, 9, 5),
        ("fillet", "side2Face"): _RoleContract(_FILLET_FACE, 9, 5),
        ("fillet", "centerFaces"): _RoleContract(_FILLET_FACE, 9, 5),
        ("fillet", "startPartialEntity"): _RoleContract(_PARTIAL, 7, 3),
        ("fillet", "endPartialEntity"): _RoleContract(_PARTIAL, 7, 3),
        ("fillet", "keepEdges"): _RoleContract(_KEEP_EDGES, 9, 5),
        ("fillet", "smoothCornerExceptions"): _RoleContract(_CORNERS, 7, 4),
    }
)


def matches_dormant_query_filter(
    category: str, role: str, param: dict[str, JsonValue]
) -> bool:
    """Exact category + caller role + provider parameter identity, empty query.

    The caller separately validates the complete parameter envelope/bookkeeping.
    Diagnostic strings, topology equivalence and arbitrary depth are no authority.
    """
    contract = _DORMANT_ROLES.get((category, role))
    queries = param.get("queries")
    if (
        contract is None
        or param.get("parameterId") != role
        or not isinstance(queries, list)
        or queries != []
    ):
        return False
    return _matches(
        param.get("filter"),
        contract.shape,
        nodes=contract.nodes,
        depth=contract.depth,
        depth_limit=contract.depth_limit,
    )
