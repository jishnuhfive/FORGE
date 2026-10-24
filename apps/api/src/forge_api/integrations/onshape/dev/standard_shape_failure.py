"""Request-local first failure from the production current-UI predicate itself."""

from pydantic import JsonValue

from forge_api.cad_edits.domain import Closed, EditError

from ..standard_edit_shapes import ui_quantity_parameter
from ..standard_shape_contract import ShapeCategory, ShapeFailure, ShapeValidationError


class ShapeValidation(Closed):
    category: ShapeCategory
    failure: ShapeFailure | None


def diagnose_ui_shape(
    feature: dict[str, JsonValue], category: ShapeCategory
) -> ShapeValidation:
    try:
        ui_quantity_parameter(feature, "depth" if category == "extrude" else "radius")
    except ShapeValidationError as error:
        return ShapeValidation(category=category, failure=error.failure)
    return ShapeValidation(category=category, failure=None)


def shape_validation_coverage(data: JsonValue) -> tuple[ShapeValidation, ...]:
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise EditError("invalid_provider_response", 503)
    features = data["features"]
    assert isinstance(features, list)
    if len(features) > 20:
        raise EditError("invalid_provider_response", 503)
    results: list[ShapeValidation] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        if feature.get("featureType") == "extrude":
            results.append(diagnose_ui_shape(feature, "extrude"))
        elif feature.get("featureType") == "fillet":
            results.append(diagnose_ui_shape(feature, "fillet"))
    return tuple(results)
