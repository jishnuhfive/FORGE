# UI architecture through Phase 9B controlled safe editing

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

Presentation views accept typed records and callbacks. Dedicated auth, CAD and AI
client boundaries validate network responses before rendering; TypeScript types
alone do not validate external data. Phase 6 Analysis owns local request/progress
state and uses `ai/api.ts` for bounded normalized streaming. Business logic,
engineering calculations, CAD authorization and AI orchestration stay backend-only.

## Design system

Import primitives from `@forge/design-system` and tokens/component styles from
`@forge/design-system/styles.css`. Tokens cover surfaces, borders, text, accent,
PASS/success, WARNING, FAIL/error, UNVERIFIED, spacing, radius, shadow and fonts.
Dark is the new-user default; light and dark palettes share semantic variables. Explicit System theme follows
`prefers-color-scheme`, including changes during a session. Reduced motion disables
loading animation. System fonts require no external font requests.

Reusable primitives: Button, IconButton, Input, Textarea, Card, Panel, Badge,
StatusBadge, Tabs, Dialog, Tooltip, Dropdown, Separator, Skeleton, Toast,
EmptyState, ErrorState, ProgressStep and ValidationRow. Radix manages tab keyboard
navigation, dialogs, focus trapping, menus, tooltips and notifications. Statuses
combine a symbol, explicit text and color; UNVERIFIED has its own treatment.

The shell uses container queries: narrow panels show a compact header, mode tabs
and one content column; wider views retain a centered reading column.
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

- Prompt suggestions populate and focus the composer. Sending in standalone
  mode prepares an in-memory draft. Inside a supported authenticated Onshape
  workspace, Phase 6 sends an explicit read-only AI request. Enter adds a line;
  Ctrl/Command+Enter submits, except during input-method composition. Busy and
  stop states control the actual foreground Phase 6 request.
- Sending in the lab opens a fixed example brief. It does not interpret the prompt.
  Brief edits are local to that mounted view and do not rewrite the separate fixed
  sample plan. Assumptions, missing input and sample-confirmed fields are explicit.
- Approve and Build advances only to the sample progress view. States are selected
  manually, without simulated timed execution. The sample report is independently
  selectable even after cancellation; it is not a result of that preview run.
- The DEV Modify fixture uses a fixed 4 → 9 mm thickness example, explicitly independent of arbitrary
  prompt text. Only the one-face sample permits Apply. Selection changes discard
  proposals; Apply records only a local preview acknowledgement.
- Learn uses an authored three-step fundamentals lesson with short experience/goal
  setup, Why/vocabulary disclosures and an explicitly requested three-level hint
  ladder. Mark step done is learner-reported progress. The fundamentals sample has no Check my step action; the Mounting Bracket
  guided project now provides the explicit deterministic checker described below. The completion summary records interactions only.
- History receives typed arrays; normal history is empty. All fixture timelines,
  operations and reports are explicitly labeled sample data.

Browser storage contains only versioned preferences: theme, future display units,
onboarding completion, printer name, bounded printer dimensions and material text.
Dimension inputs use mm and accept integer values from 1 to 2000; this is input
hygiene, not a verified manufacturing capability. Sample records retain explicit
units. Prompts, brief edits and reading progress are never persisted in browser storage.
Phase 9B proposals use short-lived backend operational storage described below.
The reader reconstructs an allowlisted record and rejects invalid stored values.
Blocked storage preserves usable session state and explains the limitation.

Phase 2 established backend OAuth and account persistence. Phase 4–6 subsequently
added real read-only CAD and explicit hosted AI requests. Phase 9B separately adds default-OFF guarded suppression and ephemeral approval
records. No engineering certification or private model reasoning is persisted.

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

## Phase 3 live-capable CAD Context

`/extension` uses the existing app and hash navigation, with `OnshapeProvider` outside
AuthGate. A typed in-memory context exposes launch and message status; no raw query
strings reach feature components. CAD Context now shows Not inside Onshape, Waiting
for document context, safe launch IDs/revision, or validation/origin errors. IDs are
abbreviated; document names and element types are never inferred. The narrow header
opens the existing context dialog and the wide view retains the context rail.

