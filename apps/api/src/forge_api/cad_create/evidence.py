"""Creation evidence has no existing feature target. All raw data stays ephemeral."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.integrations.onshape.contracts import CadId
from forge_api.integrations.onshape.semantic_inventory import canonical_feature


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

    def require_empty(self) -> None:
        if self.inventory["features"] or self.bodies["bodies"]:
            raise EditError("unsupported_target")


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
        raise EditError("verification_failed")
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
            raise EditError("verification_failed")
        states = b["featureStates"]
    expected["featureStates"] = states

    def semantic(inv: dict[str, Any]) -> dict[str, Any]:
        return {**inv, "features": [canonical_feature(f) for f in inv["features"]]}

    if acknowledged.get("featureType") == "newSketch":
        expected_bodies = deepcopy(before.bodies)
        expected_bodies["microversionId"]["theId"] = marker
        if fingerprint(expected_bodies) != fingerprint(after.bodies):
            raise EditError("verification_failed")
    elif len(after.bodies["bodies"]) != 1:
        raise EditError("verification_failed")
    cfg = {**before.configuration, "sourceMicroversion": marker}
    if fingerprint(semantic(expected)) != fingerprint(semantic(b)) or fingerprint(
        cfg
    ) != fingerprint(after.configuration):
        raise EditError("verification_failed")
