# Phase 6.5 — second visual-review record

Current decision: **Phase 6.5 visually approved after two human-review passes**.
The second-pass design is accepted and frozen. One commit and normal push are
now authorized after the complete final quality gate. See
[PHASE_6_5_FINAL_REVIEW.md](PHASE_6_5_FINAL_REVIEW.md) for current results. Phase 7
has not started. The remaining record documents the refinement and its original
pre-approval verification; previous test counts are historical.

## 1. Visual refinement status

The first real Onshape human review did **not approve** the first pass. This record
covers the resulting refinement. Implementation and synthetic screenshots are for
second human review; they do not constitute approval. No commit, push or Phase 7
work is authorized. Backend, OAuth, CSRF, API schemas, AI provider, deterministic
wording/grounding, read-only CAD and selection lifecycle boundaries are retained.

Screenshots are generated from invented fixtures in the real production panel
iframe and the DEV lab, then opened for visual inspection. They are equivalent
panel states, not a new human review of private CAD inside real Onshape. No real
Groq/OpenAI calls were made by verification.

## 2. Material changes

Shared material B has a 70% cool graphite backing, 10px bounded blur, interior
luminance gradient, darker base, directed 2px optical edge, inset highlight and
soft ambient shadow. The existing edge-only SVG displacement stays bounded at 6.
A static, local titanium luminance bed supplies Forge-owned variation. No parent
viewport capture, graphics dependency, full-panel blur, idle animation or rainbow.
Small related controls share `.glass-action` highlights without another blur.

UI Lab → **Material comparison** places A previous/B refined/C opaque side by side.
The geometry and content match; this compares recipes rather than reconstructing
an old screenshot. Screenshot review selected B because its brighter leading edge
and internal light reveal depth while typed text stays clear. C preserves the same
hierarchy without optics. Real Onshape material/trackpad approval remains human.

## 3. Composer changes

Compact 44px input grows with text to 144px. Width changes schedule one fitting
frame through a cleaned-up form observer. A static optical bed, stronger typing
separation, blue focus edge and integrated selection/shortcut/info toolbar form one
control. Send uses a restrained blue optical fill; hover highlights and press
compression stay small. Send/stop glyphs morph in one fixed footprint. Progress has
a reserved slot immediately above the input. Example space remains during the first
request, so progress does not shift the composer. Sending is always explicit;
keyboard send, IME protection, cancellation and cooldown retain existing behavior.

## 4. Logo candidates

Three original monochrome vectors are retained **only in the DEV comparison**:
A Oblique plane, B Open joint and C Stepped billet. The comparison renders every
candidate at 16/20/24/32/64/128px on dark and light, and in the actual header,
welcome, 16px context and 32px icon contexts. All use solid geometry, no fine-line
dependence, flame, tools, AI hexagon, circuit or sparkle.

## 5. Chosen logo

**A · Oblique plane** is the implemented identity. The oblique top plane, vertical
extrusion and open inner plane provide the strongest dimensional silhouette at
16px, where B/C read more like flat stepped F bars. Three polygons suggest the
sketch → extrusion → object idea without fine strokes. Only this geometry ships in
`ForgeMark`, the accent/monochrome public SVGs and the app icon. B/C remain internal
review fixtures and are excluded from the production bundle. The human subsequently approved this identity.

## 6. Empty state changes

A small mark beside the welcome heading and one sentence leads into three quiet
36px example actions and the composer. Examples gain a local hover/focus highlight
and directional affordance; they populate and focus the input. The composition is
near the top and compact. Welcome branding/examples disappear after the first
exchange, making the panel a working tool.

## 7. Header changes

One identity group, one compact optical Read-only capability state and one workspace
menu. The second row is one contextual control explicitly naming the CAD inspector.
The separate Settings icon is removed. Saved-version and unavailable-context
handling remain honest. The header stays outside the scrolling work area.

## 8. Response hierarchy changes

