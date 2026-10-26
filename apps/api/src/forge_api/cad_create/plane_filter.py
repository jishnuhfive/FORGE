"""Closed-vocabulary check for the provider-managed `filter` on query parameters.

OpenAPI 1.222 declares ``BTMParameterQueryList-148.filter`` as a ``BTQueryFilter-183``:
an entity-picker restriction the UI shows for a parameter (for a sketch plane or an
Extrude's entities), carried alongside ``queries``. The selection that the feature
evaluates is the ``queries`` list, which Forge still verifies exactly; the filter only
limits what a person may pick. It is therefore accepted only when it is a bounded
And/Or tree of leaf filters from the closed set below, each with exactly its own
fields and literal values. Anything else (unknown type, extra/missing key, wrong
scalar type, excess size/depth) is rejected, so an unexpected filter never passes.

The exact value Onshape attaches to a sketch plane has not been captured; the
structure descriptor below exists so the first accepted filter can be reviewed.
"""

from typing import Any

_MAX_NODES = 64
_MAX_DEPTH = 8
_BOOL = (True, False)
_LEAVES: dict[str, dict[str, tuple[Any, ...]]] = {
    "BTFlatSheetMetalFilter-3018": {"allows": ("MODEL_AND_FLATTENED", "MODEL_ONLY")},
    "BTSketchObjectFilter-184": {
        "isSketchObject": _BOOL,
        "objectType": ("ANY_SKETCH_OBJECT", "NOT_SKETCH_OBJECT"),
    },
    "BTEntityTypeFilter-124": {"entityType": ("FACE", "EDGE", "VERTEX", "BODY")},
    "BTGeometryFilter-130": {
        "geometryType": (
            "PLANE",
            "LINE",
            "CIRCLE",
            "ARC",
            "CYLINDER",
            "CONE",
            "REVOLVED",
        )
    },
    "BTConstructionObjectFilter-113": {"isConstruction": _BOOL},
    "BTModifiableEntityOnlyFilter-1593": {"modifiableOnly": _BOOL},
    "BTBodyTypeFilter-112": {"bodyType": ("SOLID", "SHEET", "MATE_CONNECTOR")},
    "BTAllowMeshGeometryFilter-1026": {"allowsMeshGeometry": _BOOL},
    "BTMateConnectorFilter-163": {
        "allowImplicitMateConnector": _BOOL,
        "isMateConnectorInferenceEnabledByDefault": _BOOL,
        "requiresOccurrence": _BOOL,
    },
}
_COMBINATORS = ("BTAndFilter-110", "BTOrFilter-167")


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
        if bt_type in _COMBINATORS:
            if node.keys() != {"btType", "operand1", "operand2"}:
                return False
            stack.append((node["operand2"], level + 1))
            stack.append((node["operand1"], level + 1))
            continue
        fields = _LEAVES.get(bt_type)
        if fields is None or node.keys() != {"btType", *fields}:
            return False
        if not all(_same(node[name], allowed) for name, allowed in fields.items()):
            return False
    return True


def describe(raw: Any) -> str:
    """Value-free-of-identity structure label for review, e.g. And(Entity=FACE,...)."""
    if not valid_selection_filter(raw):
        return "<invalid>"

    def walk(node: dict[str, Any]) -> str:
        bt_type = node["btType"]
        short = bt_type.split("-")[0].removeprefix("BT").removesuffix("Filter")
        if bt_type in _COMBINATORS:
            return f"{short}({walk(node['operand1'])},{walk(node['operand2'])})"
        values = ",".join(f"{k}={node[k]}" for k in sorted(set(node) - {"btType"}))
        return f"{short}[{values}]"

    return walk(raw)
