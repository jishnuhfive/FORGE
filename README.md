# Forge

AI engineering inside Onshape.

Forge is an engineering tutor and read-only CAD assistant embedded in Onshape's
right panel. Learners perform the CAD operations while Forge helps explain what
to do, why it matters and how to recover when stuck. Approval-bound design
execution and deterministic checks of supported constraints remain planned.

**Current status: Phase 7 Learning Mode foundation approved after successful real Onshape human validation.**
Phase 6.5 remains visually approved after two human-review passes.
The product UI and canonical design system are frozen: Obsidian, Arc Blue, the
Oblique Plane identity, restrained functional Liquid Glass and answer-first
reading. Final product copy uses timeless capability and uncertainty language.
See [the final review](docs/PHASE_6_5_FINAL_REVIEW.md) and
[the approved design system](docs/FORGE_DESIGN_SYSTEM.md).

Real read-only Groq AI was verified inside Onshape during Phase 6.
Phases 0–5 are preserved, including real OAuth, validated right-panel context and
selection, four backend read operations and the CAD Inspector verified against a
real Part Studio. The Design composer now offers read-only AI analysis inside
Onshape after an explicit send. No CAD changes or engineering validation execute.

Forge uses a provider-independent backend agent with Groq / `openai/gpt-oss-120b`
by default. OpenAI Responses / `gpt-6.1-sol` remains an explicit optional provider.
Both use one no-argument inspection tool, bounded requests and normalized progress.
Groq separates tool calling from strict final JSON-schema output into two rounds.
Explicit CAD modification requests use a deterministic read-only capability path:
the same authorized CAD inspection, zero provider calls, and no inferred edit target.
No automatic paid-provider fallback exists; shared free capacity is limited.
It reads fresh Phase 5 evidence for each send and preserves unknown units, missing
mass, incomplete evidence and unknown selection ownership. Verified answer facts
are selected from server-authored evidence statements. Optional next steps use reviewed server wording and remain explicitly unverified.
Broad inventory answers are concise deterministic presentations of captured evidence;
details are available separately. Conversations remain in panel memory, at most three exchanges.

AI requests disclose that prompts, recent conversation and bounded CAD evidence go
to the operator-configured hosted AI service. Groq inference has reliability/abuse
retention exceptions unless the operator enables its Data Controls. Optional
OpenAI uses `store:false`. Neither configuration claims zero retention by default. No automatic AI calls, database conversation storage,
localStorage conversation persistence or content logs exist.
See [Phase 6 review](docs/PHASE_6_REVIEW.md) for the complete boundary, checks and
the final user-reported live results, full quality gate and local Groq setup.
Phase 7 adds authored learning with no provider or CAD requests; Phase 8 model checking is not started.
See [the Phase 7 review](docs/PHASE_7_REVIEW.md) for lesson architecture and human acceptance.
This is not a publicly deployed production service.

## Learning Mode

Choose Learn, select your CAD experience and goal, then begin **Sketch to solid**.
Read one step at a time, open Why and vocabulary, and deliberately request a
conceptual hint, tool-specific hint or full explanation. Mark steps done yourself;
the completion summary reports only observed interactions, never mastery or CAD
correctness. The lesson works without an AI provider or model.

Learning stays in panel memory across modes/settings/history. Reset, reload, panel
destruction, sign-out or a genuine session/connection teardown clears it. No learning
records, analytics, browser-storage entries or database tables are added.

## Architecture and stack

One React + TypeScript + Vite web application will serve desktop browsers on
macOS and Windows. Tailwind CSS, Radix accessible primitives, and Lucide provide
the presentation foundation. Motion is restrained, event-driven and respects reduced-motion preferences;
there is no idle decorative animation.

FastAPI + Pydantic owns server boundaries; SQLAlchemy and psycopg are installed
with Alembic for PostgreSQL authentication persistence. uv manages Python. npm workspaces manage the web and shared design
system. Docker Compose runs PostgreSQL; native development servers provide fast
reloads. Git origin is `https://github.com/jishnuhfive/FORGE.git`.

## Prerequisites

- Node.js 24 LTS and npm 11.
- Python 3.14 and uv; the API lockfile supports Python 3.14.
- Git, Docker with a running daemon, Docker Compose, and GNU Make 3.81+ on macOS.
- Playwright browsers for browser tests, installed explicitly with `make browsers`.

Versions actually verified are recorded in `docs/PHASE_0_REVIEW.md` after validation.
No AI-provider key, Onshape account, or GitHub account is required to review the UI.

## Quick start

For the sign-in screen and credential-free development UI lab, run:

```sh
cd /Users/jishnuhiremath/Developer/FORGE && make dev-web
```

Open <http://127.0.0.1:5173>. The development-only UI lab is
<http://127.0.0.1:5173/#/lab>. Account settings after sign-in: <http://127.0.0.1:5173/#/settings>.
The reserved history route is <http://127.0.0.1:5173/#/history>. Ctrl+C stops the server.

For a fresh checkout, run `make setup` first. `make dev` still starts both native
web and API servers. Optional PostgreSQL starts with `make db-up` and stops with
`make db-down`, retaining its data. Neither is required for the development UI lab.
The API health endpoint remains <http://127.0.0.1:8000/health>.

No `.env` is required for the UI lab or tests. Real login needs the exact
[Onshape application and local HTTPS setup](docs/AUTHENTICATION.md). `.env.example`
contains empty placeholders; never put real credentials in it. The local database uses deliberately public development defaults
on loopback only. See [development](docs/DEVELOPMENT.md) before overriding them.

## Team development

Start with the [team onboarding guide](docs/TEAM_DEVELOPMENT.md) for independent
macOS/Windows setup, private integrations, branches, PRs and coding-agent worktrees.
`make team-check` checks local readiness; add `--integration` to the direct
`python scripts/team_doctor.py` command to check private integration presence safely.

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
connection action verifies identity, without accessing CAD. Standalone Design prompts remain local drafts; inside Onshape, explicit sends run
read-only AI. Learn offers a three-step Sketch to solid sample, progressive hints and vocabulary.
Progress is learner-reported; no lesson model checking runs. See [UI architecture](docs/UI.md).

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
