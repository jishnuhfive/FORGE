# Development

## Prerequisites and ownership

Use Node.js 24 LTS/npm 11, Python 3.14/uv, Git, Docker with a running daemon,
Docker Compose, and GNU Make 3.81+ on macOS. The same web product targets desktop
Windows browsers. SQLAlchemy and PostgreSQL are foundations for future persistence.
React/TypeScript/Vite/Tailwind are project dependencies, not global installations.
No Onshape, OpenAI, or GitHub credential is needed now.

Keep `package-lock.json` and `apps/api/uv.lock` committed. The API environment is
`apps/api/.venv`. Root npm workspaces link `@forge/design-system` locally. Do not
introduce pnpm/yarn or a second Python package manager.

## Setup

```sh
make setup
make browsers
make build
make test-e2e
```

`setup` uses `npm ci` and `uv sync --locked`; it does not create `.env` or configure
integrations. Browser installation is explicit and separate because it downloads
three browser engines. Run `make setup` again after pulling dependency changes.
An intentional dependency update requires npm install/uv lock, a lockfile review,
quality checks, and vulnerability auditing.

All project source/generated output belongs in Forge. Package-manager downloads
and Playwright browser executables may use normal per-user tool caches; these are
dependencies, not project source. Temporary review caches under the repository are
ignored. Don't copy project files elsewhere during development.

## Native development

```sh
make dev
```

Web: <http://127.0.0.1:5173>. API: <http://127.0.0.1:8000/health>.
OpenAPI development docs: <http://127.0.0.1:8000/docs>. Vite forwards `/api/*` to the
local API and strips `/api`; for example `/api/health` forwards to `/health`.
No broad CORS policy is enabled. The Phase 1 UI makes no API or external requests.

`scripts/dev.py` starts both servers and stops the other if one exits or Ctrl+C is
pressed. Occupied ports cause a clear failure; do not stop unrelated processes to
free them. `make dev-web` and `make dev-api` run individual servers. Database startup
is separate; the liveness API does not need a database. API access logging is disabled
in development commands to avoid creating future sensitive URL/header logs by default.

Native servers intentionally avoid container rebuilds during editing. Only PostgreSQL
is containerized in Phase 0. Production containers, HTTPS hosting, deployment,
network policy, and migrations belong to later authorized phases.

`make smoke` checks real web/API startup, `/health`, the development API proxy, and
clean shutdown. It requires free ports 5173/8000 and never stops existing services.

## Configuration

No `.env` is required. To customize configuration, copy `.env.example` to a local,
ignored `.env` and populate only necessary settings. The API loads it from the
repository root regardless of the working directory. Process environment values
take precedence. Empty values use defaults; invalid environment names/URLs fail
validation. Production hides API docs but does not turn this scaffold into a
production-ready service.

| Variable                                  | Phase 0 meaning                                                         |
| ----------------------------------------- | ----------------------------------------------------------------------- |
| `ENVIRONMENT`                             | development (default), test, or production                              |
| `APP_BASE_URL`                            | Frontend URL; default `http://localhost:5173`                           |
| `DATABASE_URL`                            | Optional redacted future connection URL; no connection is opened        |
| `SESSION_SECRET` / `TOKEN_ENCRYPTION_KEY` | Optional redacted future settings; no session/encryption implementation |
| `ONSHAPE_*`                               | Future OAuth placeholders only                                          |
| `OPENAI_API_KEY` / `OPENAI_MODEL`         | Future backend-only placeholders; no model calls                        |
| `POSTGRES_*`                              | Compose database/user/password/host-port overrides                      |

There are no `VITE_*` secrets. Never dump settings or `.env` contents into logs.
Onshape tokens and OpenAI keys must not enter frontend source or browser storage.

## PostgreSQL workflow

```sh
make compose-check
make db-up
docker compose ps
make db-down
```

Compose runs `postgres:18.6` pinned by image digest, exposes `127.0.0.1:5432`, and retains data in a named
volume at `/var/lib/postgresql`. `db-up` waits for `pg_isready` to pass. `db-down`
stops/removes containers and networks while retaining the volume.

Public local defaults are database/user `forge_local` and password
`local-development-only`. They are deliberate placeholders, **not secrets** and
must not be used beyond isolated local development. Compose uses these defaults
when overrides are absent or blank. Do not use trust authentication.

