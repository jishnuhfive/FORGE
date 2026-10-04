# Architecture

## Current implementation — Phase 1 UI foundation

Forge is a monorepo with one web client (`apps/web`), one Python API (`apps/api`),
and a shared presentation package (`packages/design-system`). It is intended to
run inside Onshape as a right-panel web extension on macOS and Windows desktop
browsers. It does not require native applications on either platform.

The client now provides a narrow-panel Design/Modify/Learn shell, local drafts,
an authored lesson preview, settings, onboarding and empty history. A DEV-gated
UI lab supplies synthetic engineering briefs, plans, progress, validation,
selection and history. It never invokes the backend, AI or CAD services.

The API still exposes only `GET /health` plus development documentation.
SQLAlchemy/psycopg remain dependencies only. PostgreSQL can start independently
through Compose. No backend domain models, migrations, authentication, model
calls, external adapters or executable CAD workflows have been added.

See [UI.md](UI.md) for component ownership, state contracts, tokens and route
behavior. No live Onshape integration exists yet. No OpenAI calls exist yet.
No CAD is modified. Phase 2 is not implemented.

## Intended component responsibilities

| Component        | Responsibility                                                                                      | Current state                   |
| ---------------- | --------------------------------------------------------------------------------------------------- | ------------------------------- |
| Frontend         | Narrow-panel UI, accessible controls, typed API calls, approved plan presentation                   | Local UI + development fixtures |
| API              | Configuration, sessions, authorization, validated contracts, orchestration                          | Settings and liveness only      |
| Database         | Users linked to Onshape identity, encrypted token records, sessions, plans, inventory, audit events | Container only                  |
| AI layer         | Responses API, bounded agent loop, allowlisted functions, streamed user-facing status               | Documentation only              |
| Onshape layer    | Server REST adapter, OAuth, document inspection, supported feature/assembly operations              | Documentation only              |
| Validation layer | Unit-aware deterministic calculations and evidence-backed results                                   | Documentation only              |
| Tool layer       | High-level operations joining user permissions, approvals, schemas, adapters, verification          | Documentation only              |

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
may become appropriate for long-running operations, but is not part of Phases 0–1.
Use production secret management, encryption key rotation, backups, migration
review, request/rate/usage limits, sanitized telemetry, and deployment gates.

Set the extension's `frame-ancestors` allowlist at the hosting layer after verifying
registered Onshape environments. Browser third-party-cookie restrictions require
real embedded-session testing. Do not assume an iframe works because the standalone
UI renders. [SECURITY.md](SECURITY.md) records the required controls;
[ONSHAPE.md](ONSHAPE.md) records integration verification gates.