Embedded signed-out/expired sessions have a recheck button and safe top-level/new-tab
sign-in. Local themes and onboarding are retained. The DEV-only
`#/onshape-simulator` previews internal no-selection/face/edge/clear/change/stale
states, including multiple selection beyond the live adapter.
Normal product UI shows only validated live counts: one face, one edge or no selection.
Malformed trusted selection shows unavailable and removes stale references. See
[ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md) for the remaining live verification.

Development frames with valid context also have a **Selection diagnostic** section
below the app, including when iframe auth is unavailable. It starts disabled and
exposes a wrapped readonly sanitized textarea plus copy/clear/disable buttons. It
never changes selection labels; the independent adapter validates live messages. Narrow layouts wrap
buttons and code; clipboard-policy failures provide a manual-copy fallback. Both
this diagnostic and the simulator are absent from production.

The Design prompt context badge also reads the normalized store. A valid workspace
shows **Onshape workspace context**; an explicit version shows **Onshape version
context · messaging unverified**. Standalone/waiting/error states are distinct. The
old missing-prop “No CAD context” fallback is no longer used by the Design workspace.
Preview labels remain explicitly synthetic and no CAD operation is enabled.

**Launch context diagnostic** is a DEV-only section below the workspace/footer,
before selection diagnostics. It remains visible on `/extension` when context is
invalid. Show/copy/clear controls manage a wrapped readonly sanitized metadata report;
no ID values, raw URL or credentials are rendered. Production has no such panel.

## Phase 6 analysis in the existing Design workspace

A validated Phase 3 workspace launch plus a connected Forge session enables the
composer immediately, including `EMBEDDED_INITIALIZING` while selection is waiting.
A trusted later show/selection message is not required. No URL parsing or weakened
origin/parent check was added. Unsupported contexts remain unavailable; selection
is extra evidence, not a requirement to select a face or edge before asking.

The existing composer retains Cmd/Ctrl+Enter, multiline Enter, composition handling,
labels and button primitives. The AI view displays progress, escaped structured
answers, evidence statuses, uncertainties, unverified suggestions, assumptions and
capture time. Empty live regions are not mounted while idle, preserving the
inspector modal's accessibility boundary. Normalized API errors require explicit
retry; pending refs block duplicate sends and cancellation aborts fetch.

Only the user's explicit send transfers the disclosed prompt, minimal recent
conversation and bounded current CAD to the configured hosted AI service. Normal CAD workflow copy remains Forge-branded; provider quota failures show a generic capacity-unavailable state with explicit retry. No calls occur on selection,
visibility or Refresh CAD. At most three exchanges remain in memory. Exact context
and session keys clear old requests/conversation; ordinary same-context tab
switching preserves them. No localStorage, PostgreSQL conversation or provider
Conversation objects are used. Standalone local drafts and all DEV previews remain
separate from the live agent. The separate default-OFF Modify workflow is described below; Design stays read-only.
See [AI_AGENT.md](AI_AGENT.md) for the server boundary and privacy caveats.

### Phase 6 live-response repair

The primary inventory answer is a concise server-rendered overview; raw parameter
kinds and repetitive parameter caveats stay out of it. Detailed evidence is secondary.
An Evidence disclosure button uses `aria-expanded` and mounts rows only when open;
no empty hidden list markup enters Chrome's rich clipboard when copying a collapsed
answer. Empty/whitespace evidence is rejected, with a defensive render filter; zero
rows omit the section. Suggestions contain optional reviewed next steps, never the
factual answer repeated as prose. Empty/identical suggestion text is omitted.

"Selection unknown" is intentional on fresh launch before a verified message.
A trusted empty SELECTION shows "No selection"; FACE/EDGE show their observed
category only. Neither show nor lack of intentional selection proves no selection.
No bridge semantics or security checks changed in this repair.

