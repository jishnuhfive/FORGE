# Forge

AI engineering inside Onshape.

Forge is a planned mechanical engineering and CAD agent embedded in Onshape's
right panel. Users describe **what** a mechanism must accomplish; Forge will help
determine **how** it should be engineered, with approval before CAD changes and
deterministic checks of supported constraints.

**Current status: Phase 0 — Foundation.** This repository contains a minimal web
page, a health-only API, local PostgreSQL infrastructure, development tools,
tests, and architectural documentation. Live OpenAI, Onshape, OAuth, CAD generation,
and engineering validation are **not implemented**. No Phase 1 UI is included.

## Architecture and stack

One React + TypeScript + Vite web application will serve desktop browsers on
macOS and Windows. Tailwind CSS, Radix accessible primitives, and Lucide provide
the presentation foundation. No animation library is needed in Phase 0.

FastAPI + Pydantic owns server boundaries; SQLAlchemy and psycopg are installed
for future PostgreSQL access, but no database models, connections, or migrations
exist yet. uv manages Python. npm workspaces manage the web and shared design
system. Docker Compose runs PostgreSQL; native development servers provide fast
reloads. Git provides local source control; no remote is configured.

## Prerequisites

- Node.js 24 LTS and npm 11.
- Python 3.14 and uv; the API lockfile supports Python 3.14.
- Git, Docker with a running daemon, Docker Compose, and GNU Make 3.81+ on macOS.
- Playwright browsers for browser tests, installed explicitly with `make browsers`.

Versions actually verified are recorded in `docs/PHASE_0_REVIEW.md` after validation.
No OpenAI key, Onshape account, or GitHub account is required for Phase 0.

## Quick start

From the repository root:

```sh
make setup
make db-up
make dev
```

Open <http://127.0.0.1:5173>. The API health endpoint is
<http://127.0.0.1:8000/health>; development API docs are at
<http://127.0.0.1:8000/docs>. Ctrl+C stops both native development servers.
`make db-down` stops PostgreSQL and retains its data.

No `.env` file is required. `.env.example` contains empty placeholders for future
configuration. The local database uses deliberately public development defaults
on loopback only. See [development](docs/DEVELOPMENT.md) before overriding them.

## Developer commands

| Command                         | Purpose                                                          |
| ------------------------------- | ---------------------------------------------------------------- |
| `make setup`                    | Install JavaScript and Python dependencies from lockfiles        |
| `make dev`                      | Run the native web and API servers together                      |
| `make dev-web` / `make dev-api` | Run one server independently                                     |
| `make test`                     | Run Vitest/React Testing Library and Pytest                      |
| `make browsers`                 | Install Playwright Chromium, Firefox, and WebKit                 |
| `make test-e2e`                 | Test the built placeholder in three browser engines; build first |
| `make lint`                     | Check ESLint, Prettier, Ruff lint, and Python formatting         |
| `make typecheck`                | Run strict TypeScript and mypy checks                            |
| `make format`                   | Format with Prettier and Ruff                                    |
| `make build`                    | Build the web application                                        |
| `make compose-check`            | Validate Compose without starting services                       |
| `make db-up` / `make db-down`   | Start a healthy database / stop it, keeping data                 |
| `make audit`                    | Scan npm and Python dependencies for known vulnerabilities       |
| `make check`                    | Run lint, types, unit tests, build, and Compose validation       |

`make smoke` additionally verifies real native web/API startup, health, proxy,
and clean shutdown. Ports 5173 and 8000 must be free.

## Repository structure

```text
apps/web/                 React/Vite placeholder and frontend unit tests
apps/api/                uv-managed FastAPI source, tests, and Python lockfile
packages/design-system/  Shared accessible presentation primitives
docs/                    Architecture, security, integrations, workflow, roadmap
infra/                   Local infrastructure notes
scripts/                 Native development server supervisor
tests/e2e/               Playwright browser tests
AGENTS.md                Permanent instructions for future engineering sessions
docker-compose.yml       Local PostgreSQL and health check
Makefile                 Root command interface
package-lock.json        Reproducible JavaScript dependency graph
```

## Scope, limitations, and security

`GET /health` reports process liveness only. It does not claim database, OpenAI, or
Onshape readiness. The placeholder's phase label is a development label, not a
service-health indicator. Design/Modify/Learn modes, authentication, inventory,
agent tools, audit persistence, and CAD editing await later phases.

Never commit secrets. Keep future OpenAI keys and Onshape tokens backend-only.
No client `VITE_*` secret variables are defined. Production sessions, encrypted
tokens, authorization, rate limits, request limits, CSP, and deployment controls
are documented requirements, not finished controls. Phase 0 is not a production
release and claims no security certification.

Forge v1 targets education and low-risk mechanical prototyping. Future results
must distinguish PASS, WARNING, FAIL, and UNVERIFIED. Design assistance is not
professional engineering certification.

## Development expectations

Read [AGENTS.md](AGENTS.md), [architecture](docs/ARCHITECTURE.md), and
[development](docs/DEVELOPMENT.md) before changes. Preserve the agreed stack,
write meaningful tests for important behavior, run quality checks, and document
architecture changes. Never add fake integrations or fabricate validation results.
Advance only into the phase explicitly authorized by the user. This repository
has no public contribution policy or open-source license selected yet.
