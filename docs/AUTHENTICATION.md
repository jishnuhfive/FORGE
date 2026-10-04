# Phase 2 authentication

Implemented OAuth identity and lifecycle; real Onshape verification is pending
human credentials. Phase 3 embedding, messaging and CAD context are not implemented.
See [Onshape evidence](ONSHAPE.md) and [security review](PHASE_2_REVIEW.md).

## Sequence and trust boundaries

1. The browser opens `/auth/onshape/start` at the top level. The backend creates
   independent 256-bit state and browser-binding values. PostgreSQL stores only
   their SHA-256 digests, with a ten-minute expiration. The binding is an HttpOnly
   cookie. A new attempt in the same browser invalidates its preceding state.
2. Onshape receives the client identifier, fixed registered callback, opaque state
   and optionally an operator-configured company ID. No secrets or return URLs
   are accepted from the browser.
3. The callback conditionally consumes matching, unexpired state in one database
   update, committed **before** contacting Onshape. A second callback cannot reuse
   it, including after a network failure. Restart sign-in after a failed exchange.
4. The backend exchanges the code via URL-encoded POST, then fetches only
   `/api/users/sessioninfo` with Bearer authorization. No CAD endpoint is called.
   Provider redirects are not followed; unexpected payloads fail closed. Known
   fields have strict types and size bounds; unused extra provider fields are
   discarded, following Onshape's forward-compatibility advice.
5. A user is upserted by `(Onshape user ID, configured API stack)`. Names are optional;
   email and the rest of the profile are discarded. The refresh token is encrypted.
   A fresh random Forge session replaces and revokes the initiating browser's old
   session. The callback redirects to a fixed Forge URL, removing codes from the
   current address. Responses are no-store with no-referrer policy.

There is no Forge password database, JWT login, browser token store, arbitrary
HTTP adapter, or configurable mock authentication mode. The browser receives only
minimal account status and a CSRF token; all provider credentials remain backend-only.

## Persistence

Alembic revision `0001_authentication` adds:

| Table                  | Purpose                                                                                                                           |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| users                  | Forge UUID, durable Onshape ID + stack, display name and login timestamps                                                         |
| onshape_authorizations | Encrypted refresh token, stack/company, reported scope if supplied, expiration, generation, verification and disconnection status |
| sessions               | SHA-256 digest of the random cookie value, user, lifetime, last mutation activity and revocation                                  |
| user_preferences       | Theme/units foundation; existing UI settings remain browser-local in Phase 2                                                      |
| oauth_states           | Expiring, browser-bound, one-use state digests                                                                                    |
| audit_events           | Fixed event/outcome codes and optional Forge user reference; no free-form payload                                                 |

UTC timestamps are integer Unix seconds. Foreign keys, unique identity constraints,
status/preference constraints and lookup/expiry indexes are defined in the migration.
Startup checks the revision and never creates, drops or repairs tables. Migrations
are an explicit operator command. Destructive downgrade is disabled.

## Tokens, refresh coordination and encryption

Access tokens exist only in a bounded (1,024 entries), process-local memory cache.
The database retains expiration metadata but never access-token ciphertext or
plaintext. Restarts and cache misses require a refresh. Separate workers may each
refresh once on a cache miss; they serialize through PostgreSQL `FOR UPDATE` locks
and always read the latest encrypted refresh token. There is no shared plaintext cache.

`TokenManager.get_valid_onshape_access_token(user_id)` checks the current grant and
its generation before using a cached token, with 30 seconds of expiration margin.
Refresh-token replacement, status, generation and audit are committed together.
An omitted replacement token preserves the prior token. Provider-reported scope is
stored verbatim, or the sessioninfo `oauth2Scopes` integer is tagged as a raw Onshape
bitmask when available; missing scope stays null. Cache entries are published
after commit and stale generations cannot be reused after disconnect/reconnect.

`invalid_grant` removes token material and marks the grant revoked. Service/network
errors mark authorization error and impose a 60-second retry delay. No automatic
retry loop runs. Corrupt ciphertext removes unusable material and requires reconnect.
An explicit CSRF-protected connection check verifies the identity still matches.
Its row lock prevents stale verification results overwriting a newer authorization.
“Connected” describes the last verification, not continuous monitoring; remote
revocation is discovered on a check or future authorized API use.