Compatible broad overviews show **Current model**, captured feature order and
compact typographic counts. At 320px the facts use two columns. Other answers keep
original prose; exact selection evidence can title Selected face/Selected edge.
Generic responses have an accessible Response heading with no repeated visible
Forge analysis label. The content reading plane remains solid and quiet.

The pure frontend display grammar accepts only unique IDs, verified exact canonical
feature/part/body count statements, up to three fully active supported feature
records, up to two parts and one body, and matching canonical overview paragraphs.
Any missing/unknown/ambiguous count, unsupported/mismatched wording, suppression or
extra qualification falls back to prose. It performs no engineering computation,
ownership join or new request. It never replaces unknown topology with zero.
Known topology uses “returned” labels. Additional paragraphs remain visible, and the
exact complete original answer is available inside expanded Evidence.

## 9. Evidence changes

A full-width quiet optical action shows Evidence, count and chevron. Expansion
mounts all original statements, grouped under their existing status, with one status
marker per group. Unknown/unverified/assumption remain distinct. Capture time and
send-time selection caveat remain inside. Compact overviews also expose Full answer.
Conditional mounting preserves the existing copy behavior.

## 10. Uncertainty changes

A fine muted amber rule, compact heading and readable text preserve the caveats.
Only exact uncertainty strings already present in earlier exchanges may collapse
under an **unchanged limits** disclosure. New limits stay visible; expanding retains
the original text. Context/auth changes still clear the conversation.

## 11. Secondary UI cleanup

Privacy is in Workspace menu → Privacy and the composer toolbar's Data use info
button. Both explain explicit prompt/conversation/bounded-evidence transfer, local
memory and provider retention. Introduction also explains sharing. The visible
About your data/footer metadata is removed. Optional guidance follows the core
answer, uncertainty and evidence, with lower hierarchy; empty guidance stays absent.
No unsupported history/service-readiness menu item is introduced.

## 12. Development UI relocation

Workspace menu → Developer opens sanitized diagnostics in development. Signed-out
DEV embeds have a Developer recovery action. The normal workspace contains no
Development tools footer. Enable/show controls, sanitization and observer behavior
are retained. A small external view store retains an early open request until the
lazy view mounts, avoiding a lost-click race. It grants no backend capability and
is excluded from production alongside diagnostics and UI Lab.

## 13. Dark material range

Canvas #000000, deep #040506, raised #080A0D, hover #0D1014. Cool graphite luminance
is localized to functional materials. No global blue fog, wallpaper or animated grid.
Light/System themes and prior explicit preferences remain supported.

## 14. Accent integration

Arc Blue appears in the selected mode, keyboard focus, active send/selection control
and small brand mark. Read-only and secondary links remain quiet. Selected FACE/EDGE
uses a small geometric icon and human text, without Onshape orange or ownership claims.

## 15. Motion refinement

One 420ms plane-alignment intro runs when the header initializes. Normal mode
changes preserve the header instance. Focus illumination, bounded hover/press,
send/stop morph, evidence chevron/opacity and actual stage transitions carry feedback.
There is no bounce, idle shimmer or staged delay. Reduced motion disables transitions,
the intro and pointer tracking. Finished intro animations may remain in the browser's
animation inventory; the performance check counts only running animations.

## 16. Scroll / sticky behavior

One intentional `.workspace-pane` scroll plane contains mode navigation and content.
It is a named, keyboard-focusable region with an inset focus ring; this also supports
screens without focusable content. The header stays fixed above it, mode navigation
sticks to the top, and the conversation composer stays in flow near the bottom with
a small reading fade. Long answers/evidence do not acquire a second scroller.
Dialogs and a capped multiline input can scroll independently when necessary.

## 17. Responsive changes

Production iframe checks capture 320/380/480px. The existing lab gate also covers
360/400/600px and wide layouts. Body text wraps at its normal scale; narrow facts
form a two-column layout, optional shortcut hides, context actions remain usable,
and no horizontal overflow is accepted. Comparison views become stacked below 900px.

## 18. Performance result

