# Phase 3 Onshape extension

Reviewed 2026-10-10. **PASS — Phase 3 complete.** The human verified real Part Studio
right-panel embedding, embedded authentication and valid launch context. Live
FACE/EDGE/clear sanitized structures match the strict single-entity/clear adapter.
The corrected authoritative FACE capture resolves the earlier labeling discrepancy;
no parser or security change was required. The complete quality gate passed, and
only targeted FACE regressions were repeated for this final evidence update.
That Phase 3 checkpoint added no REST operations, scopes, AI calls or CAD writes.
Subsequent read-only phases and default-OFF Phase 9B Modify are documented below;
[the runtime review](PHASE_9_REVIEW.md) governs current controlled-write validation.

## Source review and live contract evidence

Current official sources consulted before implementation:

- [App development](https://onshape-public.github.io/docs/app-dev/): one web app
  integrates through official client messaging; REST remains server-side.
- [Extensions](https://onshape-public.github.io/docs/app-dev/extensions/): Action URL
  replacement parameters, default server metadata, exact origin restrictions and
  extension locations. Right panels embed HTTPS content and have no action type.
- [Client messaging](https://onshape-public.github.io/docs/app-dev/messages/):
  applicationInit, exact incoming origin matching, SELECTION event name and show
  focus guidance. No SELECTION payload schema is given.
- [Element right panel](https://onshape-public.github.io/docs/app-dev/messages/element-right-panel/):
  initialization and panel destruction lifecycle. The outgoing
  requestSelectionHighlight example specifies selectionType/selectionId/entityType;
  that does **not** establish the incoming SELECTION structure. Forge does not
  guess that these are interchangeable and sends no selection/highlight commands.
- [Hello World](https://onshape-public.github.io/docs/app-dev/helloworld/): current
  extension form labels, Inside part studio context, private subscription workflow
  and the legacy workspaceId message field for a workspace launch value.
  Its wildcard messaging, broad read/write permissions and unauthenticated HTTP
  sample are not adopted as security requirements.
- [Individual settings](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm)
  and [organization settings](https://cad.onshape.com/help/Content/Plans/enterprise_settings_developer.htm):
  existing OAuth applications can have extensions; internal assignment differs from
  individual private App Store subscription. Cloud apps use HTTPS.

The published official docs repository was also checked at commit
`2d5b575` (deployment of source `b636ee334a6018d416310f366d3ca497941a0fbe`).
Its messaging pages contain no incoming SELECTION definition. Onshape's official
app-bom example only handles show/hide. Old snippets are not evidence of a current
selection contract.

The October 10 sanitized captures establish a `SELECTION` envelope with a top-level
`selections` array, one ENTITY with selectionId/string, entityType/FACE or EDGE,
occurrencePath/undefined and an unknown string field, or an empty array when cleared.
The unknown field is deliberately neither named nor interpreted. Test references
and metadata are invented; no private capture values are in the repository. The
human corrected the mislabeled FACE sample; its verified structure matches the
existing synthetic fixture and parser. Redacted reference values remain private.

## Architecture and trust

The same Vite SPA serves `/` and `/extension`; Vite's SPA fallback handles the path.
There is no second frontend or bundle. Existing hash settings/history navigation
continues beneath that path. Production hosting must serve index.html for
`/extension`, proxy `/api` and `/auth` unchanged and set response headers below.

`OnshapeProvider` constructs one `createBridge` per frame. It parses the launch
once, installs the listener before applicationInit, and publishes normalized,
in-memory `OnshapeClientContext` through React context. StrictMode effect replay
reinstalls the listener without sending duplicate initialization. Unmount removes
it. Nothing attaches a bridge to the development simulator.

1. An iframe plus the `/extension` path chooses embedded presentation only.
2. A bounded query parser validates IDs and rejects duplicate/unknown parameters.
3. `server` must normalize to the operator-owned exact allowlist in
   `apps/web/src/onshape/policy.ts`, currently only `https://cad.onshape.com`.
   A nonempty referrer with a different origin rejects the launch. An absent
   referrer grants nothing; the incoming origin/source checks remain mandatory.
4. Each event must have that exact browser-supplied origin and `window.parent`
   source before its data is examined. Other frames on the same origin fail.
5. The documented exact `{messageName: 'show'}` focuses the active frame and preserves
   its selection. It provides no new context identity. `selection.ts` validates
   SELECTION after origin/source checks. Valid
   data atomically replaces selection; malformed trusted selection clears references
   to unavailable, never claiming an empty selection. Unsupported message names
   and messages from the wrong origin/source leave state unchanged.
6. The only outgoing message is applicationInit with documentId, workspaceId and
   elementId, sent once to the exact approved origin for a normalized workspace.
   Explicit version context is retained for display but never sent as workspaceId;
   version messaging remains unverified and is withheld. No wildcard or tokens are used.

Ordinary browser visibility and blur/focus preserve this same frame's validated
launch and latest verified selection. There is no automatic CAD read or repeated
applicationInit. Actual pagehide/navigation and persisted-pageshow restoration
clear selection and suspend acceptance; show alone cannot revive that old launch.
A fresh frame is required after navigation suspension. The official right-panel
sequence destroys the iframe when the panel closes and starts a new application
when it opens. This differs from switching ordinary browser tabs.
A changed Action URL loads a new frame/context and therefore clears old state.
No invented documentChanged/elementChanged message is accepted. Panel reopen starts
fresh. Without a documented selection timestamp/context contract, in-place geometry
freshness cannot be proven; later server reads must independently revalidate it.

The UI distinguishes STANDALONE, EMBEDDED_INITIALIZING, EMBEDDED_CONNECTED,
EMBEDDED_CONTEXT_ERROR and UNTRUSTED_ORIGIN. Connected means a validated supported
client message arrived, not OAuth authentication or CAD access. Launch IDs are
shown as abbreviated references with no fabricated document names. The UI reports
waiting/stale selection rather than claiming no selection from missing evidence.

## Normalized context and selection presentation

OnshapeClientContext holds documentId, elementId, approved server origin, and a
revision discriminated as workspace/workspaceId or version/versionId. Optional
microversionId is validated if supplied; do not add an unsupported right-panel
replacement parameter. Element type is reserved in the model but not guessed from
the registration context. Document/element names are not provided by this launch.

The currently registered Action URL supplies workspaceId from the documented
workspaceOrVersionId replacement for the human's actual workspace test. The parser
also preserves the explicit workspaceOrVersion=w/v plus workspaceOrVersionId form,
or versionId, never ambiguous combinations. A bare workspaceId carries no revision
kind evidence beyond its field name: a version ID mislabelled in that field cannot
be distinguished by its hexadecimal format. Keep this configured URL for workspace
tests only. Explicit version inputs stay versions and do not initialize messaging;
no version support is claimed for the workspace-only registration.
Onshape identifiers must be 24 lowercase hexadecimal characters. URL userinfo,
paths, query/fragment in server, nonstandard ports and unapproved hosts fail closed.
Known Onshape default parameters are validated then discarded. Unknown parameters,
including OAuth credentials or return URLs, are rejected without reflecting them.

`SelectionContext` reports waiting, available, stale or unavailable. The live adapter
accepts only zero or one item in `selections`. A single item must have own fields
selectionType `ENTITY`, entityType `FACE` or `EDGE`, and a nonempty string selectionId
of at most 1024 characters without C0/DEL controls. This bound is a resource limit,
not a guessed topology-ID syntax. occurrencePath must be absent or undefined;
assembly paths and other categories are unsupported. Unknown fields are discarded
without traversal. Only normalized type and opaque reference are retained in memory,
scoped to this launch and source element. Nothing is logged, persisted or submitted
to the backend. Multi-selection is rejected until independently verified; the DEV
simulator's multiple-edge label is presentation only.

An empty array produces **No selection**. A single FACE/EDGE produces **1 face selected**
or **1 edge selected**; a new valid message replaces the old selection atomically.
Malformed/unsupported selection content produces **Selection details unavailable** and
removes old references. Navigation suspension and fresh document/workspace/element
launches clear selection. When a trusted SELECTION supplies documented envelope
documentId/workspaceId/elementId fields, each must exactly match the validated
launch; a mismatch clears the context until a fresh launch. Unsupported context-change message names cannot
change launch context. No captured selection timestamp or context revision exists,
so geometry freshness and authorization still require future server verification.

The 2026-10-14 lifecycle repair rechecked the current official messaging and
right-panel sequence above. The general messaging guidance treats show as a focus
cue; it gives no selection-reset, browser-visibility or selection-replay guarantee.
The Element Tab page's hide/show semantics are not applied as a right-panel close
contract. No invented lifecycle message or requestSelection polling is used.

## Frame headers and authentication

Development HTTPS and production-preview responses send:

```text
Content-Security-Policy: frame-ancestors https://cad.onshape.com
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
```

Set these at production ingress too; HTML meta cannot enforce frame-ancestors.
Do not add X-Frame-Options DENY/SAMEORIGIN to the embedded entry. Only the configured
standard stack is supported; enterprise origins need an explicit operator policy
review, matching backend stack and real testing. Never allow arbitrary *.onshape.com.

Phase 2 sessions, encryption, redirects, OAuth state and CSRF are unchanged. The
bridge sits outside AuthGate so launch context can remain visible when the session
is unavailable. A signed-out/expired `/api/me` in a frame gets a restrained session
notice, **Check panel session**, top-level Continue with Onshape, and **Open Forge
in a new tab** with noopener/noreferrer. Rechecking calls only `/api/me`. It neither
exchanges provider credentials nor treats client context as authentication.

Unavailable session does not prove cookies were blocked: the user may simply be
signed out. A separate-tab login and a subsequent panel recheck distinguish this
operationally without moving credentials across windows. No localStorage token,
postMessage session relay, popup credential bridge or automatic cookie-policy change
is introduced. Existing `SESSION_SAMESITE=lax` cannot share its session in a cross-site
iframe. The existing operator option `none` still requires HTTPS and full CSRF
validation; it may be evaluated explicitly but is not changed by this phase.

The human's current real panel session works. Browser-wide compatibility is not
established by that single session. Remaining policy considerations:

- [Chromium](https://privacysandbox.google.com/cookies/prepare/overview): settings,
  Incognito and managed policies can restrict third-party cookies. None/Secure
  permits cross-site sending only where browser policy allows it.
- [WebKit/Safari](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/):
  third-party blocking prevents assuming a standalone login is available in-frame.
- [Firefox and other browsers](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies):
  partitioned storage can separate the Onshape-embedded session from top-level Forge.

Storage Access API is not implemented. Playwright fixtures verify the unavailable
session UI, not real Onshape browser-cookie compatibility. Record actual browser
version, cookie settings, certificate trust and results in the manual review.

## Exact local URLs and development simulator

Existing trusted local HTTPS is preserved. Check that the user's existing web/API
services are listening before starting another process. Browser-test servers use
separate ports and stop after verification.

- Standalone: `https://localhost:5173/`
- Extension entry without context: `https://localhost:5173/extension`
- Account: `https://localhost:5173/#/settings`
- DEV simulator: `https://localhost:5173/#/onshape-simulator`
- Existing UI lab: `https://localhost:5173/#/lab`
- OAuth callback (unchanged): `https://localhost:5173/auth/onshape/callback`

Use `make dev-api` and `make dev-web-https` if not running; never start a competing
server on the same ports. See AUTHENTICATION.md for existing certificate setup.
The ordinary HTTP lab also works at `http://127.0.0.1:5173/#/onshape-simulator` when
using `make dev-web` instead. Do not mix HTTP/HTTPS origins during authentication.

The DEV-only simulator is lazy imported behind import.meta.env.DEV. The production
build removes its route/component/fixtures and cannot enable it through a query or
storage flag. It previews standalone, missing/valid/invalid context, untrusted
server, no selection, one face, two edges, replacement/clear, document/element
switch, stale selection and unavailable auth. It states that selections are only
presentation fixtures. Message attacks run through unit and cross-origin browser
tests; simulator probes also exercise the pure bridge with a test-owned parent
object. No real window-message origin is trusted or bypassed, and no fake
authenticated session is created.

## Development-only sanitized selection diagnostic

This is separate from the synthetic simulator. In a real `/extension` frame with
validated launch context, scroll to **Selection diagnostic** below the Forge UI.
Click **Enable sanitized selection diagnostic** explicitly. It starts disabled on
every frame load and is available even when the iframe cannot access its session.
No query parameter, browser preference, or environment secret enables it.

The same single bridge first checks exact `event.origin === context.server` and
`event.source === window.parent`. Only a `messageName: "SELECTION"` envelope reaches
the observer. The diagnostic never modifies CAD state; the separate live parser
validates each payload independently and retains only its supported normalized fields. Development code is lazy-loaded only
under `import.meta.env.DEV`; production removes the observer call, UI and sanitizer
chunks. Tests inspect production assets and try query-flag activation.

The observer synchronously creates a new bounded structure and retains only that
sanitized string. It never retains raw data, logs it, sends it to the backend or
writes it to browser storage. It outputs fixed structural key names, primitive
types, capped array lengths and a small fixed vocabulary of geometry/type labels
on category fields. All other string values (including IDs, names and URLs) are
redacted; numbers and booleans are represented by type only. Secret-labelled
subtrees are suppressed. Unknown property names are also redacted, because object
keys can contain private IDs or names. This conservative choice may require a
follow-up diagnostic revision if the real schema uses unknown field names.

Limits: depth 6, 160 visited nodes, 24 fields per object, 3 array examples, reported
array length capped at 10,000, output capped at 24,000 characters, and at most one
capture per 100 ms. Cycles/non-plain objects/accessors are omitted; input toJSON is
never called. Traversal stops early. These bounds apply to Forge's processing and
output, not the browser's structured-clone work before a message is delivered.
No arbitrary input string is copied into the output.

**Copy sanitized structure** writes only that visible sanitized string to the
clipboard after an explicit click. If iframe clipboard policy denies access,
select the textarea contents and copy manually. **Clear diagnostic** removes the
sample, **Disable diagnostic** clears and stops capture, and frame reload disables
it. Clipboard content remains under the user's control after copying.

## Human extension registration

These instructions follow the current official form and Hello World workflow
linked above. The human has already registered and opened this extension. Preserve
that registration and Action URL during the selection retest.

1. Open [Onshape](https://cad.onshape.com). Account icon (top right) → **My account**
   → **Developer** → **OAuth applications** → existing **Forge Development**.
   Keep that application's identity, keys, redirects and OAuth settings.
2. Open **Extensions** → **Add extension**. Fill:
   - **Name:** Forge
   - **Description:** Forge document context panel (optional)
   - **Location:** Element right panel
   - **Context:** Inside part studio
   - **Action URL:** paste the exact single line below.
   - **Icon:** choose a Forge image. A source icon is supplied at
     `apps/web/public/forge-icon.svg`; icon upload-format acceptance is unverified.
3. Click **OK**. This is an embedded UI extension. There is no separate Action to
   create, no GET/POST/Open in new window action type or action body, and no second
   OAuth app. Application type stays **Integrated Cloud App**.
4. Keep only **Application can read your profile information (OAuth2ReadPII)**.
   No new CAD read/write/delete permission is justified by passive Phase 3 context.
   The Hello World sample's broad scopes are not evidence that passive messaging
   requires them. Verify actual launch availability; if Onshape refuses it, obtain
   an explicit scope requirement rather than silently broadening access.

```text
https://localhost:5173/extension?documentId={$documentId}&workspaceId={$workspaceOrVersionId}&elementId={$elementId}
```

Onshape appends `server` and other default query parameters. Do not hardcode a server
parameter or duplicate it. Do not paste a document URL or OAuth callback as Action URL.

5. Individual account: app **Details** → **Create store entry** → Category **Content**,
   Description **Forge document context panel**, Vendor Name **your name** → **Create**.
   Visit [App Store](https://cad.onshape.com/appstore?sort=date), select your private
   app → **Subscribe** → **Get for free** → **Close**. Reuse an existing private entry/
   subscription if present. Do not publish the app publicly.
6. Organization-owned app: administrator opens company/classroom/enterprise settings
   → **Applications** → select **Forge Development** → **Add users or teams** → select
   the testing user/team → **Add**. This internal assignment avoids a store entry.
7. If access has not been granted, open **My account → Applications**, select Forge
   and grant Onshape access. External OAuth remains unconfigured. The Forge sign-in
   button continues to start its backend OAuth flow directly.
8. Open/reload a Part Studio and click the **Forge icon in the right panel**. The
   extension is not inserted as a new document element through the + tab menu.

Localhost reaches the machine running the browser, not the developer's server from
another person's machine. Trust the certificate in that browser before embedding.
A managed browser or organization may prohibit localhost frames; use an explicitly
approved HTTPS development origin in that case and update fixed OAuth configuration
consistently. Do not weaken TLS or use a redirect to a different iframe origin.

## Manual real-Onshape capture (no CAD modification)

1. Start `make dev-api` and `make dev-web-https` in separate terminals if the
   corresponding ports are free. Use the existing trusted certificate and local
   settings. If PostgreSQL is stopped, use `make db-up`; do not delete its volume.
2. Visit `https://localhost:5173/`. Confirm certificate trust and the known working
   Phase 2 account. Never copy secret-bearing network data.
3. Register/assign the extension above. Open an existing test document containing
   a Part Studio with geometry; do not create/edit CAD for this test.
4. Click the Forge right-panel icon. Record browser/version and whether the account
   is visible. If unavailable, use **Open Forge in a new tab**, sign in, return and
   click **Check panel session**. Record a persistent restriction; the diagnostic
   remains usable without an authenticated iframe session.
5. Open **View CAD context** if the narrow layout hides the context rail. Compare
   abbreviated document/element references to the normal Onshape document URL.
   Check the workspace/version label; names must not be fabricated. Close the dialog.
6. Scroll down inside Forge to **Selection diagnostic**. Click **Enable sanitized
   selection diagnostic**. Expect the listening message. Do not open developer
   tools or copy raw postMessage/network payloads.
7. Clear any existing Onshape selection, then select exactly **one face**. Wait for
   **Sanitized SELECTION structure received**. Click **Copy sanitized structure**.
   Save/paste that text for Codex labelled **one face**. If clipboard access is
   denied, select the sanitized textarea text and copy it manually.
8. Clear Onshape selection first. Then click **Clear diagnostic** in Forge and
   select exactly **one edge**. Wait for a new received status, copy the structure
   and label it **one edge**.
9. Click **Clear diagnostic**, then click empty graphics space or press Space in
   Onshape to clear selection. Wait for a new received status. Copy and label it
   **selection cleared**. If no event arrives, report that fact; do not reuse the
   previous sample or infer an empty payload. Pause at least 100 ms between actions.
10. Give Codex only those three copied sanitized structures, plus browser/version
    and whether account/context worked. No credentials, names, full IDs, raw
    payloads or network export are required. If output says truncated or contains
    redacted-key placeholders, preserve them; do not fill in private values.
11. Switch to another existing Part Studio/element and confirm a new launch element
    and stale selection reset. Switch document, then close/reopen Forge. No previous
    selection should carry over, and diagnostic capture must start disabled again.
12. Click **Disable diagnostic** when finished. Leave the CAD model unchanged.

If no diagnostic appears, ensure the HTTPS Vite development server is running
(`make dev-web-https`, not a production preview), the extension Action URL resolves
its replacement parameters, and the CAD Context shows valid approved launch context.
If context is valid but no SELECTION envelope arrives, report the exact visible
status; do not broaden the origin policy or invent a message shape.

## Live adapter retest (existing registration)

1. Keep the exact registered Action URL above. Confirm `https://localhost:5173/`
   loads over trusted HTTPS. Leave the existing API/session configuration unchanged.
2. Close Forge in Onshape, reload the document page, then reopen the Forge right-panel
   icon in the same Part Studio workspace. This creates a fresh bridge rather than
   relying on Vite hot reload of an already initialized frame.
3. Confirm the authenticated display name and **Onshape workspace context**. In
   **View CAD context**, confirm abbreviated document/element/workspace references.
4. Close that dialog if it covers the graphics. Select one face, then reopen
   **View CAD context**: expect **1 face selected**. Enable the development Selection
   diagnostic below Forge if troubleshooting is needed. The corrected live FACE
   structure has been verified; share sanitized output only.
5. Select one edge after clearing the previous selection; expect **1 edge selected**.
   Click empty graphics space to clear; expect **No selection**. Repeat face/edge
   replacement without accumulating selections. Do not modify geometry.
6. Switch existing Part Studios, workspaces and documents; reopen Forge if Onshape
   destroys the extension. Confirm new abbreviated context and no previous selection.
   Close/reopen Forge and verify capture starts disabled and selection starts fresh.
7. Record the browser/version and visible results. Multiple selection, assembly paths,
   version messaging and browser-wide session compatibility remain unverified.

## Launch diagnostic and metadata compatibility

The development `/extension` page has **Launch context diagnostic** below the
workspace, before the selection diagnostic, including invalid-context/auth states.
Click **Show sanitized launch diagnostic**, then **Copy sanitized launch diagnostic**.
The output contains names, presence/types/lengths, validation/reason codes and the
approved normalized server origin only; it never contains ID/metadata values,
credentials or a raw URL. Unknown suspicious names are redacted. Clear removes the
report. Clipboard-policy failures have a manual textarea-copy fallback. Production
removes the UI and module; query flags cannot enable it.

The prior real capture showed valid CAD IDs/server but rejected ancillary metadata:
clientId's guessed syntax and the previously unknown sessionCompanyId/theme names.
Exactly those three metadata fields now use a nonempty, control-free, at-most-128
character opaque validator, then are discarded. They do not establish user/company
identity, theme or trust. Duplicate/unknown parameters still fail closed, and required
IDs/server/version validation is unchanged. The human now reports `valid-context`
with no reason codes. No Action URL or authentication change was required.

Phase 5 final live evidence (2026-10-14): the user verified FACE, EDGE and clear
selection, preserved FACE/inspection/capture time across an ordinary Chrome tab
switch with no CAD refresh/reopen demand, and cleared old evidence on a real Part
Studio change. This supersedes the earlier requirement to retest those repairs.
No selection ownership or wider browser/provider compatibility claim is made.

## Phase 9B controlled Modify validation

The existing Action URL, redirects, context bridge and FACE/EDGE messaging remain.
Selection does not identify feature ownership. Modify obtains fresh authorized
server inventory and opaque candidate handles, with explicit target choice and
approval. Only a workspace Part Studio on the standard configured stack is supported.
The private suppression client uses pinned document microversions and a mandatory
provider skew guard; no general REST or FeatureScript authority is exposed.

Writes default OFF; external app permissions were not changed. Human owners must
retain OAuth2ReadPII/OAuth2Read, add OAuth2Write only, and explicitly reauthorize.
Unknown scope evidence fails closed. Follow [the runtime review](PHASE_9_REVIEW.md)
for exact OAuth, disposable CAD, suppression-payload Gate A, atomic stale-rejection
Gate B and screenshot instructions. Real CAD-write validation remains pending.

## Hosted URL transition plan

The deployment foundation now serves `/extension` from the same FastAPI service as
`/api` and `/auth`, with the existing exact Onshape frame policy. No registration,
OAuth scope, credential or Action URL is changed. See
[DEPLOYMENT.md](DEPLOYMENT.md) for the final HTTPS callback/Action URL shapes,
Onshape-added default parameters (do not hardcode server), embedded cookie limits
and the later coordinated Railway/custom-domain transition.
