"""Deterministic v17 feature adapter. No semantic plan ever contains provider IDs."""

import json
import logging
import re
from math import hypot
from time import monotonic
from typing import Any, cast

from forge_api.cad_edits.domain import EditError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.write_client import SafeEditClient

from .evidence import CreationEvidence
from .models import (
    BasePlaneRef,
    BlindExtent,
    CreateSketchCircle,
    CreateSketchRect,
    CreationStep,
    ExtrudeNew,
    ExtrudeRemove,
)


class AckRejected(EditError):
    """A provider acknowledgement failed one named check; the code stays closed.

    ``check`` is a fixed label and ``names`` are field names only (never values),
    so a rejection can be located without exposing CAD data.
    """

    def __init__(self, check: str, names: set[str] | None = None) -> None:
        super().__init__("verification_failed")
        self.check = check
        self.names = tuple(
            sorted(
                n
                for n in (names or ())
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,39}", n)
            )
        )[:8]


class StopLabelled(EditError):
    """Wraps a failure with its closed label, keeping the original closed code."""

    def __init__(
        self, check: str, cause: EditError, names: tuple[str, ...] = ()
    ) -> None:
        super().__init__(cause.code, cause.status)
        self.check = check
        self.names = names


def read(provider: SafeEditClient, context: WorkspaceReference) -> CreationEvidence:
    return CreationEvidence.project(*provider._read_evidence(context))


def parameter(key: str, kind: str, **values: Any) -> dict[str, Any]:
    return {"btType": kind, "parameterId": key, **values}


def feature(step: CreationStep, verified: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if any(ref not in verified for ref in step.depends_on):
        raise EditError("unsupported_target", 422)
    op = step.op
    name = f"Forge {step.id}"
    if isinstance(op, (CreateSketchRect, CreateSketchCircle)):
        if not isinstance(op.target, BasePlaneRef) or op.target.plane != "TOP":
            # Face-reference mapping requires real deterministic face evidence;
            # no arbitrary face or unapproved semantic-reference substitution.
            raise EditError("unsupported_target", 422)
        sketch = {
            "btType": "BTMSketch-151",
            "featureType": "newSketch",
            "name": name,
            "suppressed": False,
            "parameters": [
                parameter(
                    "sketchPlane",
                    "BTMParameterQueryList-148",
                    queries=[
                        {
                            "btType": "BTMIndividualQuery-138",
                            "queryString": (
                                'query=qCreatedBy(makeId("Top"), EntityType.FACE);'
                            ),
                        }
                    ],
                )
            ],
            "constraints": [],
            "entities": [],
        }
        x, y = op.center_x_um / 1e6, op.center_y_um / 1e6
        if isinstance(op, CreateSketchCircle):
            sketch["entities"] = [
                {
                    "btType": "BTMSketchCurve-4",
                    "entityId": "circle",
                    "centerId": "circle.center",
                    "geometry": {
                        "btType": "BTCurveGeometryCircle-115",
                        "radius": op.diameter_um / 2e6,
                        "xCenter": x,
                        "yCenter": y,
                        "xDir": 1.0,
                        "yDir": 0.0,
                        "clockwise": False,
                    },
                }
            ]
        else:
            w, h = op.width_um / 2e6, op.height_um / 2e6
            points = [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)]
            entities = []
            for i, (px, py) in enumerate(points):
                qx, qy = points[(i + 1) % 4]
                length = hypot(qx - px, qy - py)
                entities.append(
                    {
                        "btType": "BTMSketchCurveSegment-155",
                        "entityId": f"edge{i}",
                        "startPointId": f"edge{i}.start",
                        "endPointId": f"edge{i}.end",
                        "startParam": 0.0,
                        "endParam": length,
                        "geometry": {
                            "btType": "BTCurveGeometryLine-117",
                            "pntX": px,
                            "pntY": py,
                            "dirX": (qx - px) / length,
                            "dirY": (qy - py) / length,
                        },
                    }
                )
            sketch["entities"] = entities
        return sketch
    if not isinstance(op, (ExtrudeNew, ExtrudeRemove)) or not isinstance(
        op.extent, BlindExtent
    ):
        raise EditError("unsupported_target", 422)
    sketch = verified[op.profile]
    if sketch.get("featureType") != "newSketch":
        raise EditError("unsupported_target", 422)
    if isinstance(op, ExtrudeRemove):
        # REMOVE scope/default-mode semantics are not guessed from NEW examples.
        raise EditError("unsupported_target", 422)
    return {
        "btType": "BTMFeature-134",
        "featureType": "extrude",
        "name": name,
        "suppressed": False,
        "parameters": [
            parameter(
                "bodyType",
                "BTMParameterEnum-145",
                enumName="ExtendedToolBodyType",
                value="SOLID",
            ),
            parameter(
                "operationType",
                "BTMParameterEnum-145",
                enumName="NewBodyOperationType",
                value="NEW",
            ),
            parameter(
                "entities",
                "BTMParameterQueryList-148",
                queries=[
                    {
                        "btType": "BTMIndividualSketchRegionQuery-140",
                        "featureId": sketch["featureId"],
                    }
                ],
            ),
            parameter(
                "endBound",
                "BTMParameterEnum-145",
                enumName="BoundingType",
                value="BLIND",
            ),
            parameter(
                "depth",
                "BTMParameterQuantity-147",
                expression=f"{op.extent.depth_um / 1000:g} mm",
            ),
        ],
    }


