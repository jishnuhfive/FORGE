# Team development

A single onboarding guide for three people building Forge during a 36-hour
hackathon. Developer 1 and Developer 2 use macOS; Developer 3 uses Windows.
Forge stays one web application inside Onshape's right panel, with no native client.
This checkpoint prepares collaboration only. Phase 7 has not started; Learning
Mode, CAD writes and changes to the frozen Phase 6.5 design system are not authorized.
The `phase7/*` branch names below are examples for separately authorized future tasks.

## 1. How collaboration works

```text
GitHub main → each developer clones their own copy → own branch → commit
→ push branch → Pull Request → review/tests → merge to main
```

Ask the repository owner to invite your own GitHub account to
[jishnuhfive/FORGE](https://github.com/jishnuhfive/FORGE), and accept the invitation.
Use your own GitHub authentication (Git Credential Manager or your own SSH key).
Never share passwords, edit on another person's computer, or send ZIP copies back
and forth. GitHub is the source of truth. Each person owns their local checkout,
local settings and database. `main` is the stable integration branch; normal team
work goes through PRs, including work produced by coding AIs. An emergency direct
commit must be an explicit team decision, never an accidental default.

## 2. Check prerequisites first

Keep compatible installations. Check PATH and versions before installing anything.
Node **24.x**, npm **11.x**, and Python **3.14.x** are required by `package.json`
and `apps/api/pyproject.toml`/`uv.lock`; patch versions need not match another teammate.
The current package-manager declaration is npm 11.19.0; the engine allows npm 11.x.
Use npm workspaces and uv only. Use a 64-bit Windows host. Apple Silicon macOS is
the verified backend host; the locked cryptography wheel no longer supports Intel
macOS (see [development platform notes](DEVELOPMENT.md#authentication-migrations-and-checks)).
Windows is supported by the architecture but has less real host verification than
macOS. Record setup problems and browser versions; do not bypass security controls.

### macOS

Required: Git, Node.js 24 LTS/npm 11, Python 3.14, uv, Docker Desktop with
Docker Compose, GNU Make 3.81+, and mkcert. In Terminal:

```sh
git --version
node --version
npm --version
python3 --version
uv --version
docker --version
docker compose version
make --version
mkcert -version
```

### Windows PowerShell

Required: Git for Windows, Node.js 24 LTS/npm 11, Python 3.14, uv, Docker Desktop
with Docker Compose (Linux containers), mkcert and PowerShell. **Make is not required.**

```powershell
git --version
node --version
npm --version
python --version
uv --version
docker --version
docker compose version
mkcert -version
$PSVersionTable.PSVersion
```

If `python` is not your 3.14 interpreter, check `py -3.14 --version` and use
`py -3.14` for direct script commands. If PowerShell blocks `npm.ps1`, use `npm.cmd`
for the same commands; do not disable security policy globally.

### Install only missing prerequisites

Use official instructions: [Git/macOS](https://git-scm.com/download/mac),
[Git for Windows](https://gitforwindows.org/), [Node downloads](https://nodejs.org/en/download)
(select 24 LTS; npm is bundled), [Python](https://www.python.org/downloads/)
(select 3.14), [uv](https://docs.astral.sh/uv/getting-started/installation/),
[Docker Desktop](https://docs.docker.com/desktop/),
[PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell),
and [mkcert](https://github.com/FiloSottile/mkcert#installation).
On macOS, Xcode Command Line Tools supply Git and Make; check that Make reports GNU
Make 3.81+. If you already use Homebrew, the mkcert instructions support
`brew install mkcert` (Firefox trust also needs `nss`). On Windows use the mkcert
project's Chocolatey/Scoop instructions or official release binary. Restart your
terminal after PATH changes, then repeat the version checks. Start Docker Desktop
and wait for its engine; `docker info` should succeed. Do not share its full output.

## 3. Clone and install dependencies

Both platforms, from the directory where you keep projects:

```sh
git clone https://github.com/jishnuhfive/FORGE.git
cd FORGE
git log -1 --oneline
```

The Phase 6.5 baseline is `d76e358 feat: polish Forge product UI and design system`.
This onboarding checkpoint adds a newer commit. After Phase 7 begins, confirm the
current team-agreed `main`, rather than requiring that historical hash forever.
If cloning fails, confirm your GitHub invitation and your own account authentication.

macOS, from the repository root:

```sh
make setup
make browsers
```

`make setup` installs npm dependencies with `npm ci` and Python dependencies with
locked uv sync. `make browsers` explicitly downloads Chromium, Firefox and WebKit
for Playwright. Neither command creates secrets or configures integrations.

Windows PowerShell, from the repository root:

```powershell
npm ci
uv sync --project apps/api --locked
npm exec playwright install chromium firefox webkit
```

Stop if an install fails; check versions/PATH and lockfile errors first. Repeat
frozen installs after pulling dependency changes. Do not regenerate lockfiles just
to bypass an installation failure.

## 4. Create your own private local configuration

Only if `.env` does not already exist, copy it once from the root `.env.example`.
Never overwrite existing working settings.

macOS:

```sh
cp .env.example .env
chmod 600 .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Keep it accessible only to your local user using your normal OS file permissions.
**Never commit `.env` or send it through Discord, email, ChatGPT, Codex, a GitHub
issue, a Google Doc or screenshots.** Never copy another developer's full `.env`.
Enter your own credentials in your private editor; do not paste them into coding AIs,
shell command arguments or chat. `.env.example` must retain empty placeholders.

Generate your local token encryption key after dependency setup (both platforms):

```sh
uv run --project apps/api --frozen python scripts/generate_dev_key.py
```

Expected: a confirmation that the key was saved in the ignored `.env`; the key is
not printed. The generator requires exactly one blank `TOKEN_ENCRYPTION_KEY=` entry
and refuses to overwrite a configured key. One private key per developer is fine.
Keep it stable: replacing it may invalidate encrypted local OAuth refresh data and
require signing in again. Never print or share it. This is a deliberate human setup
step; the team doctor never generates credentials.

## 5. Configure local HTTPS

Real Onshape development requires trusted HTTPS. These commands create a local CA
trust relationship and local certificates; run them yourself. Do not replace
existing working certificates unnecessarily. `.certs` stays ignored. Never share
the local CA private key (`rootCA-key.pem`), localhost private key, or CA directory.

macOS:

```sh
mkcert -install
mkdir -p .certs
mkcert \
  -cert-file .certs/localhost.pem \
  -key-file .certs/localhost-key.pem \
  localhost 127.0.0.1 ::1
```

Windows PowerShell:

```powershell
mkcert -install
New-Item -ItemType Directory -Force .certs
mkcert -cert-file .certs/localhost.pem `
       -key-file .certs/localhost-key.pem `
       localhost 127.0.0.1 ::1
```

The PowerShell backtick must be the last character on its line, with **no trailing
spaces** ([Microsoft parsing guide](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Parsing)).
You can also put the complete mkcert command on one line. If trust fails, follow
[mkcert's browser/platform instructions](https://github.com/FiloSottile/mkcert).
Do not click through a certificate warning or disable TLS validation.

## 6. Register your own Onshape development application

Recommended: each developer uses their **own** development OAuth registration and
client secret, rather than casually sharing one secret. Use a development account
and test Part Studio. In Onshape **My account → Developer → OAuth applications**,
create an **Integrated Cloud App**. Configure:

| Field                           | Value                                                           |
| ------------------------------- | --------------------------------------------------------------- |
| Redirect                        | `https://localhost:5173/auth/onshape/callback`                  |
| OAuth start (Forge login entry) | `https://localhost:5173/auth/onshape/start`                     |
| Permissions                     | Profile read (`OAuth2ReadPII`) and document read (`OAuth2Read`) |

**No document/CAD write or delete permission.** Profile-only older Phase 3 guidance
is historical; current read-only CAD inspection also requires document read.
Register the callback exactly. Enter the application's client ID/secret only in
your root ignored `.env`. See [authentication](AUTHENTICATION.md#local-setup-with-real-credentials)
and [Onshape registration](ONSHAPE.md) for account-specific details.

Add an extension to that application:

| Field      | Value               |
| ---------- | ------------------- |
| Name       | Forge               |
| Location   | Element right panel |
| Context    | Inside part studio  |
| Action URL | Exact line below    |

```text
https://localhost:5173/extension?documentId={$documentId}&workspaceId={$workspaceOrVersionId}&elementId={$elementId}
```

Use this registration for **workspace Part Studios**, not version viewing.
Onshape supplies its default metadata; do not append a duplicate `server` parameter.
For an individual app, create a **private** store entry from its Details page and
subscribe to it with your own account. For an organization app, ask the admin to
assign the development user/team. Follow the short
[extension registration procedure](ONSHAPE_EXTENSION.md#human-extension-registration)
for the private subscription/assignment steps, retaining the two read permissions
above. Do not publish the development app publicly. Reload a Part Studio and look
for the Forge icon in the **right panel**, not the document's + menu.

`localhost` always means the browser user's own computer:

```text
Developer A's browser → Developer A's Forge localhost
Developer B's browser → Developer B's Forge localhost
```

Never weaken exact origin validation to connect teammates. If an organization
blocks localhost registrations/frames, record the restriction and arrange an
approved HTTPS development origin with consistent fixed configuration. Do not
broaden origins, OAuth scopes, CSRF or TLS checks.

## 7. Fill local auth and Groq settings

Edit the existing root `.env` entries locally. This is a **shape to follow**, not
an additional file to commit; angle-bracket values are placeholders to replace.
Leave the generated token key intact and provider endpoint overrides blank.
The database password below is the repository's deliberately public loopback-only
development default; never use it for a hosted service.

```dotenv
ENVIRONMENT=development
APP_BASE_URL=https://localhost:5173
DATABASE_URL=postgresql+psycopg://forge_local:local-development-only@127.0.0.1:5432/forge_local
ONSHAPE_REDIRECT_URI=https://localhost:5173/auth/onshape/callback
ONSHAPE_CLIENT_ID=<developer's local client id>
ONSHAPE_CLIENT_SECRET=<developer's local client secret>
SESSION_SAMESITE=lax
FORGE_AI_PROVIDER=groq
GROQ_API_KEY=<developer key>
FORGE_GROQ_MODEL=openai/gpt-oss-120b
FORGE_GROQ_REASONING_EFFORT=low
```

Use the [Groq Console keys page](https://console.groq.com/keys) yourself. Separate
development keys per developer are recommended where the account/project supports
it, allowing independent revocation. Do not automate account/secret creation.
Keys and OAuth credentials remain **backend-only**, never `VITE_*`, frontend source,
browser storage or AI-assistant input. There is no automatic paid OpenAI fallback.

Separate keys do not guarantee separate free quota. Groq limits are bounded and
[apply at organization level](https://console.groq.com/docs/rate-limits);
[project limits](https://console.groq.com/docs/projects) can further constrain them.
Review the account's Limits/Data Controls, coordinate usage and remain on the free
plan if paid usage is not intended. A capacity error requires waiting/explicit
retry, not provider switching. Provider retention is explained in [SECURITY.md](SECURITY.md#phase-6-external-ai-and-prompt-injection).

The API reads root `.env`; `apps/api/.env` is not used. Nonempty process environment
values override the file. Restart your API after changing settings. Do not dump
settings, environment variables or raw errors to team chat.

## 8. Check setup without changing anything

macOS:

```sh
make team-check
make team-check-integration
```

Windows (or either platform using its installed Python 3.14):

```powershell
python scripts/team_doctor.py
python scripts/team_doctor.py --integration
```

The same standard-library script powers both entry points. Default checks inspect
OS, tools/versions, Docker daemon/Compose, repository root, branch category, Git
status, ignore rules and loopback ports 5173/8000/5432. `--integration` also checks
`.env`, certificate presence, required setting names, selected provider/key and
Onshape/token-key presence. It displays the exact standard localhost URLs only
when matched; other configured URLs are withheld. Branch names/file names from Git
status and command errors are withheld to avoid leaking private text.

`PASS` means the specific check passed; `WARN` needs review (including running
services, Windows's lesser host verification, local edits or nonstandard URLs);
`FAIL` means a missing/unsupported prerequisite or failed check. Exit code is 1
if any check fails, otherwise 0; warnings alone do not fail the command.
The doctor checks presence, not secret validity, certificate trust/expiry/key match,
database health, migrations, OAuth grants or provider quota. It supports the simple
single-line `.env` syntax shown here; unsupported syntax reports a fixed error.
The API remains authoritative for configuration validation. It installs nothing,
writes nothing, starts/stops nothing, and runs no migrations or external API calls.
Port probes connect on loopback without sending data; a free-port result is a
momentary observation, not a reservation. An occupied port may be your running
Forge service; inspect it yourself, never kill an unknown process blindly.

## 9. Start Forge

### macOS

Terminal 1, repository root (stop on any failure):

```sh
make db-up
make migrate
make migration-check
make dev-api
```

Terminal 2, repository root:

```sh
make dev-web-https
```

### Windows PowerShell

Terminal 1, repository root (run each command only after the previous succeeds):

```powershell
docker compose up --detach --wait postgres
cd apps/api
uv run --frozen alembic upgrade head
uv run --frozen alembic check
uv run --frozen uvicorn forge_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, **repository root** (not `apps/api`):

```powershell
npm run dev --workspace @forge/web -- --mode local-https
```

Expected: PostgreSQL healthy (`docker compose ps` from the root), migrations at
head, `alembic check` reports no new upgrade operations, API startup completes,
and Vite serves **https://localhost:5173** without certificate warnings.
`http://127.0.0.1:8000/health` proves process liveness only; it does not prove auth
or database readiness. Do not mix localhost and 127.0.0.1 during login.
If startup fails, check the doctor, paths and private configuration locally.
Do not start duplicate servers on occupied ports.

### First real run checklist

1. `https://localhost:5173` loads without a certificate warning.
2. `docker compose ps` shows a healthy database.
3. The API starts and `/health` responds.
4. Continue with Onshape succeeds through your own OAuth registration.
5. The Forge right-panel icon opens in your test workspace Part Studio.
6. Workspace context appears; open the CAD inspector through the context action.
7. **Refresh CAD** reads the test Part Studio and shows honest evidence/unknowns.
8. Send a simple read-only AI prompt such as “What features are in this model?”
9. Confirm no CAD modification occurs; engineering validation remains UNVERIFIED.
10. Check that no secrets appear in the browser console; never share raw network
    exports, cookies, callback URLs, private CAD or screenshots containing them.

Embedded sessions depend on browser cookie policy. Start with the documented `lax`
configuration; if the panel cannot see the session, use **Open Forge in a new tab**,
sign in, return and **Check panel session**. This may still fail in a restricted
browser. Record the result/version and consult
[embedded session guidance](ONSHAPE_EXTENSION.md#frame-headers-and-authentication).
An operator-reviewed `none` option already exists and requires HTTPS, but it does
not guarantee iframe access. Never relay tokens or disable CSRF/cookie security.
Automated tests do not prove your own real Onshape/provider setup works.

Stop servers you started with Ctrl+C. Stop your database with `make db-down` on
Mac or `docker compose down` from the root on Windows; both retain the volume.

## 10. Branch, commit, push and review

Before a new task, finish/commit intended existing work and ensure a clean tree.
Then (both platforms):

```sh
git checkout main
git pull origin main
git checkout -b feature/short-name
```

Prefer `feature/<short-name>`, or for an explicitly authorized future Phase 7 task,
`phase7/lesson-engine`, `phase7/learning-ui`, or `phase7/check-my-step`. Name one
owner per feature area. Branch naming is not permission to start a roadmap phase.
Run focused tests while editing. Before pushing, run relevant tests and inspect
only intended files; never use an indiscriminate add for local integrations.
Replace angle-bracket placeholders below before running:

```sh
git add <intended files>
git status
git diff --staged
git commit -m "feat: describe the scoped change"
git push -u origin <branch>
```

Open a Pull Request on GitHub targeting `main`. Describe the problem, change,
tests and limitations. Another teammate reviews it and checks the tests before
merging. Passing local tests alone does not prove deployment readiness.

To pull team changes, first commit your intended feature work and check the tree
is clean. Use a normal merge to avoid rewriting published history:

```sh
git checkout main
git pull origin main
git checkout feature/short-name
git merge main
```

If `pull` asks for a divergence strategy, stop and review why local `main` has
commits; use `git pull --no-rebase origin main` only after reviewing that merge.
Do not use destructive reset or force-push as the normal workflow. After dependency
changes rerun the frozen setup commands. After migrations, run `make migrate` or,
from `apps/api` on Windows, `uv run --frozen alembic upgrade head`, followed by
`uv run --frozen alembic check`.

### Merge conflicts

**STOP** if Git reports a conflict. Do not let an AI blindly choose “ours” or
“theirs.” Read both changes, coordinate with their authors, resolve intentionally,
then inspect the diff and run tests again. Be especially careful with package
lockfiles, database migrations, shared design tokens, roadmap/docs and future
lesson schemas. The Phase 6.5 design system is frozen; resolve conflicts without
silently changing it. Review migration ordering together; do not invent schema repairs.

## 11. Coding AI tools and separate worktrees

Teammates may use Codex, ChatGPT coding workflows, Claude Code, Cursor, GitHub
Copilot or other legitimate coding tools. Every tool must obey repository rules.
Use this reusable agent-start instruction:

> Read AGENTS.md before making any change.
> Work only within the currently authorized task.
> Inspect existing code and Git status first.
> Do not weaken Forge security, privacy, evidence or design-system boundaries.
> Do not commit secrets.
> Do not begin a later roadmap phase.
> Run relevant tests before declaring work complete.

**DO NOT run multiple coding agents against the SAME working tree at once.**
They can overwrite files, the Git index, uncommitted changes and generated files.
For simultaneous agents on one machine, use separate worktrees/directories and
branches (future authorized task examples):

```sh
git worktree add ../FORGE-learning-ui -b phase7/learning-ui
git worktree add ../FORGE-checker -b phase7/check-my-step
```

Run these from a clean, updated `main`; each directory gets its own branch. Each
needs its own frozen dependency install. `.env` and `.certs` are ignored/untracked
and are **not** automatically copied. For credential-free tests, leave them absent.
For real integration, create that worktree's `.env` from `.env.example`, generate
its own local encryption key and enter credentials privately. Generate localhost
certificates in its own `.certs` with the same mkcert commands. Never commit secrets
to make worktrees easier, and never send the settings through an agent/chat.

Only one real integration stack should run per machine at a time using the standard
ports. Stop the stack you own before switching. Compose's explicit project name
`forge` means worktrees on the same machine otherwise address the same containers
and volume. To isolate a second worktree's database, configure a **distinct** public
local `POSTGRES_PORT` and matching `DATABASE_URL`, and use a distinct Compose project
name consistently, e.g. `docker compose -p forge_learning_ui up --detach --wait postgres`
and later `docker compose -p forge_learning_ui down`. Do not use `make db-up/down`
for that alternate project. Do not run parallel APIs/web servers on the standard
ports or change origins to avoid this constraint. Keep one active localhost
integration and use other worktrees for isolated tests.

## 12. Local databases and migrations

Each developer has their own PostgreSQL on their own computer. Do not share database
files or volumes. Commit new migration scripts to Git, and apply pulled migrations
locally. Changing `POSTGRES_*` does not rewrite existing database credentials.
Never delete a teammate's data volume to fix a migration problem without understanding
it and agreeing on a backup/recovery plan. `db-down`/`docker compose down` retains
data; do not add volume-deletion flags.

## 13. Quality commands

From the repository root on Mac:

```sh
make format
make lint
make typecheck
make test
make build
make test-e2e
make compose-check
make audit
```

Windows PowerShell equivalents, from the root (stop when a command fails):

```powershell
npm run format
cd apps/api
uv run --frozen ruff format . ../../scripts
cd ../..
npm run lint
cd apps/api
uv run --frozen ruff check . ../../scripts
uv run --frozen ruff format --check . ../../scripts
cd ../..
npm run typecheck
cd apps/api
uv run --frozen mypy src tests migrations ../../scripts
cd ../..
npm test
uv run --project apps/api --frozen pytest apps/api/tests
npm run build
npm run test:e2e
docker compose config --quiet
npm run audit:dependencies
uv run --project apps/api --frozen pip-audit --skip-editable
```

The directory changes ensure Python tools find the API configuration. Build before
browser tests. The default backend suite includes the
doctor tests; a focused run is `uv run --project apps/api --frozen pytest apps/api/tests/test_team_doctor.py`.
Real PostgreSQL regressions need explicit private test configuration as described
in [DEVELOPMENT.md](DEVELOPMENT.md#authentication-migrations-and-checks).
Tests use synthetic data and no real provider keys. Do not skip a failing gate or
regenerate a dependency lockfile to hide the problem.

## 14. Rules for the 36-hour build

- Keep `main` deployable; use small PRs and merge frequently after review/tests.
- Give each feature area one owner and announce shared-file changes.
- Avoid giant cross-cutting refactors; preserve the approved design system.
- Pull `main` before a new task; run focused tests during development.
- Run complete gates at milestones and record platform/credential limitations.
- Share no secrets in team chat and never broaden OAuth permissions casually.
- Keep CAD read-only and Phase 7 unstarted until separately authorized.