### Phase 6 hard selection grounding

A direct selected-FACE/EDGE question confirms the observed panel category, then
shows owning part/body/feature, dimensions and selection-specific geometry as unknown.
Selected face surface type/area/normal and edge adjacent geometry are unavailable.
Such answers omit Assumptions, Suggestions and To explore next; they never imply
Forge can retrieve a mapping/measurement that the current tool does not provide.
Other optional assumptions/questions use reviewed hypothetical/request wording.
The existing public schema and selection bridge are unchanged.

## Phase 6.5 presentation

The canonical visual specification is [FORGE_DESIGN_SYSTEM.md](FORGE_DESIGN_SYSTEM.md).
Dark is the default for new/invalid preferences; existing explicit System/Light/Dark
choices remain honored. The optional allowlisted `reduceTransparency` boolean is
local display preference only. OS reduced motion/transparency, increased contrast
and forced colors also adapt the shared material.

The shell is a single compact panel at every width: brand, one capability state,
context/inspector action and segmented navigation. Marketing rails, concept artwork
and repeated analysis badges have been removed from the working workspace. Saved
versions remain visibly distinct and do not enable analysis. Modify implements the default-OFF safe-write workflow below; Learn remains student-operated.

`GlassSurface`, `GlassDefinitions` and `ForgeMark` live in the shared design system.
One CSS material supplies bounded blur, edge-only SVG displacement and event-driven
illumination. Real DOM text is unaffected. There is no graphics dependency, shader,
parent viewport access or permanent animation. Backdrop SVG support is progressive;
unsupported engines retain the complete baseline material.

`AnswerContent` is a pure presentation view shared by real analysis and the DEV lab.
Contextual Limits precede a collapsed Evidence control; full technical limits stay
inside it. Equal evidence statuses share a
single heading; original statements and safe escaped text remain intact. Evidence
rows mount on expansion and disappear on collapse. Captured time stays inside the
disclosure. No response schema, API request, provider, grounding or lifecycle code
was changed. The sticky composer reserves a real progress line, retains keyboard/
IME behavior and uses one send/stop footprint. Material backing separates it from
scrolled evidence. Data-transfer detail is available beside the point of send.

`#/lab` adds Phase 6.5 workspace and design-system states, manual status selection,
320/360/400/480/600px layouts and simulated motion/transparency/contrast adaptations.
Those previews never call AI/Onshape. Existing synthetic workflows remain available.
Launch/selection diagnostics are behind Workspace menu → Developer (a dialog);
a signed-out development embed has a Developer recovery action. Modules remain
production-excluded and observer semantics are unchanged.

Second-review refinement details are in [PHASE_6_5_REFINEMENT_REVIEW.md](PHASE_6_5_REFINEMENT_REVIEW.md).
`ai/presentation.ts` is an exact display grammar over the existing Answer evidence,
not a network/schema or grounding change. Compatible small canonical overviews
become a feature sequence and count line. Any unmatched qualification, unknown
inventory count or ambiguous evidence keeps prose. The exact full answer remains
inside expanded Evidence; additional paragraphs stay visible. Names remain escaped
DOM text. Evidence statuses, mass caveats and selection ownership are unchanged.

The authorized Phase 14 polish adds `ai/friendly.ts`, a conservative display grammar
for exact canonical inventory/order/terminal/activity, dependency limitations,
selected ownership and read-only capability replies. It never summarizes model
prose into CAD facts or joins identities by labels. Ambiguous IDs/names/positions,
statuses and unmatched wording keep the original answer. Full canonical answers,
all uncertainties and secondary guidance remain inside Evidence. The primary answer
shows only relevant known Limits; unrecognized limits remain visible. Empty inventory
is a valid simple answer with no irrelevant suggestions in the primary view.

