# Onshape integration

Current Phase 9 terminal-suppression evidence policy is recorded in
[the runtime review](PHASE_9_REVIEW.md). The current [v17 OpenAPI](https://cad.onshape.com/api/openapi)
exposes `featureStates` without a complete-coverage guarantee; the live disposable
three-feature target returned an empty map in both bounded sketch read modes.
An exactly empty object is explicitly unavailable state evidence, never inferred
OK/inactive. Nonempty maps require exact inventory coverage and strict entries;
partial/missing/null/malformed/extra maps reject. The documented explicit feature
`suppressed` Boolean and fixed partial suppression update govern this sole operation,
with all existing structural, body-output, pinned-version and approval safeguards.
No provider query, scope, host, write authority or FeatureScript capability expands.

The same current schema makes auxiliary `suppressionState` optional but does not
define null semantics. The live target has null at all three positions, explicit
`suppressed=false`, and missing parent/configured suppression Booleans. Explicit
policy permits null to supply no evidence; omitted Booleans are not inferred.
Strict supported base objects remain allowed; configured/expression/parent and
unknown specializations reject. The subsequent explicit guard policy uses a complete
supported top-level structure for missing parent evidence and the independent pinned
configuration endpoint for missing configured evidence. Both arrays must be present
and empty, with matching source and no skew; explicit conflicts still reject.
No missing-to-null/false conversion is used. The older v9 omitted-default guidance
is not the sole justification. Raw fields and evidence modes remain fingerprinted.

The current v17 `BTMicroversionId-366` schema makes `theId`, `ambiguous` and `deleted`
optional. Forge still requires a present marker object and exact returned `theId`.
Bodydetails supports `wvm=m`; [Onshape architecture](https://onshape-public.github.io/docs/api-intro/architecture/)
establishes immutable document microversions. For this operation, both absent flags
are recorded as `EXACT_PINNED_ID_FLAGS_UNAVAILABLE` only after fixed pinned transport
and head bracketing prove the requested revision. No false values are inferred.
Both explicit false flags give `EXPLICIT_CLEAN_FLAGS`; mixed/true/null/wrong-type
flags reject. One SOLID and `NO_ERROR` remain required before and after mutation,
with the after-ID equal to the new acknowledged marker. The runtime review records
the live GET-only coverage; neither human write-conformance gate is proven.

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
registration. Authentication now exists; the Phase 3 launch bridge is now implemented. A narrow client selection adapter is implemented;
document REST reads are implemented and live verified in Phase 4; writes remain future work. HTTPS is used locally for a
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
No right-panel extension was created in Phase 2. Phase 3 instructions for the
existing application are in [ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md).

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
OAuth2Read is now required for Phase 4 CAD reads. OAuth2Write remains deferred
to a separately authorized CAD-write phase. Changes will require a permissions review and renewed user consent.
No delete, share, purchase or internal scopes are justified now.

Server configuration defaults to the official standard OAuth and CAD API origins.
HTTPS Onshape hosts with fixed paths only are accepted; URL userinfo, query strings,
fragments and nonstandard ports are rejected. Enterprise API stack and company ID
are operator-configured and retained, never accepted from browser launch parameters.
Real enterprise/company association and cross-stack behavior are unverified.

## Current Phase 3 and future integration boundaries

Phase 3 must verify real right-panel embedding and third-party-cookie behavior,
restricted frame ancestors, expected parent window, exact postMessage origin and
strict event schema/size/freshness. Context IDs are untrusted references, not proof
of resource access. Top-level sign-in remains available without exposing tokens.

Later adapters will use fixed high-level tools, documented versioned CAD endpoints,
independent object authorization, bounded retries and rate limits. CAD changes
require schema/unit/numeric validation, approval bound to a specific plan/document
version, sanitized audit and actual result verification. No model receives shell,
arbitrary HTTP or unrestricted Onshape execution. No CAD or AI calls exist in Phase 2.

## Phase 3 evidence — 2026-10-10

The human verified real Phase 2 OAuth login, genuine Part Studio right-panel embedding,
an authenticated iframe display name and valid workspace launch context. The existing
Action URL is unchanged. Earlier composer and ancillary-metadata incompatibilities
are repaired; CAD IDs, server trust and revision validation remain strict.

Official docs establish the Element right panel location, Action URL replacement
parameters, applicationInit, show and SELECTION message names, but do not publish an
inbound selection payload schema. The real sanitized captures establish a top-level
selections array with one ENTITY/FACE or ENTITY/EDGE reference and undefined
occurrencePath, or an empty array when cleared. The human supplied the corrected
authoritative FACE capture and confirmed the earlier EDGE-valued sample was mislabeled.
The corrected structure matches the existing parser without implementation changes.
These samples do not establish multi-selection/assembly/version behavior.

The strict adapter atomically replaces or clears memory-only selection. Unsupported
trusted content removes old references and shows unavailable. Exact origin/source
checks precede parsing; no outgoing highlight command, CAD request or new scope exists.
DEV-only sanitized diagnostics remain available, redacted and excluded from production.
Explicit version revisions are retained but never initialized as workspaces.

[ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md) records sources, the exact unchanged
registration, bounded contract, lifecycle, browser/session limitations and live retest.
[PHASE_3_REVIEW.md](PHASE_3_REVIEW.md) records the passing quality gate and resolved
FACE evidence. Phase 3 is complete. Phase 4 real REST verification passed; its
commit/push is authorized after the complete final repository gate. Phase 5 implements a read-only workspace Part Studio inspector; its final real
live verification passed on 2026-10-14.

## Phase 4 official REST contract and permission update

The live [Glassworks OpenAPI contract](https://cad.onshape.com/api/openapi), reviewed
2026-10-10, advertises **v17**. Its features, parts-in-element, bodydetails and
massproperties GET operations all require **OAuth2Read**. The existing Phase 2
registration instructions above are historical: the profile-only grant must now
be expanded to document read and renewed. Do not add write permission.

Open the existing Forge Development OAuth application → Permissions, retain
OAuth2ReadPII, enable **Application can read your documents (OAuth2Read)** and save.
Revoke the old grant in My account → Applications if necessary, then reconnect
through Forge and approve the updated read consent. Do not recreate the extension,
change its Action URL or regenerate the secret. A token response's explicit scopes
are used when available; the stored identity bitmask remains uninterpreted.

The full endpoint allowlist, schema observations, model choices, exact user steps
and evidence limitations are in [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md). Browser launch
origin never selects a backend host. Only the standard CAD stack and workspace
Part Studios are supported for these reads. Four separate requests cannot prove an
atomic snapshot; mass units remain provider-native/unverified. The user reports
final real success for 2 features, 1 part and 1 body. Mass now parses successfully
and displays **Mass unavailable; material/density may be missing**, with the old
invalid-response message gone. OAuth2Read authorization is verified by these reads.
The final live sign capture establishes zero nominal mass, negative lower tolerance,
positive upper tolerance, `hasMass=false` and positive missing count. The previous
blanket negative-component rule was the exact rejection. The verified v17 order
is `[nominal, lower, upper]`; its mass, volume and periphery (surface area) descriptions
identify nonnegative physical nominal quantities, distinct from tolerance limits.
Forge now requires strict finite triples, a nonnegative nominal and ordered bounds
for these three fields. This nominal constraint is Forge's physical validation,
not a claim that OpenAPI imposes numeric minima on tolerance limits. Centroid,
inertia, principal-inertia components and principal axes remain unchanged.
Official mass-tool documentation describes density-dependent calculations that
omit parts without assigned material. A false mass flag now suppresses the physical
estimate, while retaining valid volume and the missing count. The mass section
parses successfully; the proof UI reports mass unavailable instead of malformed
provider data. Positive missing counts are valid; partial assigned mass remains
unverified. No material assignment is required merely to parse the provider response.
Useful bounded DEV diagnostics remain, without validator replay or raw numeric
values. The user also verified a separate empty Part Studio returned 0 features,
0 parts, 0 bodies and no mass-property bodies, clearing the earlier snapshot.
No further diagnostic capture or live retest is currently required. Actual live
browser/version was not supplied; cross-engine automated coverage is separate.

## Phase 5 official schema review and inspector scope

The public [live OpenAPI contract](https://cad.onshape.com/api/openapi) was fetched
again on 2026-10-13. It still advertises v17, schema
`1.222.90730-c8d74e607a47`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
It establishes exact boolean/string/enum value fields, quantity expression strings,
query-list entries, feature namespaces and `BTPartMetadataInfo` fields.
The [feature guide](https://onshape-public.github.io/docs/api-adv/featureaccess/)
and [standard library](https://cad.onshape.com/FsDoc/library.html#chamfer)
support the narrow Sketch/Extrude/Fillet/Chamfer labels. They do not establish
universal parameter interpretation, entity-query cardinality or assembly support.

The inspector labels query-entry count only, not resolved entity count. Quantity
expressions are not evaluated. Missing optional fields remain unknown; no default
false, zero, empty geometry or active suppression is inferred. Provider parameters
can include inactive options, which the UI explicitly cautions about.

The four fixed GETs, query flags, default configuration, end-of-list evaluation,
OAuth2Read permission and unverified unit policy remain unchanged. Aggregate mass
cannot be assigned to individual parts. Topology counts derive only from nonempty
returned arrays; unverified empty collections remain unknown. FACE/EDGE selection
is separate from REST evidence. Assembly inspection,
version/microversion reads, configurations, rollback-state synchronization and
selection ownership mapping remain unsupported. No extension registration or
permission change is needed for Phase 5. See [PHASE_5_REVIEW.md](PHASE_5_REVIEW.md)
for exact live inspector steps; Phase 4 live success does not validate this new UI.

### Phase 5 live topology investigation — 2026-10-14

The current official v17 OpenAPI was fetched again with the same version/hash above.
`BTExportModelBody-1272` makes faces/edges/vertices optional and gives no guarantee
that an empty array is authoritative topology absence. The documented
`includeGeometricData` default is true; its generic description and the official
[body-details guide](https://onshape-public.github.io/docs/api-adv/partstudios/)
do not specify which topology arrays false omits or empties. Forge's fixed false
option, endpoint and bounds remain unchanged; no larger geometry read is justified.
Missing/null already stayed unknown. The repaired normalizer also treats empty
arrays as unknown instead of unconditional zero. The final sanitized live capture established present arrays with 6 face entries
and empty edge/vertex arrays. The final UI correctly shows 6 / Unknown / Unknown.
The user verified this behavior along with feature, part and physical inspection.
See [PHASE_5_REVIEW.md](PHASE_5_REVIEW.md) for the completed live evidence.

### Phase 5 browser lifecycle repair — 2026-10-14

Rechecked current [client messaging](https://onshape-public.github.io/docs/app-dev/messages/)
and the [right-panel sequence](https://onshape-public.github.io/docs/app-dev/messages/element-right-panel/).
applicationInit is once per startup; panel close destroys the extension and reopening
starts a new frame. show is a focus cue, with no new context or documented selection
reset/replay requirement. Ordinary browser visibility/focus in the same live frame
now preserves validated context, verified selection and captured inspector evidence.
No new bridge message, initialization replay, automatic CAD request or polling was
added. Exact origin/parent checks and real navigation/context/session clearing stay.
The user verified same-frame browser-tab preservation, FACE/EDGE/clear, local
filtering and Part Studio switching with empty 0/0/0 results. The topology repair
and useful bounded DEV diagnostics are preserved. See the Phase 5 review for the
final live evidence; no further capture is required for Phase 5.