Encryption uses cryptography's reviewed Fernet authenticated encryption, through
MultiFernet, with a `fernet:v1:` format marker. Each encryption has a fresh IV and
authentication tag. `TOKEN_ENCRYPTION_KEY` is required to enable auth. A database
snapshot alone cannot decrypt tokens. Production keys belong in a secret manager,
separate from backups and database credentials, and must be recoverably backed up
under restricted access. Losing all keys requires reauthorization.

`TOKEN_ENCRYPTION_PREVIOUS_KEYS` optionally accepts comma-separated previous keys.
New encryption uses the primary key; reads try the key ring. For rotation, deploy a
new primary while retaining old keys, restart all workers, and refresh/reauthorize
all active grants before removing old keys. An operator must verify decryptability
with the new key before retirement; a bulk re-encryption command is planned.
Never remove a key merely because one account refreshed successfully.

There is an unavoidable external transaction boundary: Onshape can rotate a token
just before a database commit fails or the process crashes. Forge cannot roll back
that provider operation. Fail closed and reconnect if the saved grant is unusable.

## Sessions and CSRF

Session cookies contain 256 random bits, never a user ID or provider token. Database
storage is hashed, and authentication rotates the session. Defaults: eight-hour
absolute lifetime, one-hour idle lifetime. `last_seen_at` advances on successful
CSRF-protected account actions; read-only polling does not prolong a session.
Session revocation and expiration are checked for every account request.

Cookies are host-only, path `/`, HttpOnly, SameSite=Lax by default. HTTPS uses Secure
and the `__Host-` prefix; production requires HTTPS and complete configuration.
SameSite=None is opt-in and rejected without HTTPS. The OAuth binding cookie stays
Lax because authorization returns through a top-level navigation.

Every mutation requires both an exact Forge Origin (or exact-origin Referer fallback
when Origin is absent) and a session-bound HMAC CSRF token delivered by `/api/me`.
Null, missing or mismatched origins and missing/mismatched tokens are rejected.
Requests carry no user ID; ownership always comes from the valid session. Account
POSTs accept empty bodies only. There is no credentialed CORS allowlist or wildcard.
SameSite is defense in depth and is not the CSRF mechanism.

Logout revokes the current Forge session and clears its cookie. It retains the
Onshape grant and other sessions. Disconnect removes local refresh material,
invalidates access caches by generation, and retains the Forge session. Forge does
not claim it has remotely revoked a grant. The UI directs users to Onshape
**My account → Applications → Revoke**. No documented remote token-revocation endpoint
was established in this review, so none is guessed or called.

## Local setup with real credentials

Do not paste credentials into chat. These steps are performed by the human in a
private terminal/editor. No real `.env` is created by implementation/tests.

1. From the repository root run `cp .env.example .env` only if `.env` does not exist,
   then `chmod 600 .env`. Do not overwrite an existing environment.
2. Run `uv run --project apps/api --frozen python scripts/generate_dev_key.py`.
   It fills only the blank encryption-key placeholder without printing the key.
