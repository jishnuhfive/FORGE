"""Version/path policy verified against cad.onshape.com/api/openapi, 2026-10-10."""

from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import quote, urlsplit

from pydantic import BaseModel, ConfigDict, Field

API_VERSION = "v17"
SCHEMA_VERSION = "1.222.90730-c8d74e607a47"
ACCEPT = "application/json;charset=UTF-8; qs=0.09"
ORIGIN = "https://cad.onshape.com"
# Same opaque identifier shape as Phase 3 and the official Explorer URL parser.
CadId = Annotated[str, Field(pattern=r"^[a-f0-9]{24}$", min_length=24, max_length=24)]


class WorkspaceReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )
    documentId: CadId
    workspaceId: CadId
    elementId: CadId
    revisionKind: Literal["workspace"]


def provider_origin(value: str) -> str:
    """Exact reviewed origin, independent of broader Phase 2 enterprise auth config."""
    if len(value) > 256 or any(
        ord(c) < 33 or ord(c) == 127 or c.isspace() or c == "\\" for c in value
    ):
        raise ValueError("Unsupported Onshape provider")
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or url.hostname != "cad.onshape.com"
            or url.username is not None
            or url.password is not None
            or url.port not in (None, 443)
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or "?" in value
            or "#" in value
        ):
            raise ValueError
    except ValueError:
        raise ValueError("Unsupported Onshape provider") from None
    return ORIGIN


def api_origin(base: str) -> str:
    url = urlsplit(base)
    if url.path != "/api" or url.query or url.fragment:
        raise ValueError("Unsupported Onshape API base")
    return provider_origin(base[:-4])


class Operation(StrEnum):
    FEATURES = "features"
    PARTS = "parts"
    BODIES = "bodies"
    MASS = "mass"


# No caller-selected paths, query options, methods, versions, redirects or hosts.
def endpoint(
    operation: Operation, reference: WorkspaceReference
) -> tuple[str, dict[str, str]]:
    ids = [
        quote(value, safe="")
        for value in (reference.documentId, reference.workspaceId, reference.elementId)
    ]
    suffix = f"d/{ids[0]}/w/{ids[1]}/e/{ids[2]}"
    match operation:
        case Operation.FEATURES:
            return f"/partstudios/{suffix}/features", {
                "includeGeometryIds": "false",
                "noSketchGeometry": "true",
            }
        case Operation.PARTS:
            return f"/parts/{suffix}", {
                "withThumbnails": "false",
                "includePropertyDefaults": "false",
            }
        case Operation.BODIES:
            return f"/partstudios/{suffix}/bodydetails", {
                "includeGeometricData": "false"
            }
        case Operation.MASS:
            return f"/partstudios/{suffix}/massproperties", {
                "massAsGroup": "true",
                "useMassPropertyOverrides": "false",
            }
    raise ValueError("Unsupported read operation")