The synthetic timing sample reports:

| Engine   | Median interval | p95 interval | Running idle animations |
| -------- | --------------: | -----------: | ----------------------: |
| Chromium |        16.70 ms |     16.70 ms |                       0 |
| Firefox  |        16.66 ms |     17.56 ms |                       0 |
| Webkit   |        17.00 ms |     18.00 ms |                       0 |

Production JS is 418.40 kB / 130.58 kB gzip; CSS is 51.12 kB / 10.62 kB gzip. No
runtime renderer/package was added. The material has no idle loop; illumination
has at most one queued frame per pointed surface, geometry read only on entry,
and cleanup on leave/unmount/visibility loss. Reduced effects/save-data avoid tracking.
The form-width observer schedules only on width changes and cleans up queued work.

The synthetic sample measures 59 post-warmup frame opportunities after interaction,
not CAD GPU throughput, a sustained pointer benchmark or real Onshape trackpad feel.
Real CAD responsiveness still requires the human review described below.

## 19. Accessibility result

All 411 browser cases passed across Chromium, Firefox and WebKit. Accessibility
checks returned no axe violations in the tested states. Coverage includes axe
WCAG 2 A/AA and 2.1 AA, light/dark, narrow layouts, keyboard focus and return,
evidence expansion/copy, reduced motion/transparency, increased contrast and production
exclusion. The new scroll region has a keyboard target even without child controls.
Automated checks are not a screen-reader usability certification.

## 20. Frontend test count

**534 passed, 24 files.** Includes exact summary/fallback/unknown/hostile-name/copy
behavior and early Developer-request retention/cleanup. `make format`, `make lint`,
`make typecheck`, `make test` and `make build` passed. Backend: **764 passed, 3 skipped**;
only isolated PostgreSQL tests require `FORGE_TEST_DATABASE_URL`. No backend or
infrastructure source changed. Frozen npm/uv installs were used. npm audit reports
0 vulnerabilities; pip-audit reports no known vulnerabilities.

## 21. Playwright count

**411 passed**: 137 per engine, Chromium/Firefox/WebKit; final full run **3.5 minutes**
with two workers and no retries. An initial full run
exposed the nonfocusable workspace scroller and an early lazy Developer-open race;
both were fixed instead of suppressing assertions. A long WebKit run also had
timeouts. The final complete run uses two workers. Existing authorization,
CSRF, origin/source, selection ownership, stale-context, cancellation, read-only
write boundary and privacy assertions remain included. No real AI calls.

## 22. Exact real Onshape review steps

1. Keep existing PostgreSQL, API and private configuration. If the HTTPS frontend
   is stopped, run `make dev-web-https` in `/Users/jishnuhiremath/Developer/FORGE`.
   No install, migration, backend restart, OAuth scope or registration change.
2. Open the existing current-workspace Part Studio and Forge right panel. Close/
   reopen the panel or reload its iframe to use current Vite source. Keep the
   existing Action URL/launch parameters. A standalone page cannot supply CAD context.
3. Workspace menu (ellipsis) → Appearance & settings → Dark. Keep Reduce transparency
   off first. Return to Design. Confirm compact identity, one Read-only state,
   named CAD inspector and no Development tools/About your data footer.
4. Clear any existing conversation. Review welcome, three examples and connected
   composer. Click an example: it should populate/focus without sending. Type a
   multiline prompt: input should grow only up to its cap. Resize the panel through
   available widths around 320/380/480px; check wrapping and keyboard focus.
5. Select one FACE, then one EDGE, then clear selection in Onshape. Check the
   integrated human selection text; selection alone must never call AI. Use the
   context control → Refresh CAD to review the real captured inspector evidence.
6. Explicitly send **What is in this Part Studio?** with Cmd/Ctrl+Enter or Send.
   This human action uses the configured hosted AI service and existing quota.
   Observe the real progress state, fixed send/stop footprint and grounded answer.
   A compatible small overview condenses; any other model safely keeps prose.
