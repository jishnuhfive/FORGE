# Architecture

## Phase 0 implementation

Forge is a monorepo with one web client (`apps/web`), one Python API (`apps/api`),
and a shared presentation package (`packages/design-system`). It is intended to
run inside Onshape as a right-panel web extension on macOS and Windows desktop
browsers. It does not require native applications on either platform.

Currently the client shows only Forge, its purpose, and the Phase 0 label. The
API exposes `GET /health` plus development documentation. SQLAlchemy/psycopg are
dependencies only. PostgreSQL can start independently through Compose. There are
no domain models, migrations, authentication, model calls, external adapters,
or product workflows.

## Intended component responsibilities

| Component        | Responsibility                                                                                      | Phase 0 state              |
| ---------------- | --------------------------------------------------------------------------------------------------- | -------------------------- |
| Frontend         | Narrow-panel UI, accessible controls, typed API calls, approved plan presentation                   | Static placeholder         |
| API              | Configuration, sessions, authorization, validated contracts, orchestration                          | Settings and liveness only |
| Database         | Users linked to Onshape identity, encrypted token records, sessions, plans, inventory, audit events | Container only             |
| AI layer         | Responses API, bounded agent loop, allowlisted functions, streamed user-facing status               | Documentation only         |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | Documentation only         |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Documentation only         |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | Documentation only         |

Reserved backend ownership boundaries are described in `src/forge_api/db/`,
`integrations/`, and `validation/` README files. These are documentation placeholders,
not runnable implementations or capabilities advertised to the model.

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
  it is private and not published. It exposes a Radix separator and a static badge.
- **No motion, router, state framework, or AI SDK:** Phase 0 has no behavior that
  warrants these dependencies. Add only when an authorized feature requires them.
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
may become appropriate for long-running operations, but is not part of Phase 0.
Use production secret management, encryption key rotation, backups, migration
review, request/rate/usage limits, sanitized telemetry, and deployment gates.

Set the extension's `frame-ancestors` allowlist at the hosting layer after verifying
registered Onshape environments. Browser third-party-cookie restrictions require
real embedded-session testing. Do not assume an iframe works because the standalone
placeholder renders. [SECURITY.md](SECURITY.md) records the required controls;
[ONSHAPE.md](ONSHAPE.md) records integration verification gates.