def preflight(
    step: CreationStep, verified: dict[str, dict[str, Any]], evidence: CreationEvidence
) -> dict[str, Any]:
    return {
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": feature(step, verified),
        "sourceMicroversion": evidence.marker,
        "rejectMicroversionSkew": True,
        "serializationVersion": evidence.inventory["serializationVersion"],
        "libraryVersion": evidence.inventory["libraryVersion"],
    }


def _sketch_entities(expected: list[dict[str, Any]], actual: Any) -> None:
    from forge_api.cad_edits.domain import fingerprint

    if not isinstance(actual, list) or len(actual) != len(expected):
        raise AckRejected("ack_entities")
    # Only current v17 declared entity bookkeeping/default fields are permitted.
    # They remain in the acknowledgement and must be exact on the fresh reread.
    defaults = {
        "namespace": "",
        "name": "",
        "parameters": [],
        "isConstruction": False,
        "isFromEndpointSplineHandle": False,
        "isFromSplineControlPolygon": False,
        "isFromSplineHandle": False,
        "controlBoxIds": [],
        "internalIds": [],
        "curvedTextIds": [],
        "functionName": "",
        "offsetCurveExtensions": [],
    }
    for wanted, got in zip(expected, actual, strict=True):
        if not isinstance(got, dict):
            raise AckRejected("ack_entity_keys")
        unknown = set(got) - (
            set(wanted) | set(defaults) | {"nodeId", "index", "entityType"}
        )
        if unknown:
            raise AckRejected("ack_entity_keys", unknown)
        for key, value in defaults.items():
            if key in got and fingerprint(got[key]) != fingerprint(value):
                raise AckRejected("ack_entity_defaults")
        if "nodeId" in got and (
            not isinstance(got["nodeId"], str) or not 1 <= len(got["nodeId"]) <= 256
        ):
            raise AckRejected("ack_entity_node")
        if "index" in got and (
            type(got["index"]) is not int or not 0 <= got["index"] <= 64
        ):
            raise AckRejected("ack_entity_node")
        kind = (
            "LINE"
            if wanted["geometry"]["btType"] == "BTCurveGeometryLine-117"
            else "CIRCLE"
        )
        if "entityType" in got and got["entityType"] not in ("CURVE", kind):
            raise AckRejected("ack_entity_geometry")
        for key, value in wanted.items():
            if key == "geometry":
                geometry = got.get(key)
                if not isinstance(geometry, dict) or set(geometry) - (
                    set(value) | {"entityType"}
                ):
                    raise AckRejected("ack_entity_geometry")
                if geometry.get("entityType", kind) != kind:
                    raise AckRejected("ack_entity_geometry")
                if fingerprint({k: geometry.get(k) for k in value}) != fingerprint(
                    value
                ):
                    raise AckRejected("ack_entity_geometry")
            elif fingerprint(got.get(key)) != fingerprint(value):
                raise AckRejected("ack_entity_fields")


