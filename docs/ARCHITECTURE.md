# Architecture

## Current implementation — Phase 2 authentication

One React/TypeScript/Vite web client, one FastAPI/Pydantic API and shared presentation
primitives serve desktop browsers. Native clients are not part of Forge.

The Phase 1 Design/Modify/Learn shell remains, now behind an Onshape sign-in gate.
The development UI lab is independent of authentication and remains excluded from
production builds. Engineering workflows remain local or explicitly synthetic.
No AI, CAD reads/writes or extension messaging are implemented.

FastAPI owns OAuth code exchange, identity, revocable opaque sessions, encrypted
refresh tokens and CSRF. SQLAlchemy models and Alembic migrations use PostgreSQL.
Browser status calls receive minimized identity, connection status and CSRF data.
No provider credentials cross into the browser. See [AUTHENTICATION.md](AUTHENTICATION.md)
for the sequence, model contracts, cache/refresh tradeoffs and lifecycle semantics.

`GET /health` still means liveness only. Database schema checks run at startup when
DATABASE_URL is supplied. Without credentials the app starts and reports sign-in
unconfigured. Production fails closed on incomplete auth settings. Tests inject
HTTP transports; no runtime setting enables mock sessions.

## Intended component responsibilities

| Component        | Responsibility                                                                                      | Current state                                           |
| ---------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Frontend         | Narrow-panel UI, accessible controls, typed API calls, approved plan presentation                   | Authenticated local UI + DEV fixtures                   |
| API              | Configuration, sessions, authorization, validated contracts, orchestration                          | OAuth, sessions, CSRF and liveness                      |
| Database         | Users linked to Onshape identity, encrypted token records, sessions, plans, inventory, audit events | Identity, grants, sessions, states and audit migrations |
| AI layer         | Responses API, bounded agent loop, allowlisted functions, streamed user-facing status               | Documentation only                                      |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | OAuth and identity only; CAD planned                    |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Documentation only                                      |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | Documentation only                                      |

Backend `auth/` owns identity/security and `db/` owns persistence. `integrations/`
and `validation/` reserve the future CAD/AI and deterministic validation boundaries.
No authentication helper is exposed as a model tool.

## Planned flow and trust boundaries

```text
Onshape parent frame -> origin/schema-checked browser messaging -> Forge web UI
Forge web UI -> authenticated same-origin API -> scoped orchestration
orchestration -> Responses API -> proposed allowlisted tool calls
tool gate -> authorization + approved plan + validated arguments -> Onshape adapter
Onshape adapter -> official REST API -> reinspection -> deterministic validator
API -> minimized PostgreSQL records + sanitized audit events
```

Every arrow crosses an explicit boundary. Browser document/element IDs, selections,
text prompts, CAD metadata, and model output are untrusted inputs. Origin validation
does not establish authorization; the API must independently verify that the
current session may access the exact Onshape resource. Model arguments are requests
for an operation, never evidence of permission or correctness.

Approval must identify the user, target document/workspace/element, immutable plan,
units, operations, and inspected version. Reinspect stale context before executing.
Do not blindly repeat timed-out writes; reconcile the resulting CAD state first.
Keep units and bounds explicit, and treat missing evidence as UNVERIFIED.

## Development decisions

- **npm workspaces:** Node already includes npm. A second package manager or a
  monorepo orchestration framework would add no value for two small workspaces.
- **One uv project:** Python dependencies/lockfile/environment live in `apps/api`.
  Adding a Python workspace is unnecessary until there are multiple Python packages.
- **Native web/API, containerized database:** faster reloads and fewer Dockerfiles.
  Production images are deferred to the deployment phase.
- **Source-exported design system:** Vite compiles the local TypeScript package;
  it is private and not published. It exports semantic tokens, component styles
  and reusable accessible primitives backed by Radix where appropriate.
- **Small local UI state:** React hooks and a hash subscription own Phase 1 UI
  state. No router, global-state framework, motion library or AI SDK was added.
  Five small Radix packages provide focus management, keyboard behavior and
  notifications. The development-only lazy import is eliminated by production
  compilation, including its synthetic fixture module.
- **PostgreSQL 18:** pinned release image, persistent volume mounted at the supported
  parent path, a real health check, and host access limited to loopback.
- **Health is liveness:** database readiness and external-service checks need a
  separate future contract. Returning `ok` does not validate integrations.

This follows the requested layout. Additional configuration, lockfiles, and a
development supervisor support reproducibility; no substantive structural deviation
or alternate framework was introduced.

## Planned deployment

Serve the built SPA and `/api` through one HTTPS origin, with the API and managed
PostgreSQL on private networks. A same-origin proxy avoids permissive CORS. A worker
may become appropriate for long-running operations, but is not part of Phases 0–2.
Use production secret management, encryption key rotation, backups, migration
review, request/rate/usage limits, sanitized telemetry, and deployment gates.

Set the extension's `frame-ancestors` allowlist at the hosting layer after verifying
registered Onshape environments. Browser third-party-cookie restrictions require
real embedded-session testing. Do not assume an iframe works because the standalone
UI renders. [SECURITY.md](SECURITY.md) records the required controls;
[ONSHAPE.md](ONSHAPE.md) records integration verification gates.

## Phase 2 deployment decisions

- Vite proxies `/auth` and `/api` unchanged to FastAPI; the historical `/api/health`
  liveness proxy is retained. Production hosting must make the same paths available.
- Standard-library primitives provide randomness, hashing and HMAC. cryptography
  provides authenticated encryption; Alembic provides migrations. The existing
  httpx2 transport dependency is now a runtime dependency. No framework change.
- Access tokens remain ephemeral; refresh tokens are encrypted in PostgreSQL.
  Per-grant row locks coordinate workers. A cache miss can add one refresh per
  worker, trading modest provider traffic for less persisted sensitive data.
- Identity includes its configured Onshape stack; company context is operator-owned.
  Multi-stack routing and live enterprise validation remain future work.
- Credentials and live OAuth are externally configured and remain unverified.
  Phase 3 has not begun.
