# UI architecture through Phase 2

## Ownership

`App.tsx` applies the authentication gate and composes the shell, modes, hash navigation, preferences, onboarding,
notifications and error boundary. React hooks own local interaction state; no
state-management or routing framework is required. The `auth/` frontend boundary validates `/api/me` at runtime; account mutations
include a session-bound CSRF header. Provider credentials never enter this boundary.

| Directory                    | Responsibility                                                                                |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| `packages/design-system/src` | Tokens, shared CSS, reusable accessible presentation primitives                               |
| `apps/web/src/components`    | Application shell, composer, CAD context, onboarding, error boundary and concept illustration |
| `apps/web/src/features`      | Design draft, brief, plan, progress, validation, Modify, Learn, settings and history views    |
| `apps/web/src/lib`           | Typed UI records, allowlisted browser preferences, fixed public error copy                    |
| `apps/web/src/preview`       | DEV-only UI lab and synthetic fixtures                                                        |

Feature components accept typed records and callbacks. They do not perform
network calls. Future backend adapters must validate responses at their boundary
before supplying records; a TypeScript type alone does not validate external data.
Business logic, engineering calculations, CAD authorization and orchestration
remain backend responsibilities for later phases.

## Design system

Import primitives from `@forge/design-system` and tokens/component styles from
`@forge/design-system/styles.css`. Tokens cover surfaces, borders, text, accent,
PASS/success, WARNING, FAIL/error, UNVERIFIED, spacing, radius, shadow and fonts.
Light and dark palettes use the same semantic variables. System theme follows
`prefers-color-scheme`, including changes during a session. Reduced motion disables
loading animation. System fonts require no external font requests.

Reusable primitives: Button, IconButton, Input, Textarea, Card, Panel, Badge,
StatusBadge, Tabs, Dialog, Tooltip, Dropdown, Separator, Skeleton, Toast,
EmptyState, ErrorState, ProgressStep and ValidationRow. Radix manages tab keyboard
navigation, dialogs, focus trapping, menus, tooltips and notifications. Statuses
combine a symbol, explicit text and color; UNVERIFIED has its own treatment.

The shell uses container queries: narrow panels show a compact header, mode tabs
and one content column; wide views add workspace navigation and a context rail.
CAD context can be opened from the header at any width. Forms and action bars wrap.
The rail-carriage SVG is a labeled concept illustration, not generated CAD.

## Routes and data boundaries

| Hash            | Behavior                                                                    |
| --------------- | --------------------------------------------------------------------------- |
| `#/` or no hash | Sign-in gate, then authenticated Design/Modify/Learn workspace              |
| `#/settings`    | Account status, disconnect/sign out; local preferences                      |
| `#/history`     | Empty history; no fake real project records                                 |
| `#/lab`         | Development only: lazy-loaded mock preview with state/layout/theme controls |

An unknown hash falls back to the workspace. In production `import.meta.env.DEV`
is false, so Vite removes the UI lab and synthetic data from JavaScript assets.
There is no production environment toggle that silently exposes the lab.
The Playwright suite verifies both the compiled production boundary and dev lab.

Lab states: Design empty, engineering brief, plan, running/failed agent,
validation report, validation failure, no results, Modify, Learn, settings,
history, disconnected Onshape, no document, errors, loading and components.
Run states are pending/active/complete/warning/failed/cancelled. Selection states
are none/one face/two edges/ambiguous/unsupported/stale. Error fixtures cover
connection, document, permission, network, timeout, AI unavailable, CAD failure,
rate limit, cancellation and unexpected failure.

## Local interaction semantics

- Prompt suggestions populate and focus the composer. Sending in the normal
  workspace prepares an in-memory draft; it does not invoke AI. Enter adds a line;
  Ctrl/Command+Enter submits, except during input-method composition. Busy and
  stop states are presentation affordances for future streaming.
- Sending in the lab opens a fixed example brief. It does not interpret the prompt.
  Brief edits are local to that mounted view and do not rewrite the separate fixed
  sample plan. Assumptions, missing input and sample-confirmed fields are explicit.
- Approve and Build advances only to the sample progress view. States are selected
  manually, without simulated timed execution. The sample report is independently
  selectable even after cancellation; it is not a result of that preview run.
- Modify uses a fixed 4 → 9 mm thickness example, explicitly independent of arbitrary
  prompt text. Only the one-face sample permits Apply. Selection changes discard
  proposals; Apply records only a local preview acknowledgement.
- Learn is an authored four-step reading preview. Show me and Explain why display
  local text. Check my work returns UNVERIFIED because no CAD inspection exists.
  Completing the lesson marks reading complete, not CAD work complete.
- History receives typed arrays; normal history is empty. All fixture timelines,
  operations and reports are explicitly labeled sample data.

Browser storage contains only versioned preferences: theme, future display units,
onboarding completion, printer name, bounded printer dimensions and material text.
Dimension inputs use mm and accept integer values from 1 to 2000; this is input
hygiene, not a verified manufacturing capability. Sample records retain explicit
units. Prompts, proposals, brief edits and reading progress are never persisted.
The reader reconstructs an allowlisted record and rejects invalid stored values.
Blocked storage preserves usable session state and explains the limitation.

Phase 2 adds real backend OAuth and account persistence; real-provider verification
awaits credentials. No OpenAI calls or CAD reads/writes exist. There are no real CAD
approval records, engineering validations or private model reasoning.

The gate supports checking session, signed out, authorizing, denied, invalid/expired
state, session expired, network failure and unconfigured deployment. Account settings
support connected, disconnected/reconnect, revoked and authorization-error states.
Connection status describes the last verification; Check connection performs a real
identity request. Disconnect has an accessible confirmation and clearly distinguishes
local token deletion from revocation in Onshape. Sign out ends only the current session.

The frontend polls minimized session status once per minute and on focus. CSRF tokens
stay in memory; cookies are HttpOnly. The login action navigates the top-level browser;
a separate-tab link supports blocked embedding. The development-only lab bypasses
the gate for presentation review but can neither mint sessions nor call provider APIs.