def acknowledge(
    sent: dict[str, Any], data: Any, before: CreationEvidence
) -> tuple[str, dict[str, Any]]:
    from pydantic import TypeAdapter

    from forge_api.cad_edits.domain import fingerprint
    from forge_api.integrations.onshape.contracts import CadId
    from forge_api.integrations.onshape.semantic_inventory import canonical_feature

    if not isinstance(data, dict) or data.get("microversionSkew") is not False:
        raise AckRejected("ack_skew")
    marker = TypeAdapter(CadId).validate_python(
        data.get("sourceMicroversion"), strict=True
    )
    actual = data.get("feature")
    if (
        marker == before.marker
        or not isinstance(actual, dict)
        or not isinstance(actual.get("featureId"), str)
        or not 1 <= len(actual["featureId"]) <= 256
    ):
        raise AckRejected("ack_envelope")
    for key in ("btType", "featureType", "name", "suppressed"):
        if actual.get(key) != sent[key] or type(actual.get(key)) is not type(sent[key]):
            raise AckRejected("ack_header")
    for key, value in (
        ("namespace", ""),
        ("subFeatures", []),
        ("returnAfterSubfeatures", False),
        ("parentSuppressed", False),
        ("suppressionConfigured", False),
    ):
        if key in actual and fingerprint(actual[key]) != fingerprint(value):
            raise AckRejected("ack_defaults")
    allowed = {
        "btType",
        "featureType",
        "name",
        "suppressed",
        "featureId",
        "parameters",
        "namespace",
        "subFeatures",
        "returnAfterSubfeatures",
        "parentSuppressed",
        "suppressionConfigured",
        "suppressionState",
        "nodeId",
        "entities",
        "constraints",
        # BTMFeature-134 base property (array of BTMParameter-1, OpenAPI 1.222). Only
        # the empty array is accepted: it carries no library parameters or semantics.
        "parameterLibraries",
    }
    if "parameterLibraries" in actual and actual["parameterLibraries"] != []:
        raise AckRejected("ack_parameter_libraries")
    if set(actual) - allowed:
        raise AckRejected("ack_feature_keys", set(actual) - allowed)
    suppression = actual.get("suppressionState")
    if suppression is not None and (
        not isinstance(suppression, dict)
        or set(suppression) - {"btType", "nodeId", "suppressionConfigured"}
        or suppression.get("btType") != "BTMSuppressionState-1924"
        or suppression.get("suppressionConfigured") is not False
    ):
        raise AckRejected("ack_suppression")
    canonical_feature(actual)  # Reject malformed modeled node slots.
    params = actual.get("parameters")
    if not isinstance(params, list) or any(
        not isinstance(p, dict) or not isinstance(p.get("parameterId"), str)
        for p in params
    ):
        raise AckRejected("ack_parameters")
    by_id = {p["parameterId"]: p for p in params}
    if len(by_id) != len(params):
        raise AckRejected("ack_parameters")
    if sent["featureType"] == "extrude":
        # Existing closed NEW/SOLID/BLIND quantity/default-mode contract, unchanged.
        from forge_api.integrations.onshape.edit_registry import quantity_parameter

        quantity_parameter(actual, "SET_EXTRUDE_DEPTH")
    else:
        plane = by_id.get("sketchPlane", {})
        unknown_plane = set(plane) - {
            "btType",
            "parameterId",
            "queries",
            "nodeId",
            "importMicroversion",
            "parameterName",
            "valueString",
            "libraryRelationType",
        }
        if unknown_plane:
            raise AckRejected("ack_plane", unknown_plane)
        for field, default_value in (
            ("parameterName", ""),
            ("valueString", ""),
            ("libraryRelationType", "DEFAULT"),
            ("importMicroversion", 0),
        ):
            if field in plane and fingerprint(plane[field]) != fingerprint(
                default_value
            ):
                raise AckRejected("ack_plane")
        if set(by_id) != {"sketchPlane"}:
            raise AckRejected("ack_parameters")
        if fingerprint(actual.get("constraints")) != fingerprint(sent["constraints"]):
            raise AckRejected("ack_constraints")
        _sketch_entities(sent["entities"], actual.get("entities"))
    for expected in sent["parameters"]:
        received = by_id.get(expected["parameterId"])
        if received is None:
            raise AckRejected("ack_parameters")
        for key, value in expected.items():
            if key == "queries":
                queries = received.get("queries")
                if not isinstance(queries, list) or len(queries) != 1:
                    raise AckRejected("ack_query")
                q = queries[0]
                if not isinstance(q, dict) or set(q) - {
                    "btType",
                    "queryString",
                    "featureId",
                    "nodeId",
                    "importMicroversion",
                    "deterministicIds",
                    "filterInnerLoops",
                    "query",
                    "deterministicIdList",
                    "persistentQuery",
                    "queryStatement",
                    "variableName",
                }:
                    raise AckRejected("ack_query")
                if q.get("btType") == "BTMIndividualQuery-138" and (
                    "featureId" in q or "filterInnerLoops" in q
                ):
                    raise AckRejected("ack_query")
                if q.get("btType") == "BTMIndividualSketchRegionQuery-140" and (
                    q.get("filterInnerLoops", False) is not False
                    or q.get("queryString", "") != ""
                ):
                    raise AckRejected("ack_query")
                if "nodeId" in q and (
                    not isinstance(q["nodeId"], str) or not 1 <= len(q["nodeId"]) <= 256
                ):
                    raise AckRejected("ack_query")
                if q.get("importMicroversion", 0) != 0:
                    raise AckRejected("ack_query")
                for field, wanted in value[0].items():
                    if fingerprint(q.get(field)) != fingerprint(wanted):
                        raise AckRejected("ack_query")
                for field in (
                    "query",
                    "deterministicIdList",
                    "persistentQuery",
                    "queryStatement",
                    "variableName",
                ):
                    if q.get(field) is not None:
                        raise AckRejected("ack_query")
                ids = q.get("deterministicIds", [])
                if (
                    not isinstance(ids, list)
                    or len(ids) > 2000
                    or any(
                        not isinstance(i, str) or not 1 <= len(i) <= 256 for i in ids
                    )
                ):
                    raise AckRejected("ack_query")
            elif fingerprint(received.get(key)) != fingerprint(value):
                raise AckRejected("ack_parameters")
    return marker, actual


