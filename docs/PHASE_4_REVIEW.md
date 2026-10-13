# Phase 4 review — complete

Review updated: 2026-10-13. The user reports the final real Onshape REST test
**PASS**: **2 features, 1 part, 1 body**, with mass successfully parsed and safely
unavailable. Switching to a separate empty Part Studio returned **0 / 0 / 0** and
**No mass-property bodies returned**, without retaining the earlier snapshot.
OAuth2Read authorization, four real reads and stale-context clearing are verified
by that external report. The complete final repository gate and final source
review passed. A single Phase 4 commit and normal push to existing origin/main
are explicitly authorized; publication hashes are recorded in the final handoff.
Earlier diagnostic sections are evidence history, superseded by this closeout.
Phase 5 is not authorized and has not begun.

## Recovery and scope

The initial tree was clean and HEAD was exactly
`2f0088d05e50d3613a3c2e01183b90de61b95a0e` (Phase 3). The continuation instruction
was read and the current diff, added files and tests were inspected. All partial
Phase 4 work was preserved. Work resumed with backend fixture/type/lint cleanup,
frontend tests, browser verification and documentation; nothing was reset or stashed.

This phase adds backend-only CAD reads and a compact proof interaction. Phase 2
sessions, encryption, refresh coordination and Phase 3 context validation remain
in place. The only Phase 3 markup repair is moving the selection live-region role
inside its definition-list value, after the new embedded accessibility check found
that applying `role=status` directly to `dd` broke its semantics.

No AI calls, CAD mutation capability, FeatureScript execution, exports, assembly
operations, inspector UI, database migrations or dependency changes are included.

## Official contract evidence

Only official Onshape documentation and the live Glassworks contract were used.
On 2026-10-10, the Explorer's public JavaScript selected `/api/openapi`, whose
`servers` advertised `https://cad.onshape.com/api/v17` as Current. The schema's
`info.version` was `1.222.90730-c8d74e607a47`. Its SHA-256 was
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
The downloaded public schema is outside the repository, not a CAD fixture.

Sources:

