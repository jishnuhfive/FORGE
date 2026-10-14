# Phase 5 review — complete

Review date: 2026-10-14. The human supplied final external verification of the real
read-only CAD Inspector, topology repair and browser lifecycle repair. The final
complete repository gate is recorded below. Phase 6 has not begun.

## Repository base and authorization

Phase 5 began from clean main at
`fe857d1b75f555f368bbed53ec22d952479a3288` (`feat: add read-only Onshape CAD inspection`).
The interrupted implementation and both live repairs were preserved throughout.
The user now authorizes exactly one commit, `feat: add Forge CAD inspector`, then
normal main-to-origin push after every final check passes, followed by exact remote
hash verification. No force push or Phase 6 work is authorized.

All automated fixtures are invented. No raw live provider response, CAD IDs,
selection references, screenshots or network captures are included in this change.
Live observations below are the human's evidence, distinct from automated tests.

## Final real live verification

| Area                       | Human-observed result                                                                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Features                   | PASS: Sketch 1 then Extrude 1, recognizable Sketch/Extrude types, Active suppression state                                                 |
| Parameters                 | PASS: supported real summaries visible; unsupported/incomplete evidence explicitly caveated                                                |
| Filtering                  | PASS: Sketch/Extrude searches filter locally; clear restores provider order; no request per keystroke                                      |
| Parts                      | PASS: Part 1, solid/type/state/mesh metadata; missing description/part number explicit; per-part mass unverified                           |
| Bodies                     | PASS: one SOLID Body 1; Faces 6; Edges Unknown; Vertices Unknown                                                                           |
| Sanitized body structure   | Present arrays: faces length 6, edges length 0, vertices length 0; empty collections are not authoritative topology zeros                  |
| Physical properties        | PASS: unavailable mass, missing material/density contributions, reported volume, provider-native/unverified units; numeric values withheld |
| FACE                       | PASS: 1 face selected; no feature/part/dimension/surface ownership inference                                                               |
| EDGE                       | PASS: 1 edge selected; no ownership inference                                                                                              |
| Clear                      | PASS: No selection                                                                                                                         |
| Ordinary Chrome tab switch | PASS: same inspector, original capture time and FACE preserved; no automatic CAD request, loading, reopen demand or false context reset    |
| Real Part Studio switch    | PASS: Part Studio 1 evidence/selection clears before inspection of Part Studio 2                                                           |
| Empty Part Studio          | PASS: 0 features, 0 parts, 0 bodies and no mass-property bodies; no prior results persist                                                  |

Chrome was named for the human lifecycle test; its exact browser version was not
provided. Automated Chromium/Firefox/WebKit coverage is separate. No broader live
browser, configuration, assembly or geometric-completeness claim is made.

## Architecture and contract

```text
Four existing backend-only Onshape GETs
  → strict provider projection + exact parameter adapters
  → existing normalized request-local Snapshot
  → compact proof + bounded inspector projection
  → forge-cad-inspector-v1
  → strict frontend validation → human-readable inspector
```

GET `/api/onshape/part-studio/inspector` and the unchanged compact
`/api/onshape/part-studio/snapshot` share `routes.acquire`. Each action acquires one
snapshot using the existing service. The inspector embeds the compact proof as
`source`; the UI calls only `/inspector`. It does not fetch per component or search
keystroke. Both endpoints share the same per-user admission gate and cooldown.

The public evidence model contains:

| Field          | Meaning                                                                                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| schema_version | `forge-cad-inspector-v1`                                                                                                                                       |
| context        | Workspace Part Studio, default configuration, end-of-list evaluation                                                                                           |
| source         | Unchanged `forge-cad-read-v1` proof: UTC capture time, random request reference, section status/code/count/retry delay, consistency and conservative mass flag |
| freshness      | `captured_unverified`, or `stale` for a consistency mismatch                                                                                                   |
| features       | Ordered feature summaries, supported parameter evidence, completeness, returned and omitted counts                                                             |
| parts          | Selected metadata and explicit unverified per-part mass                                                                                                        |
| bodies         | Ordinal labels, body type and optional topology counts                                                                                                         |
| physical       | Aggregate mass/volume availability, missing-mass evidence and unverified units                                                                                 |

