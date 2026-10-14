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
exist. Only Phase 4’s explicit CAD Context action performs live CAD reads; no CAD is modified. Sample approval and Apply actions only change local preview state.
Manufacturing fields use explicit mm, regardless of the saved future units
preference. Read [UI.md](UI.md) for state ownership and fixture behavior.

## Authentication migrations and checks

`make migrate` applies the additive authentication migration. `make migration-check`
checks for model/schema drift against the configured database. Startup refuses an
unmigrated database; it never runs schema creation or destructive repair.

For real PostgreSQL verification, use the local connection URL from your ignored
`.env`. Replace the placeholder below; never put connection credentials in source
or share them:

```sh
FORGE_TEST_DATABASE_URL='<your-local-PostgreSQL-connection-URL>' make test-postgres
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

## Phase 3 development and verification

Use the existing HTTPS/API services. `/extension` is the same app's iframe entry;
`https://localhost:5173/#/onshape-simulator` previews synthetic presentation, including
multi-selection beyond the current live contract. No local-origin bypass exists.
See [ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md) for the unchanged Action URL,
registration, sanitized diagnostics and exact live retest procedure.

The human verified real embedding, iframe authentication and valid launch context.
The narrow adapter handles one FACE/EDGE ENTITY or an explicit empty array. Its tests
use invented reference values matching captured structure only. The corrected live
FACE capture resolves the final evidence blocker; it matches the existing fixture
and parser. Phase 3 is complete. Keep automated fixture evidence distinct from the
human's real Onshape observations. Phase 4's separate real REST and stale-context
tests are now verified by the user's final report.

Run targeted tests with `npm run test --workspace @forge/web -- src/onshape`.
The complete gate is `make format`, `make check`, `make test-e2e`, `make migration-check`
and `make audit`, with explicit PostgreSQL regressions where configured.
`tests/e2e/extension.spec.ts` intercepts synthetic HTTPS origins and exercises actual
browser-generated postMessage origin/source against production and DEV assets. It
covers valid/replaced/cleared/malformed selection, document/workspace/element reload,
wrong-origin/source senders, no reference storage/UI leaks, diagnostics and production
exclusion. Browser screenshots contain synthetic data only in ignored `.cache/phase3/`.
Playwright owns ports 4173/4174 and stops those services; preserve the user's 5173/8000.

For troubleshooting, **Launch context diagnostic** works even with invalid context
or unavailable auth. **Selection diagnostic** requires validated launch context and
starts disabled. Both appear below the DEV app, never in production. Enable explicitly
and share only sanitized copy-button output; never raw IDs, URLs, network data or logs.
The selection observer is separate from selection parsing and cannot establish trust.
Cookie/session/CSRF configuration is unchanged. Real browser-wide cookie behavior,
assembly paths, multiple selection and version messaging remain unverified.

## Phase 4 read development

No new environment variables, dependencies or database migration are needed. Retain
the existing HTTPS/API services and working iframe session configuration. Update
the existing OAuth app's profile-only permission to include OAuth2Read, then renew
consent as described in [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md). Never enable document
write permission for this test.

Use CAD Context → **Read CAD data** inside the existing workspace Part Studio.
The response is a count/status proof, not the future inspector. Default configuration
and end-of-list evaluation are the verified request settings. Each click can make
four GETs; no CAD polling occurs. Read time and unverified/mismatched consistency are
visible. Context/account changes and actual navigation clear old results. Ordinary
browser visibility/focus preserves the same frame's inspection and captured time.

Targeted checks:

```sh
cd apps/api
uv run --frozen pytest tests/test_cad_read.py tests/test_mass_structure.py tests/test_mass_normalization.py
cd ../..
npm run test --workspace @forge/web -- src/cad
npm run build
npm run test:e2e -- --grep 'Phase 4'
```

Run the full `make format`, `make check`, `make test-e2e`, `make migration-check`,
`make audit` and isolated PostgreSQL regressions for the phase gate. If the runtime
sandbox restricts the default uv cache, set `UV_CACHE_DIR=/tmp/forge-uv-cache`.
The project lockfiles remain authoritative. Do not weaken frozen installs.

The dev-only read diagnostic's copy button includes only fixed statuses/codes,
completion time, consistency and a random Forge request reference. No raw JSON
inspection is needed. Production excludes that module. Server integrations may
enable INFO for logger `forge.onshape.read` and serialize its allowlisted fields;
never enable HTTP/access debug logs or ingress CAD query/body capture. Browser
screenshots/test traces use synthetic fixtures only and remain ignored.

