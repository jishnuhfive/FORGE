# Phase 6.5 — first-pass review history

Current decision: **Phase 6.5 visually approved after two human-review passes**.
The design system is frozen. See [PHASE_6_5_FINAL_REVIEW.md](PHASE_6_5_FINAL_REVIEW.md)
for the current final gate and authorized publication. Phase 7 has not started.

Historical first-pass implementation record; remaining sections describe that
pass and its then-pending decision, not the current approval state. The subsequent real Onshape human
review did **not approve** this design. Current changes, results and review steps
are in [PHASE_6_5_REFINEMENT_REVIEW.md](PHASE_6_5_REFINEMENT_REVIEW.md).

## 1. Status

Implementation, automated verification and local screenshot review are complete.
Human visual review in real Onshape is pending.
No commit or push is authorized. Phase 7 is not started. Baseline HEAD was exactly
`44aa86b5d7c1b19b3aa5beb16095e09a919b96b8` and the working tree was clean.

## 2. Research

See [FORGE_DESIGN_SYSTEM.md](FORGE_DESIGN_SYSTEM.md) for the dated source table:
Apple HIG Materials/Motion/Accessibility, Liquid Glass overview, WWDC25 transcript,
public Design Resources and LiquidGlassDesign.com guide/gallery. No third-party
artwork/code, proprietary Apple assets or font files were copied.

## 3. Visual audit

Local browser baseline review found oversized concept artwork/headline, repeated
capability labels, dense technical framing, tiny metadata, bordered responses and
marketing rails. They competed with Onshape instead of supporting it.

## 4. Philosophy

Quiet engineering precision. CAD is the hero; content reads on obsidian, controls
occupy a small functional material layer. Hierarchy uses type, space and alignment.

## 5. Liquid Glass

One internal `GlassSurface`/`.glass` implementation: tint, blur, saturation, optical
edge, inset light, ambient separation, pointer/focus response and pressed feedback.
Existing Button, Tabs and Dropdown primitives were upgraded rather than duplicated.
No renderer or material dependency was added.

## 6. Refraction

One shared SVG map encodes opposing x/y edge displacement using `feImage` and
`feDisplacementMap`, bounded at scale 6. A masked perimeter applies the backdrop
filter where supported; real DOM text in the center is never displaced. A Chromium
render comparison checks that removing refraction changes screenshot pixels.
Tier A remains complete when SVG backdrop filters are unsupported. No WebGL,
chromatic rainbow, cross-origin parent capture, screenshot reconstruction or canvas
text is used. This is a controlled web approximation, not Apple's native material.

## 7. Performance strategy

No idle animation loop, shader, permanent `will-change` or large-viewport blur.
One pending frame maximum per actively pointed material; geometry read on entry,
style writes in the frame; cancel on leave/hide/unmount. Reduced motion/transparency,
increased contrast and save-data skip tracking. Persistent glass is limited to
navigation/composer; menus are transient. Target 60fps/16.7ms on the M4. Budget:
production JS under 135 KiB gzip, CSS under 12 KiB gzip, zero idle animations.

## 8–12. Color, type, spacing, curvature and motion

Obsidian #000000 / #050607 / #0A0C0F, hover #111318. Primary #F5F7FA, secondary
#A7ADB7, tertiary #8C95A3. Arc blue #78A8FF is the only brand accent. Semantic green,
amber and red are accompanied by text/symbols. Retained light/system choices.

System-first font stack, no font requests. Title 20/28, section 15/24, body 13/20,
control 12/16, caption 11/16px. 4/8/12/16/24/32/48px spacing; 6/8/12px radii.
120/180/240/280ms purposeful transitions with cubic-bezier(0.22,1,0.36,1), .985 press
compression, no perpetual movement. Optical exceptions are documented in the system.

## 13. Accessibility adaptation