3. Install [mkcert using its official platform instructions](https://github.com/FiloSottile/mkcert),
   then run the following locally. The first command adds a local development CA
   to your trust store; that is a human-controlled setup step, not app startup.

   ```sh
   mkcert -install
   mkdir -p .certs
   mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1
   ```

   Keep `.certs` and mkcert's CA private. Never publish the CA private key.

4. Use the registration procedure in [ONSHAPE.md](ONSHAPE.md), then edit the ignored
   `.env` yourself. Set:

   | Setting               | Local value                                                                                                                     |
   | --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
   | ENVIRONMENT           | development                                                                                                                     |
   | APP_BASE_URL          | `https://localhost:5173`                                                                                                        |
   | DATABASE_URL          | `postgresql+psycopg://forge_local:local-development-only@127.0.0.1:5432/forge_local` for the public local Compose defaults only |
   | ONSHAPE_REDIRECT_URI  | `https://localhost:5173/auth/onshape/callback`                                                                                  |
   | ONSHAPE_CLIENT_ID     | identifier from **Keys and secret**                                                                                             |
   | ONSHAPE_CLIENT_SECRET | secret shown after application creation, or a regenerated secret                                                                |
   | TOKEN_ENCRYPTION_KEY  | generated by step 2; keep it stable across restarts                                                                             |
   | SESSION_SAMESITE      | lax                                                                                                                             |

   Leave provider URLs empty to use the documented HTTPS Onshape defaults. Leave
   company ID and previous keys empty for the initial standard-stack test.
   No `SESSION_SECRET` is needed: sessions are opaque random values, not signed
   client payloads, and the CSRF MAC uses the random session credential as its key.

5. Run:

   ```sh
   make setup
   make db-up
   make migrate
   make migration-check
   make dev-api
   ```

   In a second terminal at the repository root:

   ```sh
   make dev-web-https
   ```

   Open **https://localhost:5173** consistently. Do not mix localhost and 127.0.0.1
   during a login: the cookie and exact-origin checks intentionally distinguish them.
   The Vite HTTPS server proxies `/auth` and `/api` unchanged to FastAPI on loopback
   port 8000. This is the backend callback's browser-facing URL.

The ordinary `make dev` HTTP setup remains available without credentials. The UI lab
at `http://127.0.0.1:5173/#/lab` needs no API, database, encryption key or account.
If `.env` is configured for HTTPS, use the two HTTPS commands above for real login.
The cloud-app registration guidance requires HTTPS; Forge does not depend on the
HTTP-localhost exception for installed desktop applications. If your organization
blocks localhost registrations, use an organization-approved HTTPS development
origin and the same proxy paths; do not weaken redirect checks or TLS validation.

## Manual real-login verification (never in the default suite)

Use a dedicated development account. No CAD documents are read or changed.

1. Confirm the local certificate is trusted, PostgreSQL is healthy and migrations
   pass. Visit `/api/me` through the frontend origin; expect signed_out/configured true.
2. Click Continue with Onshape. Confirm the application name and profile-read
   permission. Deny once; Forge should explain denial without exception text.
3. Start again and approve. Expect the workspace and your display name. The current
   address must contain no OAuth code. Settings should show Connected.
4. Inspect only cookie **attributes**, not values: HttpOnly, Secure, path `/`,
   SameSite=Lax, `__Host-forge_session`. Do not save HARs, network response bodies,
   callback URLs, traces or screenshots containing codes/cookies/provider credentials.
5. Click Check connection. Restart only the API, retain the browser session, then
   check again: the empty access cache forces refresh. Expect verified status.
6. Sign out, reload, and confirm signed-out state. Sign in again; the account
   should be reused. Disconnect; verify the local-removal guidance and reconnect.
7. In Onshape My account → Applications revoke Forge. Click Check connection in
   Forge and expect revoked/reconnect state, then grant access again through Forge.
8. Record results and browser/version without secrets. Stop both servers with
   Ctrl+C, then `make db-down` to retain the database volume.

Live refresh replacement, profile payloads, grant errors and registration acceptance
remain **UNVERIFIED** until these steps run with genuine credentials.

## Embedded browsers and enterprise scope

The sign-in action uses top-level navigation. A separate-tab fallback remains
available if an iframe sandbox prevents that navigation. No tokens are transferred
via localStorage, URL fragments or `postMessage`. Opening another tab provides a
working standalone session; it does not magically unblock iframe cookies.

Future embedded deployment can set SESSION_SAMESITE=none on HTTPS, but browsers
may still block third-party cookies. Onshape explicitly calls out allowing them.
Real embedded Chromium/Firefox/WebKit compatibility is a Phase 3 gate, including
approved frame ancestors, browser policy, sandboxing and storage-access evaluation.
The three-engine tests in Phase 2 validate standalone behavior and synthetic OAuth
navigation only. They do not prove third-party-cookie compatibility.

A deployment has one operator-configured Onshape API stack and optional company ID.
No browser parameter can select a provider host or company. User identity and
credentials retain that stack; the same raw user ID on another stack is not silently
merged. Changing the configured stack or company invalidates use of old sessions/grants and requires new authentication.
Enterprise selection/company association is documented by Onshape, but live
enterprise support and multi-stack routing have not been tested or implemented.

## Operations and remaining launch work

Protect backups, use a least-privilege database role, and apply explicit retention
before public deployment: OAuth attempts one day; expired/revoked sessions 30 days;
security audit events 90 days, subject to the deployment's approved requirements.
No automated retention scheduler or account-erasure endpoint is implemented.
Operator-assisted account deletion must remove sessions, grants, preferences and
identity with a documented audit/backup policy. The UI does not pretend otherwise.

Ingress query/header/body limits, shared rate limits, HTTPS hosting, CSP, secret
manager deployment, restore tests, monitoring and account lifecycle operations
remain launch requirements. Ingress and APM must omit query strings, headers,
request bodies and response bodies for auth routes. Library HTTP/access logs are
suppressed by the app; deployment-side access logs need separate configuration.
