"""The same strict final schema for both providers, with content-free failures."""

from pydantic import ValidationError

from forge_api.integrations.onshape.client import bounded_json

from .diagnostics import Reason, validation_details
from .models import AiError, ModelAnswer


def parse_model_answer(content: str) -> ModelAnswer:
    try:
        value = bounded_json(content.encode())
    except ValueError, UnicodeError:
        raise AiError(
            "invalid_response", reason=Reason.PROVIDER_MALFORMED_JSON
        ) from None
    try:
        return ModelAnswer.model_validate(value)
    except ValidationError as error:
        reason, field = validation_details(error)
        raise AiError("invalid_response", reason=reason, field=field) from None