OS reduced motion/transparency, increased contrast, forced colors and a persisted
strict reduced-transparency preference. Lab simulation controls cover all three.
Focus remains visible, status text survives without color, disclosures expose
expanded state, progress uses a polite live region only while active. Meaningful
text stays DOM text; decorative filter SVG is aria-hidden and noninteractive.

## 14–15. Identity and files

Original **Aligned planes** F: a vertical plane plus two sheared extrusion planes.
The small silhouette suggests sketch → extrusion without pictograms or clichés.
DOM wordmark text uses the system font. Assets:

- `apps/web/public/brand/forge-mark.svg` — arc blue
- `apps/web/public/brand/forge-mark-mono.svg` — currentColor/black; inline or mask for white
- `apps/web/public/brand/forge-icon.svg` — compact dark badge/favicon
- `apps/web/public/forge-icon.svg` — compatible existing icon path
- `ForgeMark` in `packages/design-system/src/glass.tsx` — native DOM SVG, theme-aware

## 16–24. Product presentation

- **Shell:** small original mark, one Read-only state, inspector/context action,
  settings/menu. No marketing rail or giant product title.
- **Navigation:** compact glass segmented control with shared moving selected shape;
  existing Radix keyboard semantics. Modify is planned; Learn is authored reading.
- **Composer:** compact bottom-sticky functional glass in flow; multiline entry,
  keyboard send/IME protection retained, one send/stop footprint and reserved status.
- **Response:** prompt followed by the grounded answer, visible uncertainty, optional
  guidance. No response card border or repeated read-only badge. Request/lifecycle
  logic, normalized API schemas, escaping and grounding are unchanged.
- **Evidence:** collapsed by default, grouped statuses with one heading per group,
  all original statements retained, capture time inside disclosure. Expanded rows
  mount only on demand, preserving the rich-copy fix.
- **Progress:** actual server stage transitions in the composer's fixed status slot;
  the submitted question stays visible during analysis. No spinner, staged delay
  or synthetic execution.
- **Selection:** one canonical composer label for unknown/none/FACE/EDGE; no inferred
  ownership, dimensions, geometry or validation.
- **Errors/empty:** compact alert and explicit retry; small mark and three concise
  first-use prompts. Onboarding now describes current read-only capability instead
  of stale Phase 2/future-build claims. Privacy copy reflects actual explicit sends.
- **Development UI:** closed Development tools disclosure; lazy DEV modules and
  lab/synthetic states remain production-excluded.

## 25. Responsive behavior

Synthetic review covers actual 320, 360, 400, 480 and 600px panel boxes and a wider
standalone view, in addition to existing 320/380/480 iframe regressions. No nested
application scroller; composer remains in normal flow with a sticky reading boundary.
Header names truncate while actions remain usable. Body text wraps, never shrinks
below the role scale. Native dialogs are independently scrollable when necessary.

## 26. Performance results

| Engine   | Median rAF interval | p95 interval | Idle animations |
| -------- | ------------------- | ------------ | --------------- |
| Chromium | 16.70 ms            | 16.70 ms     | 0               |
| Firefox  | 16.66 ms            | 17.54 ms     | 0               |
| Webkit   | 17.00 ms            | 21.00 ms     | 0               |

59 post-warmup intervals per engine. These measure synthetic localhost frame
opportunities after interaction, not real Onshape GPU/rendering throughput.
Pointer sampling/cancellation and rendered Chromium refraction checks pass.
Production bundle: JS 417.16 kB / 129.52 kB gzip; CSS 41.54 kB / 8.96 kB gzip.
No dependencies added; both declared gzip budgets are met.
The results are retained in ignored `.cache/phase6.5/performance-*.json`.

## 27. Accessibility results

The browser gate includes axe WCAG 2 A/AA and 2.1 AA checks, both themes, keyboard
navigation/focus restore, evidence expansion/collapse, opaque material, increased
contrast simulation and reduced motion. Bright backdrop stress preview is available
in the material showcase. Automated accessibility checks are not a screen-reader
usability certification. Human keyboard/trackpad review remains required.

