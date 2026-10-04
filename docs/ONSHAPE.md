# Onshape integration

## Phase 2 verification record — 2026-10-04

Primary sources reviewed:

- [Authentication](https://onshape-public.github.io/docs/auth/): public App Store
  applications require OAuth2; API keys do not authenticate application users.
- [OAuth2](https://onshape-public.github.io/docs/auth/oauth/): GET authorization at
  `https://oauth.onshape.com/oauth/authorize`; backend form POST at
  `https://oauth.onshape.com/oauth/token`; Bearer API requests; refresh grants and
  replacement refresh tokens; identity at `https://cad.onshape.com/api/users/sessioninfo`.
  The same redirect_uri accompanies authorization and code exchange. Permissions
  limit access. Enterprise authorization can carry `company_id`; users may choose
  their enterprise at authorization. Third-party cookies may need enabling.
- [Individual Developer Settings](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm)
  and [Company/Classroom/Enterprise Developer Settings](https://cad.onshape.com/help/Content/Plans/enterprise_settings_developer.htm):
  current registration fields, credentials, scope names, ownership, HTTPS callback
  requirements, and internal-user distribution.
- [REST introduction](https://onshape-public.github.io/docs/api-intro/): enterprise
  API base URLs can use a company hostname. Ignore undocumented response fields.
- [Official User API reference](https://github.com/onshape-public/go-client/blob/master/onshape/docs/UserApi.md):
  sessioninfo is the signed-in user's identity endpoint. The
  [official OpenAPI schema](https://github.com/onshape-public/go-client/blob/master/onshape/api/openapi.yaml)
  confirms its inherited `id`/`name` fields and optional `oauth2Scopes` integer.
  The live profile remains
  part of the credential-based smoke test; absent stable ID is a login failure.

Forge implements these protocol operations in Python/FastAPI. It does not copy
Express/Passport session storage, raw exception responses or sample state handling.
No documented PKCE support or direct remote grant-revocation contract was established;
neither is guessed. Confidential-client code exchange, one-use browser-bound state
and the fixed redirect protect the implemented flow. Reassess PKCE with Onshape
before public launch. Logout and local disconnect are distinct.

Earlier Forge documentation described OAuth as future work and speculated about
registration. Authentication now exists; extension registration, message handling,
document inspection and writes remain future phases. HTTPS is used locally for a
cloud application; the documented HTTP localhost exception is for installed desktop
apps and is not assumed to apply to Forge.

## Registration: exact human steps

Use a dedicated development account; do not share credentials in chat.

1. Sign into Onshape. Open your name menu → **My account** → **Developer** →
   **OAuth applications**. Company administrators can instead open the company's
   settings → Developer; ownership and API usage then belong to that organization.
2. Choose **Create new OAuth application**. Enter **Forge Development** as Name,
   **com.jishnuhiremath.forge.dev** as the suggested unique Primary format, and
   **Forge engineering workspace — account authentication** as Summary. The
   primary format is permanent; choose a different unique identifier if needed.
3. Select **Integrated Cloud App**. Enter Redirect URLs:
   **https://localhost:5173/auth/onshape/callback**.
4. Set OAuth URL to **https://localhost:5173/auth/onshape/start**. The documented
   local-work option is to leave it blank until deployment; Forge's own sign-in
   button still starts the flow. This field is Forge's entry point, not Onshape's
   `/oauth/authorize` endpoint. Leave External OAuth unconfigured.
5. Select only **Application can read your profile information (OAuth2ReadPII)**.
   Leave document read/write/delete, sharing and purchases unchecked in Phase 2.
6. Click **Create application**. Privately save the one-time secret as
   ONSHAPE_CLIENT_SECRET. Open **Keys and secret**, copy the client identifier into
   ONSHAPE_CLIENT_ID. Use secret regeneration there only if the original was lost.

These labels and navigation are from the official
[registration guide](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm).
Use [AUTHENTICATION.md](AUTHENTICATION.md) to create the ignored `.env`, generate
an encryption key, trust local HTTPS, start Forge and run the manual login test.
No right-panel extension is created in Phase 2.

Company administrators can assign a testing user through company settings →
Applications → Forge Development → Add users or teams → Add. Individual distribution
can use a private App Store entry and subscription if required by the account's
registration workflow; do not publish publicly. The creator can first test through
Forge's direct Continue with Onshape button. If grant availability is blocked,
verify ownership/user assignment with Onshape rather than fabricating success.
See [company distribution instructions](https://cad.onshape.com/help/Content/Plans/enterprise_settings_developer.htm).

## Permissions and stack policy

OAuth2ReadPII supports identity; Forge discards email and unnecessary profile data.
Permissions are configured on the application. If the token response supplies scope,
Forge retains it; otherwise a reported identity `oauth2Scopes` mask is retained as
`onshape_bitmask:<integer>` without interpreting undocumented bit assignments.
When neither is supplied, the field stays null; permissions are never invented.
OAuth2Read and OAuth2Write are planned for authorized CAD-read and CAD-write phases,
respectively. Changes will require a permissions review and renewed user consent.
No delete, share, purchase or internal scopes are justified now.

Server configuration defaults to the official standard OAuth and CAD API origins.
HTTPS Onshape hosts with fixed paths only are accepted; URL userinfo, query strings,
fragments and nonstandard ports are rejected. Enterprise API stack and company ID
are operator-configured and retained, never accepted from browser launch parameters.
Real enterprise/company association and cross-stack behavior are unverified.

## Future phases: unchanged integration boundaries

Phase 3 must verify real right-panel embedding and third-party-cookie behavior,
restricted frame ancestors, expected parent window, exact postMessage origin and
strict event schema/size/freshness. Context IDs are untrusted references, not proof
of resource access. Top-level sign-in remains available without exposing tokens.

Later adapters will use fixed high-level tools, documented versioned CAD endpoints,
independent object authorization, bounded retries and rate limits. CAD changes
require schema/unit/numeric validation, approval bound to a specific plan/document
version, sanitized audit and actual result verification. No model receives shell,
arbitrary HTTP or unrestricted Onshape execution. No CAD or AI calls exist in Phase 2.
