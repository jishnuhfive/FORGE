"""Fixed Onshape OAuth and identity endpoints, never a general HTTP tool."""

from urllib.parse import urlencode

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from forge_api.core.config import Settings


class ProviderError(Exception):
    def __init__(self, *, revoked: bool = False) -> None:
        super().__init__("Onshape authorization unavailable")
        self.revoked = revoked


class TokenResponse(BaseModel):
    # Onshape can add fields: strictly validate the consumed projection only.
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)
    access_token: SecretStr = Field(min_length=1, max_length=16384)
    refresh_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=16384
    )
    expires_in: int = Field(gt=0, le=86400)
    token_type: str = Field(pattern=r"^(?i:bearer)$")
    scope: str | None = Field(default=None, max_length=1024)


class Identity(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)
    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str | None = Field(default=None, max_length=200)
    oauth2_scopes: int | None = Field(
        default=None, alias="oauth2Scopes", ge=0, le=2**63 - 1
    )
    # Email and the rest of the profile are intentionally discarded.


class OnshapeProvider:
    def __init__(self, settings: Settings, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.onshape_client_id or "",
            "response_type": "code",
            "state": state,
            "redirect_uri": str(self.settings.onshape_redirect_uri),
        }
        # Permissions are configured in Onshape Developer Settings, not invented
        # runtime scope strings. Phase 4 additionally requires OAuth2Read;
        # registration and renewed consent are operator/user actions.
        if self.settings.onshape_company_id:
            params["company_id"] = self.settings.onshape_company_id
        return str(self.settings.onshape_authorization_url) + "?" + urlencode(params)

    def _token(self, values: dict[str, str]) -> TokenResponse:
        secret = self.settings.onshape_client_secret
        values.update(
            client_id=self.settings.onshape_client_id or "",
            client_secret=secret.get_secret_value() if secret else "",
        )
        try:
            response = self.client.post(
                str(self.settings.onshape_token_url), data=values
            )
            if response.status_code != 200:
                revoked = False
                if response.status_code in (400, 401):
                    try:
                        payload = response.json()
                        revoked = (
                            isinstance(payload, dict)
                            and payload.get("error") == "invalid_grant"
                        )
                    except ValueError:
                        pass
                raise ProviderError(revoked=revoked)
            return TokenResponse.model_validate(response.json())
        except httpx.HTTPError, ValueError, ValidationError:
            raise ProviderError from None

    def exchange(self, code: str) -> TokenResponse:
        result = self._token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": str(self.settings.onshape_redirect_uri),
            }
        )
        if result.refresh_token is None:
            raise ProviderError
        return result

    def refresh(self, refresh_token: str) -> TokenResponse:
        return self._token(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    def identity(self, access_token: str) -> Identity:
        try:
            response = self.client.get(
                str(self.settings.onshape_api_base_url) + "/users/sessioninfo",
                headers={"Authorization": "Bearer " + access_token},
            )
            if response.status_code != 200:
                raise ProviderError(revoked=response.status_code in (401, 403))
            return Identity.model_validate(response.json())
        except httpx.HTTPError, ValueError, ValidationError:
            raise ProviderError from None
