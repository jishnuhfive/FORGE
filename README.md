# Forge

Forge is an AI tutor and CAD assistant that lives in the right-hand panel of an
Onshape Part Studio. You work in Onshape like normal, and Forge sits next to you. It
reads what's actually in your model, explains what to do next, and checks your work
with plain deterministic rules (no guessing from a language model).

It's a hackathon project, not a hosted product. You run it on your own machine and
point your own Onshape account at it. This README gets you from a fresh clone to a
working panel.

## What it does

- **Design.** Ask questions about the part you have open. Forge reads the Part Studio
  (features, bodies, mass, your current selection) and answers from that. It can also
  just chat. Nothing is sent to the AI until you press send.
- **Learn.** Guided lessons, including a Mounting Bracket project. "Check my step"
  looks at your real model and reports PASS, FAIL, WARNING or UNVERIFIED. The AI never
  decides those; it can only explain them when you ask ("Ask Forge").
- **Modify.** Edits to the model, and this is **off by default**. You describe a change,
  Forge turns it into a short list of typed operations (suppress or unsuppress the final
  fillet, rename a feature, set an extrude depth, set a fillet radius), shows you
  exactly what will happen, and only runs it after you approve. Every step is
  re-checked against the live model, and nothing is retried or rolled back for you.
  The backend for this is done. The panel UI for it is still being built.

Forge isn't engineering certification. It doesn't check strength, fit or tolerances.

## What you need first

