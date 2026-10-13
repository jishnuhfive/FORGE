"""Describe the reviewed mass schema without copying provider values or keys."""

import json
import math

from pydantic import JsonValue, TypeAdapter, ValidationError

from ..models import Number

FIELDS = (
    "mass",
    "volume",
    "periphery",
    "centroid",
    "inertia",
    "hasMass",
    "massMissingCount",
    "principalInertia",
    "principalAxes",
)
REASONS = {
    "float_type": "type_mismatch",
    "int_type": "type_mismatch",
    "bool_type": "type_mismatch",
    "list_type": "type_mismatch",
    "dict_type": "type_mismatch",
    "string_type": "type_mismatch",
    "model_type": "type_mismatch",
    "too_long": "length_limit",
    "too_short": "length_limit",
    "finite_number": "nonfinite_number",
    "negative_nominal": "invalid_bounds",
    "bounds_order": "invalid_bounds",
    "greater_than_equal": "numeric_bound",
}
MAX_DIAGNOSTIC = 4096


def mass_facts(body: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Only authorized sign/availability categories, from one failed mass record."""
    facts: dict[str, JsonValue] = {}
    raw_values = body.get("mass")
    if isinstance(raw_values, list) and len(raw_values) == 3:
        try:
            values = TypeAdapter(list[Number]).validate_python(raw_values, strict=True)
        except ValidationError:
            pass
        else:
            facts["massSigns"] = {
                f"position{index}": "negative"
                if value < 0
                else "positive"
                if value > 0
                else "zero"
                for index, value in enumerate(values)
            }
    has_mass = body.get("hasMass")
    if isinstance(has_mass, bool):
        facts["hasMass"] = has_mass
    missing_count = body.get("massMissingCount")
    if type(missing_count) is int and missing_count >= 0:
        facts["massMissingCountCategory"] = "zero" if missing_count == 0 else "positive"
    return facts


def scalar_comparisons(value: JsonValue) -> dict[str, JsonValue]:
    """Compare finite triples only; validation reasons come directly from the model."""
    if not isinstance(value, list) or len(value) != 3:
        return {}
    try:
        values = TypeAdapter(list[Number]).validate_python(value, strict=True)
    except ValidationError:
        return {}
    return {
        f"position{left}_vs_position{right}": "less"
        if values[left] < values[right]
        else "greater"
        if values[left] > values[right]
        else "equal"
        for left, right in ((0, 1), (0, 2), (1, 2))
    }


def category(value: JsonValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return (
            "number"
            if not isinstance(value, float) or math.isfinite(value)
            else "nonfinite_number"
        )
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def describe_mass(raw: JsonValue, error: ValueError | None) -> str:
    fields: list[dict[str, JsonValue]] = []

    def describe(name: str, value: JsonValue = None, *, present: bool = True) -> None:
        entry: dict[str, JsonValue] = {
            "field": name,
            "type": category(value) if present else "absent",
        }
        if present and isinstance(value, list):
            entry["length"] = min(len(value), 100000)
            item_types: list[JsonValue] = [
                item for item in sorted({category(item) for item in value})
            ]
            entry["items"] = item_types
        fields.append(entry)

    describe("response", raw)
    root = raw if isinstance(raw, dict) else {}
    for name in ("microversionId", "bodies"):
        describe(name, root.get(name), present=name in root)
    bodies = root.get("bodies")
    record: JsonValue = None
    kind = "none"
    if isinstance(bodies, dict) and bodies:
        kind = "aggregate" if "-all-" in bodies else "body"
        record = bodies["-all-"] if kind == "aggregate" else next(iter(bodies.values()))
    describe("bodyRecord", record, present=kind != "none")
    body = record if isinstance(record, dict) else {}
    for name in FIELDS:
        describe(name, body.get(name), present=name in body)
    axes = body.get("principalAxes")
    if isinstance(axes, list) and axes:
        axis = axes[0]
        describe("principalAxes.item", axis)
        if isinstance(axis, dict):
            for name in ("x", "y", "z", "btType"):
                describe("principalAxes." + name, axis.get(name), present=name in axis)
    reasons: list[dict[str, JsonValue]] = []
    failed_mass_body: dict[str, JsonValue] | None = None
    if isinstance(error, ValidationError):
        for failure in error.errors(
            include_url=False, include_context=False, include_input=False
        )[:8]:
            location = failure["loc"]
            # Locations can contain private body keys. Never serialize them.
            safe_location = (
                (*location[:1], *location[2:])
                if location and location[0] == "bodies"
                else location
            )
            known = [
                part
                for part in safe_location
                if part in (*FIELDS, "microversionId", "bodies")
            ]
            name = known[-1] if known else "response"
            entry: dict[str, JsonValue] = {
                "field": name,
                "reason": REASONS.get(failure["type"], "schema_invalid"),
            }
            if (
                failure["type"] in ("negative_nominal", "bounds_order")
                and name in ("mass", "volume", "periphery")
                and len(location) == 3
                and location[0] == "bodies"
                and isinstance(location[1], str)
                and isinstance(bodies, dict)
            ):
                failed_body = bodies.get(location[1])
                if isinstance(failed_body, dict):
                    # Fixed field-level error codes remove the validator replay.
                    entry["failedPredicates"] = [failure["type"]]
                    comparisons = scalar_comparisons(failed_body.get(name))
                    if comparisons:
                        entry["comparisons"] = comparisons
                    if name == "mass" and failed_mass_body is None:
                        failed_mass_body = failed_body
            reasons.append(entry)
    report: dict[str, object] = {
        "diagnostic": "forge-mass-structure-v1",
        "reason": "schema_validation"
        if isinstance(error, ValidationError)
        else "invalid_json_or_normalization"
        if error
        else "transport_metadata",
        "recordKind": kind,
        "fields": fields,
        "validation": reasons[:8],
    }
    if failed_mass_body is not None:
        # Match the first field-specific mass failure, not the sampled aggregate.
        report.update(mass_facts(failed_mass_body))
    text = json.dumps(report, separators=(",", ":"), allow_nan=False)
    if len(text) > MAX_DIAGNOSTIC:
        # Fixed fallback, never truncation of private or malformed JSON.
        return (
            '{"diagnostic":"forge-mass-structure-v1","reason":"diagnostic_limit",'
            '"recordKind":"none","fields":[],"validation":[]}'
        )
    return text
