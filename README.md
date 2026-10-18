# Forge

AI engineering inside Onshape.

Forge is an engineering tutor and CAD assistant embedded in Onshape's right
panel. Learners perform lesson CAD operations while Forge explains what to do,
why it matters and how to recover. Deterministic lesson checks report evidence
with explicit limits. Modify implements one explicitly approved Fillet suppression,
disabled by default. Gate A is human-proven; full provider conformance remains pending.

**Current status: Phase 7 COMPLETE; Phase 8 COMPLETE, HUMAN VALIDATED, and MERGED; Phase 9A PREPARATION COMPLETE; Phase 9B IMPLEMENTED; Gate A PROVEN; Gate B provider-audit confirmation deferred; Phase 10 IMPLEMENTED and MERGED, human validation pending; Phase 11 NOT STARTED.**
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
Onshape after an explicit send. Design remains read-only; engineering validation is not claimed.

Forge uses a provider-independent backend agent with Groq / `openai/gpt-oss-120b`
by default. OpenAI Responses / `gpt-6.1-sol` remains an explicit optional provider.
Both expose one no-argument inspection tool, bounded requests and normalized progress.
Groq can answer general chat without reading CAD; model-specific answers still require inspection.
Groq separates tool calling from strict final JSON-schema output into two rounds.
Explicit CAD modification requests in Design use a deterministic read-only capability path:
the same authorized CAD inspection, zero provider calls, and no inferred edit target.
No automatic paid-provider fallback exists; shared free capacity is limited.
When inspection is required, it reads fresh Phase 5 evidence and preserves unknown units, missing
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
Phase 7 provides authored learning without provider or CAD requests. Phase 8 is
**COMPLETE, HUMAN VALIDATED, and MERGED** into main at `81199ea`; it adds the
Mounting Bracket guided project and explicit deterministic **Check my step** from
fresh CAD evidence. Phase 9A is **PREPARATION COMPLETE**. Phase 9B implements
`suppress_terminal_fillet_v1` behind backend `FORGE_CAD_WRITES_ENABLED` (default OFF):
proposal → explicit approval → fresh state/version check → guarded write → fresh
post-write verification. The first human-approved real suppression entered uncertainty;
Forge made no success claim and did not retry. After deliberate operator recovery,
a fresh approved suppression reached verified success from fresh evidence: Gate A
is PROVEN. Gate B reached the pause; the human advanced the workspace and stale
suppression did not apply. Provider-side rejection audit confirmation was deferred,
so full provider conformance is not claimed. Writes returned OFF.
See the [Phase 9 runtime review](docs/PHASE_9_REVIEW.md) for exact human instructions, the
[Phase 8 review](docs/PHASE_8_REVIEW.md),
[safe-write specification](docs/PHASE_9_SAFE_WRITE_SPEC.md) and
[preparation review](docs/PHASE_9_PREP_REVIEW.md). Phase 10 was implemented and
merged to main separately; this branch now integrates that history and its
investigation/transfer learning. Automated validation is complete; real-Onshape
human validation remains pending. Phase 11 is **NOT STARTED**.
See [the Phase 7 review](docs/PHASE_7_REVIEW.md) for lesson architecture and human acceptance.
This is not a publicly deployed production service.

## Learning Mode

Choose Learn and select your CAD experience and goal. Fundamentals opens the
**Sketch to solid** sample; the guided-project goal opens **Mounting Bracket**.
Both offer authored instructions, Why, vocabulary and deliberate progressive hints,
without AI provider calls. The bracket's explicit **Check my step** retrieves fresh
CAD evidence and computes PASS / FAIL / WARNING / UNVERIFIED deterministically.
Feature names do not determine results; the supported single-L-profile alternative
is accepted. A later non-verified result revokes the active step's Forge verification,
and a later verified result restores it. Learner-marked completion stays separate.
Dimensions, units, hole placement, fit and strength are not certified.

The user confirms final human validation and merge to main at
`81199ea95df04b34e6065441cad87d60b637dcf2`. The unchanged
[Phase 8 review](docs/PHASE_8_REVIEW.md) preserves the original implementation and
validation observations; its provisional status wording is superseded by this
confirmation.

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
read-only AI. Learn offers Sketch to solid and the Mounting Bracket guided project, with
progressive hints and vocabulary.
Learner progress and deterministic Forge verification are distinct. See
[UI architecture](docs/UI.md).

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

Phase 10 (merged to main before Phase 9 and now integrated here; real-Onshape human validation pending) adds mistake
investigation, prediction prompts, explainable guidance fading and an optional transfer challenge to
the Mounting Bracket. It is read-only and session-local. See
[PHASE_10_REVIEW.md](docs/PHASE_10_REVIEW.md).

Phase 11 (implemented on `phase11/contextual-ai-tutor`; not merged, not yet human-validated) adds **Ask Forge**,
a learner-requested AI tutor inside the Mounting Bracket lesson. Deterministic checkers still own every status;
the tutor explains and cannot verify, grade or edit. See [PHASE_11_REVIEW.md](docs/PHASE_11_REVIEW.md).
