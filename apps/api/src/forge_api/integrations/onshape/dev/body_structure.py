"""DEV-only first-body field presence, never IDs, geometry or unknown names."""

import json

from pydantic import JsonValue


def describe_body(raw: JsonValue) -> str | None:
    # Called only after bounded JSON and successful provider normalization.
    # Still enforce this tiny projection's own limits; never stringify raw data.
    if not isinstance(raw, dict):
        return None
    bodies = raw.get("bodies")
    if not isinstance(bodies, list) or not bodies or len(bodies) > 2000:
        return None
    body = bodies[0]
    if not isinstance(body, dict):
        return None
    fields: dict[str, object] = {}
    for name in ("faces", "edges", "vertices"):
        value = body.get(name)
        if value is not None and not isinstance(value, list):
            return None
        if isinstance(value, list) and len(value) > 20000:
            return None
        fields[name] = {
            "present": name in body,
            "type": "array" if isinstance(value, list) else "missing",
            "length": len(value) if isinstance(value, list) else None,
        }
    report = json.dumps({"bodyDetails": fields}, separators=(",", ":"))
    return report if len(report) <= 512 else None