The top mode bar optionally auto-hides within the existing workspace scroller:
48 px downward travel hides it, 16 px upward travel reveals it, and the first 24 px
always shows it. Direction hysteresis, one passive/rAF-throttled listener and
visibility-only DOM updates avoid per-pixel React renders or layout measurements.
Transform/opacity preserve layout space; reduced motion removes transitions.
Tab focus reveals it immediately, and mode changes restore visibility. The bottom
sticky composer and accepted visual system are unchanged. See the user-reported
PASS for all eight human read-only checks and seven targeted post-polish UX visual checks in
[Phase 14](PHASE_14_ASK_FORGE_GRAPH_GROUNDING.md).

A single workspace scroller contains the mode control and content; the shell header
sits outside it. Flex sizing anchors the conversation composer near the bottom.
The first-use composition stays compact near the top. Prompt input grows 44–144px;
its form-width observer queues one fit per change and cancels on cleanup. Data use
is an info action in the composer toolbar; Privacy is in the workspace menu.
Material comparison and Logo candidates are separate DEV-only UI Lab views.

## Approved freeze

Phase 6.5 was visually approved after two human-review passes. Preserve the accepted
layout, logo, material strength, typography, spacing, composer and navigation.
Normal product copy uses timeless capability/selection/uncertainty language;
internal phase/adapter/schema language belongs only to development records and
DEV diagnostics. Actual quoted CAD text remains untrusted data, never rewritten as
product policy. Settings micro-polish reuses existing controls/tokens; the context
strip and 420ms intro remain unchanged. The forced-color/opaque filter declarations
use prefixed-first/unprefixed-last order to survive the production CSS optimizer.
See [the final review](PHASE_6_5_FINAL_REVIEW.md).

Forced-color mode maps semantic colors to system Canvas/CanvasText/LinkText and
ButtonFace/ButtonText, so text and control contrast follow the user’s system palette.
This adaptation does not change the approved normal appearance.

## Phase 7 fundamentals-sample interaction and lifecycle

`learning/` separates lesson definitions and their runtime validation, pure session
transitions, selectors, provider ownership and small setup/guidance/progress views.
The provider sits above Radix tab content and settings/history hash routes, so
ordinary navigation does not destroy the lesson. Changing session CSRF identity or
connection status clears only learning state; account confirmation UI survives.
Logout/expiry unmounts it. Reset explicitly confirms removal of the profile and all
progress. Reload, iframe destruction and a new panel start at learner setup. Ordinary
focus, visibility, selection and unchanged `/api/me` checks preserve it without reads.

Experience changes introduction wording; the goal frames the same available sample.
The guided-project choice now opens the Phase 8 Mounting Bracket lesson described
below; the fundamentals goal retains this sample.
No hidden mastery adaptation is inferred. Each hint request replaces the prior level
with stronger help; access has no delay or failure prerequisite. After the final
reveal the same focusable control says Full explanation shown and is aria-disabled.
Why and vocabulary mount on request and keep predictable button focus/aria-expanded.
Opening the same term again does not increase the unique-term count. Hints cannot
be requested after a step is marked done. All three steps are required.

The active step has a semantic title, objective, instruction, optional Why and
vocabulary, help, quiet progress, and a continuation area. Reading stays on the
solid layer; controls reuse frozen functional glass styling and tokens. Native
radio groups, named progress and a live hint region support assistive technology.
Explicit introduction/step/completion transitions focus the heading; entering Learn
through tab navigation preserves tab focus. Reduced motion/transparency and forced
colors inherit the design system. Six widths are covered by browser tests.

In the fundamentals sample, only session observations are counted: marked steps, requested hint levels, distinct
term IDs opened, and completed steps with no hints. No percentages, grades, claims
of mastery or verified CAD outcomes appear. Lesson state never enters preferences,
localStorage/sessionStorage, database, analytics or logs. No AI or CAD request is
made by a fundamentals-sample action; bracket checking is explicit as described below. Existing auth status refresh behavior is unchanged.

