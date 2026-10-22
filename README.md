# Forge

**AI engineering inside Onshape.**

Learning CAD can be frustrating when you know what you want to build but do not know how to get there. Forge helps students work through those moments without leaving Onshape.

Forge is an engineering tutor and read-only CAD assistant in Onshape’s right panel. It explains steps, answers questions about supported model information, and helps students understand the choices behind their work. Students make the CAD changes themselves.

Forge does not currently edit models or check whether a design meets engineering requirements. We plan to add checks for supported constraints and design changes that require the user’s approval. The app is still in development and is not yet a public production service.

## How the CAD assistant works

Students type a question in the Design panel and send it when they want help. Inside Onshape, Forge reads fresh CAD information for that request and uses the configured AI service to help answer it. It only starts an AI request after the student sends a prompt.

Forge uses Groq with `openai/gpt-oss-120b` by default. OpenAI Responses with `gpt-6.1-sol` is also supported, but it must be set up separately. Forge never switches to a paid provider automatically. Availability on the shared free service is limited.

Both providers use one read-only inspection tool that takes no arguments. Requests have set limits, and both providers report progress in the same format. With Groq, inspecting the model and producing the final structured answer happen in separate rounds.

If a student asks Forge to change a model, it stays read-only. It inspects the authorized CAD information without calling the AI provider, guessing what to edit, or making changes.

Outside Onshape, prompts stay as local drafts.

## How Forge handles evidence

Forge should be clear about what it knows and what it cannot tell from the model. If units, mass, or other information are missing, it leaves them unknown. If it cannot establish which part owns a selection, it does not guess.

Facts presented as verified come from evidence statements prepared by the server using captured CAD information. General questions about what is in a model get a short summary, with more detail available separately.

Suggested next steps use reviewed wording and are marked as unverified. A suggestion is not confirmation that a design works.

Forge is intended for learning and low-risk mechanical prototyping. It does not provide professional engineering certification.

## Learning Mode

Learning Mode gives students a starting point when they need more guidance. Students choose their CAD experience and goal, then begin the three-step **Sketch to solid** lesson.

The lesson shows one step at a time. Students can open **Why and vocabulary** to learn why the step matters and what the terms mean. They can also ask for a general hint, a hint about the tool to use, or a full explanation.

Students do the work in Onshape and mark each step complete themselves. At the end, Forge summarizes their lesson interactions. It does not check the model or claim that completing the lesson proves mastery.

Learning Mode uses prepared lessons, so it works without an AI provider or model. It makes no AI or CAD requests.

Progress stays in memory while students move between modes, settings, and history. Resetting or reloading the panel, closing it, signing out, or ending the session or connection clears that progress. Forge does not save learning records or collect learning analytics.

## Data and privacy

Before an AI request, Forge explains what will be shared with the AI service configured by the operator: the student’s prompt, recent conversation, and a limited amount of CAD evidence.

Conversations stay in panel memory and are limited to three exchanges. Forge does not save them to a database or browser storage, and it does not keep logs of their content. AI-provider credentials stay on the backend.

The provider’s own retention rules still apply. Groq has retention exceptions for reliability and abuse handling unless the operator enables its Data Controls. The optional OpenAI integration uses `store:false`. Neither setup guarantees zero retention by default.

## Architecture and stack

Forge is built as one web app for desktop browsers on macOS and Windows.

The frontend uses React, TypeScript, and Vite. Tailwind CSS handles styling, Radix provides accessible interface components, and Lucide supplies the icons. Animations are kept small and useful, respond to user actions, and respect reduced-motion settings. There are no animations running just for decoration.

The backend uses FastAPI and Pydantic to handle requests and validate data. PostgreSQL stores authentication data. SQLAlchemy and psycopg handle database access, and Alembic manages database migrations.

We use `uv` for Python dependencies and npm workspaces for the web app and shared design system. Docker Compose runs the local PostgreSQL database. The web and API development servers run natively so changes reload quickly.

The code is available in the [Forge repository](https://github.com/jishnuhfive/FORGE).

## Prerequisites

For the full local development setup, you will need:

- Node.js 24 LTS and npm 11
- Python 3.14 and `uv`
- Git
- Docker with a running daemon and Docker Compose
- GNU Make 3.81 or newer on macOS

The API lockfile supports Python 3.14. The versions tested during development are listed in `docs/PHASE_0_REVIEW.md`.

To run browser tests, install the Playwright browsers:

```bash
make browsers
```

You can review the UI without an AI-provider key, an Onshape account, or a GitHub account. The development UI lab and tests do not need an `.env` file. The UI lab also works without PostgreSQL.

To use real Onshape sign-in, follow the application configuration and local HTTPS steps in the [authentication guide](https://github.com/jishnuhfive/FORGE/blob/main/docs/AUTHENTICATION.md).

Keep real credentials out of `.env.example`. That file should contain empty placeholders only.

## Credits

Ved Tripathi
Jishnu Hiremath
Lakshiet Dasari