7. Expand Evidence by keyboard and pointer. Review status groups, unknown counts,
   original statements and Full answer where condensed. Scroll long content: header
   stays available, composer remains usable and only the workspace scrolls.
8. After cooldown ask **What do you know about the face I selected?** with a FACE,
   then the equivalent EDGE question. Ownership and unavailable geometry must stay
   unknown. Check repeated caveats remain accessible and new limits stay visible.
9. Ask **Make this model 20 mm wider.** It must retain the deterministic read-only
   explanation and unknown controlling dimension. Confirm no CAD/history change.
10. Test Data use info and menu Privacy, Escape and focus return. Open Appearance &
    settings → Reduce transparency; compare legibility and hierarchy. Test OS reduced
    motion, Light and System. Test normal keyboard scrolling and trackpad feel.
11. In a separate trusted local DEV tab open `https://localhost:5173/#/lab`.
    Choose Material comparison → Wide standalone for A/B/C, then Logo candidates
    for all six sizes and contexts. Phase 6.5 workspace offers manual failure,
    selection, progress and reduced-effect states without service calls.
12. Open Workspace menu → Developer only when intentionally checking diagnostics.
    Confirm sanitized controls remain available, then close the dialog. Capture
    first-open/FACE/EDGE/answer/evidence/narrow/wide/reduced-effect real Onshape images
    for the human verdict. Do not commit/push unless explicitly authorized afterward.

## 23. Git status

Baseline HEAD remains `44aa86b5d7c1b19b3aa5beb16095e09a919b96b8`; changes stay
unstaged and uncommitted on the existing branch. First-pass edits were preserved.
No push or Phase 7 work. No API source, dependencies, lockfiles, environment values,
OAuth scopes or migrations changed. Synthetic screenshots/logs/traces live under
ignored `.cache/phase6.5-refinement/` (existing state/performance outputs also under
`.cache/phase6.5/`). Temporary QA services/tabs are stopped/closed after review;
existing user services and database volumes are preserved.

## Verification ledger

- `make format`: passed.
- `make lint`: ESLint/Prettier/Ruff passed.
- `make typecheck`: strict TypeScript and mypy passed.
- `make test`: frontend 534 passed; backend 764 passed, 3 isolated-PostgreSQL skips.
- `make build`: passed; JS 418.40 kB / 130.58 kB gzip, CSS 51.12 kB / 10.62 kB gzip.
- `make test-e2e` exposed issues described above; the final full rerun via
  `npm run test:e2e -- --workers=2`: 411 passed, 3.5 minutes, no retries.
- `make audit`: npm 0 vulnerabilities, pip-audit no known vulnerabilities.
- `git diff --check` and changed/new-file credential-pattern scan: passed.
- 52 changed/new files, all unstaged; no API/lockfile/dependency/environment/migration changes.
- QA ports 4173/4174/4175 stopped; temporary browser tab closed, viewport restored.
  Existing 5173/8000 services were preserved. No database service or volume was changed.

Final logs are ignored in `.cache/phase6.5-refinement/`. The initial failed browser
log is retained as `playwright-initial.log`; `playwright.log` contains the clean
complete rerun. The first-pass review is historical and does not represent human approval.

## Screenshot index

All images were opened for visual inspection. The normal panel captures use the
production bundle in an isolated synthetic Onshape-parent iframe.

- `material-abc.png`: previous/refined/opaque, same typed content.
- `logo-candidates.png`: three concepts, six scales, dark/light and panel contexts.
- `first-open-{320,380,480}.png`: compact first-use composition.
- `face-{320,380,480}.png`, `edge-{320,380,480}.png`: integrated selection context.
- `answer-{320,380,480}.png`: condensed grounded inventory.
- `expanded-evidence-{320,380,480}.png`: evidence and sticky composer.
- `reduced-transparency.png`, `reduced-motion.png`: DEV equivalent adaptations.

Images and logs are in `../.cache/phase6.5-refinement/` relative to this document.
