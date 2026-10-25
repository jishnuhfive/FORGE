# Development

For three-person macOS/Windows onboarding, independent credentials, Git/PR workflow
and check-only diagnostics, start with [team development](TEAM_DEVELOPMENT.md).

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

Native servers intentionally avoid container rebuilds during editing. The local
Compose service remains PostgreSQL only. The separately authorized production
foundation now supplies a root Dockerfile and Railway config; see
[DEPLOYMENT.md](DEPLOYMENT.md). No production hosting has occurred. Phase 2 adds
Alembic migrations.

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
SESSION_SECRET is needed for opaque server-side sessions. Phase 6 hosted-provider configuration is documented below.

There are no `VITE_*` secrets. Never dump settings or `.env` contents into logs.
Onshape tokens and AI-provider keys must not enter frontend source or browser storage.

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

OAuth code exists, but real OAuth requires credential verification. Phase 6 adds explicit read-only hosted AI calls inside Onshape. CAD Context refresh and the Phase 6 inspection tool perform explicit CAD reads; no CAD is modified. Sample approval and Apply actions only change local preview state.
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
repeatable checks. Phase 6 is now separately authorized; its review records the new boundary.

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
Chrome tab switches, FACE/EDGE/clear and real Part Studio switching. Phase 6 is separately authorized below.

## Phase 6 local Groq setup and tests

The existing root `/Users/jishnuhiremath/Developer/FORGE/.env` is the backend settings
source. Preserve its working OAuth/database/HTTPS configuration. Do not overwrite
it or put keys in `apps/web`, `VITE_*`, chat, screenshots or shell history. If absent,
copy `.env.example` once. `apps/api/.env` is ignored but is not read by Settings.

