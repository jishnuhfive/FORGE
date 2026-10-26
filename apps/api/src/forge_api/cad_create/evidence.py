"""Creation evidence has no existing feature target. All raw data stays ephemeral."""

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.integrations.onshape.contracts import CadId
from forge_api.integrations.onshape.semantic_inventory import canonical_feature

from .plane_filter import valid_selection_filter


class VerifyRejected(EditError):
    """Fresh post-write verification failed one named check (closed label)."""

    def __init__(self, check: str, code: str = "verification_failed") -> None:
        super().__init__(code)
        self.check = check


@dataclass(frozen=True, repr=False)
class CreationEvidence:
    marker: str
    inventory: dict[str, Any]
    configuration: dict[str, Any]
    bodies: dict[str, Any]

    @classmethod
    def project(
        cls, marker: str, inventory: Any, configuration: Any, bodies: Any
    ) -> CreationEvidence:
        TypeAdapter(CadId).validate_python(marker, strict=True)
        if not all(isinstance(x, dict) for x in (inventory, configuration, bodies)):
            raise EditError("unsupported_target")
        features = inventory.get("features")
        if (
            not isinstance(features, list)
            or len(features) > 64
            or inventory.get("isComplete") is not True
            or inventory.get("microversionSkew") is not False
            or inventory.get("sourceMicroversion") != marker
            or type(inventory.get("libraryVersion")) is not int
            or not isinstance(inventory.get("serializationVersion"), str)
            or not inventory["serializationVersion"]
            or type(inventory.get("rollbackIndex")) is not int
            or inventory.get("rollbackIndex") not in (-1, len(features))
            or configuration.get("sourceMicroversion") != marker
            or configuration.get("microversionSkew") is not False
            or configuration.get("configurationParameters") != []
            or configuration.get("currentConfiguration") != []
            or bodies.get("errorEnum") != "NO_ERROR"
        ):
            raise EditError("unsupported_target")
        revision = bodies.get("microversionId")
        items = bodies.get("bodies")
        if (
            not isinstance(revision, dict)
            or revision.get("theId") != marker
            or revision.get("ambiguous", False) is not False
            or revision.get("deleted", False) is not False
            or not isinstance(items, list)
            or len(items) > 1
            or any(
                not isinstance(b, dict) or b.get("type") != "SOLID" or not b.get("id")
                for b in items
            )
        ):
            raise EditError("unsupported_target")
        ids = []
        for f in features:
            if (
                not isinstance(f, dict)
                or not isinstance(f.get("featureId"), str)
                or not f["featureId"]
                or f.get("featureType") not in ("newSketch", "extrude")
                or f.get("suppressed") is not False
            ):
                raise EditError("unsupported_target")
            ids.append(f["featureId"])
        states = inventory.get("featureStates")
        if len(set(ids)) != len(ids) or not isinstance(states, dict):
            raise EditError("unsupported_target")
        if states and (
            set(states) != set(ids)
            or any(
                not isinstance(s, dict)
                or s.get("featureStatus") != "OK"
                or s.get("inactive") is not False
                for s in states.values()
            )
        ):
            raise EditError("unsupported_target")
        return cls(
            marker, deepcopy(inventory), deepcopy(configuration), deepcopy(bodies)
        )

    @property
    def digest(self) -> str:
        return fingerprint(
            [self.marker, self.inventory, self.configuration, self.bodies]
        )

    @property
    def parts(self) -> dict[str, str]:
        """Per-category digests; they alone locate a mismatch without raw CAD data."""
        return {
            "marker": fingerprint(self.marker),
            "inventory": fingerprint(self.inventory),
            "configuration": fingerprint(self.configuration),
            "bodies": fingerprint(self.bodies),
        }

    def require_empty(self) -> None:
        if self.inventory["features"] or self.bodies["bodies"]:
            raise EditError("unsupported_target")


