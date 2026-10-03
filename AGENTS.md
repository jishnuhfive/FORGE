# Forge engineering instructions

## Before changing anything

1. Read this file before making changes, then read the relevant files in `docs/`.
2. Inspect the actual code, configuration, lockfiles, tests, and Git status. Do not
   assume that a documented future capability is implemented.
3. Work within the phase authorized by the user. Phase 0 establishes foundations
   only; do not proceed to Phase 1 or add product behavior without authorization.

## Architecture and stack

- Forge is one cross-platform web application embedded in Onshape's right panel,
  serving desktop browsers on macOS and Windows; there are no native client apps.
- Preserve React, TypeScript, Vite, Tailwind, accessible primitives, FastAPI,
  Pydantic, SQLAlchemy, PostgreSQL, uv, Docker Compose, and Git.
- npm workspaces own JavaScript dependencies; `apps/api/uv.lock` owns Python
  dependencies. Commit lockfiles and use frozen installs for verification.
- Never silently introduce a competing framework or package manager. Document a
  concrete incompatibility and the migration rationale before changing the stack.
- Avoid unnecessary dependencies. Prefer clear, maintainable code over cleverness.
- Shared presentation primitives belong in `packages/design-system`; business
  logic belongs in the API, not in that package or the browser.

## Security and integration boundaries

- Never commit secrets, local environments, tokens, private CAD data, or keys.
  `.env.example` contains empty placeholders only. Do not print secrets in tools,
  logs, test failures, screenshots, or documentation.
- OpenAI API keys and Onshape OAuth tokens must remain backend-only. Never put
  them in frontend source, `VITE_*` variables, browser storage, or browser payloads.
- Forge will use Onshape OAuth2, not its own password database. Server-side
  sessions and encrypted tokens require the controls in `docs/SECURITY.md`.
- The AI model must never receive arbitrary shell, raw HTTP, or raw Onshape API
  execution capabilities. Use allowlisted, high-level Forge tools.
- Use strict schemas at all boundaries, including configuration, API responses,
  AI arguments, Onshape responses, and future `postMessage` events.
- All future CAD-changing operations require authentication, object-level
  authorization, schema and unit validation, numeric bounds, logging, and result
  verification. Bind user approval to a specific plan and document version.
- Keep deterministic engineering validation separate from LLM judgment. Preserve
  PASS, WARNING, FAIL, and UNVERIFIED; never fabricate validation or success.
- Never expose or persist private chain-of-thought/model reasoning. Persist only
  useful user-facing plans, actions, statuses, approvals, and verified results.
- Use official supported APIs. Add no fake integrations, mock success states, or
  simulated service readiness to product interfaces.

## Quality and verification

- Add meaningful tests for every important new behavior; test failure paths and
  security boundaries when those behaviors are introduced.
- After substantial changes run `make format`, `make lint`, `make typecheck`,
  `make test`, and `make build`. Run `make test-e2e` for browser changes.
- Run `make compose-check` for infrastructure changes and verify real database
  health where Docker is available. Shut down services you started.
- Fix failures before declaring a phase complete. Explicitly report credentials,
  external services, platform restrictions, or tools that prevent verification.
- Maintain strict TypeScript and Python type checking, accessibility, browser
  compatibility, narrow-panel layouts, and professional code quality.
- Update architecture, security, development, and roadmap documentation whenever
  implementation choices or controls change. Label future work as planned.
- Run dependency audits and inspect changes for secrets before committing. Do not
  claim security certifications or production readiness from passing tests alone.

## Git and scope discipline

- Preserve user changes and inspect status before editing, staging, or committing.
- Keep commits understandable and scoped. Do not invent a Git identity, publish
  to a remote, change global Git settings, or delete user data without authority.
- Never silently erase database volumes or use destructive resets. `db-down`
  stops containers while retaining data.
- Do not develop weapons or harmful-device features. Forge v1 focuses on education,
  makers, student engineering, and low-risk mechanical prototyping. Design help
  and validation are not professional engineering certification.

## Documentation map

- `docs/ARCHITECTURE.md`: components, trust boundaries, deployment, decisions.
- `docs/SECURITY.md`: implemented controls and future security requirements.
- `docs/AI_AGENT.md`: planned agent loop, safe tools, validation and limits.
- `docs/ONSHAPE.md`: planned OAuth, extension, messaging, REST integration.
- `docs/DEVELOPMENT.md`: setup, commands, testing, platform notes, infrastructure.
- `docs/ROADMAP.md`: phase boundaries and future implementation sequence.
