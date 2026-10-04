# Development

## Prerequisites and ownership

Use Node.js 24 LTS/npm 11, Python 3.14/uv, Git, Docker with a running daemon,
Docker Compose, and GNU Make 3.81+ on macOS. The same web product targets desktop
Windows browsers. SQLAlchemy, Alembic and PostgreSQL persist Phase 2 identity and authentication.
React/TypeScript/Vite/Tailwind are project dependencies, not global installations.
No credentials are required for automated tests or the development UI lab.
Real OAuth requires the setup in [AUTHENTICATION.md](AUTHENTICATION.md).

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
local API without rewriting; `/auth/*` is proxied as well. The legacy
`/api/health` alias alone forwards to `/health`. No broad CORS policy is enabled.
The sign-in gate reads `/api/me`; engineering previews still make no CAD/AI requests.

`scripts/dev.py` starts both servers and stops the other if one exits or Ctrl+C is
pressed. Occupied ports cause a clear failure; do not stop unrelated processes to
free them. `make dev-web` and `make dev-api` run individual servers. Database startup
is separate; the liveness API does not need a database. API access logging is disabled
in development commands to avoid creating future sensitive URL/header logs by default.

Native servers intentionally avoid container rebuilds during editing. Only PostgreSQL
is containerized in Phase 0. Production containers, HTTPS hosting, deployment,
and network policy belong to later authorized phases. Phase 2 adds Alembic migrations.

`make smoke` checks real web/API startup, `/health`, the development API proxy, and
clean shutdown. It requires free ports 5173/8000 and never stops existing services.

## Configuration

No `.env` is required. To customize configuration, copy `.env.example` to a local,
ignored `.env` and populate only necessary settings. The API loads it from the
repository root regardless of the working directory. Process environment values
take precedence. Empty values use defaults; invalid environment names/URLs fail
validation. Production hides API docs but does not turn this scaffold into a
production-ready service.

See [AUTHENTICATION.md](AUTHENTICATION.md) for the complete local HTTPS credential
setup. Settings actually read by Phase 2:

| Setting                                         | Meaning/default                                                 |
| ----------------------------------------------- | --------------------------------------------------------------- |
| ENVIRONMENT                                     | development, test or production                                 |
| APP_BASE_URL                                    | Exact frontend origin; `http://127.0.0.1:5173` by default       |
| DATABASE_URL                                    | Optional PostgreSQL URL; configured DB must already be migrated |
| TOKEN_ENCRYPTION_KEY                            | Required to enable OAuth; Fernet key, backend-only              |
| TOKEN_ENCRYPTION_PREVIOUS_KEYS                  | Optional comma-separated decryption key ring                    |
| ONSHAPE_CLIENT_ID / ONSHAPE_CLIENT_SECRET       | Registered confidential client credentials                      |
| ONSHAPE_REDIRECT_URI                            | Exact APP_BASE_URL plus `/auth/onshape/callback`                |
| ONSHAPE_AUTHORIZATION_URL                       | `https://oauth.onshape.com/oauth/authorize`                     |
| ONSHAPE_TOKEN_URL                               | `https://oauth.onshape.com/oauth/token`                         |
| ONSHAPE_API_BASE_URL                            | `https://cad.onshape.com/api`; operator-configured stack        |
| ONSHAPE_COMPANY_ID                              | Optional validated enterprise company identifier                |
| SESSION_SAMESITE                                | lax default; none requires HTTPS                                |
| SESSION_LIFETIME_SECONDS / SESSION_IDLE_SECONDS | 28800 / 3600, validated bounds                                  |
| POSTGRES_*                                      | Local Compose overrides                                         |

Empty placeholders keep defaults. Production requires HTTPS and complete auth
configuration; a database/key/credential failure never enables mock login. No
SESSION_SECRET is needed for opaque server-side sessions. OpenAI remains unimplemented.

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

The database URL format is
`postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/DATABASE`, populated through an
ignored environment file or secret manager. The API uses the explicitly configured value and never prints it. Changing `POSTGRES_*` initialization settings does not change an existing
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
onboarding, storage validation and development preview behavior. Pytest exercises liveness, config, migrations, OAuth state/callback/identity, session
expiry/revocation, CSRF, refresh rotation, encryption and sensitive-log exclusions.
`make test-postgres` with FORGE_TEST_DATABASE_URL explicitly set adds real PostgreSQL
migration and concurrency checks in isolated, temporary schemas.
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

Open <http://127.0.0.1:5173> for the sign-in gate and
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

OAuth code exists, but real OAuth requires credential verification. No OpenAI calls
exist and no CAD is read or modified. Sample approval and Apply actions only change local preview state.
Manufacturing fields use explicit mm, regardless of the saved future units
preference. Read [UI.md](UI.md) for state ownership and fixture behavior.

## Authentication migrations and checks

`make migrate` applies the additive authentication migration. `make migration-check`
checks for model/schema drift against the configured database. Startup refuses an
unmigrated database; it never runs schema creation or destructive repair.

Real PostgreSQL verification uses a public local development URL only:

```sh
FORGE_TEST_DATABASE_URL='postgresql+psycopg://forge_local:local-development-only@127.0.0.1:5432/forge_local' make test-postgres
```

The tests create/drop only their own UUID-named schemas, preserving application data.
Default tests use migrated temporary SQLite databases for fast isolation; SQLite is
permitted only in test configuration. Production refresh locking is separately
verified with PostgreSQL. No real OAuth runs in the default suite.

`make dev-web-https` explicitly selects Vite's local-https mode and reads the ignored
`.certs/localhost.pem` and `.certs/localhost-key.pem`; it has no effect on normal builds.
Use `make dev-api` in another terminal. The certificate and trust setup are in
[AUTHENTICATION.md](AUTHENTICATION.md). No dev server is exposed to the internet.

The cryptography 50.0.2 wheel used here supports this Apple Silicon development host
and 64-bit Windows/Linux backend environments. Upstream removed Intel macOS and
32-bit Windows support; native backend development on those hosts is unverified.
This does not change Forge's browser support on macOS/Windows. See the
[upstream release notes](https://cryptography.io/en/latest/changelog/).
