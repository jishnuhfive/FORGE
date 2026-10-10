# Forge

AI engineering inside Onshape.

Forge is a planned mechanical engineering and CAD agent embedded in Onshape's
right panel. Users describe **what** a mechanism must accomplish; Forge will help
determine **how** it should be engineered, with approval before CAD changes and
deterministic checks of supported constraints.

**Current status: Phase 3 complete.** The human verified real Onshape right-panel
embedding, embedded authentication, launch context and FACE/EDGE/clear message
structures. The strict single-entity/clear adapter matches those live captures.
See [Phase 3 review](docs/PHASE_3_REVIEW.md). Forge has a responsive Design/Modify/Learn
workspace, Onshape sign-in, revocable server sessions, encrypted refresh tokens,
account controls and database migrations. The development UI lab works without an account.

**No OpenAI calls or CAD REST reads/writes exist.** `/extension` validates launch
context and receives narrowly validated client selection messages. Engineering
workflows remain local drafts or labeled synthetic previews. This is not a publicly
deployed production service. Phase 4 has not begun.

## Architecture and stack

One React + TypeScript + Vite web application will serve desktop browsers on
macOS and Windows. Tailwind CSS, Radix accessible primitives, and Lucide provide
the presentation foundation. Motion is limited to loading skeletons and respects reduced-motion preferences.

FastAPI + Pydantic owns server boundaries; SQLAlchemy and psycopg are installed
with Alembic for PostgreSQL authentication persistence. uv manages Python. npm workspaces manage the web and shared design
system. Docker Compose runs PostgreSQL; native development servers provide fast
reloads. Git origin is `https://github.com/jishnuhfive/FORGE.git`; Phase 2 main matches origin/main.

## Prerequisites

- Node.js 24 LTS and npm 11.
- Python 3.14 and uv; the API lockfile supports Python 3.14.
- Git, Docker with a running daemon, Docker Compose, and GNU Make 3.81+ on macOS.
- Playwright browsers for browser tests, installed explicitly with `make browsers`.

Versions actually verified are recorded in `docs/PHASE_0_REVIEW.md` after validation.
No OpenAI key, Onshape account, or GitHub account is required to review the UI.

## Quick start

For the sign-in screen and credential-free development UI lab, run:

```sh
cd /Users/jishnuhiremath/Developer/FORGE && make dev-web
```

Open <http://127.0.0.1:5173>. The development-only UI lab is
<http://127.0.0.1:5173/#/lab>. Account settings after sign-in: <http://127.0.0.1:5173/#/settings>.
Projects/activity: <http://127.0.0.1:5173/#/history>. Ctrl+C stops the server.

For a fresh checkout, run `make setup` first. `make dev` still starts both native
web and API servers. Optional PostgreSQL starts with `make db-up` and stops with
`make db-down`, retaining its data. Neither is required for the development UI lab.
The API health endpoint remains <http://127.0.0.1:8000/health>.

No `.env` is required for the UI lab or tests. Real login needs the exact
[Onshape application and local HTTPS setup](docs/AUTHENTICATION.md). `.env.example`
contains empty placeholders; never put real credentials in it. The local database uses deliberately public development defaults
on loopback only. See [development](docs/DEVELOPMENT.md) before overriding them.

## Developer commands

| Command                         | Purpose                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| `make setup`                    | Install JavaScript and Python dependencies from lockfiles    |
| `make dev`                      | Run the native web and API servers together                  |
| `make dev-web` / `make dev-api` | Run one server independently                                 |
| `make test`                     | Run Vitest/React Testing Library and Pytest                  |
| `make browsers`                 | Install Playwright Chromium, Firefox, and WebKit             |
| `make test-e2e`                 | Test production UI and dev lab in three engines; build first |
| `make lint`                     | Check ESLint, Prettier, Ruff lint, and Python formatting     |
| `make typecheck`                | Run strict TypeScript and mypy checks                        |
| `make format`                   | Format with Prettier and Ruff                                |
| `make build`                    | Build the web application                                    |
| `make compose-check`            | Validate Compose without starting services                   |
| `make db-up` / `make db-down`   | Start a healthy database / stop it, keeping data             |
| `make audit`                    | Scan npm and Python dependencies for known vulnerabilities   |
| `make check`                    | Run lint, types, unit tests, build, and Compose validation   |

`make smoke` additionally verifies real native web/API startup, health, proxy,
and clean shutdown. Ports 5173 and 8000 must be free.

## Repository structure

```text
apps/web/                 React/Vite workspace, feature views, UI lab and unit tests
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

`GET /health` reports process liveness only. Authentication readiness is distinct.
The workspace displays the last verified Onshape authorization status; its Check
connection action verifies identity, without accessing CAD. Design prompts remain
local drafts and Learn validation remains UNVERIFIED. See [UI architecture](docs/UI.md).

Provider credentials stay backend-only. Sessions, CSRF, token encryption and audit
persistence are implemented. Real OAuth login was manually verified by the human. Browser-wide iframe compatibility, managed hosting,
rate limits and operational launch controls still need verification/configuration.
See [Phase 2 review](docs/PHASE_2_REVIEW.md). No certification is claimed.

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

Phase 2 adds `make migrate`, `make migration-check`, `make test-postgres` and
`make dev-web-https`. See [authentication](docs/AUTHENTICATION.md) before using them
with real account credentials. Existing Phase 0 and Phase 1 commits remain intact.

Phase 3 extension registration, exact local URLs, source-contract gap and manual
acceptance steps: [Onshape extension](docs/ONSHAPE_EXTENSION.md).
