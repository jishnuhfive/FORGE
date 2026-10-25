"""Two exact entities contracts from the human writes-OFF Phase 16 evidence.

These private immutable shapes are acceptance authority, not diagnostic tokens.
No known-node allowlist, tree rewriting, Boolean equivalence or default inference.
Only the two named role predicates are exposed; all other roles stay unproven.
"""

from dataclasses import dataclass
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


def _matches(raw: JsonValue, expected: _Binary, *, nodes: int, depth: int) -> bool:
    # Walk only the fixed expected operand slots. Extra/missing keys reject before
    # examining values. Work is bounded even for cyclic/deep synthetic inputs.
    stack: list[tuple[JsonValue, _Binary | _Leaf, int]] = [(raw, expected, 1)]
    visits = max_depth = 0
    while stack:
        node, shape, level = stack.pop()
        visits += 1
        max_depth = max(max_depth, level)
        if visits > 64 or level > 8 or not isinstance(node, dict):
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