- **Node.js 24** and npm 11
- **Python 3.14** and [uv](https://docs.astral.sh/uv/)
- **Git**
- **Docker** (running) for the PostgreSQL database
- **mkcert**, for local HTTPS (Onshape only embeds HTTPS pages)
- An **Onshape account** where you can create an OAuth application (a free account works)
- A **Groq API key** if you want the AI parts. It's free at
  [console.groq.com/keys](https://console.groq.com/keys)

`make` is optional. On macOS and Linux the commands below use it; on Windows each one has
a plain equivalent right beside it.

You can skip Onshape and the key entirely if you only want to look at the interface.
See "Just the UI" below.

## Just the UI (two minutes)

```sh
git clone https://github.com/jishnuhfive/FORGE.git
cd FORGE
make setup        # Windows: npm ci   then   cd apps/api && uv sync --locked
make dev-web      # Windows: npm run dev:web
```

Open <http://127.0.0.1:5173>. There's also a component playground at
<http://127.0.0.1:5173/#/lab>. This mode needs no `.env`, database or accounts.

## Full setup (real Onshape panel)

### 1. Install dependencies

```sh
make setup
```

Windows: `npm ci`, then `cd apps/api && uv sync --locked`.

### 2. Create your `.env`

```sh
cp .env.example .env        # Windows: copy .env.example .env
```

Keep this file private. It's already in `.gitignore`. Never commit it or paste it
anywhere. Then generate the key that encrypts stored Onshape tokens:

```sh
uv run --project apps/api --frozen python scripts/generate_dev_key.py
```

It fills in `TOKEN_ENCRYPTION_KEY` without printing it. Keep that value stable, because
if you change it, existing logins stop working and you'll have to sign in again.

### 3. Make a local HTTPS certificate

Install [mkcert](https://github.com/FiloSottile/mkcert), then from the repo root:

```sh
mkcert -install
mkdir .certs
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1
```

The `.certs` folder is git-ignored. Don't share it.

### 4. Register Forge in Onshape

You do this once, signed in to Onshape:

1. Click your account icon, then **My account**, **Developer**, **OAuth applications**,
   and **Create new OAuth application**.
2. Name it `Forge Development`. The "Primary format" has to be unique across Onshape and
   can't be changed later, so use something like `com.yourname.forge.dev`.
3. Choose **Integrated Cloud App**.
4. Redirect URL: `https://localhost:5173/auth/onshape/callback`
5. OAuth URL: `https://localhost:5173/auth/onshape/start`
6. Permissions: tick **OAuth2ReadPII** and **OAuth2Read**. Add **OAuth2Write** only if
   you plan to try Modify (see below).
7. Create it and save the secret straight away. It's only shown once. The client ID is
   under **Keys and secret**.

Next, add the panel itself. Under **Extensions**, choose **Add extension**:

- Location: **Element right panel**
- Context: **Inside part studio**
- Action URL (one line):
  `https://localhost:5173/extension?documentId={$documentId}&workspaceId={$workspaceOrVersionId}&elementId={$elementId}`

Don't add a `server` parameter to the Action URL; Onshape adds it for you. If your
account asks for a private store entry before you can use the app, create one under
the app's **Details** (category Content) and subscribe to it. Don't publish it publicly.
[docs/ONSHAPE_EXTENSION.md](docs/ONSHAPE_EXTENSION.md) has the longer version with the
edge cases.

### 5. Fill in `.env`

Open `.env` and set these. Leave anything not listed blank and the defaults apply.

```dotenv
ENVIRONMENT=development
APP_BASE_URL=https://localhost:5173
ONSHAPE_REDIRECT_URI=https://localhost:5173/auth/onshape/callback
ONSHAPE_CLIENT_ID=<from Keys and secret>
ONSHAPE_CLIENT_SECRET=<saved in step 4>
DATABASE_URL=postgresql+psycopg://forge_local:local-development-only@127.0.0.1:5432/forge_local

# AI (optional, but Design chat and Ask Forge need it)
FORGE_AI_PROVIDER=groq
GROQ_API_KEY=<your Groq key>
```

The database URL uses the throwaway local Compose credentials, which is fine for
this setup. Use `https://localhost:5173` everywhere, not `127.0.0.1`. Cookies and the
origin checks treat them as different sites, and mixing them breaks login.

Using OpenAI instead of Groq? Set `FORGE_AI_PROVIDER=openai` and `OPENAI_API_KEY`. There's
no automatic fallback between the two.

### 6. Start the database and run migrations

```sh
make db-up
make migrate
```

Windows: `docker compose up --detach --wait postgres`, then
`cd apps/api && uv run --frozen alembic upgrade head`.

If Postgres complains that port 5432 is taken, set `POSTGRES_PORT` in `.env` and update
`DATABASE_URL` to match.

### 7. Run it

Two terminals, both from the repo root.

```sh
make dev-api          # Windows: cd apps/api && uv run --frozen uvicorn forge_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

```sh
make dev-web-https    # Windows: npm run dev --workspace @forge/web -- --mode local-https
```

Open <https://localhost:5173>, click **Continue with Onshape** and approve. Then open
a Part Studio in Onshape and click the Forge icon in the right panel.

Run only one API process. A leftover server from an earlier run can quietly hold the
port and cause odd "disconnected" errors. If things act strange, kill every `uvicorn`
process and start one fresh.

## If something's off

| Symptom                                  | What to check                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------- |
| Panel is blank or won't load             | Open <https://localhost:5173> in the same browser first and trust the cert |
| Login loops or "session expired"         | You mixed `localhost` and `127.0.0.1`, or kept an old tab around           |
| "Forge couldn't read your model"         | Reconnect from Settings; check the API terminal for errors                 |
| API won't start, mentions migrations     | Run `make migrate`                                                         |
| AI replies say it isn't configured       | `GROQ_API_KEY` empty, or the API wasn't restarted after editing `.env`     |
| Third-party cookie warnings in the panel | Allow cookies for `localhost` in your browser, then reload                 |
| Port 5173 or 8000 already in use         | Something else is running; stop it rather than changing ports              |

## Modify and CAD writes

Modify can change a real document, so it's disabled until you opt in. To try it, use a
throwaway Part Studio, give the OAuth app **OAuth2Write**, and set this in `.env`:

```dotenv
FORGE_CAD_WRITES_ENABLED=true
```

Restart the API and reconnect your Onshape account so the new permission is granted.
Turn it back off when you're done. Writes happen only after you explicitly approve a
shown plan, and Forge stops at the first thing that looks wrong. The details and the
limits of what's been tested are in [docs/HACKATHON_MODIFY_A2.md](docs/HACKATHON_MODIFY_A2.md)
and [docs/PHASE_9_REVIEW.md](docs/PHASE_9_REVIEW.md).

## Everyday commands

| Command                         | What it does                                                        |
| ------------------------------- | ------------------------------------------------------------------- |
| `make dev`                      | Web and API together, plain HTTP, no login                          |
| `make dev-web` / `make dev-api` | One server at a time                                                |
| `make test`                     | Frontend (Vitest) and backend (pytest) tests                        |
| `make test-e2e`                 | Browser tests; run `make browsers` once, then build first           |
| `make lint` / `make typecheck`  | ESLint, Prettier, Ruff, TypeScript, mypy                            |
| `make check`                    | Lint, types, tests, build and Compose validation                    |
| `make db-up` / `make db-down`   | Start or stop PostgreSQL (data is kept)                             |
| `make migrate`                  | Apply database migrations                                           |
| `make test-postgres`            | Extra tests against a real database (set `FORGE_TEST_DATABASE_URL`) |

Tests never touch a real Onshape account or AI provider. On Windows, `test_dev_key`
and two long `test_cad_read` cases fail for reasons unrelated to the app (POSIX file
permissions and long test ids), and they fail the same way on a clean checkout.

## How it's put together

```text
apps/web/                React + TypeScript + Vite interface
apps/api/                FastAPI backend (uv-managed), tests and migrations
packages/design-system/  Shared UI components
docs/                    Architecture, security, per-phase reviews
scripts/                 Dev server supervisor, key generator
tests/e2e/               Playwright tests
docker-compose.yml       Local PostgreSQL
```

Python 3.14, FastAPI, Pydantic, SQLAlchemy and Alembic on the back end, with PostgreSQL
for sessions. The front end is React, Tailwind and Radix. Onshape tokens, session
handling and AI keys stay on the server, and the browser only gets a session cookie and
a CSRF token.

## Where to read more

- [Architecture](docs/ARCHITECTURE.md) and [development notes](docs/DEVELOPMENT.md)
- [Authentication](docs/AUTHENTICATION.md), [Onshape setup](docs/ONSHAPE.md) and
  [the panel extension](docs/ONSHAPE_EXTENSION.md)
- [AI agent](docs/AI_AGENT.md) and [security](docs/SECURITY.md)
- Modify: [A1 executor](docs/HACKATHON_MODIFY_A1.md), [B1 planner](docs/HACKATHON_MODIFY_B1.md),
  [A2 approval API](docs/HACKATHON_MODIFY_A2.md)
- [Roadmap](docs/ROADMAP.md) and [AGENTS.md](AGENTS.md) for contributors and coding agents

## Privacy and limits

When you use the AI, your message, the last few turns of conversation and the relevant
model data go to the AI provider you configured. Groq keeps some data for reliability
and abuse checks unless you turn on its data controls; OpenAI is called with storage
off. Nothing is stored in the database about your chats. There's no license selected
yet and no public hosting. Don't point this at documents you can't afford to lose
until you've tried Modify on a disposable one.