_SEGMENT = re.compile(r"[A-Za-z][A-Za-z0-9]{0,39}")


def _first_path(a: Any, b: Any, path: tuple[str, ...] = ()) -> tuple[str, ...] | None:
    """First differing key path; list positions become '[]', values never appear."""
    if type(a) is not type(b):
        return path or ("<root>",)
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            name = key if _SEGMENT.fullmatch(key) else "<key>"
            if key not in a or key not in b:
                return (*path, name, "<present>")[:8]
            found = _first_path(a[key], b[key], (*path, name))
            if found is not None:
                return found[:8]
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return (*path, "[]", "<length>")[:8]
        for x, y in zip(a, b, strict=True):
            found = _first_path(x, y, (*path, "[]"))
            if found is not None:
                return found[:8]
        return None
    return None if a == b else (path or ("<root>",))


def difference(a: CreationEvidence, b: CreationEvidence) -> tuple[str, tuple[str, ...]]:
    """First differing category and a name-only path; ('none', ()) when identical."""
    if a.marker != b.marker:
        return "marker", ()
    for name in ("inventory", "configuration", "bodies"):
        found = _first_path(getattr(a, name), getattr(b, name))
        if found is not None:
            return name, found
    return "none", ()


def _unfiltered(feature: dict[str, Any]) -> dict[str, Any]:
    """Drop only valid provider-managed selection filters before comparing features.

    The filter is a UI picker restriction that may appear in a reread but not in a
    POST acknowledgement (or conversely); the selection itself is the compared
    ``queries``. An invalid filter is kept, so it can never match or hide a change.
    """
    if feature.get("featureType") not in ("newSketch", "extrude"):
        return feature
    result = deepcopy(feature)
    for param in result.get("parameters", []):
        if (
            isinstance(param, dict)
            and param.get("btType") == "BTMParameterQueryList-148"
            and "filter" in param
            and valid_selection_filter(param["filter"])
        ):
            del param["filter"]
    return result


def verify_added(
    before: CreationEvidence,
    after: CreationEvidence,
    acknowledged: dict[str, Any],
    marker: str,
) -> None:
    a, b = before.inventory, after.inventory
    if (
        marker == before.marker
        or after.marker != marker
        or len(b["features"]) != len(a["features"]) + 1
    ):
        raise VerifyRejected("ver_count")
    # Full inventory/config metadata and all prior feature states remain exact;
    # only the source revision, rollback position and newly appended entry change.
    expected = dict(a)
    expected["sourceMicroversion"] = marker
    expected["rollbackIndex"] = b["rollbackIndex"]
    expected["features"] = [*a["features"], acknowledged]
    states = dict(a["featureStates"])
    if states:
        newstate = b["featureStates"].get(acknowledged["featureId"])
        states[acknowledged["featureId"]] = newstate
    elif b["featureStates"]:
        # Empty state coverage cannot silently turn into different prior evidence.
        if a["features"]:
            raise VerifyRejected("ver_inventory")
        states = b["featureStates"]
    expected["featureStates"] = states

    def semantic(inv: dict[str, Any]) -> dict[str, Any]:
        return {
            **inv,
            "features": [canonical_feature(_unfiltered(f)) for f in inv["features"]],
        }

    if acknowledged.get("featureType") == "newSketch":
        expected_bodies = deepcopy(before.bodies)
        expected_bodies["microversionId"]["theId"] = marker
        if fingerprint(expected_bodies) != fingerprint(after.bodies):
            raise VerifyRejected("ver_bodies")
    elif len(after.bodies["bodies"]) != 1:
        raise VerifyRejected("ver_bodies")
    cfg = {**before.configuration, "sourceMicroversion": marker}
    if fingerprint(semantic(expected)) != fingerprint(semantic(b)):
        raise VerifyRejected("ver_inventory")
    if fingerprint(cfg) != fingerprint(after.configuration):
        raise VerifyRejected("ver_config")