## 28–30. Automated regression gate

- Frontend: **520 passed**, 22 test files.
- Playwright: **393 passed**, Chromium/Firefox/WebKit; final full run 2.1 minutes.
- Backend: **764 passed, 3 skipped** (isolated PostgreSQL URL not configured).
- Format, ESLint/Prettier/Ruff, TypeScript/mypy and production build: passed.
- npm audit: **0 vulnerabilities**; pip-audit: **no known vulnerabilities**.
- Whitespace and changed/new-file credential-pattern checks: passed.

The complete final browser suite was rerun after the pending-question presentation
change. Earlier copy-selector expectations were updated to the compact header and
an exact document-label match; validation/ownership/lifecycle assertions remain.
Automated tests make no real AI requests. Existing origin/parent validation, session,
CSRF, ownership, read-only API, selection grounding, cancellation, context changes,
conversation privacy, production exclusion and deterministic write boundary tests
remain included. Three isolated real-PostgreSQL tests require FORGE_TEST_DATABASE_URL;
no infrastructure or database code changed in this phase.

## 31. Files changed

41 files; no API source, manifests, lockfiles, environment or migrations.

- `apps/web/index.html`
- `apps/web/public/brand/forge-icon.svg`
- `apps/web/public/brand/forge-mark-mono.svg`
- `apps/web/public/brand/forge-mark.svg`
- `apps/web/public/forge-icon.svg`
- `apps/web/src/App.test.tsx`
- `apps/web/src/ai/Analysis.test.tsx`
- `apps/web/src/ai/Analysis.tsx`
- `apps/web/src/auth/AuthGate.tsx`
- `apps/web/src/components/Material.test.tsx`
- `apps/web/src/components/Onboarding.tsx`
- `apps/web/src/components/PromptComposer.tsx`
- `apps/web/src/components/Shell.tsx`
- `apps/web/src/features/Design.tsx`
- `apps/web/src/features/Modify.tsx`
- `apps/web/src/features/Settings.tsx`
- `apps/web/src/lib/preferences.ts`
- `apps/web/src/lib/types.ts`
- `apps/web/src/main.tsx`
- `apps/web/src/onshape/OnshapeProvider.tsx`
- `apps/web/src/preview/Phase65Preview.tsx`
- `apps/web/src/preview/UiLab.tsx`
- `apps/web/src/styles.css`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `docs/FORGE_DESIGN_SYSTEM.md`
- `docs/PHASE_6_5_REVIEW.md`
- `docs/ROADMAP.md`
- `docs/SECURITY.md`
- `docs/UI.md`
- `packages/design-system/src/components.css`
- `packages/design-system/src/components.tsx`
- `packages/design-system/src/glass.css`
- `packages/design-system/src/glass.tsx`
- `packages/design-system/src/index.ts`
- `packages/design-system/src/styles.css`
- `packages/design-system/src/tokens.css`
- `tests/e2e/ai.spec.ts`
- `tests/e2e/design.spec.ts`
- `tests/e2e/extension.spec.ts`
- `tests/e2e/foundation.spec.ts`

## 32. Git status

Changes remain unstaged and uncommitted on the original branch/HEAD. No push.
Screenshots, logs, performance samples, traces and temporary cache files are ignored.
No credentials/private CAD were added. Final whitespace/secret-pattern inspection
and dependency audits are recorded in the gate results below.

## 33. Exact real Onshape visual review

1. Keep the existing PostgreSQL and API services and their private settings running.
   If the HTTPS frontend is stopped, run `make dev-web-https` from
   `/Users/jishnuhiremath/Developer/FORGE`. No backend restart, install, migration,
   OAuth permission change or extension registration change is needed.
2. Open the existing Onshape document/workspace Part Studio and its Forge right
   panel. Close/reopen the panel or reload its iframe so it uses the current Vite
   source. Do not change the Action URL or any launch parameters. The normal
   standalone URL cannot supply CAD context.