class CreationClient:
    def __init__(self, provider: SafeEditClient, context: WorkspaceReference) -> None:
        self.provider = provider
        self.context = context
        self.last_rejection: str | None = None

    def note_failure(self, label: str, names: tuple[str, ...] = ()) -> None:
        """Keep the closed label for the audit and, in development, a field-name log."""
        self.last_rejection = label
        if self.provider._development:
            logging.getLogger("forge.creation").warning(
                "creation_stop %s", json.dumps({"check": label, "fields": names})
            )

    def _renew(self) -> None:
        # Each capture or dispatch gets its own 30 s ceiling. A sequential plan makes
        # many reads, so one ceiling shared by the whole approval would expire
        # mid-plan; a hung request is still bounded.
        self.provider._deadline = monotonic() + 30

    def capture(self) -> CreationEvidence:
        self._renew()
        return read(self.provider, self.context)

    def preflight(
        self,
        step: CreationStep,
        verified: dict[str, dict[str, Any]],
        before: CreationEvidence,
    ) -> object:
        import json

        payload = preflight(step, verified, before)
        if len(json.dumps(payload, allow_nan=False).encode()) > 8192:
            raise EditError("unsupported_target", 422)
        return (payload, before)

    def dispatch(self, payload: object) -> tuple[str, dict[str, Any]]:
        if not self.provider._enabled:
            raise EditError("write_disabled", 403)
        body, before = cast(tuple[dict[str, Any], CreationEvidence], payload)
        context = self.context
        path = (
            f"/partstudios/d/{context.documentId}/w/{context.workspaceId}"
            f"/e/{context.elementId}/features"
        )
        self._renew()
        try:
            result = self.provider._exchange("POST", path, body)
        except EditError as error:
            raise StopLabelled("post_transport", error) from None
        try:
            return acknowledge(body["feature"], result, before)
        except AckRejected as error:
            raise StopLabelled(error.check, error, error.names) from None
        except EditError as error:
            raise StopLabelled("ack_contract", error) from None