Follow the official [Groq quickstart](https://console.groq.com/docs/quickstart):
sign in to Groq Console, open [API Keys](https://console.groq.com/keys), create an API
key, and enter it directly into the root `.env` using your local editor:

```dotenv
FORGE_AI_PROVIDER=groq
GROQ_API_KEY=<enter locally only>
FORGE_GROQ_MODEL=openai/gpt-oss-120b
FORGE_GROQ_REASONING_EFFORT=low
```

No OpenAI key is required. These are all additional Phase 6 settings; preserve the
already-working Onshape/DB/session/HTTPS settings from earlier phases. Keys are
backend-only: one operator-hosted backend serves authorized users, never giving
end users the operator's provider key. Invalid provider/model/effort settings fail
validation; a missing selected key produces a safe unconfigured state.

Review the Console account's Limits/Data Controls before use. The published free
limits are 30 RPM, 1,000 RPD, 8,000 TPM, 200,000 TPD for GPT-OSS 120B, shared by the
organization. Two requests per model-assisted read turn and token budgets constrain actual capacity.
Free inference is not unlimited or guaranteed; account limits are authoritative.
Remain on Free if paid Groq use is not intended. No automatic paid OpenAI fallback
exists, even if an OpenAI key is also present. Groq data retention exceptions and
optional administrator-enabled ZDR are described in [AI_AGENT.md](AI_AGENT.md).

To select the retained optional OpenAI adapter deliberately, configure instead:

```dotenv
FORGE_AI_PROVIDER=openai
OPENAI_API_KEY=<enter locally only>
FORGE_OPENAI_MODEL=gpt-6.1-sol
FORGE_OPENAI_REASONING_EFFORT=high
```

This requires an eligible API project with model access and quota/billing; no Groq
key is required. Legacy FORGE_AI_MODEL/FORGE_AI_REASONING_EFFORT aliases configure
OpenAI only; explicit OpenAI settings win. This is an operator choice, never a
runtime fallback or a browser option. All `.env.example` placeholders stay empty.

Stop/restart your existing API process with `make dev-api` to load settings. Keep
the existing `make dev-web-https`, healthy PostgreSQL and Onshape OAuth2Read session.
Reload the Forge panel in the real workspace Part Studio 1. No dependency install,
migration, extension registration or permission change is needed. **Send prompt**
or Cmd/Ctrl+Enter makes the external request. No initial Refresh CAD is required;
each send acquires fresh evidence. Allow five seconds between sends. Refresh CAD
shares the evidence cooldown, so wait and retry explicitly if necessary.

Automated tests never need a key or spend API credits:

```sh
npm ci
uv sync --project apps/api --locked
make format
make check
make test-e2e
make migration-check
make audit
```

Run isolated PostgreSQL regressions with FORGE_TEST_DATABASE_URL as described above.
Targeted AI backend tests:
`uv run --project apps/api --frozen pytest apps/api/tests/test_ai.py apps/api/tests/test_groq.py`.
Frontend: `npm run test --workspace @forge/web -- src/ai`.
Browser: `npm run test:e2e -- --grep 'Phase 6'`. Test servers own 4173/4174;
preserve user services at 5173/8000 and the already-running database. Synthetic
screenshots live in ignored `.cache/phase6/`; never capture private live CAD.

Local conversation is memory-only, with no content logs/analytics or persistent
provider conversation. Groq suppresses reasoning and omits unsupported store flags;
optional OpenAI uses `store:false`. Neither establishes zero provider retention.
Exact live prompts, expected answers and lifecycle/no-auto-call checks are in
[PHASE_6_REVIEW.md](PHASE_6_REVIEW.md). The user reported final real Groq
verification passed on 2026-10-16 and authorized one Phase 6 commit and normal push
after the complete final gate. Phase 7 remains unstarted and requires separate authorization.

### Phase 6 live-response repair verification

The first live inventory/grounding test passed according to the user. Repair
verification runs focused AI tests, adjacent inspector/context regressions, static
checks, a production build and `tests/e2e/ai.spec.ts` in all three browser engines.
The earlier focused repair gate preceded live retesting. The final user-reported
live results and complete post-repair repository gate are now recorded in
PHASE_6_REVIEW. No live provider requests belong in automated tests.

Restart the existing API with `make dev-api` and reload the HTTPS Forge panel to
load the new provider-neutral final schema (`suggestion_ids`, no free discussion).
Keep the existing Groq key, provider/model/effort, OAuth, PostgreSQL and HTTPS
settings. Both provider adapters use the updated strict schema; no install or
migration is needed. Retest collapsed/expanded Evidence and copied output, summary,
parameter detail, useful next steps and selection states as recorded in
[PHASE_6_REVIEW.md](PHASE_6_REVIEW.md).

### Phase 6 selection-grounding retest

Restart the API (`make dev-api`) for the strict internal `assumption_ids`/`question_ids`
schema. Retain existing provider/OAuth/DB/HTTPS settings; no key change, dependency
install or migration is needed. Reload Forge, keep one FACE selected and Clear
conversation. Ask "What do you know about the face I selected?". Expect one face
reported, owning part/body/feature and geometry/dimensions explicitly unknown,
no ownership assumption, no area/normal/surface value and no capability follow-up.
Repeat with one EDGE. Singleton CAD inventory cannot change these unknowns.
Only mocked transports are used in tests; the selection tests are in
`apps/api/tests/test_ai_selection.py`, with UI coverage in the existing AI suites.
The user verified these FACE/EDGE results live on 2026-10-16. The complete final
gate passes; Phase 7 remains unstarted.

### Phase 6 write-request repair retest

Keep the existing ignored root `.env` provider/key, OAuth, HTTPS and PostgreSQL
settings. Restart the API terminal with `make dev-api`; leave healthy PostgreSQL
running. For Vite development the existing `make dev-web-https` process picks up
the unchanged production frontend; reload the Forge panel. If serving a built
frontend, rebuild/restart that preview. No dependency install or migration is needed.

Clear conversation and ask exactly "Make this model 20 mm wider.". Expect normal
inspection progress, then "Forge cannot modify CAD in Phase 6. I can explain or
propose how the change could be made." and an explicit unknown width-driving
dimension. No verification error, success/edit claim or inferred parameter should
appear. Evidence starts collapsed; expand it and verify meaningful statements,
including unknown target evidence. Check Onshape geometry and feature history:
Forge must not have changed anything. Respect cooldown/capacity before any explicit
retry; no automatic provider retry or paid fallback occurs.
This exact explicit write request now performs zero Groq/OpenAI calls: Forge uses
the existing authorized inspection directly. After cooldown, clear conversation and
ask "What is in this Part Studio?" to verify the normal two-round model/tool path.
It must still give a grounded inventory with no invented mass, units or ownership.

For a remaining failure, ensure the existing server environment is development
(`ENVIRONMENT=development`), restart the API, and repeat once. Share only the terminal
line beginning `ai_validation`, with fixed reason/stage/field/status/correlation
and allowlisted provider error code/type/parameter;
never share keys, raw requests, provider output, private CAD or Network captures.
Production keeps generic errors and emits no such diagnostics. Automated focused
checks use invented CAD and mocked Groq/OpenAI transports; they spend no credits.

## Phase 6.5 visual review

See [FORGE_DESIGN_SYSTEM.md](FORGE_DESIGN_SYSTEM.md) for tokens/material rules and
[PHASE_6_5_REFINEMENT_REVIEW.md](PHASE_6_5_REFINEMENT_REVIEW.md) for current verification
and real Onshape review (the first human review was not approved).
Keep the existing HTTPS Vite process, API, private configuration and PostgreSQL.
No dependency, migration, credential or OAuth registration change is needed.

Open `https://localhost:5173/#/lab` on the existing trusted local HTTPS development
origin. Choose **Phase 6.5 workspace** or **Phase 6.5 design system** under Preview
state. Choose Layout, Workspace state and the three accessibility adaptations.
All data is synthetic. On the real panel, DEV launch/selection reports are now
behind **Workspace menu → Developer**. Signed-out DEV embeds retain a **Developer**
recovery action. Production excludes both.

Screenshots/performance summaries are ignored under `.cache/phase6.5/`. Never capture
private CAD in automated screenshots or traces. `tests/e2e/design.spec.ts` adds the
six-width visual/accessibility gate, state matrix and synthetic timing sample.
`make test-e2e` owns/stops ports 4173/4174. Do not stop the user's 5173/8000 services.
A temporary QA server may use 4175 and must be stopped after review. For sandboxed
uv caches, `UV_CACHE_DIR=.cache/uv make ...` preserves frozen lockfile use.

The human approved the second real Onshape visual review and authorized one
Phase 6.5 commit/normal push after the complete final gate. The design system is
frozen. Phase 7 had not started at that checkpoint; its subsequent implementation
and the current Phase 8–10 status are recorded in the roadmap and reviews below.

The refined lab also provides **Material comparison** (A previous/B refined/C opaque)
and **Logo candidates**. Choose Wide standalone to compare three columns; narrow
layouts stack them. Internal candidates are excluded from the production bundle.
`tests/e2e/refinement.spec.ts` captures these comparisons and production iframe
first-open/FACE/EDGE/overview/evidence at 320/380/480px, plus reduced effects.
Screenshots and final logs are ignored in `.cache/phase6.5-refinement/`.

## Phase 6.5 final freeze gate

Phase 6.5 is visually approved after two human-review passes. Follow the frozen
[design system](FORGE_DESIGN_SYSTEM.md) and [final review](PHASE_6_5_FINAL_REVIEW.md).
Final copy has no user-facing roadmap phases or provider/schema internals. Backend
edits are deliberately limited to canonical response wording; policy, transports,
requests, authorization, grounding, unknown statuses and write refusal are unchanged.

Run `make format`, `make check`, all three complete browser projects, `make audit`
and `make migration-check`. For real PostgreSQL tests, use the existing safe opt-in
URL workflow above; UUID schemas are isolated and application data is preserved.
Never print the URL or private settings. Do not reset volumes or migrate the real
application merely to make a drift check pass. Final synthetic images/logs belong
under ignored `.cache/phase6.5-final/`; manual CAD captures are never tracked.
`tests/e2e/freeze.spec.ts` adds 320/360/380/400/480/640px Settings/privacy/keyboard
checks and production forced-color fallback verification. Existing browser tests
cover first-open, overview, selection, evidence, reduced effects and lifecycle.

## Phase 7 learning review

No dependencies, migration, environment variables or provider keys are required.
Use UI Lab → Learn mode → Learning preview state for representative authored states.
The real authenticated Learn tab uses the same views and keeps its session across
Design/Modify/settings/history navigation. Reload intentionally clears learning.

Focused checks: `npm run test --workspace @forge/web -- src/learning` and
`npm run test:e2e -- tests/e2e/learning.spec.ts` after a production build. The browser
suite exercises all six panel widths and writes synthetic images at 320/380/480/640px
to ignored `.cache/phase7/`. It intercepts auth and makes no real AI/Onshape requests.
Keep all manual Onshape screenshots/private identifiers outside Git. Full gate and
real panel acceptance steps are in [PHASE_7_REVIEW.md](PHASE_7_REVIEW.md).

## Phase 9B runtime verification and controlled handoff

Phase 8 is complete, human validated and merged; Phase 9A preparation is complete.
[Phase 9 runtime review](PHASE_9_REVIEW.md) records the implementation, provider
research and exact human OAuth/CAD procedures. Gate A is human-proven; Gate B
provider-side rejection audit confirmation is deferred. Phase 10 implementation is
merged and integrated here; its real-Onshape human validation remains pending.

Run `make setup` for npm ci and uv locked sync. Run format, lint, typecheck (including
strict mypy), test, build and test-e2e. Tests use synthetic provider transports only.
Real PostgreSQL tests require FORGE_TEST_DATABASE_URL supplied privately; run both
`apps/api/tests/test_postgres.py` and `apps/api/tests/test_safe_edit_postgres.py`.
Each owns/removes its random schema, never user data/volumes. Run compose-check,
migrate, migration-check and dependency audits. Alembic `0002_safe_edit` is additive;
startup does not create tables or migrate silently.

`FORGE_CAD_WRITES_ENABLED` defaults false; `.env.example` is an empty placeholder.
Leave the real flag OFF and developer-app permissions unchanged during development.
Do not use real CAD mutations in tests. No frontend/AI flag override exists.
`FORGE_CAD_WRITE_CONFORMANCE_PAUSE_SECONDS` defaults 0, accepts 0–10 only in
development, and supports the documented human Gate B race after final head check.
It is not a production feature. Human permission expansion, explicit new consent,
disposable CAD only and both real conformance gates are required before activation.
Unknown provider scope/bitmask or missing critical fields must stop validation.
Keep private screenshots, network captures, credentials and CAD data outside Git.

### Read-only safe-edit eligibility diagnostic

When target discovery fails during controlled validation, keep writes OFF. The
optional `FORGE_SAFE_EDIT_DIAGNOSTICS_ENABLED=true` is accepted only in development
with `FORGE_CAD_WRITES_ENABLED=false`. Restart the local API with those values,
then explicitly use CAD Inspector → Refresh CAD. The backend emits only a fixed
rejection reason, known field/category, primitive type/Boolean and optional bounded
position, plus fixed coverage metadata for both bounded `noSketchGeometry` read
variants at one pinned microversion. No IDs, names, geometry or raw maps are logged.
`safe_edit_suppression_coverage` additionally reports positions 1–3 only, fixed
auxiliary shape/btType categories and hard-Boolean presence/type/value. Null,
missing and false remain distinct. Both flags remain false/true respectively
(writes OFF, diagnostics ON) for this controlled human investigation.
`safe_edit_body_coverage` reports only returned-ID presence/match, fixed optional
flag categories, bounded body count, body-type category and error category, after
the pinned read passes head bracketing. It never emits the ID or raw body data.
Phase 16 additionally emits `safe_edit_representation_coverage` for both existing
feature read variants after matching-head checks, with **zero extra provider GETs**.
Strict frozen metadata includes only positions/categories, capped counts, known
adapter parameter IDs, duplicate/malformed/unknown indicators, closed enum/quantity/
query/Boolean categories and replacement/rename shape summaries. Unknown IDs,
expressions, names, node/geometry/CAD IDs, query contents, tokens and URLs never log.
The representation hook rechecks DEV/diagnostics-ON/writes-OFF before projection
and emission. `exact_match` means current adapter shape only, not write eligibility
or provider conformance. Follow the [writes-OFF human checkpoint](PHASE_16_MODIFY_LIVE_CONFORMANCE.md)
using Inspector Refresh only. The human has since reported structural PASS and
replacement FAIL for ordinary UI features. A separate
`safe_edit_standard_parameter_coverage` record classifies the finite public
standard-library input vocabulary, plus quantity `value`/`units`/import-marker
presence/type, from those same responses. Recognition supplies no edit authority;
the original adapter report and all rejection/count limits remain unchanged.
Unknown strings, values, queries and identifiers still never log. After the second
human checkpoint, the registry adds finite current-UI contracts alongside the
unchanged minimal A1 profile. Every present input must validate, and explicit mode
guards are mandatory; omitted inactive children never insert defaults. Valid
expanded shapes now report replacement/rename exact_match with zero registry
unknowns. Total parameter count clipping at 20 is informational because all raw
inputs are validated against the 50/38-input closed maps; malformed/duplicate or
unsupported states still reject. Source recognition alone remains non-authoritative.
Follow the Phase 16 record's same-fixture writes-OFF recheck before any live stage.
The latest human recheck remained unsupported and exposed defaultScope=false;
the corrected Extrude contract requires that exact observed state. Fillet rules
remain unchanged. The opt-in probe now also emits
`safe_edit_standard_shape_failure category=... parameter=... reason=...`, or
`safe_edit_standard_shape_validation category=... outcome=exact_match`, from the
same production current-UI predicate. Only known category/parameter/reason literals
escape; no raw values or JSON. Projection and each log recheck DEV, diagnostics ON
and writes OFF, and require complete/source-matched pinned evidence and a matching
head. There are no extra GETs. Group new lines with existing per-variant metadata;
they diagnose the current-UI parameter contract only, not approval/write eligibility.
See the Phase 16 record for the next single-refresh checkpoint; do not enable writes.
For a rejected documented common field, that same failure line now appends only
`common_field=parameterName|valueString|libraryRelationType present=true state=...`.
Text states are nonempty_string or a closed wrong-primitive category; library
states distinguish ignore_library_values, unknown_library_value,
empty_string, unrecognized_string or a wrong primitive. Values never log.
Only absent/empty-string text placeholders validate. Following the human
ordinary-fixture observation, library metadata accepts only absence or the exact
string DEFAULT; all other states still reject. Accepted DEFAULT does not emit a
metadata failure, and the shared predicate continues to the next field. A later
failure must still log; success requires the entire closed profile to pass.
Unknown field names do not enter this projection. The existing
source-vocabulary quantity `other_field_count` is unchanged and informational;
the shared production predicate decides replacement/rename exact_match.
No extra read or browser payload is added. Follow the final DEFAULT checkpoint
in the Phase 16 record; actual ordinary-fixture conformance remains unproven.
The next entities-envelope failure now distinguishes a documented filter from an
unknown extra field. It emits reason=query_filter_unproven with only filter_root,
root_state, child_count, max_depth, node_count, categories, malformed,
missing_operand, unexpected_fields, uninspected and truncated. These are fixed
SDK categories, bounded counts and flags, never raw provider JSON/values. AND/OR
have only operand1/operand2; NOT has only operand. Depth counts root as 1 and caps
at 8; node visits cap at 64. Counts describe inspected structure only. Unknown and
other-known payloads are not traversed, and uninspected/truncated are not evidence
of a complete tree. Leaf enum/geometry values are never read. All present filters
still reject, including inactive roles and null/malformed filters. An unrelated
extra envelope field retains unexpected_field without a filter summary. No extra
GET or public payload. Follow the query-filter evidence checkpoint in Phase 16,
with one same-fixture writes-OFF Refresh and sanitized labels only.

The Phase 16 final safety review found and repaired a historical minimal-profile
nested-field bypass before writes were enabled. Keep the historical and current-UI
fixtures separate: all five/three historical IDs must be present exactly once,
with closed nested envelopes. Fillet tangentPropagation is now required. Adding
UI metadata/filter fields to a historical fixture must reject; failing a profile
must never fall through. Suppression tests instead assert the independent minimal
attribute payload. Follow the final profile-repair checkpoint in the Phase 16
record: one same-fixture writes-OFF Inspector refresh, no proposal or mutation.

The next signature diagnostic extends only that rejection log with signature,
signature_truncated and leaf_states. Signatures contain fixed subtype/operator
tokens in operand order. Leaf states are finite official enum/Boolean labels,
prefixed by a local preorder visit counter, never CAD identities. Missing/null /
wrong_type/unknown_value are explicit; raw strings never pass through. Depth 8,
visits 64, signature 4,096-character and whole-filter 16,384-character limits are
tested. No real tree has been accepted. Follow the exact-signature checkpoint in
the Phase 16 record: one same-fixture writes-OFF refresh, no proposals or writes.

The flat-sheet-metal follow-up projects only the official optional `allows` enum
through finite labels. Absence is `allows=missing`; null/wrong primitives are
`null`/`wrong_type`; UNKNOWN and arbitrary strings are `unknown_value`. Extra
subtype fields must raise the existing unexpected/uninspected diagnostic flags.
Run `tests/test_modify_flat_sheet_metal.py`, `tests/test_modify_filter_signature.py`,
`tests/test_modify_query_filter_evidence.py`, standard-shape and Modify diagnostic
regressions before the normal full gate. Synthetic allows inputs are not live
evidence. Keep writes OFF and perform only the next single human Inspector refresh
documented in the Phase 16 record; no role-specific filter acceptance is added.

After complete human filter evidence, run `tests/test_modify_filter_contracts.py`
first, then signature/flat-sheet-metal/query-filter, minimal-profile, UI-conformance,
shape-failure and Modify diagnostic suites. The new provider-shaped synthetic
fixture reconstructs the exact observed entities trees; it is not private CAD or
proof of live writes. Test both exact role matches and rejection at every schema
slot, then the full API/PostgreSQL/frontend gate, Modify browser cases in all three
engines, frozen installs, format/lint/strict typing/build/audits/Compose and isolated
migrations/drift. Never use the application database or real provider traffic.
Existing Inspector diagnostics now report exact_match for both roles when the
whole feature passes; the representation report must show registry=true and
replacement/rename exact_match. The next human action remains exactly one
same-fixture Inspector refresh with diagnostics ON/writes OFF. No proposal,
approval or mutation is part of that checkpoint.

For the all-role evidence continuation, run
`tests/test_modify_query_role_inventory.py` with the existing strict-contract,
signature/filter, minimal-profile, first-failure, representation, standard-source
and Modify diagnostic suites, then the full normal gate with isolated PostgreSQL,
all frontend tests, Modify browsers in three engines, frozen installs, audits,
Compose and migration drift checks. Keep real CAD writes OFF. The collector reuses
existing reads and logs `safe_edit_query_role` plus `safe_edit_query_role_summary`
for both noSketchGeometry variants. Current full fixtures have 13 Extrude / 8
Fillet query roles; actual returned roles are derived rather than assumed. Report
all rows, actual discovered/inspected totals, completeness and aggregate flags in
one human refresh. Empty roles still require filter evidence. Unknown identities,
duplicates or clipping leave evidence incomplete. See the newest Phase 16 section;
full representation exact_match is not expected yet and no dormant role is accepted.

For the remaining query-evidence closure, first run
`tests/test_modify_query_evidence_closure.py`, then inventory/signature/filter,
strict-contract, minimal-profile and diagnostic regressions. The default rejection
projection stays depth 8; only inventory uses diagnostic depth 16, with the same
64-node cap. Schema-maximum tests include all three mate-connector fields. Full
tests must include isolated PostgreSQL, frontend, Modify browsers, frozen installs,
format/lint/types/build/audits/Compose and migrations/drift. If capacity requires,
use execution-only lower test parallelism without changing assertions/timeouts.
The deep synthetic fixture is not a real direction-tree capture. The next human
single-refresh target is clean 13/13 Extrude and 8/8 Fillet, including complete
real direction signature and explicit mesh/mate states. Keep diagnostics ON/writes
OFF; first-failure dormant-role rejection remains expected. No proposal or write.

The separately authorized Phase 16 payload repair uses two fixed server-owned
limits: 8 KiB ordinary/suppression requests, 32 KiB validated full rename/depth /
radius replacement requests. Count actual serialized bytes, including JSON escapes;
never trim CAD metadata or filters to fit. Both preflight and transport enforce
the bound. There is no setting or model/public request field selecting a budget.
Keep CAD writes OFF during tests and implementation. Dormant-role acceptance and
actual live wire-size/conformance validation remain separate pending work.

It performs pinned GET reads without proposals or mutations, and adds no
public diagnostic route/header. It is not invoked by Learn or AI. See
[the investigation record](PHASE_9_REVIEW.md) before interpreting missing fields;
never paste private payloads or weaken eligibility from a visual CAD inspection.

Current synthetic safe-edit provider fixtures exercise the observed empty v17
state map. Complete-map tests remain strict; missing/partial/extra/invalid maps
reject. The explicit unavailable mode is bound to proposals; old-policy previews
must be recreated. `tests/test_safe_edit_empty_states.py` covers both modes, hard
predicates, fresh rejection and post-write uncertainty entirely with mock providers.
The revised policy establishes supported body output/explicit suppression only,
not whole-model health. Real write flag and both pending human gates are unchanged.

`tests/test_safe_edit_suppression.py` covers null-unavailable versus ordinary-object
auxiliary modes without synthesizing fields, all specialized/malformed rejections,
explicit suppression requirements, privacy and post-write uncertainty. The live null
auxiliary fields and omitted guards have distinct evidence modes, never defaults.
`tests/test_safe_edit_guard_evidence.py` exercises independent configuration proof,
complete top-level structural proof, explicit conflicts, mode/presence binding,
post-write re-proof and no false defaulting. Unsupported structure or nonempty/
stale/skewed configuration fails closed. No production query or feature-state-map
policy changes. Old previews must be prepared again under `terminal-fillet-6`;
no migration is needed. A manually created configured-control comparison is optional
additional evidence and is never created by Forge/Codex.

`tests/test_safe_edit_body_evidence.py` covers explicit-clean and both-omitted marker
modes, exact pinned-ID/transport proof, conservative mixed-shape rejection, unchanged
body invariants, stale approval and post-write uncertainty/fences. No flag is
defaulted or synthesized. Both accepted after-modes are independently re-proven at
the new acknowledged revision. Keep writes OFF and diagnostics ON; refresh CAD
Inspector only and collect fixed metadata, without preparing or approving a write.

The first real write and full repair investigation are recorded in the runtime
review. Safe-write reads now include full returned sketch definitions while still
excluding geometry IDs; caps remain unchanged. `test_safe_edit_verification.py`
covers comprehensive final checks, strict unrelated-change detection, obsolete
policy 5, acknowledgement mismatches, full Sketch geometry and timeouts/no-retry.
Fixed `safe_edit_verify` logs are DEV-only; failed checks/stages are also sanitized
durable audit outcomes. The internal `dev/verify.py` helper requires DEV/writes OFF,
uses only fixed GETs and returns closed metadata, never raw snapshots.

The original uncertain row expired during investigation; the trusted decoded
baseline remains memory-held. Its durable fence was later cleared by the separately
authorized operator recovery recorded in the runtime review, with zero Onshape
contact and writes OFF. The local API/reloader were restored with writes OFF after
temporary pausing; health passed. Keep the private baseline holder alive until
operator review and do not clear fences as part of code verification.
Follow the fresh Gate A/B procedures in the review. For a
human write trial the read-only probe flag must be OFF; for this repair writes stay
OFF. Phase 8 and the existing reconcile/no-retry/retention policies are unchanged.

`cad_edits/dev_recovery.py` is an internal operator helper, not a CLI or HTTP route.
Only after explicit operator authorization and independently established settlement,
construct its strict `RecoveryReference` from trusted preserved evidence **in
memory**, never from a guessed fence or logged/command-line identifiers. Invoke
`recover_orphaned_fence` with the configured session factory and development Settings
while both configured and running API writes remain OFF. It uses the existing user
lock and session/grant/fence row locks. The original session may be expired but must
still identify the exact owner; recovery never logs it in or refreshes any token.
The helper requires an exact single matching orphan, elapsed 15-minute retention,
an entirely empty operational table and a unique ordered four-event uncertainty
audit window. Any retained record (even a tombstone/unknown state), candidate
ambiguity or prior recovery fails closed. Audit and exact three-field deletion
commit together. It accepts no arbitrary deletion query and has no provider client.
Do not use it to infer upstream settlement, recover a live claim or clear multiple
fences. New CAD work always requires a new proposal and approval. Focused coverage:
`tests/test_safe_edit_operator_recovery.py` and the PostgreSQL recovery concurrency
case in `tests/test_safe_edit_postgres.py`.

Retained records require the **separate** reviewed
[retained-record operator V1 runbook](RETAINED_RECORD_OPERATOR_RECOVERY.md).
Its internal coordinator is deliberately not exposed as a CLI, route or browser
control. Do not invoke it for live recovery as part of implementation verification.
It requires independently preserved operation evidence, pre-reviewed settlement
and drained writers, a surviving hard-inactive original session and a current
generation's already cached read credential in the trusted operator process.
Missing receipts or cache state are blockers, not reasons to copy DB values,
refresh/export tokens, edit rows or weaken the orphan helper. Focused verification
uses `tests/test_retained*.py` with synthetic transports and temporary DBs. PostgreSQL
races must use an independently disposable service/random schemas, never the live
FORGE database. No migration or production configuration change is needed.

The temporary October 20 recovery mechanism and its dedicated tests have been
removed after the authorized one-time closure. The
[closed incident record](LEGACY_RETAINED_RETIREMENT.md) is historical documentation,
not an operator procedure. Permanent retained-record verification remains in
`tests/test_retained*.py`; no incident enrollment or recovery entry point remains.

## Phase 11 tutor checks

Backend: `uv run --frozen pytest tests/test_tutor_core.py tests/test_tutor_route.py tests/test_tutor_eval.py`.
Frontend: `npx vitest run src/learning/Tutor.test.tsx`. Browser: `npx playwright test tests/e2e/tutor.spec.ts`.
All use mocked providers and CAD; no live service or secret is needed. After pulling Phase 9, run
`uv run --frozen alembic upgrade head` once from `apps/api` against your local database.

## Hackathon Modify A1 checks

A1 is backend-only: [typed contracts and integration instructions](HACKATHON_MODIFY_A1.md).
Keep CAD writes OFF; tests use only synthetic fixtures and MockTransport. Run
`uv run --project apps/api --frozen pytest apps/api/tests/test_modify_plan.py` and
all existing `test_safe_edit*.py` regressions. With the existing privately supplied
FORGE_TEST_DATABASE_URL, additionally run `test_modify_plan_postgres.py`,
`test_safe_edit_postgres.py` and `test_postgres.py`; they own only random schemas.
Run the standard format/lint/strict-type/test/build/audit gate and migration drift
check. No migration, dependencies, browser contract or live write is required.
Team B must keep planner calls separate from the explicit human approval handler.

## Modify planner tests (B1)

`apps/api/tests/test_modify_planner.py` runs entirely on invented CAD and fake model
transports (Groq and OpenAI shapes); no key or network is required. Run it with the A1
(`test_modify_plan.py`), Phase 9 `test_safe_edit*.py` and AI tests. No migration,
dependency or live write is involved.

## Generalized approval tests (A2)

Run `uv run --frozen pytest tests/test_modify_plan_routes.py` from `apps/api`, then
`tests/test_modify_plan_routes_postgres.py` with the existing isolated local
FORGE_TEST_DATABASE_URL. Include `test_modify_plan.py`, `test_modify_plan_postgres.py`,
`test_modify_planner.py`, all `test_safe_edit*`, AI/provider/tutor and PostgreSQL
regressions, then the full repository gate. All CAD/model traffic is mocked; no
credential or live write is needed. Isolate tests from operator dotenv when testing
unconfigured settings. A2 adds no migration or frontend change. See
[the API, bounded events and cancellation/disconnect contract](HACKATHON_MODIFY_A2.md).

B2 checks: `npm test --workspace @forge/web -- src/modify --maxWorkers=2`,
`npm run typecheck`, full frontend tests/build, and
`./node_modules/.bin/playwright test tests/e2e/modify.spec.ts --workers=2`.
All browser provider outcomes are intercepted synthetic fixtures. See [B2](HACKATHON_MODIFY_B2.md).

## Modify recovery hotfix

For Phase 16 run `test_modify_conformance.py` alongside all `test_modify*.py`,
`test_safe_edit*.py`, `test_retained*.py` and `test_ai_write.py` regressions, including
opt-in PostgreSQL cases against a separately disposable local service. Run focused
frontend Modify tests, all standard gates and Modify browser cases in all three
engines. Isolate tests from operator dotenv; keep the real write flag OFF. See
[Phase 16](PHASE_16_MODIFY_LIVE_CONFORMANCE.md) for exact results and the later
human-only fixture/representation/approval sequence. Do not enable real writes,
clear application fences or contact private CAD as part of this automated gate.

See [recovery contracts and live validation](MODIFY_RECOVERY_HOTFIX.md).
`FORGE_MODIFY_REASONING_EFFORT` defaults to `high`; it affects only Modify planner
fallback, independently of Design/Learn Groq effort. Supported explicit commands
use fresh deterministic A1 previews without an AI request or AI credentials.

Include `test_modify_recovery.py`, `test_modify_deterministic.py` and
`test_modify_diagnostics.py` in focused verification. With a privately supplied
FORGE_TEST_DATABASE_URL also run `test_modify_recovery_postgres.py`; every database
case owns a random schema and uses synthetic CAD. Browser `modify.spec.ts` covers
tab remount, refresh, explicit inspection and retained fencing after disagreement.
Never use the actual application fence as a fixture or run real provider calls.

## Production image verification

Keep local development commands/settings unchanged; leave WEB_BUILD_DIR unset.
For the hosted foundation run `make build`, then
`docker build --tag forge:railway-foundation .` and `make deployment-check`.
The latter checks real Docker context exclusion rules and image contents, then
uses only synthetic configuration and its own disposable PostgreSQL/network for
container smoke, `make migration-check` and `make test` with real PostgreSQL tests.
It removes its own resources and leaves any existing local DB untouched.
See [DEPLOYMENT.md](DEPLOYMENT.md) for the variable inventory and later Railway /
Onshape transition. Do not run `make migrate` against an existing/live database
as part of this deployment-foundation gate.

## Phase 13 Inspector graph verification

From `apps/api`, run:

```sh
uv run --frozen pytest tests/test_inspector_graph.py \
  tests/test_inspector_graph_equivalence.py tests/test_cad_inspector.py \
  tests/test_model_graph.py
```

Then run the full repository gate including
all three browser engines, migration/Compose checks and audits. Equivalence reuses
existing parameterized Inspector/topology fixtures against a test-only frozen Phase 12
projection; the production UI and API schema need no changes. Use a disposable synthetic
PostgreSQL instance for migration/integration checks; retain existing local data.
No new environment variable, dependency, scope or migration is required. Human work is
read-only; follow [the Phase 13 plan](PHASE_13_INSPECTOR_GRAPH_ADOPTION.md), with writes OFF.

## Phase 14 Ask Forge graph verification

Run `uv run --frozen pytest tests/test_ai_graph.py` from `apps/api` first, followed
by the existing AI/provider/selection/write/presentation and graph/Inspector suites.
Then run `make format`, `make lint`, `make typecheck`, `make test`, `make build`,
`make test-e2e`, `make migration-check`, `make compose-check` and `make audit`.
Use frozen `make setup` installs and an isolated synthetic PostgreSQL database;
set FORGE_TEST_DATABASE_URL for the full API suite and DATABASE_URL only to that
disposable database for migration checks. Health-check, migrate and remove only
resources created for this verification; retain existing databases/services.

Coverage includes one accepted Snapshot/one graph/four GETs, independent context,
same-Snapshot rich evidence and duplicate names, bounded AVAILABLE order/terminal
facts, missing/UNKNOWN relationships, quoted malicious names, identity minimization,
byte bounds, authorization/revocation/cancellation, singleton selection UNKNOWN and
the deterministic zero-model-call write capability path. Tutor/Learn/Check my step
and Modify keep their existing tests and acquisition paths. Direct Inspector remains
Phase 13. No new dependency, environment variable, migration or public API is needed.
PRECEDES is returned order, not dependency; there is no ownership inference,
topology continuity, engineering correctness or new CAD authority. Reads remain
sequential/non-atomic; Railway remains unhosted. User-reported pre-polish human
read-only validation passed; the small post-polish visual recheck in
[the Phase 14 record](PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md) remains manual.
Do not execute it automatically or enable writes.

For the UX follow-up, run the focused `ai/friendly`, `ai/presentation`,
`ai/Analysis`, `ai/chatLead` and `components/ModeNavigation` Vitest files first.
Build the production frontend, then run `tests/e2e/phase14-polish.spec.ts`, the
real-panel refinement cases in `tests/e2e/refinement.spec.ts` and the unchanged
material performance sample in `tests/e2e/design.spec.ts` across all
three projects before the complete normal quality gate. Browser workers, retries,
assertion budgets and the <35 ms median threshold remain unchanged. New browser
fixtures mock all CAD/auth/model transports and are not live human validation.

## Phase 15 Tutor graph verification

From `apps/api`, run `uv run --frozen pytest tests/test_tutor_graph.py` first,
then the existing `test_tutor_core.py`, `test_tutor_route.py`, `test_tutor_eval.py`,
`test_step_checks.py`, `test_transfer_step_checks.py`, `test_step_check_route.py`
and Phase 14 `test_ai_graph.py`. Check/token implementations and their tests remain
unchanged. Follow with frozen `make setup`, `make format`, `make lint`,
`make typecheck`, `make test`, `make build`, `make test-e2e`,
`make migration-check`, `make compose-check` and `make audit`. Run all PostgreSQL
cases by setting FORGE_TEST_DATABASE_URL for the complete API suite. Use only a
disposable synthetic database for DATABASE_URL/migration checks; health-check,
migrate and remove the instance you created, preserving existing local services.

Only learner-requested Tutor CAD grounding is migrated: direct Inspector is Phase
13, Design Ask Forge Phase 14, Learn Tutor Phase 15; Modify remains unmigrated.
Check my step remains deterministic and unchanged, including signed token authority.
No dependency, OAuth scope, migration, UI redesign, deployment or new CAD authority
is added. PRECEDES means returned order, not dependency or ownership; no topology
continuity or engineering correctness. Reads remain sequential/non-atomic. The full
UI overhaul remains future work and Railway remains unhosted. The prepared
[human read-only plan](PHASE_15_TUTOR_GRAPH_GROUNDING.md) is manual; do not run Gate
A/B, invoke real Modify, perform CAD writes or deploy Railway for this phase.

For the narrow relationship-guard precision review, run
`uv run --frozen pytest tests/test_tutor_relationship_precision.py` first, then all
Phase 15 tests, existing Tutor tests and Phase 14 graph tests. The precision suite
uses actual graph-backed projection and asserts ordinary teaching survives, all
prose fields reject specific relationship claims, and general labels cannot hide
named-model claims. The original general-teaching test retains its safety assertions
and adds exact prose preservation. Run lint, strict typing, audits and the full API
suite (including isolated PostgreSQL), plus
`npm exec playwright test tests/e2e/tutor.spec.ts` after building for browser-visible
output verification. No UI, graph, acquisition, token or evidence-limit change is
part of this refinement.

For the live inventory regression repair, first run
`uv run --frozen pytest tests/test_tutor_structural.py`, then the precision,
Phase 15 and existing Tutor/token/check/Phase 14 suites above. The new tests use
the exact reported question and controlled incidental relationship prose, including
an HTTP route case with three active features and four GETs. Existing fixed-answer
assertions now explicitly ask relationship questions; extra non-relationship cases
require unsafe fields to be discarded. General-teaching cases explicitly ask for
teaching rather than relying on the inventory default. No existing safety assertion
or bound is removed. Run the full API suite with isolated PostgreSQL, format/lint/
strict typing, build/audit and focused Tutor browser tests. Human Test 1 initially
failed, then its rerun and Test 2 passed according to the user. Test 3 was safety-
correct but functionally failed because the relevant canonical order was omitted.

For the Test 3 relationship answer repair, first run
`uv run --frozen pytest tests/test_tutor_dependency_grounding.py`, then structural,
precision, all Phase 15 and existing Tutor/token/check/Phase 14 suites. The tests
require exact canonical order without model-selected IDs in both dependency
directions, conservative missing/malformed/ambiguous-name fallbacks, ownership
safety and the unchanged four-GET HTTP path. Existing safety checks remain;
expected primary text now includes relevant verified order for supported dependency
questions. Run frozen setup, full API tests including isolated PostgreSQL,
format/lint/strict types, build/audit and the focused Tutor browser suite. Do not
resume human Test 3 until the repair gate passes or claim a human pass from these
fixtures. See the Phase 15 record for the separate reported and automated results.