If database access is added later, the local URL format is
`postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/DATABASE`, populated through an
ignored environment file or secret manager. The API does not construct or use it
now. Changing `POSTGRES_*` initialization settings does not change an existing
database's credentials. No command deletes volumes; deletion requires a reviewed
decision and backups. Choose another `POSTGRES_PORT` if 5432 belongs to another app.

## Quality, tests, and audits

```sh
make format
make lint
make typecheck
make test
make build
make test-e2e
make audit
```

ESLint includes React hooks checks and rejects warnings. Playwright runs axe
accessibility checks against the rendered page. Prettier
handles web/config/documentation formatting; Ruff formats/lints Python. TypeScript
strict mode covers the app, shared package, Vite config, and browser tests. mypy
strict mode with the Pydantic plugin covers API source, tests, and the supervisor.

Vitest + React Testing Library exercise application landmarks, purpose and phase
labels, modes, composer behavior, brief/plan interactions, all progress states,
validation provenance, stale selections, lessons, error messages, settings,
onboarding, storage validation and development preview behavior. Pytest exercises `/health`, response shape, absent product routes,
production documentation policy, environment validation, and secret redaction.
Playwright tests the production SPA and development-only lab in Chromium, Firefox
and WebKit with axe WCAG checks, keyboard navigation, dialog focus, theme changes,
reduced motion and overflow checks. Build first. Production preview runs on port
4173 and the dev lab on 4174. Neither reuses an unrelated server. Both are stopped
by Playwright after the run. Chromium lab screenshots go to ignored
`.cache/phase1/` for visual review. Traces are retained only on failure and must not contain real private data.

`make audit` runs npm audit and pip-audit against installed dependencies. Investigate
findings and update within supported versions; don't automatically apply forced
major upgrades. Add deployment/CI scanning when a remote and CI provider are chosen.
No GitHub publishing or CI account is configured in Phase 0.

## Windows development notes

The product is browser-based and uses no platform-specific native client APIs.
macOS is the verified development host for Phase 0. Windows development is supported
by the same tools, but has not been verified on a Windows host yet. Make is optional
there; use a shell with the appropriate Python command and run these equivalents:

```sh
npm ci
uv sync --project apps/api --locked
python scripts/dev.py
npm test
uv run --project apps/api --frozen pytest apps/api/tests
npm run build
npm run test:e2e
docker compose up --detach --wait postgres
docker compose down
```

`python` may be `py` or `python3` depending on installation. The supervisor locates
platform executables through PATH and handles Windows child-process cleanup. The
macOS `npm run dev`/Make entry uses `python3`; call the supervisor directly with
the installed interpreter on Windows. Remaining lint/type commands map directly
to Makefile recipes, which use only Make 3.81-compatible syntax.

## Troubleshooting

- Connection refused for Docker: start Docker Desktop and check `docker info`.
- Tool missing: inspect PATH before installing anything; don't use Codex-private runtimes.
- Dependency checks fail: verify supported Node/Python versions and frozen installs.
- Browser missing: run `make browsers`; don't silently skip E2E verification.
- API config error: inspect variable names/validity without printing secret values.
- Database unhealthy: review local container logs; retain existing volumes and data.

## Phase 1 UI review

```sh
make dev-web
```

Open <http://127.0.0.1:5173> for the normal disconnected workspace and
<http://127.0.0.1:5173/#/lab> for synthetic previews. The lab has state, layout and
theme controls and an onboarding preview. Normal standalone pages use
`#/settings` and `#/history`. Hash navigation needs no server rewrite or router.
Production `make build` removes the lab, its route entry links and fixtures;
`#/lab` in a production preview falls back to the normal workspace.

Use browser responsive tools at 320, 380 and 480 px with an 850 px height, then
1280 px desktop width. Check every mode, settings, onboarding and below-fold
controls. Container queries also keep a narrow lab frame narrow on a wide screen.
The automated lab matrix covers every state at 320 px dark and 1280 px light.
Additional regular workspace coverage exercises all four widths and both themes.

No live Onshape integration exists yet. No OpenAI calls exist yet. No CAD is
modified. Sample approval and Apply actions only change local preview state.
Manufacturing fields use explicit mm, regardless of the saved future units
preference. Read [UI.md](UI.md) for state ownership and fixture behavior.