- [Live OpenAPI contract](https://cad.onshape.com/api/openapi) and
  [Glassworks Explorer](https://cad.onshape.com/glassworks/explorer/).
- [Part Studio guide](https://onshape-public.github.io/docs/api-adv/partstudios/)
  for feature and mass-property examples. Its v9 examples do not override the
  currently advertised version.
- [OAuth](https://onshape-public.github.io/docs/auth/oauth/),
  [registration and permission settings](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm),
  [response codes](https://onshape-public.github.io/docs/api-adv/errors/), and
  [API limits](https://onshape-public.github.io/docs/auth/limits/).

`integrations/onshape/contracts.py` isolates the API version, reviewed schema
version, media type, origin policy, operations and path/query templates. No runtime
browser setting selects any of these. All four operations require `OAuth2Read`.

## Allowlist

All CAD requests use **GET**, `Authorization: Bearer` injected on the server,
`Accept: application/json;charset=UTF-8; qs=0.09`, `Accept-Encoding: identity`,
and `User-Agent: Forge/0.4 CAD-Read`.

| Operation                   | Path under `/api/v17`                                 | Fixed options                                           |
| --------------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| getPartStudioFeatures       | `/partstudios/d/{did}/w/{wid}/e/{eid}/features`       | `includeGeometryIds=false`, `noSketchGeometry=true`     |
| getPartsWMVE                | `/parts/d/{did}/w/{wid}/e/{eid}`                      | `withThumbnails=false`, `includePropertyDefaults=false` |
| getPartStudioBodyDetails    | `/partstudios/d/{did}/w/{wid}/e/{eid}/bodydetails`    | `includeGeometricData=false`                            |
| getPartStudioMassProperties | `/partstudios/d/{did}/w/{wid}/e/{eid}/massproperties` | `massAsGroup=true`, `useMassPropertyOverrides=false`    |

The official defaults apply otherwise: default configuration, end-of-list rollback
evaluation, no extra surface/composite-body inclusion. These calls do not move the
rollback bar. The live browser's active configuration/rollback position is not
established by the Phase 3 launch contract; the UI labels default configuration.
No arbitrary query options, links returned by Onshape, methods or paths are used.

## Authentication, ownership and origin

`GET /api/onshape/part-studio/snapshot` accepts exactly four query parameters:
`documentId`, `workspaceId`, `elementId`, `revisionKind=workspace`. IDs have the
24-lowercase-hex shape already validated by Phase 3 and used by the official
Explorer's URL parser. They remain opaque: no timestamp or ownership is inferred.
Duplicate/missing/unknown fields are rejected without echoing values. Version and
microversion contexts return `unsupported_context`; they never become workspaces.
Part Studio endpoints let Onshape authorize and evaluate the actual element type.

Ownership comes exclusively from the existing unexpired, unrevoked Forge session.
Every resource uses that user's TokenManager, configured stack/company and current
grant generation. Expired access tokens use the existing serialized refresh and
encrypted refresh-token replacement. No user/grant/session identifier is accepted
as request data. Onshape authorizes each exact document with that user's token;
a validated browser reference alone grants no access. Completed data is discarded
if the owning session was ended or its authorization disconnected/revoked in flight.

Although GET is read-only, it spends provider quota. This endpoint additionally
requires the existing session-bound `X-CSRF-Token`. It rejects mismatched/duplicate
Origin and cross-site Fetch Metadata. Same-origin GET can omit Origin/Referer under
Forge's no-referrer policy, but cannot omit the secret header. Credentialed CORS
is not enabled. Existing account mutation CSRF policy is unchanged.

The CAD adapter accepts only normalized `https://cad.onshape.com` from server
configuration; its base must end in `/api`. HTTPS, exact hostname, no URL credentials,
nonstandard port, path/query/fragment tricks, whitespace/control characters or
backslashes are enforced. Standard explicit port 443 normalizes to the same origin.
Enterprise authentication settings remain supported by Phase 2 as before, but CAD
reads there return `unsupported_provider` until separately reviewed. Localhost,
private-network hosts and arbitrary external hosts cannot become CAD destinations.
Redirects are **never followed**, including same-host redirects. Transport ignores
proxy environment variables; TLS verification remains enabled.

## Provider and Forge model boundary

`models.py` defines small strict provider projections with bounded fields and
independent Forge summaries. `normalize.py` is the only transformation boundary.

- Features: ID, type, name, suppression, optional parameter ID/provider-type
  summaries, completeness, rollback index, serialization version and skew flag.
  Counts are withheld if completeness is absent or false. Default origin/plane
  features are not counted as user features.
- Parts: ID, name, description, part number, body type, state, mesh flag and
  microversion. No arbitrary custom property is promoted into the domain model.
- Bodies: body ID/type and optional face/edge/vertex counts. No geometric reasoning.
  Body details' microversion uses the documented object `microversionId.theId`,
  unlike the string microversion in mass/parts. Ambiguous/deleted IDs are not used.
- Mass: hasMass, missing-mass count, nominal/lower/upper mass and volume,
  centroid/inertia/principal-inertia arrays retained in provider order. Scalar
  triples follow the documented calculated/minimum/maximum ordering. Present
  mass, volume and periphery (surface area) must be finite numeric triples with
  nonnegative physical nominal and ordered bounds; lower tolerances may be negative.
  Missing/null optional estimates remain unknown. A false mass flag suppresses
  the normalized physical mass, and partial missing contributions cannot produce
  an available-mass claim in the proof UI. Periphery is validated but not promoted
  to a new summary.

The reviewed endpoint schema does not provide a sufficiently explicit unit/frame
contract for all these fields. Forge records `provider_native_unverified` and
performs no unit conversion or matrix/frame interpretation. No mass values are
rendered in the proof UI. This is not engineering validation or certification.

`ProviderDocument` retains the bounded original JSON only in request-local server
memory (with representations suppressed), alongside the typed normalization and
source microversions. Unknown feature/parameter fields remain available during
that read without entering business logic. This data is neither logged, persisted,
cached nor serialized to the browser. It is released at request completion; a
future consumer must explicitly design any longer-lived private-data handling.
The internal snapshot records provider API/schema metadata; the external proof
contract is `forge-cad-read-v1`.

## Snapshot, freshness and resilience

Four sequential reads preserve independent section outcomes. Optional body/mass
failures do not erase successful feature/part data. Authorization/permission and
rate/quota failures stop remaining calls to avoid waste; those sections carry the
same blocking state. Other section failures allow remaining resources to be tried.

There is no CAD cache. Each admitted click fetches fresh data. `captured_at` is UTC
completion time, not a claim of a transactionally consistent document state.
Multiple source microversions or a provider skew flag produce `mismatch`. Otherwise
consistency remains `unverified`, even when available IDs match, because the four
workspace reads are not an atomic snapshot. No version or microversion pinning is
silently inferred. Microversion IDs are retained server-side, not in proof output.

There are **zero automatic CAD retries**, including 401, 403, 429 and 5xx. A 401
forgets the ephemeral access token; a subsequent explicit action can trigger the
existing refresh path. It does not automatically revoke a grant or replay the CAD
request. Transient OAuth refresh failures retain Phase 2's 60-second retry delay.

The per-process admission gate permits one in-flight read per user, at most 32
active users, and a five-second minimum between completed requests. A bounded
1,024-entry cooldown map stores only Forge user IDs and deadlines, no CAD data.
429's documented delta-seconds Retry-After is parsed without signs/date/text and
clamped to 1–86,400 seconds; a missing/invalid header yields a 60-second server
cooldown. No polling or timer-triggered fetch exists. The browser disables repeat
clicks while pending and through the relevant cooldown. Shared deployment-wide
quotas across multiple workers remain a production deployment requirement.

Connect/read/write/pool timeouts are 3/8/3/2 seconds. Response reading checks a
20-second elapsed budget on each received chunk in addition to transport timeouts.
The size limit is 2 MiB per resource, with Content-Length preflight and streamed
byte counting. Encoded/compressed payloads are rejected. JSON has a 32-level depth,
100,000-node and bounded string/key budget; duplicate keys, malformed JSON and
nonfinite numbers are rejected. Collection limits constrain model expansion.
These are deliberate Phase 4 limits, not silently truncated successful results.

## Error mapping and observability

| Situation                                   | Safe state/code                                         |
| ------------------------------------------- | ------------------------------------------------------- |
| Signed out / expired Forge session          | HTTP 401 `connection_required`                          |
| Disconnected/revoked grant / provider 401   | unauthorized / `connection_required`                    |
| Explicit known OAuth scopes lack OAuth2Read | unauthorized / `read_permission_required`               |
| Provider 403, OAuth2Read explicitly known   | forbidden / `document_forbidden`                        |
| Provider 403, scope absent/uninterpreted    | forbidden / `permission_or_access_required`             |
| Provider 404                                | not_found / `not_found`                                 |
| Provider 429 / 402                          | rate_limited / `rate_limited` or `quota_exceeded`       |
| Timeout / network or other provider failure | provider_failure / fixed timeout/unavailable code       |
| Redirect / malformed or incompatible JSON   | provider_failure / fixed redirect/invalid-response code |
| Too large / unsupported configured stack    | unavailable / fixed size/provider code                  |

The Phase 2 `onshape_bitmask:<integer>` scope is not decoded using guessed bit
assignments. Absence of a scope claim does not assert read access. A 403 is never
relabeled as not found. Missing read scope does not destroy encrypted credentials.

The `forge.onshape.read` Python logger emits structured LogRecord fields: operation,
outcome, HTTP status class, duration milliseconds, retry count (zero), and a fresh
server-generated request ID. Deployment logging must enable INFO on this logger
and serialize only those fields. No exception objects, provider URLs, tokens,
full IDs, feature text or bodies are included. Proof results expose the matching
random reference, never a provider-derived request ID. `no-store`, `no-referrer`
and `nosniff` apply to all responses. Ingress/APM must also omit CAD query strings,
request/response bodies, cookies and headers; app-side suppression cannot configure
an external ingress.

## Proof UI

CAD Context offers **Read CAD data** for authenticated workspace context. It shows
loading, feature/part/body counts, mass availability, per-section safe errors,
read time and consistency caveat. Context/account changes remount the reader and
abort/discard old results. Aborting a browser request may still leave its bounded
synchronous backend reads running until completion. Page hiding and stale Phase 3 context clear results.
Versions, known non-Part-Studios and disconnected accounts cannot issue reads.

DEV alone lazy-loads **DEVELOPMENT ONLY · REST diagnostic**. Its explicit copy button
projects only schema tag, random request ID, timestamp, consistency and fixed
section status/code/cooldown fields. It omits counts, raw data, names, IDs and secrets.
If clipboard access fails or is absent, the same serialized report appears in a
read-only, selectable **Sanitized read diagnostic** text area beneath the copy
button and manual-copy message. Output is capped at 2,000 characters; oversized
reports fail closed. The text area fits the narrow panel and has a bounded height.
Production compilation eliminates the diagnostic module and identifying strings.
This UX repair does not change REST reads, sanitization or the mass parser.
Targeted fallback verification passed: 7 component tests, 12 Playwright checks
across Chromium/Firefox/WebKit (including 320px manual selection and production
exclusion), frontend lint, TypeScript checking and the production build. The
backend and full suites were not rerun for this development-only repair.

## Automated verification

### Live mass rejection investigation

The real sanitized report at `2026-10-10T23:49:50.973299+00:00` shows successful
features, parts and bodies and mass `provider_failure / invalid_response`. This
code alone cannot identify the rejected field or distinguish response metadata,
JSON parsing and strict normalization failures.

The public OpenAPI schema was fetched again from the official endpoint. It still
advertises v17, version `1.222.90730-c8d74e607a47`, with the same SHA-256 recorded
above. `BTMassPropertiesBulkInfo.bodies` is an object whose records are
`BTMassPropertiesInfo`; `microversionId` is a string. Mass, volume, periphery,
centroid, inertia and principal inertia are numeric arrays; principal axes are
`BTVector3d-389` objects with numeric x/y/z and optional type text. The endpoint
documents calculated/minimum/maximum ordering for triples, but does not specify
array cardinalities. The linked guide demonstrates `-all-`, scalar triples,
9 centroid values, 27 inertia values, 3 principal inertia values and 3 vectors.
The existing mass/volume parser already supports that nested triple representation.
The available official evidence therefore does **not** prove a specific parser
bug responsible for this live rejection. No parser or tolerance rule was changed.

Following the authorized diagnostic path, only a development backend imports
`onshape/dev/mass_structure.py`. On mass `invalid_response`, it describes known
field presence, types, array lengths and element categories, plus at most eight
fixed validation reason codes. It samples the aggregate record if present,
otherwise the first record, and the first principal-axis vector. No body keys,
unknown field names, scalar values, exception inputs/messages/context, URLs or
credentials are copied. The compact header is capped at 4,096 characters.

After the final session/grant check, DEV alone attaches `X-Forge-Mass-Structure`
to the existing response. The count/status JSON contract, four GETs, rate gate and
normalization remain unchanged. Successful mass reads produce no structure header.
Production/test backends do not enable the builder or emit the header. The DEV
frontend dynamically imports a fixed-vocabulary validator, rejects unexpected
fields/values, caps formatted output at 8,192 characters, and displays a read-only
**Sanitized mass response structure** text area. Production compilation excludes
both validator and UI. The existing sanitized read report is unchanged.

Live capture: reload the existing development Forge panel; open **View CAD
context**, click **Read CAD data**, then scroll below **DEVELOPMENT ONLY · REST
diagnostic** to **DEVELOPMENT ONLY · Mass response structure**. Select the text in
**Sanitized mass response structure**, use Select All within that text area and
copy manually. Share that report, the existing sanitized read diagnostic, visible
counts/status and browser/version only. If mass succeeds, record the displayed
mass status instead. If no structure box appears while mass still reports
`invalid_response`, report that fact; do not copy network headers or responses.
Another sanitized structure capture is required before a provider compatibility
change can be justified. Phase 5, committing and pushing remain unauthorized.

Targeted verification for this investigation: **158 backend tests** (all existing
134 REST/security tests plus 24 diagnostic tests), **76 CAD frontend tests** and
**15 Playwright checks** across Chromium/Firefox/WebKit passed. These include the
final disconnect/grant boundary, privacy, production exclusion and 320px manual
selection. Format, frontend/backend lint, TypeScript, mypy (39 files) and production
build passed. Production JavaScript/CSS hashes are unchanged from the prior repair.
The expensive full Phase 4 gate was not rerun.

Files changed for this investigation:

- Backend: `apps/api/src/forge_api/integrations/onshape/client.py`, `routes.py`,
  `dev/__init__.py`, `dev/mass_structure.py`, and `apps/api/tests/test_mass_structure.py`.
- Frontend: `apps/web/src/cad/api.ts`, `api.test.ts`, `dev/ReadDiagnostic.tsx`,
  `dev/ReadDiagnostic.test.tsx`, `dev/massStructure.ts`, `dev/massStructure.test.ts`,
  and `__fixtures__/massStructure.ts`.
- Browser/tool checks: `tests/e2e/extension.spec.ts` and `tsconfig.tools.json`
  (Vite environment types for imported frontend test fixtures).
- Documentation: this review, `ARCHITECTURE.md`, `SECURITY.md`, `ONSHAPE.md`,
  `DEVELOPMENT.md`, and `ROADMAP.md`.

The provider `models.py`, `normalize.py`, `contracts.py` and snapshot `service.py`
were inspected and left unchanged. No dependencies or lockfiles changed.

### 2026-10-11 live structure follow-up — exact scalar still pending

The user supplied the authoritative DEV mass structure: aggregate record, mass /
volume / periphery arrays of 3 numbers, centroid of 9, inertia of 27, principal
inertia of 3, and three xyz principal-axis objects with observed type text. The
error is `schema_validation`, with the coarse `bodies / invalid_bounds` code.
The public v17 OpenAPI and official guide were rechecked; the schema version and
SHA-256 are unchanged.

Source tracing establishes that only `MassBody.scalar_bounds` raises the mapped
`value_error`. It checks **mass and volume only**. `normalize.estimate` is also
called for those two fields only. Principal inertia, centroid and inertia are
retained in provider order and never passed through a scalar bounds check.
Periphery and principal axes are currently ignored by the provider projection and
remain request-local; this follow-up does not introduce their normalization.
With both scalar lengths verified as 3, the error must come from a negative scalar
component or a triple failing the existing lower ≤ nominal ≤ upper check.
The supplied structure does not disclose which scalar fails or which predicate.
It therefore cannot justify a field-specific compatibility correction yet.

The confirmed diagnostic bug was loss of field identity: model-level validation
locates the bounds error on the body, and the prior sanitizer could name only
`bodies`. Following the user's explicit fallback instruction, the DEV builder now
uses that request-local error location to select the failing record and reruns the
**same unchanged MassBody validator** with only mass, then only volume. It emits
`mass / invalid_bounds`, `volume / invalid_bounds`, or both, only when that field
fails the existing check. Private body keys are removed by location position, so a
body key matching a safe field name cannot be mistaken for the validation field.
No raw values or exception messages/inputs are emitted. The 8-reason and output
limits remain unchanged. Production never imports or enables this replay.

A new fixture matches all live-observed shapes using invented numbers. It proves
the existing parser accepts the structure and keeps principal inertia components
separate from scalar estimates. Tests independently reproduce mass and volume
bounds failures, both failures, failures outside the sampled aggregate, private
body-key collisions, unchanged snapshot errors and DEV-only headers. The frontend
structure fixture now demonstrates `mass / invalid_bounds` with the existing UI.

**Another sanitized capture is required; no semantic parser repair is claimed.**
Reload the development Forge panel, open **View CAD context**, click **Read CAD
data**, and manually copy **Sanitized mass response structure** below the REST
diagnostic. Share the `validation` section (safe field names and codes only), or
the whole sanitized structure. No provider response or CAD values are needed.
Production models, normalizer, endpoint, snapshot and security controls are
unchanged. No commit, push or Phase 5 work is authorized.

This follow-up changes only `onshape/dev/mass_structure.py`,
`apps/api/tests/test_mass_structure.py`, the frontend
`cad/__fixtures__/massStructure.ts`, and this review plus architecture, security,
Onshape, development and roadmap documentation.

Verification for the field-localization follow-up: **173 backend tests** (134
existing REST/security tests and 39 diagnostic tests), **76 CAD frontend tests**,
and **6 targeted browser checks** (safe scalar name/manual capture and production
exclusion in Chromium/Firefox/WebKit) passed. Format, lint, TypeScript, mypy
(39 files) and production build passed. Production asset hashes remain unchanged.
No full phase gate, database operation, dependency change, commit or push was run.

### 2026-10-12 mass-only follow-up — exact predicate still pending

The newest authoritative sanitized capture reports `mass / invalid_bounds` only;
mass is a three-element finite-number array, and volume no longer fails.
The exact reachable rejection in `MassBody.scalar_bounds` is:

```python
any(v < 0 for v in values) or not values[1] <= values[0] <= values[2]
```

Zero and equality are accepted. No strict-positive, nonzero-lower, tolerance
width, epsilon, symmetry, `hasMass` or `massMissingCount` interaction exists.
The sanitized input does not identify which disjunct is true. The current code
does impose a separate negative-component guard; the public contract does not
describe negative tolerance limits or sentinel semantics. It is retained pending
evidence, not represented as a verified Onshape requirement.

A fresh public [OpenAPI](https://cad.onshape.com/api/openapi) retrieval verified
version `1.222.90730-c8d74e607a47`, server `/api/v17`, SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
`getPartStudioMassProperties` specifies calculated, minimum and maximum positions.
The official [Part Studios guide](https://onshape-public.github.io/docs/api-adv/partstudios/#get-the-mass-properties-of-a-part-studio)
demonstrates this `[nominal, lower, upper]` ordering for mass, volume and periphery.
Forge's mapping was already correct. `normalize_provider_scalar_estimate` now
makes the existing interpretation explicit in one named helper; no values are
reordered and no production validation is changed. Periphery and axes remain
request-local raw fields; centroid/inertia and principal-inertia components keep
their existing distinct handling and `provider_native_unverified` units.

The DEV builder now enriches only a field-specific scalar failure with
`failedPredicates`: fixed `negative_component`, `bounds_order` or
`unexpected_length` codes. For a finite triple, `comparisons` contains exactly
`position0_vs_position1`, `position0_vs_position2`, and
`position1_vs_position2`, each `greater`, `equal` or `less`. It uses the same
strict finite-number conversion as the model and the failed request-local record,
never the sampled aggregate or exception messages. No operands, sign values,
private keys, IDs, credentials, URLs or raw payload are copied. The existing
4096-character header and 8192-character display bounds remain; overflow fails
closed. DEV frontend validation accepts only these reviewed optional keys and
enums. Production excludes the builder callback/header and diagnostic frontend.

This is evidence collection, not a completed mass compatibility fix. Another
sanitized capture is necessary even though the provider order is proven: the
actual live predicate remains unobservable in the supplied report. Reload the
existing development iframe, open **CAD Context**, press **Read CAD data**, then
manually copy **Sanitized mass response structure** under **DEVELOPMENT ONLY ·
Mass response structure**, immediately below the REST diagnostic. Share the
`validation` entries containing `failedPredicates` and `comparisons`, or the whole
sanitized box, plus visible section statuses. If mass succeeds instead, report
the exact displayed availability/status. No raw CAD numeric values are needed.

Files changed for this follow-up: backend `models.py` (comment only),
`normalize.py` (explicit helper naming), `dev/mass_structure.py`,
`test_mass_structure.py`, new `test_mass_normalization.py`; frontend
`dev/massStructure.ts`, `dev/massStructure.test.ts`,
`__fixtures__/massStructure.ts`; the production-exclusion assertions in
`tests/e2e/extension.spec.ts`; and this review plus architecture, security,
development, Onshape and roadmap documentation. The REST architecture, routes,
provider requests, minimized proof JSON, authentication and token handling are
unchanged. No commit, push or Phase 5 work is authorized.

Targeted verification for this follow-up passed: **264 backend tests** (134
REST/security, 54 diagnostic, 76 scalar normalization/provider-model tests),
**94 CAD frontend tests**, and **6 browser checks** (manual comparison capture
and production exclusion across Chromium, Firefox and WebKit). `make format`,
`make lint`, `make typecheck` (including mypy, 40 files), and `make build` passed.
Production asset names remain `index-DzUVbMkr.js` and `index-1OxRQLqy.css`; the new
diagnostic vocabulary and UI are absent from production JavaScript. Dependency
lockfiles are unchanged. The expensive full phase gate was not repeated.
The real live mass predicate and final REST result are still unverified.

### 2026-10-12 negative-component follow-up — sign capture required

The newest authoritative live diagnostic reports only `negative_component` for
mass. Comparisons establish `lower < nominal < upper`, so the ordering predicate
passes. The exact root cause is `any(v < 0 for v in values)`. Since the lower
position is the smallest and at least one value is negative, **position 1 is
necessarily negative**. This does not prove it is the only negative position:
nominal and upper signs remain unknown. The report also contains only types for
`hasMass` and `massMissingCount`, not their live boolean/category.

Rechecking the current public v17 schema retrieved the same version and digest
recorded above. Mass, volume and periphery item schemas impose no `minimum`, and
the operation describes calculated value, lower tolerance limit and upper
tolerance limit. The official Part Studios example confirms that order. These
sources do not require tolerance limits themselves to be nonnegative, so the
blanket guard is unsupported as a provider-contract constraint. They also do not
establish negative nominal or unavailable-mass sentinel semantics. No live
nonnegative nominal can be inferred from the supplied comparisons alone.

The official [Mass Properties Tool documentation](https://cad.onshape.com/help/Content/View/mass_properties_tool.htm)
describes approximate, density-dependent mass calculations and omission of parts
without assigned material. In Forge, a strict `hasMass=false` and nonnegative
integer `massMissingCount>0` already parse successfully when supplied scalar
arrays pass the existing validator. A false flag controls the proof's
`has_mass=false` and the normal UI's unavailable/unverified message, even if a
numeric array is supplied. Missing mass is never synthesized. The exact missing
count and supplied volume remain in the request-local normalized data; independent
features/parts/body outcomes remain valid. Existing summaries do not prove that
an aggregate with missing contributions is complete. No material assignment is
required for parsing a false flag or capturing this diagnostic.

The user's task 6 explicitly says not to loosen the parser without knowing the
negative positions. Following that instruction, this follow-up changes **only
development diagnostics, tests and documentation**. It adds these authorized
facts to the report from the **first failed mass record**, not the sampled
aggregate or a different failure:

- `massSigns`: exactly `position0`, `position1`, `position2`, each only
  `negative`, `zero` or `positive`, after the same strict finite-number conversion.
- `hasMass`: only the known strict boolean; absent/malformed values are omitted.
- `massMissingCountCategory`: only `zero` or `positive` for a strict nonnegative
  integer; the count itself is never emitted.

Malformed/nonfinite mass arrays receive no sign classification. Volume-only
failure receives no mass facts. Private record keys, numeric operands, unknown
fields, exceptions, tokens, secrets, IDs and URLs remain excluded. The frontend
allows exactly these optional fields/enums only with a mass bounds failure.
The existing 4096-character header/8192-character display bounds and production
exclusion remain. The manual-copy instruction now says "numeric CAD values" to
distinguish the explicitly authorized availability boolean from mass operands.
REST architecture, provider requests, production parser/normalizer, proof JSON,
centroid/inertia/principal-inertia/axes handling and units are unchanged.

Files changed for this follow-up: backend `dev/mass_structure.py` and
`tests/test_mass_structure.py`; frontend `dev/massStructure.ts`,
`dev/massStructure.test.ts`, `dev/ReadDiagnostic.tsx`,
`__fixtures__/massStructure.ts`, and `ReadCad.test.tsx`; production-exclusion
assertions in `tests/e2e/extension.spec.ts`; this review and architecture, security,
development, Onshape and roadmap documentation. No dependencies or lockfiles
changed. No commit, push or Phase 5 work is authorized.

One final sanitized **sign capture** is required before a parser repair: reload
the existing development Forge iframe, choose **View CAD context → Read CAD
data**, then manually select/copy **Sanitized mass response structure** under
**DEVELOPMENT ONLY · Mass response structure**, immediately below the REST
diagnostic. Share `massSigns`, `hasMass`, `massMissingCountCategory` and
`validation` (or the whole sanitized box) plus the visible section statuses. No
numeric values, raw response/header inspection or material assignment is needed.
If these optional facts are absent, report that absence without substituting
assumptions. The safe parser repair and real final REST verification remain pending.

Targeted verification passed: **291 backend tests** (134 REST/security, 81
diagnostic and missing-mass snapshot tests, 76 scalar/provider-model tests),
**115 CAD frontend tests**, and **6 browser checks** across Chromium, Firefox and
WebKit. Format, lint, TypeScript, mypy (40 files) and the production build passed.
Production assets retain the same names/hashes; all emitted JavaScript excludes
the new sign/category markers and diagnostic UI. Dependency lockfiles are unchanged.
The full phase gate was not repeated. These checks verify the diagnostic extension
and existing missing-mass behavior; they do not establish a live parser repair.

### 2026-10-13 final sign evidence and field-semantic repair

The final authoritative capture proves nominal zero, negative lower tolerance,
positive upper tolerance, `lower < nominal < upper`, `hasMass=false` and positive
missing count. The only old failure was `any(v < 0 for v in values)`: a tolerance
limit was incorrectly treated as a physical quantity. There is no remaining sign
ambiguity and no need for another investigative capture before the live retest.

A fresh [public v17 schema](https://cad.onshape.com/api/openapi) check retrieved
version `1.222.90730-c8d74e607a47` and the same SHA-256 recorded above. The operation
documents calculated/lower/upper positions; mass and volume are physical scalar
quantities, and periphery is explicitly **surface area**. The nominal nonnegative
rule is Forge's physical validation of those quantities, not a claim that OpenAPI
imposes numeric minima on tolerance limits. The official [Part Studios guide](https://onshape-public.github.io/docs/api-adv/partstudios/#get-the-mass-properties-of-a-part-studio)
confirms the scalar ordering, while the [Mass Properties Tool documentation](https://cad.onshape.com/help/Content/View/mass_properties_tool.htm)
explains approximate, density-dependent calculations and omission of parts without
assigned material. No unit/frame assumption or conversion is added.

The scoped repair replaces the model-level blanket check with field validators
for **mass, volume and periphery only**. Present arrays require exactly three
strict finite numbers. A negative nominal is rejected with fixed code
`negative_nominal`; inverted `lower <= nominal <= upper` is rejected with
`bounds_order`. Zero, equality, asymmetric/narrow tolerances and negative lower
limits are accepted. Empty/singleton estimates are now rejected as required by
the user's final instructions; missing/nullable optional values remain unknown.
Centroid, inertia, principal-inertia components and principal axes are unchanged.

`normalize_provider_scalar_estimate` maps the validated triple explicitly to
nominal/lower/upper. When `hasMass=false`, the normalized mass estimate is **None**;
the zero-like provider array is not promoted as a physical mass. Volume, raw
periphery, other structures and the strict nonnegative missing count are preserved
request-locally. False availability remains false in the proof. Assigned mass
with a positive missing count yields unverified availability, avoiding a claim
of complete mass. All valid responses keep mass section `success / ok`; parsing
status and availability are independent. No material assignment is needed merely
to parse this response.

The normal UI now says **Mass unavailable; material/density may be missing** for
false availability. It keeps **Onshape data connected**, feature/part/body counts
and read consistency. Unknown/partial availability keeps the unverified message;
fully assigned mass can say **Mass properties available**. Numeric mass values,
missing counts and private references are not rendered or sent in the proof.

Useful DEV diagnostics remain bounded and production-excluded. Field-level fixed
errors now carry the safe field identity, so the investigation's per-field
validator replay and duplicated failing-predicate calculation were removed.
The builder copies only allowlisted error codes plus safe structure/comparison/sign
metadata from the failed record. It never copies error messages, contexts, numeric
operands, body keys, unknown names, IDs, tokens, secrets or provider URLs. Frontend
validation accepts the new fixed codes for reviewed scalar fields and rejects the
obsolete blanket predicate. Success produces no mass failure header or box.

Files changed for this repair: backend `models.py`, `normalize.py`, `service.py`,
`dev/mass_structure.py`; tests `test_cad_read.py`, `test_mass_normalization.py`,
`test_mass_structure.py`; frontend `ReadCad.tsx`, `ReadCad.test.tsx`,
`dev/massStructure.ts`, `dev/massStructure.test.ts`,
`__fixtures__/massStructure.ts`; `tests/e2e/extension.spec.ts`; and this review plus
architecture, security, development, Onshape and roadmap documentation. REST
endpoints, request count/settings, sessions, OAuth/CSRF, ownership checks, resource
limits, proof JSON schema and dependency lockfiles remain unchanged.

Final real retest: reload the existing development Forge iframe in the same Part
Studio, choose **View CAD context → Read CAD data** once, and confirm **Onshape
data connected**, **2 features**, **1 part**, **1 body**, and **Mass unavailable;
material/density may be missing**. The mass section should not show the invalid
provider-response message, and no mass failure structure box should appear. If
using the read diagnostic, its mass section should be `success / ok`. Report the
visible results and browser/date; use the existing sanitized manual-copy fallback
only if an unexpected error remains. No further raw/sign capture, material
assignment or credential/configuration change is required before this test.
Phase 4 completion remains pending this real result. No commit, push or Phase 5
work is authorized.

Targeted verification for the repair passed: **356 backend tests** (134
REST/security, 102 mass diagnostic/snapshot/API tests, 120 scalar/provider-model
tests), **116 CAD frontend tests**, and **9 browser checks** across Chromium,
Firefox and WebKit (missing-mass status, manual sanitized diagnostics and production
exclusion). Format, frontend/backend lint, TypeScript, mypy (40 files), and
production build passed. The production JS is `index-BQ48mDtP.js`; it contains
the repaired product status and excludes all diagnostic markers/modules. CSS is
unchanged. Dependency lockfiles are unchanged; the full phase gate was not repeated
because shared infrastructure was not changed. Synthetic tests cover the exact
live shape, suppress false physical zero, preserve volume and independent reads,
and retain strict malformed/nonfinite/negative-nominal/inverted-bound rejection.
Real end-to-end success remains pending the user's final REST test.

The original Phase 4 gate results below predate this diagnostic investigation.
Existing Phase 0–3 tests are retained.

| Check                           | Final result                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------ |
| Frozen installs                 | `npm ci` and `uv sync --locked` passed; lockfiles unchanged                          |
| Format/lint                     | Prettier, ESLint and Ruff passed                                                     |
| Type checking                   | TypeScript and mypy passed (36 checked Python files)                                 |
| Frontend unit/component tests   | 320 passed, including 43 new Phase 4 tests                                           |
| Backend default suite           | 231 passed, including 134 Phase 4 tests; 3 opt-in PostgreSQL tests skipped           |
| Explicit PostgreSQL regressions | 3 passed in isolated temporary schemas                                               |
| Playwright                      | 240 passed: 80 each in Chromium, Firefox and WebKit                                  |
| Production build                | Passed; REST/launch/selection diagnostics and synthetic fixtures excluded            |
| Migration comparison            | No new upgrade operations detected                                                   |
| Compose / real PostgreSQL       | Configuration valid; existing database healthy                                       |
| Dependency audits               | npm and pip-audit reported no known vulnerabilities                                  |
| `make check`                    | Passed; subsequent backend review fixes passed lint, mypy and the full backend suite |
| Git diff / secret scan          | Passed; no staged files, local secrets, private keys or tracked local data           |

The first targeted browser run found the definition-list role issue and duplicate
read-region landmarks. Both were corrected; the final complete browser suite passes
without disabling accessibility rules. Backend review additionally reserved cooldown
capacity for active reads and prevented a mass-available claim when the provider
supplies a flag without numeric mass. Those final changes passed the backend gate.

Visual inspection covered the read summary at 320 px dark and 1280 px light;
automated checks cover 320/380/480/1280 px in both themes. No horizontal overflow
was observed. All screenshots are synthetic and ignored. Playwright stopped its
4173/4174 servers; the existing user services were not restarted. npm emitted a
nonblocking optional fsevents install-script notice; no permission or dependency
policy was changed to suppress it.

### Files and Git state

The final change set is 39 files (16 modified, 23 new), scoped to Phase 4. The
parent is the Phase 3 hash above. One clean commit is authorized with subject
`feat: add read-only Onshape CAD inspection`, followed by a normal push of main
to existing origin. No force push or Phase 5 work is authorized. Environment
files, certificates, caches, synthetic screenshots and local database data remain
ignored. Current source and production assets have no local secret matches or
literal private CAD IDs. A pre-existing documentation connection example matched
the local database configuration and was replaced by a placeholder; history was
not rewritten. No raw live CAD fixture or capture was created.

| Area                 | Files                                                                                                    |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| Backend CAD package  | `integrations/onshape/{__init__,contracts,client,models,normalize,service,routes}.py`                    |
| Backend integration  | `main.py`, `auth/provider.py` (permission comment only), `integrations/README.md`                        |
| Backend tests        | `test_cad_read.py`, `test_client_context_boundary.py`                                                    |
| Frontend CAD package | `cad/api.ts`, `ReadCad.tsx`, their tests, `__fixtures__/proof.ts`, `dev/ReadDiagnostic.tsx` and its test |
| Existing frontend    | `auth/AuthGate.tsx`, `components/CadContext.tsx`, `components/Shell.tsx`, `styles.css`                   |
| Browser tests        | `tests/e2e/extension.spec.ts`                                                                            |
| Documentation        | root `README.md`, `ARCHITECTURE`, `SECURITY`, `ONSHAPE`, `DEVELOPMENT`, `ROADMAP`, this review           |

Backend paths above are relative to `apps/api/src/forge_api` (tests to
`apps/api/tests`); frontend paths are relative to `apps/web/src`; documentation is
under `docs` unless specified. Synthetic fixtures are manually constructed from the public
contract; they contain no live private CAD values or captured provider responses.

Coverage includes ownership and token refresh/revocation, active-request disconnect,
strict origins and reference parsing, GET-only routes, no redirect/retry, bounded
JSON, successful/partial/failed snapshots, unknown scopes, microversion mismatch,
CSRF, all UI states, late-response invalidation, no polling, rate cooldowns,
production exclusion, three browser engines, accessibility and narrow/wide layouts.

## Exact manual setup and live verification

1. In Onshape, open account menu → **My account → Developer → OAuth applications**.
   If the existing application is company-owned, use company/classroom/enterprise
   settings → Developer instead. Open the existing **Forge Development** app.
2. Open **Permissions**. Keep **Application can read your profile information
   (OAuth2ReadPII)** and enable **Application can read your documents (OAuth2Read)**.
   Save the permission change. Leave document write/delete/share/purchase permissions
   disabled. Keep the existing extension, Action URL, OAuth URL, redirect URL,
   client identifier and secret unchanged; do not regenerate keys.
3. Obtain renewed consent. In Onshape **My account → Applications**, revoke the
   previous Forge grant if it retains the old permission. Open
   `https://localhost:5173`, reconnect/continue with Onshape and approve profile
   plus document-read access. Reopen the panel afterward. Logout alone does not
   revoke provider consent. Never share codes, cookies, tokens, `.env` or HAR files.
4. Use the existing ignored `.env` and trusted local HTTPS certificates. Keep the
   working Phase 3 `SESSION_SAMESITE` configuration. If services need restarting,
   stop only their own dev terminal processes with Ctrl+C, then run from repo root:

   ```sh
   make db-up
   make migration-check
   make dev-api
   ```

   In a second repo-root terminal run `make dev-web-https`. No new migration or
   environment variable is required. Do not delete/recreate database volumes.

5. In the existing Onshape test document, open the **workspace Part Studio** that
   contains **Sketch 1**, **Extrude 1** and **Part 1**. Use its default configuration
   and end-of-list state. Open the existing Forge right-panel extension. Confirm
   the authenticated display name and valid launch context.
6. Click the header's **View CAD context**, then **Read CAD data** once. Expect
   **Onshape data connected**, **2 features**, **1 part**, and a body count. Expect
   **Mass properties available** only if Onshape supplies assigned mass. Missing
   material/density is a legitimate unavailable/unverified mass outcome; do not
   change the CAD just to manufacture a passing result.
7. Confirm read time and the explicit consistency caveat. Switch Part Studio or
   document and confirm the previous read disappears. A new explicit click should
   read the new context after any cooldown. Do not interpret a matching count as
   a CAD write or an engineering validation result.
8. If a provider read fails, in the local DEV UI click **Copy sanitized read
   diagnostic** and share only that copied report plus the visible safe message
   and browser/version. If clipboard access is unavailable in the iframe, select
   and manually copy the **Sanitized read diagnostic** text area that appears
   below the button in **DEVELOPMENT ONLY · REST diagnostic**. If no report exists
   (e.g. signed-out or API unreachable),
   report the visible message and whether `/health` is reachable. Do not copy raw
   network requests/responses, full URLs, logs or provider credentials.
9. Record the observed outcome separately from automated fixture evidence. The
   user's final results are recorded below; no further live test or authorization
   request is needed for this Phase 4 closeout.

## Final external verification and repository gate — 2026-10-13

The user supplied the final external verification report on this date. These
observations were made in the real Forge Onshape iframe; they are not inferred
from synthetic tests:

| Live check                             | Observed result                                                                          | Status |
| -------------------------------------- | ---------------------------------------------------------------------------------------- | ------ |
| OAuth2Read and real REST authorization | Four allowlisted CAD reads succeeded under the existing account/grant                    | PASS   |
| Part Studio 1 features                 | Sketch 1 and Extrude 1; Forge displayed 2 features                                       | PASS   |
| Part Studio 1 parts                    | Part 1; Forge displayed 1 part                                                           | PASS   |
| Part Studio 1 body details             | Forge displayed 1 body                                                                   | PASS   |
| Mass properties                        | Valid response parsed; old invalid-response message disappeared                          | PASS   |
| Missing mass                           | Displayed Mass unavailable; material/density may be missing; no fabricated physical zero | PASS   |
| Separate empty Part Studio 2           | Displayed 0 features, 0 parts, 0 bodies and No mass-property bodies returned             | PASS   |
| Stale context                          | Earlier 2/1/1 snapshot did not persist into the new element/context                      | PASS   |

The final sanitized evidence establishes nominal zero, negative lower tolerance,
positive upper tolerance, `hasMass=false` and positive missing count. Exact CAD
numeric values and document/workspace/element/selection IDs were neither needed
nor recorded. The user did not supply the actual live browser/version; no live
cross-browser claim is made. Assigned-material live mass and broader configurations
remain outside this sample's evidence.

The final source review covered the complete Phase 4 diff from the Phase 3 parent.
The four CAD operations are fixed GETs at the strictly controlled standard
Onshape origin. There is no CAD POST/PUT/PATCH/DELETE or arbitrary HTTP proxy.
Tokens stay backend-only, refresh tokens remain encrypted, session/grant ownership
and final revocation checks are enforced, and CSRF remains intact. Product output
is a minimized count/status proof. Useful bounded DEV diagnostics remain; the
obsolete validator replay and duplicate predicate calculation were already removed.
No verified behavior was changed during final cleanup.

| Final check                     | Result                                                                                                               |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Frozen dependency installs      | npm ci and uv sync --locked passed; lockfiles unchanged                                                              |
| Formatting and lint             | Prettier, ESLint, Ruff lint and Ruff format passed                                                                   |
| Types                           | TypeScript and mypy passed; 40 Python files checked                                                                  |
| Complete frontend suite         | 393 passed across 15 files                                                                                           |
| Complete backend default suite  | 453 passed; 3 opt-in PostgreSQL tests skipped in that invocation                                                     |
| Explicit PostgreSQL regressions | All 3 passed in self-owned temporary schemas; skipped coverage above is satisfied                                    |
| Complete Playwright matrix      | 252 passed, 84 each in Chromium, Firefox and WebKit                                                                  |
| Production build/exclusion      | Passed; all emitted JavaScript excludes diagnostic/fixture markers and local secret values                           |
| Existing PostgreSQL             | Healthy; no user data/volumes removed                                                                                |
| Migration comparison            | No new upgrade operations detected                                                                                   |
| Docker Compose                  | Configuration validation passed                                                                                      |
| Dependency/security audits      | npm and pip-audit found no known vulnerabilities                                                                     |
| make check                      | Passed, including full unit suites, build and Compose validation                                                     |
| Phase 0–3 regression coverage   | Complete retained suites and real PostgreSQL concurrency/migration tests passed                                      |
| Current source/secret scan      | 39 files checked; no remaining actual local secret or private CAD-ID matches                                         |
| Local artifacts                 | Environment/certificate files remain ignored; no HAR, CAD capture, database, key or generated build file is included |

Playwright stopped the temporary 4173/4174 servers it started. Existing development
and database services were preserved. The optional fsevents install-script notice
did not fail frozen installation or checks; no global permission policy changed.
The final staged diff and staged blobs are reviewed/scanned before the single
authorized commit. The normal push must be verified by comparing remote main to
the local commit; exact publication details belong in the final handoff.

Phase 4's implementation, external verification and final quality gate are
complete. Phase 5 has not begun and may not begin without separate authorization.

## Limits and deferred work

No further Phase 4 live capture or retest is currently required. Phase 4
supports the standard CAD stack, workspace Part Studios, default configuration and
bounded responses only. Enterprise stacks, versions/microversions, configuration
selection, rollback synchronization, complete geometry interpretation, atomic
snapshots, distributed rate limits and reliable cross-browser iframe cookies are
not established here. Missing mass units/frame interpretations remain unverified.

Phase 5's full read-only inspector, richer feature/part/assembly presentation and
evidence navigation are deferred. AI generation/agents, CAD writes, approval-bound
mutations, exports, engineering validation and assemblies/mates are later phases.