The user has verified 2 features, 1 part and 1 body live. The final sanitized mass
capture establishes a valid ordered triple with zero nominal, negative lower
tolerance, positive upper tolerance, `hasMass=false` and missing contributions.
The scalar validator now checks nominal nonnegativity rather than every tolerance
component; present estimates must still be strict finite triples with ordered
bounds. The false mass flag suppresses the normalized physical estimate while
volume and other CAD data remain valid. No material assignment is needed to parse
this response. The final real test showed **Mass unavailable;
material/density may be missing**, with the provider response error gone. Switching
to a separate empty Part Studio cleared the 2/1/1 snapshot and returned 0/0/0 with
no mass-property bodies. No material assignment was needed to pass parsing.

With the existing development backend, a failed mass read can still supply
a bounded, sanitized structure header. DEV validates it and shows **Sanitized
mass response structure** beneath the read diagnostic in CAD Context. Select and
copy within that box manually; the regular read copy button remains unchanged.
No raw response, network-header inspection or new credential/configuration is
needed. Production omits the header and excludes the validator/UI. See the review
for exact capture steps and the limits of this sampled structure report.
Useful sign, comparison, strict availability and missing-category metadata remain
DEV-only and bounded. Field-level fixed error codes replace the investigation's
validator replay and duplicated predicate logic. No further diagnostic capture is
needed after the final real test. For a later reproduction, reload the iframe and
choose **View CAD context → Read CAD data**. Successful mass parsing produces no
mass structure box. If an
unexpected failure remains, manually copy the sanitized diagnostic only; do not
inspect or share raw provider data.

## Phase 5 inspector development

Use the existing HTTPS web/API services, database and OAuth2Read grant. There are
no new dependencies, migrations, environment variables or extension settings.
The normal CAD Context action is now **Refresh CAD** and calls only `/inspector`;
the older `/snapshot` proof endpoint remains for regression compatibility.
The production UI contains no provider diagnostics or opaque CAD identifiers.

In the DEV-only `#/lab`, select **CAD inspector**, then choose the labeled
synthetic state: simple, empty, many features, suppressed/unknown feature, partial
provider failure, missing mass, FACE or EDGE. No provider request runs there.
Use Tab and Enter/Space on disclosures, search fetched features/parts locally,
and check 320/380/480 px widths in both themes. Synthetic screenshot evidence lives
in ignored `.cache/phase5/`. Never add raw real CAD responses to fixtures or traces.

Run `make format`, `make check`, `make test-e2e`, `make migration-check`,
`make test-postgres` with the existing private configuration, and `make audit`.
Targeted checks are `tests/test_cad_inspector.py`, frontend `src/cad`, and
Playwright `--grep 'Phase 4|Phase 5'`. Frozen installs remain `npm ci` and
`uv sync --locked`; no lockfile changes are required. Playwright owns and stops
ports 4173/4174. Preserve the user's existing 5173/8000 and database services.

Final real Phase 5 verification passed on 2026-10-14. The user authorized one
Phase 5 commit and a normal push after the complete final repository gate.
[PHASE_5_REVIEW.md](PHASE_5_REVIEW.md) records the completed live evidence and
repeatable checks. Phase 6 remains unauthorized.

For the live topology investigation, keep the existing development environment and
reload Forge, then choose **View CAD context → Refresh CAD**. The normal inspector
shows Unknown for missing/null/unverified empty topology arrays. Below it, the DEV
**Sanitized body response structure** textbox reports only the first body's fixed
faces/edges/vertices presence, array/missing type and length/null. Select and copy
that textbox manually; the regular diagnostic copy button is unchanged. No report
appears for an empty Part Studio or failed body section. No raw Network inspection
or new permission/setting is needed. Follow the exact capture/retest steps in the
Phase 5 review. The final sanitized capture verified empty edge/vertex arrays;
no further live capture or geometric-data request is needed.

Targeted repair checks: backend `test_body_topology.py`, `test_cad_inspector.py`,
`test_cad_read.py`; frontend `src/cad`; Playwright `--grep 'Phase 5|production excludes'`.
Run format/lint/typecheck/build as usual. Existing database/auth behavior and lockfiles
are unchanged, so this repair does not require another PostgreSQL/migration gate.

For browser lifecycle verification, inspect Part Studio 1 and select one FACE, then
switch to another browser tab and return. Inspection, captured time and FACE should
remain; focus may check `/api/me` but must not request CAD. A trusted show preserves
active selection. Closing the actual Onshape panel destroys its iframe, so reopening
has fresh selection/inspection and initializes once. Document/workspace/Part Studio
navigation, logout/disconnect/revoke, malformed trusted selection and a genuine
context mismatch still clear inspection. Targeted frontend checks include
`src/onshape`, `src/cad`, `src/auth`; browser checks cover the Phase 5 lifecycle
cases in `tests/e2e/extension.spec.ts` across all three engines. The topology
diagnostic remains available and bounded. The final human retest passed for ordinary
Chrome tab switches, FACE/EDGE/clear and real Part Studio switching; Phase 6 has not begun.