3. Open Settings and choose **Dark** for the intended obsidian review. Existing
   System/Light preferences are intentionally preserved. Return to Design. Keep
   **Reduce transparency** off for material review; then turn it on for comparison.
4. Check the small header/mark, single Read-only state, context action and compact
   navigation. Resize Onshape's panel to approximately 320, 360, 400, 480 and 600px
   where supported. Check alignment, legibility, no horizontal scroll and all actions.
5. Clear any previous conversation. Ask **What is in this Part Studio?** using
   Cmd/Ctrl+Enter. This explicit action calls the configured hosted AI service using
   the existing account/quota; automated tests do not. Observe real compact progress,
   fixed send/stop footprint, answer hierarchy and visible uncertainty. Open/close
   Evidence with keyboard and pointer. Confirm captured facts/unknowns stay intact.
6. Select one FACE, one EDGE, then clear selection in Onshape. Check the canonical
   composer label and unchanged ownership caveats. Selection alone must not call AI.
   Open **Inspect** and **Refresh CAD**; inspect feature/part/mass evidence normally.
7. After cooldown, ask **What do you know about the face I selected?** with a FACE
   selected, then the equivalent EDGE question. Ownership and unavailable geometry
   must remain unknown. Check any unavailable mass/validation is still qualified.
8. Ask **Make this model 20 mm wider.** Forge must retain the deterministic read-only
   explanation and unknown controlling dimension. Inspect Onshape geometry/history:
   nothing should change. Do not authorize any Phase 7 action.
9. Test Stop during a genuine request, explicit retry after an error/capacity event,
   ordinary browser tab switching, then switching to another Part Studio. Same-frame
   context preserves conversation; a real Part Studio change starts fresh.
10. Use Tab/Shift+Tab, arrow keys in navigation, Enter/Space on disclosures and Escape
    in menus/dialogs. Focus must remain obvious. Check mouse/trackpad feedback and
    that Onshape stays responsive while Forge is still and while interacting.
11. For all synthetic failure/progress/empty variants, open
    `https://localhost:5173/#/lab` on the existing trusted local origin. Choose
    **Phase 6.5 workspace** or **Phase 6.5 design system**, Workspace state, Layout,
    Theme and the accessibility simulations. There are no provider calls there.
12. Share screenshots for iteration only after removing private CAD/identifiers.
    Do not share credentials, raw responses or Network captures. No commit/push
    until the visual review is accepted explicitly.

## 34. Known limitations

SVG backdrop filters vary by engine; baseline blur/tint/edge/focus remain available.
No native Apple renderer parity, parent CAD refraction or shader is claimed.
A web page cannot reliably detect every OS low-power mode; save-data suppresses
tracking where exposed and opaque mode remains available. No real Onshape M4 GPU,
trackpad or screen-reader session was exercised by automation. Windows-specific
manual review remains outstanding; the three browser engines were tested locally. PostgreSQL's isolated
integration tests are skipped without their test URL. Human visual approval is
pending, and Phase 6.5 is deliberately not committed or declared complete.

## Final gate results

All required presentation-phase gates passed on the final source. Infrastructure
and database implementation did not change; no Compose/migration gate was required.
The three real-PostgreSQL tests were explicitly skipped, not counted as passed.
No real AI provider requests ran. Dependency manifests/lockfiles are unchanged.

Local visual inspection covered baseline and final screenshots, 320–600px plus wide
layouts, collapsed/expanded evidence, first-use, FACE/EDGE, capacity, empty and real
progress presentation, light/dark/opaque materials and the bright-backdrop stress
sample. The compositor-status overlap found during review was fixed; the submitted
question remains visible during analysis. Physical trackpad feel, Windows manual
review and real Onshape performance/appearance remain human acceptance items.

Temporary QA server 4175 is stopped after inspection; test-owned 4173/4174 servers
are stopped by Playwright. Existing user HTTPS/API/database services are preserved.
No commit, staging or push. HEAD remains the Phase 6 baseline.