UI Lab → Learn mode adds deterministic representative states, including safe
unavailable/invalid/load-failure recovery. Those selectors/fixtures are DEV-only.
See [PHASE_7_REVIEW.md](PHASE_7_REVIEW.md) for verification and human review steps.

## Phase 8 Check my step — complete, human validated and merged

A functional control inside the active bracket step (never on the sample lesson or the review
step). States: idle, "Checking current model…" (single genuine request, no fake stages),
verified / not yet / can't fully verify, error and cooldown. Status is shown with a symbol and
a word, never color alone, through the existing StatusBadge tokens. One polite status region;
evidence is a native disclosure. Learner "Mark step done" stays separate from "Steps Forge
verified". A failed check never reveals a hint.

The Mounting Bracket guided project preserves PASS / FAIL / WARNING / UNVERIFIED
findings from fresh CAD evidence, feature-name independence and the single-L-profile
alternative. A later non-verified check revokes that active step's Forge verification;
a later verified check restores it. Within Learn, the student performs all CAD edits.
The user confirms final human validation and merge at `81199ea`; the unchanged
[Phase 8 review](PHASE_8_REVIEW.md) preserves its earlier validation record.

## Phase 9B Modify

[Runtime review](PHASE_9_REVIEW.md) describes the implemented first-write workflow.
Modify offers a bounded intent composer, fresh server inventory, separate explicit
target selection, then an Active → Suppressed semantic preview with effect, limits,
expiry, Cancel and **Approve change**. The quiet solid reading layer and existing
controls remain; no new application, approval modal stack or generic Undo exists.
The preview states that Forge found one solid-body result and an unsuppressed final
Fillet; overall feature health is not established. A present empty provider state map
is unavailable evidence, not inferred health/activity. Success confirms only that
the selected Fillet is now suppressed after the required fresh verification.

Checking, executing and verifying use real server progress announcements. Success
requires fresh deterministic verification; stale, expired, disabled, permission,
provider and uncertain outcomes have distinct text. Uncertainty offers read-only
status/inspection and manual recovery. Context loss removes the preview. Buttons
prevent duplicate actions; server single-use claims remain authoritative.
The shell says Approval required only for available Modify; other modes stay Read-only.

Default OFF clearly says safe CAD editing is disabled, without an executable preview.
Known missing write consent requests permission; unknown authorization fails closed.
Keyboard, live announcements, forced colors/reduced motion and 320px are covered in
synthetic browser tests. Gate A is human-proven with fresh verified success.
Gate B showed no stale suppression after the human changed CAD during the pause;
provider-side rejection audit confirmation remains deferred. Writes returned OFF.

## Phase 10 investigation and transfer UI

Below a check result, an "Investigate" section shows what Forge observed, a radio-group prediction
(always including "I'm not sure yet", neutral feedback, never red/green), a labeled possible explanation,
a labeled try-next suggestion, and a "Verified after re-check" status after an explicit re-check. It adds no
second hint system. Reduced and independent guidance are explained in the panel and never hide
observations or caveats. The transfer challenge reuses the step view with its own progress and a separate
"Restart challenge". Tested at 320, 360, 380, 400, 480 and 640 px, with keyboard, reduced motion and axe.

A fresh supported PASS resolves an investigation; a later FAIL, WARNING or inability
to verify reopens it. Predictions never alter the checker result. Restart challenge
preserves guided lesson progress; Reset lesson clears both. Session counts and
challenge completion carry no grades, mastery percentages or safety claim. Learn
remains read-only and student-operated, independently of Modify availability.

## Phase 11 Ask Forge

A collapsed "Ask Forge" disclosure after the check result and investigation on Mounting Bracket steps and the
transfer challenge. One question field (600 characters, Ctrl/Cmd+Enter), Stop, polite status, fixed-copy alerts that
always say the lesson still works, and answers rendered explanation-first with server-worded "What Forge observed",
"Still unknown", "Next thing to try" and notes. The conversation is cleared on step, document, login or lesson change.
Tested at 320 px, light/dark, reduced motion and with axe.
