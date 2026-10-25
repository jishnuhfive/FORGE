"""Private operation-local server identity evidence; no approval authority or I/O."""

from copy import deepcopy
from dataclasses import dataclass
from typing import cast

from pydantic import JsonValue

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation

from .edit_registry import quantity_parameter
from .semantic_inventory import semantic_feature


def _query(feature: dict[str, JsonValue]) -> dict[str, JsonValue]:
    kind = feature.get("featureType")
    quantity_parameter(
        feature, "SET_EXTRUDE_DEPTH" if kind == "extrude" else "SET_FILLET_RADIUS"
    )
    parameters = cast(list[dict[str, JsonValue]], feature["parameters"])
    entities = next(p for p in parameters if p["parameterId"] == "entities")
    queries = entities["queries"]
    if not isinstance(queries, list) or len(queries) != 1:
        raise EditError("verification_failed")
    query = queries[0]
    if (
        not isinstance(query, dict)
        or query.get("btType") != "BTMIndividualQuery-138"
        or not isinstance(query.get("queryString"), str)
        or not cast(str, query["queryString"]).strip()
    ):
        raise EditError("verification_failed")
    return query


@dataclass(frozen=True, repr=False)
class QueryIdentityReceipt:
    ids: tuple[str, ...]

    @classmethod
    def resolve(
        cls, expected: dict[str, JsonValue], returned: dict[str, JsonValue]
    ) -> QueryIdentityReceipt:
        a, b = _query(expected), _query(returned)
        ids = b.get("deterministicIds")
        if a.get("deterministicIds") != [] or not isinstance(ids, list) or not ids:
            raise EditError("verification_failed")
        # Validators above bound every ID and reject unknown query/parameter fields.
        materialized = deepcopy(expected)
        _query(materialized)["deterministicIds"] = deepcopy(ids)
        if fingerprint(semantic_feature(materialized)) != fingerprint(
            semantic_feature(returned)
        ):
            raise EditError("verification_failed")
        return cls(tuple(cast(list[str], ids)))

    def materialize(self, expected: dict[str, JsonValue]) -> dict[str, JsonValue]:
        result = deepcopy(expected)
        query = _query(result)
        if query.get("deterministicIds") != []:
            raise EditError("verification_failed")
        query["deterministicIds"] = list(self.ids)
        return result


@dataclass(frozen=True, repr=False)
class OperationAcknowledgement:
    marker: str
    identity: QueryIdentityReceipt
    evidence: object
    operation: ResolvedOperation
    consumed: bool = False

    def consume(
        self, evidence: object, operation: ResolvedOperation, marker: str
    ) -> QueryIdentityReceipt:
        used = self.consumed
        object.__setattr__(self, "consumed", True)
        if (
            used
            or evidence is not self.evidence
            or operation is not self.operation
            or marker != self.marker
        ):
            raise EditError("verification_failed")
        return self.identity