Context identifiers remain in the authenticated request and internal snapshot.
They are not repeated in the inspector or rendered in normal CAD Context UI.
The machine model is usable by a future server consumer without scraping React;
that consumer must retain the server-owned context and all uncertainty metadata.
Ordinals are presentation positions, not stable write targets or authorization.

## Official evidence and supported adapters

The official [OpenAPI schema](https://cad.onshape.com/api/openapi), fetched on
2026-10-13, still advertises v17 with version `1.222.90730-c8d74e607a47` and SHA-256
`d93a3c77e5f4a61f69ce865e815da4fe628178bb37cb6de4d91028f2c2bdc9aa`.
The public schema download is outside the repository. No provider API-version
migration was needed. Also reviewed the official
[feature guide](https://onshape-public.github.io/docs/api-adv/featureaccess/) and
[standard library](https://cad.onshape.com/FsDoc/library.html#chamfer).

Recognized feature spec names are `newSketch`, `extrude`, `fillet` and `chamfer`.
They normalize to Sketch, Extrude, Fillet and Chamfer. A nonempty custom namespace
prevents classification as a standard feature. All other types keep a safe display
name with “Custom or unknown feature” and “Type not yet interpreted by Forge.”
Feature ordering comes directly from the provider user-feature list. Origin and
planes in `defaultFeatures` are not added. Missing names use ordinal fallbacks;
missing suppression stays unverified. Active means the reported suppression flag
is false, not that feature regeneration succeeded. Feature-state diagnostics,
subfeature trees and sketch geometry interpretation are not implemented.

| Exact provider parameter class | Inspector evidence                                              |
| ------------------------------ | --------------------------------------------------------------- |
| BTMParameterBoolean-144        | Strict boolean value; omitted defaults remain unknown           |
| BTMParameterString-149         | Literal string, including an explicitly supplied empty string   |
| BTMParameterEnum-145           | Literal enum member; enum definitions are not evaluated         |
| BTMParameterQuantity-147       | Literal expression; no evaluation, conversion or inferred units |
| BTMParameterQueryList-148      | Number of query entries; not resolved entity count              |
| All other classes/subclasses   | Unsupported parameter type; no arbitrary value promotion        |

Readable parameter names become bounded labels; opaque IDs use “Parameter N”.
Malformed supported values are unavailable without failing the feature list.
Overlong/control-containing values are wholly omitted, never cut into a different
engineering expression. Unknown classes cannot supply their own normalized summary.
The UI cautions that a returned parameter can describe an inactive option.

## Parts, bodies and physical properties

Parts show name, optional documented description/part number/body type/state and
`isMesh`. Missing fields are “Not supplied”; arbitrary custom properties, links,
materials, thumbnails, IDs and other provider objects are not exposed. The aggregate
mass query cannot prove individual part mass, so each part says unverified.

Bodies show “Body N”, reported type and lengths of nonempty face/edge/vertex
arrays. Missing, null and unverified empty arrays mean unknown counts, not zero.
The v17 contract does not establish an authoritative empty topology collection for
the fixed `includeGeometricData=false` request. No geometric payload, surface
type, dimensions, geometry classification or body-to-feature mapping is exposed.

Physical evidence distinguishes available, unavailable, partial and unverified
mass. Positive missing contributions prevent an available claim. A false mass flag
means unavailable and material/density may be missing; it never becomes physical
zero. Empty mass-body output is shown explicitly. Volume reports whether a validated
estimate was returned, without exposing its numbers. Units remain
`provider_native_unverified`. No numeric mass/volume, centroid or inertia is sent
by the inspector. This is evidence presentation, not engineering validation.

## Bounds and completeness

| Boundary                      | Limit and behavior                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| Existing transport            | 2 MiB per provider section; bounded JSON depth/nodes/strings; fixed timeouts and no retries             |
| Existing provider collections | 2,000 features/parts/bodies/mass records; 512 parameters per feature; 20,000 entries per topology array |
| Inspector features            | First 100, retaining original order and full returned count                                             |
| Inspector parts / bodies      | First 200 each                                                                                          |
| Inspector parameters          | First 16 per feature, with omitted count                                                                |
| Display values                | At most 256 UTF-8 bytes; whole value omitted if too long or containing forbidden controls               |
| Parameter labels              | Derived only from at most 80 readable ASCII characters; otherwise ordinal                               |
| Query entries                 | Up to 2,000; no query contents or entity references promoted                                            |
| Browser response              | 2 MiB streamed limit before JSON parsing; strict nested field/type/count checks                         |

Completeness describes the supported summary projection, not all possible CAD
semantics. It is complete, partial, unverified or unavailable. Unknown parameters,
missing metadata, omitted values and bounds never silently claim completeness.
The existing provider completeness flag still controls whether total feature count
is known. Over-limit provider responses retain the Phase 4 section-error behavior.
The successful sections remain usable.

## Freshness, selection and error behavior

No polling, cache or timer-triggered read exists. Refresh CAD is explicit and
clears previous evidence while loading. Read time is completion time, not atomic
version proof. Separate workspace reads remain unverified even if source versions
match; a mismatch becomes explicitly stale. Unobserved edits after capture cannot
be detected and the UI says so.

Document/workspace/element/microversion/account changes remount the reader immediately.
Disconnected accounts, stale Phase 3 context and actual page navigation/bfcache
suspension clear data and abort/discard late results. Same-frame browser visibility,
blur/focus and show preserve selection and inspection with unchanged capture metadata.
A destroyed/recreated panel requires its own explicit read; aborted server work can
still finish within existing bounded timeouts.

Selection stays in the verified Phase 3 store and updates independently of REST.
One FACE, one EDGE and clear states remain visible. No selection reference reaches
the inspector endpoint; no feature, body, part, dimensions or surface ownership is
inferred. Real context changes or navigation suspension invalidate selection;
ordinary browser-tab visibility does not.

Partial section failures do not erase successful sections. Existing fixed messages
preserve connection, permission/access, forbidden, not-found, rate/quota, timeout,
provider-unavailable, incompatible-response and unsupported-context distinctions.
No raw provider error body or exception text is rendered. Cooldown/retry delays are
respected without retries. Known assembly/version contexts cannot initiate a read;
otherwise the existing Part Studio endpoints remain authoritative for access/type.

## Privacy and read-only security

Browser data is deliberately allowlisted, ephemeral, and private to the current
session. No PostgreSQL persistence, analytics, data logging or browser storage was
added. No names, parameters, queries or provider exceptions enter diagnostic logs.
React renders literal text, not HTML, and expressions are never executed. Arbitrary
provider fields, OAuth credentials, raw BT objects, FeatureScript source, geometry,
custom-property dictionaries and unnecessary provider IDs remain outside the response.

The four provider operations remain exactly the existing GET allowlist. There is
no CAD POST/PUT/PATCH/DELETE, proxy, caller-selected host/path/method, model tool or
FeatureScript execution. Backend-only tokens, encrypted refresh tokens, session
ownership, exact origin/CSRF protection, response limits, redirect rejection, no
retries and quota gates remain intact. The compact proof remains independently
available for regressions. DEV diagnostics receive only its fixed fields and stay
production-excluded; synthetic lab imports cannot fall back into live inspection.

## UI and accessibility

The inspector uses native keyboard-accessible disclosures, existing visible focus,
explicit labels, a brief loading/status live region, ordered feature items and
wrapped text at 320/380/480 px. Overview, feature/part/body details and physical
availability remain compact. Errors and empty sections are explicit. Local substring
filters use only fetched models and preserve feature ordinals. Filter text stays in
component memory. The lab includes nine clearly labeled synthetic states.

## Completed repairs and retained diagnostics

Topology: missing/null collections already stayed unknown. The previous normalizer
unconditionally counted an empty array as zero. Final sanitized live evidence
confirmed empty edge/vertex arrays under the fixed `includeGeometricData=false`
request. The current v17 contract has no completeness guarantee for those empty
collections. Forge preserves nonempty returned-entry counts and maps missing/null/
empty arrays to null through normalization, inspector and frontend, rendered Unknown.
An empty Part Studio still correctly has zero returned bodies. No larger geometry
request, new endpoint or inferred topology was added.

Lifecycle: document-hidden handlers previously invalidated the bridge and directly
cleared the reader. Stale selection then unmounted inspection and demanded reopening.
Both visibility handlers are removed. show preserves an active frame's selection
and requests focus; it cannot revive a genuinely suspended frame. Real navigation/
bfcache suspension and fresh context/session changes still clear evidence. Optional
context IDs supplied by trusted SELECTION must match the validated launch. Malformed
trusted selection clears evidence; valid selection recovery enables explicit reading
only. Wrong origin/window messages remain ignored. The human verified the repaired
ordinary browser-tab behavior and actual Part Studio clearing.

Useful DEV diagnostics are retained. The body report samples only the first body's
faces/edges/vertices presence, array/missing type and length/null, at most 512 ASCII
characters. It is emitted only after successful bounded normalization and final
ownership validation, resets before each read and is never logged/persisted. DEV
strictly validates it before displaying a read-only manual-copy box. Production
omits the header, parser and UI, and ignores injected headers. Existing bounded
mass/selection/launch/status diagnostics remain production-excluded. No obsolete
validator replay, ad hoc raw capture or temporary runtime integration remains.
No further live capture is required for Phase 5.

## Final complete quality gate

The complete final gate passed on 2026-10-14 after both live repairs.

| Check                                 | Final result                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Format / frontend lint / backend lint | PASS: Prettier, ESLint, Ruff lint and formatting                                                  |
| TypeScript / mypy                     | PASS: strict checks; mypy checked 45 files                                                        |
| Complete frontend tests               | 466 passed across 19 files                                                                        |
| Complete backend tests                | 531 passed; 3 PostgreSQL-only tests skipped in this invocation and passed separately below        |
| Real PostgreSQL regressions           | 3 passed in isolated temporary schemas; existing service healthy                                  |
| Complete Playwright                   | 297 passed: 99 each Chromium, Firefox and WebKit                                                  |
| Production build                      | PASS; DEV diagnostics and synthetic fixtures excluded                                             |
| Migration drift                       | PASS: no new upgrade operations detected                                                          |
| Docker Compose                        | PASS: configuration validates                                                                     |
| Dependency audits                     | PASS: npm 0 vulnerabilities; pip-audit no known vulnerabilities (editable local package skipped)  |
| `make check`                          | PASS: lint, types, full unit suites, build and Compose validation                                 |
| Git/privacy review                    | PASS: all 45 files reviewed; no secrets/private artifacts; staged contents verified before commit |

The first npm audit attempt had a transient registry DNS error; a fresh audit retry
passed. The initial remote-fetch approval review timed out; its permitted retry
succeeded and confirmed origin/main at the exact Phase 4 base. Neither is an
outstanding failure. No additional implementation change was needed at finalization.
Useful bounded DEV diagnostics were retained; live-verified behavior was preserved.
Dependencies, lockfiles, migrations and database models are unchanged. Frozen
installation was verified during Phase 5; Python checks use the locked environment.
The existing user's services/volumes were preserved; test-owned browser servers
stopped after their full run. No screenshots, raw captures or temporary downloads
are staged. This is a scoped Phase 5 completion, not certification or Phase 6 work.

## Required regression coverage

| Boundary                 | Tests and evidence                                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Features and parameters  | Ordered Sketch/Extrude, suppression, custom/unknown types, exact adapters, unsupported/malformed/omitted values, UTF-8 and collection bounds           |
| Filtering                | Source ordinals preserved, client-only filtering and no provider request per keystroke                                                                 |
| Parts                    | Supplied/missing metadata, safe omission, unverified individual mass and no provider IDs                                                               |
| Bodies                   | Each nonempty/missing/null/empty collection, strict types/limits, empty Part Studio, no IDs/geometry in output                                         |
| Physical                 | Available/unavailable/partial/unverified mass, missing contributions, no numeric units or fabricated mass                                              |
| Selection                | FACE/EDGE/clear, exact origin/window validation, no ownership inference                                                                                |
| Lifecycle                | Same-frame hidden/visible, blur/focus/show, capture time preserved, no automatic CAD reads, fresh frame initialization                                 |
| Stale data and ownership | Document/workspace/element/account/session changes, logout/disconnect/revoke, late responses discarded, mismatch rejection and no context resurrection |
| Production/privacy       | DEV parser/UI/fixtures excluded, injected diagnostic rejected, ephemeral models, no storage or private logs                                            |

## Limitations and Phase 6 boundary

Only the standard Onshape stack's workspace Part Studio path is supported. No
assemblies/mates (Phase 10), version reads, active-configuration/rollback synchronization,
atomic snapshot proof, complete feature semantics, nested feature tree, resolved
queries, selection ownership, evaluated expressions or verified numeric physical units.
Display bounds may omit evidence explicitly. Multi-worker quotas, managed ingress
privacy and broader live compatibility remain deployment work. Passing tests and
live inspection is not engineering certification or general production readiness.

Phase 6 requires separate authorization for a read-only AI consumer, OpenAI Responses,
strict tools/budgets, prompt-injection handling and streaming. None is implemented.
CAD writes, autonomous execution, validation, Reality Lock, Modify and Learn remain
in their own future phases. Stop after the authorized Phase 5 push.

## Final file inventory

45 reviewed files: 28 modified and 17 new. All paths are repository-relative.

- `README.md`
- `apps/api/src/forge_api/integrations/onshape/client.py`
- `apps/api/src/forge_api/integrations/onshape/dev/body_structure.py`
- `apps/api/src/forge_api/integrations/onshape/inspector.py`
- `apps/api/src/forge_api/integrations/onshape/models.py`
- `apps/api/src/forge_api/integrations/onshape/normalize.py`
- `apps/api/src/forge_api/integrations/onshape/parameters.py`
- `apps/api/src/forge_api/integrations/onshape/routes.py`
- `apps/api/tests/test_body_topology.py`
- `apps/api/tests/test_cad_inspector.py`
- `apps/api/tests/test_client_context_boundary.py`
- `apps/web/src/auth/AuthGate.tsx`
- `apps/web/src/cad/InspectorView.test.tsx`
- `apps/web/src/cad/InspectorView.tsx`
- `apps/web/src/cad/ReadCad.test.tsx`
- `apps/web/src/cad/ReadCad.tsx`
- `apps/web/src/cad/__fixtures__/bodyStructure.ts`
- `apps/web/src/cad/__fixtures__/inspector.ts`
- `apps/web/src/cad/api.ts`
- `apps/web/src/cad/dev/ReadDiagnostic.test.tsx`
- `apps/web/src/cad/dev/ReadDiagnostic.tsx`
- `apps/web/src/cad/dev/bodyStructure.test.ts`
- `apps/web/src/cad/dev/bodyStructure.ts`
- `apps/web/src/cad/inspector.test.ts`
- `apps/web/src/cad/inspector.ts`
- `apps/web/src/cad/messages.ts`
- `apps/web/src/components/CadContext.tsx`
- `apps/web/src/components/Shell.tsx`
- `apps/web/src/onshape/OnshapeProvider.test.tsx`
- `apps/web/src/onshape/OnshapeProvider.tsx`
- `apps/web/src/onshape/bridge.test.ts`
- `apps/web/src/onshape/bridge.ts`
- `apps/web/src/preview/InspectorPreview.tsx`
- `apps/web/src/preview/UiLab.tsx`
- `apps/web/src/styles.css`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `docs/ONSHAPE.md`
- `docs/ONSHAPE_EXTENSION.md`
- `docs/PHASE_5_REVIEW.md`
- `docs/ROADMAP.md`
- `docs/SECURITY.md`
- `tests/e2e/extension.spec.ts`
- `tests/e2e/foundation.spec.ts`
- `tests/e2e/preview.spec.ts`
