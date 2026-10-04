# Planned Onshape integration

## Phase 1 status

No OAuth routes, Onshape SDK/client, client-messaging listener, extension registration,
CAD inspection, writes, assembly operations, or API calls exist. The standalone
UI does not prove that embedding or authentication works. Integration
capabilities below are planned and require live official-platform verification.

## Authentication and extension

Register an Integrated Cloud App with an Onshape right-panel extension. One deployed
web application serves desktop Onshape on macOS and Windows. Use official Onshape
OAuth2 for sign-in/authorization with least-privilege scopes and backend code exchange;
Forge stores no passwords. Keep access/refresh tokens encrypted server-side. See
[SECURITY.md](SECURITY.md) for state, sessions, refresh coordination, CSRF, disconnect,
and account deletion.

Use a registered HTTPS callback and test it through Onshape's developer environment.
Do not assume a local HTTP web callback is supported or expose development servers
to the internet as a shortcut. Obtain developer access/registration only when the
OAuth phase is authorized. Public App Store publication has separate review and
launch requirements.

Official starting points:

- [Onshape developer settings and application registration](https://cad.onshape.com/help/Content/Plans/my_account_developer.htm)
- [Onshape integration FAQ](https://www.onshape.com/en/app-integrations/faq)
- [Onshape developer documentation](https://onshape-public.github.io/docs/)
- [Official REST API explorer](https://cad.onshape.com/glassworks/explorer/)

Use current developer documentation for exact extension locations, contexts,
message schemas, API versions, scopes, and supported operations. Do not invent
endpoint URLs or claim that every mate/feature is writable through REST.

## Messaging and selections

Treat extension launch parameters, document/workspace/element context, selection
events, and parent-window messages as untrusted references. Establish allowed
origins from registered environments; compare exact origins, never substring or
suffix matches. Validate expected source window, event type, strict message schema,
size, identifiers, and freshness. Send messages with an explicit target origin.

Selection context should identify document, workspace/version, element, entity type,
and supported entity references. Do not rely on display names as stable IDs. Clear
stale selections when the document context changes. Unsupported entity/event types
must yield an explicit unsupported result, not an assumed selection.

The browser forwards permitted context to Forge's API. The backend independently
checks the session and resource permissions through the official adapter. A valid
message origin does not authorize a user to access another user's CAD document.
Resolve iframe cookie/storage limitations with real browser tests in Phases 2–3.

## REST adapter and safe operation layer

The backend-only adapter will own OAuth injection, approved base hosts, fixed
endpoint construction, API-version handling, strict response parsing, timeouts,
sanitized errors, and bounded rate-limit retries. Do not accept arbitrary user/model
hosts, URLs, headers, or methods. Keep provider tokens out of returned objects.

Read-only capabilities will be introduced before writes: document/Part Studio
inspection, features, assemblies, instances, mass/material properties where
supported. Later writes may create features, assembly instances, and supported
mates through narrowly scoped tools. Verify official support and permissions before
advertising each operation. Separate immutable versions from writable workspaces.

A high-level safe-tool layer sits above the adapter. All CAD-changing operations
must pass authentication, object-level authorization, strict schema and unit
validation, numeric bounds, approval/version checks, sanitized audit logging, and
result verification. Reinspect after writes; reconcile ambiguous network failures
before retries. Record partial outcomes and offer a reviewed revision plan; never
assume cross-service database/CAD transactions are atomic.

## Verification gates for later phases

- Prove OAuth state/replay protection, token refresh, logout, disconnect, and deletion.
- Prove narrow-panel embedding and secure sessions in real supported browsers.
- Prove message origin/schema checks and selection freshness with forged/stale inputs.
- Prove object permissions on inaccessible and cross-account documents.
- Establish API quotas, rate-limit response behavior, bounded retries, and timeouts.
- Exercise read-only inspection before the first user-approved write in a sandbox document.
- Verify editable parametric geometry and supported mates from actual inspected results.
- Meet Onshape launch requirements before public App Store submission.

Phase 1 provides labeled development-only UI fixtures for these future flows.
They perform no integration requests, execution or evidence collection.
