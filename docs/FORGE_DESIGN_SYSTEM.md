# Forge design system

Phase 6.5 · canonical approved presentation specification, frozen after two human
visual-review passes in real Onshape. The second pass is human-approved. Phase 7
has not started and requires new authorization.

## Approved Forge design language — frozen

- Quiet Engineering Precision; CAD remains visually dominant.
- Obsidian dark foundation and Arc Blue primary accent.
- Oblique Plane identity; no further logo exploration is part of this freeze.
- Liquid Glass on functional surfaces, with a solid/quiet content reading layer.
- 4px-derived spacing, restrained 6/8/12px radii and system typography.
- Answer-first hierarchy and progressive disclosure.
- Restrained physical motion, no bounce or idle decorative animation.
- Accessibility-first opaque/contrast/forced-color fallbacks.

Future authorized Phase 7 UI must conform to these rules and reuse the canonical
primitives instead of inventing new visual patterns. Approval is visual product
acceptance, not engineering validation or security certification.

## Research and decisions

Reviewed current primary guidance and visual references before changing UI code:

| Reference                                                                                                                     | Application to Forge                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [Apple HIG: Materials](https://developer.apple.com/design/human-interface-guidelines/materials)                               | A distinct functional layer; reserve glass for controls, keep content quiet.            |
| [Liquid Glass overview](https://developer.apple.com/documentation/technologyoverviews/liquid-glass)                           | Context, hierarchy and consistency matter more than ornament.                           |
| [Meet Liquid Glass, WWDC25](https://developer.apple.com/videos/play/wwdc2025/219/)                                            | Lensing, edge illumination and physical feedback inform the internal material.          |
| [Apple HIG: Motion](https://developer.apple.com/design/human-interface-guidelines/motion)                                     | Purposeful state feedback; restrained pointer motion; optional animation.               |
| [Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)                       | Legibility, contrast and equivalent feedback with effects disabled.                     |
| [Apple Design Resources](https://developer.apple.com/design/resources/)                                                       | Reviewed public previews for proportions. No Apple assets, templates or fonts imported. |
| [Liquid Glass Design gallery](https://liquidglassdesign.com/) and [guide](https://liquidglassdesign.com/what-is-liquid-glass) | Optical inspiration, not an authority for Apple behavior or licensing.                  |
| [Dark button glass](https://liquidglassdesign.com/gallery/dark-button-glass)                                                  | Local edge light and a dark resting surface. Reject its bright decorative streaks.      |
| [Animation playground](https://liquidglassdesign.com/gallery/liquid-glass-animation-playground)                               | Continuity between control states. Reject playful palette and unnecessary travel.       |

Apple documentation sometimes serves a JavaScript shell; the official indexed HIG
content and WWDC transcript were also reviewed. Third-party gallery artwork/code
is not copied. No glass library was imported or licensed; dependency, bundle and
security cost remain zero additional packages. Raw WebGL was considered and rejected:
reconstructing an iframe backdrop would add complexity, power use and fidelity
claims that a narrow, mostly black engineering panel does not justify.

## Visual audit

Baseline local browser inspection found a charcoal/orange palette, an oversized
concept drawing/headline, multiple metadata rows, small 8–10px labels, repeated
read-only badges, bordered response cards, and a large textarea. A wide-screen
sidebar advertised future work. The normal workspace must prioritize current work;
legacy synthetic workflows remain explicitly labeled in the development lab.

## 1. Brand philosophy

Quiet engineering precision. CAD is the hero; Forge is a compact intelligence layer.
Obsidian content, titanium controls, cool light, one arc-blue accent. No Apple or
Onshape visual identity is copied.

## 2. Product principles

Answer first, essential status next, uncertainty visible, evidence on demand.
Hierarchy survives removal of color, glass, borders and animation. Use typography,
position and spacing before surfaces. Show capability honestly; no fake readiness.

## 3. Material rules

One core `.glass` material and `GlassSurface` primitive in the design-system package.
Tier A uses an opaque-enough tint, bounded backdrop blur, saturation, directional
inner edges and ambient separation. Tier B adds an SVG displacement map to a masked
edge backdrop where supported, plus local pointer/focus illumination. The center and
all meaningful DOM text stay undistorted. The map is fixed, shared and generated
internally; never sample/capture the cross-origin parent. Unsupported SVG backdrop
filters retain Tier A. Decorative lensing is a web approximation, not Apple's native
renderer. No Tier C shader or chromatic rainbow is shipped.

## 4. Content and functional layers

Content is solid/quiet. Navigation, composer and transient menus use glass. Content
cards do not. Avoid nested glass; selected segments use luminance/accent rather than
another blur. A dialog's content uses a solid reading surface.

## 5. Color

Dark default: canvas #000000, surface #040506, panel #080A0D, hover #0D1014.
Text #F5F7FA, secondary #A7ADB7, tertiary #8C95A3 (raised above the proposed
#737B87 for small-text contrast). Divider white at 7.5%; functional glass edges cool white at 22%.
Arc blue #78A8FF is reserved for actions, selection and focus. Green means verified,
amber means uncertainty/unverified, red means failure. Symbols and words accompany
status. Light and system appearances remain available; no font download is required.

## 6. Typography

System-first: -apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif.
Exact roles: title 20/28px at 600; section 15/24px at 600; body 13/20px at 400;
control 12/16px at 500; metadata/caption 11/16px at 400/500; diagnostic mono 12/20px.
No decorative tracking except the compact FORGE wordmark. No tiny diagnostic-looking
normal UI or all-caps section furniture. IDs use monospace only in diagnostics.

## 7. Spacing

Canonical 4, 8, 12, 16, 24, 32, 48px. Use `--space-*`. Historical `--space-5`
is a compatibility alias to 24px. Optical exceptions: 1px hairlines, 2px focus/stroke,
3px focus offset, icon sizes and typography/control metrics; percentages for layout
and optical gradient positions. Content width max 640px; panel gutters 16px.

## 8. Radius

Small 6px; controls 8px; material 12px. Capsules only for compact status. Inner
controls have smaller curvature than their containing material.

## 9. Depth

Two ambient elevations, one inset optical edge. No shadow on ordinary content.
No neon/glow. Blur is limited to navigation, composer and an open menu.

## 10. Iconography

Lucide only, normally 16px and 1.75 stroke; 12px metadata / 20px emphasis exceptions.
The original Forge mark is the sole custom identity shape. Icons never replace
necessary names. Decorative SVGs are hidden from assistive technology.

## 11. Motion

120ms press, 180ms hover/focus, 240ms state transition, 280ms disclosure;
cubic-bezier(0.22,1,0.36,1). Press compression .985. Shared navigation indicator
moves between positions; send/stop retains the same footprint. No synthetic delays.
No permanent shimmer, spinner, breathing, sweep or idle animation. Disclosures mount
only when open (preserving the Phase 6 rich-copy fix).

## 12. Accessibility

Visible 2px focus ring; 32px minimum compact targets, 36px primary controls. Real DOM
text, Radix keyboard navigation/focus management and named native disclosures.
Reduced motion removes animation/tracking. Reduced transparency setting and the OS
media query produce opaque materials; increased contrast strengthens text/edges and
removes optics. Forced colors uses system colors. Never rely on color alone.
Glass text sits on controlled backing; only its narrow perimeter can refract backdrop.

## 13. Composer

A bottom-sticky material in normal flow with no nested scroll region. Compact
multiline input, selection label, fixed-size send/stop control, reserved progress
line. Enter adds a line; Cmd/Ctrl+Enter sends; IME composition never submits.
Idle, typed, disabled, submitting, cancellation and cooldown preserve footprint.
Suggestions populate/focus; sending remains explicit. Privacy disclosure is available
at the point of send. No changes to API arguments, cooldown or lifecycle ownership.

## 14. Response

A quiet prompt followed by Forge's answer, visible uncertainty and optional guidance.
No bordered chat bubbles, no repeated capability badge. The original full answer remains available inside expanded Evidence when compact
formatting is used. The display formatter accepts only exact canonical overview
wording matched to verified feature/part/body facts; it falls back to original
prose on ambiguity, mismatch, suppression, partial lists or unknown counts. It
never infers geometry, ownership, units or validity. Additional paragraphs and all
uncertainties remain visible.

## 15. Navigation

Compact Design/Modify/Learn segmented control. Design is the current read-only
workspace. Modify is explicitly planned; Learn is authored reading, not CAD checking.
Both remain usable and honest. Header: mark, context action, one Read-only state,
one workspace menu. No marketing rail or competing giant workspace.

## 16. Selection

One canonical composer treatment: Selection unknown / No selection / 1 face selected /
1 edge selected. Never derive ownership. Inspector retains additional caveats.

## 17. Evidence

Collapsed by default, after the answer and uncertainty. Group equal statuses with
one symbol/text per group while preserving the original statement rows. Unknown,
unverified and assumption stay distinct; a verified fact never implies validation.
Capture time and send-time selection caveat are secondary, inside disclosure.

## 18. Errors

Compact inline alert with safe human explanation and explicit retry. Keep normalized
API error mapping; never show raw transport/provider jargon. No giant red box.

## 19. Empty states

Small original mark, “Ask about this Part Studio”, one line explaining current scope,
three concise prompt examples. No giant illustration. Standalone retains local drafts
and clearly explains that live analysis requires Onshape.

## 20. Loading and progress

The submitted question remains visible during analysis. Real server stages only, in the composer's reserved status slot. A static stage
marker and crossfade communicate continuity without a spinner. Idle has zero
animations. Skeletons are static luminance blocks and exist only while loading.

## 21. Logo

“Oblique plane”: three solid polygons imply sketch, extrusion and object through
an oblique upper plane, a vertical extrusion and an open inner plane. Candidate A
was chosen after comparing A/B/C at 16/20/24/32/64/128px in header, welcome and icon
contexts. Its dimensional silhouette survives small sizes better than the two
stepped F candidates. The human subsequently approved Oblique Plane. Clean
SVGs in `apps/web/public/brand`; white/black/currentColor mono, accent and icon
variants. Wordmark remains DOM text. No baked-in blur, sparkle or proprietary font.

## 22. Anti-Vibecode rules

Glass everywhere; nested cards; giant radii; gradient borders; neon; rainbow;
animated blobs; sparkles; emoji chrome; pills everywhere; centered paragraphs;
landing-page headings in a working panel; uppercase microcopy; unreadable metadata;
random dividers; multiple accents; arbitrary shadows; spinners/shimmer everywhere;
wasted sidebar space; fake terminals; API jargon; gratuitous hover motion.

## Performance budgets and adaptation

No new dependencies. Zero idle animation frames/timers for glass. At most one queued
rAF per actively pointed material; bounding rect read on entry only, writes batched.
Cancel on leave/unmount/visibility loss; ignore tracking during reduced motion,
reduced transparency, increased contrast or save-data preference. No layout reads
inside animation frames. Two persistent small filtered surfaces in the workspace;
no full-iframe blur. No permanent `will-change`. Target 60fps/16.7ms on the M4;
automated synthetic measurements and limits are recorded in PHASE_6_5_REFINEMENT_REVIEW.
Real Onshape responsiveness and native trackpad feel require human verification.

## Second visual-review refinement

The first real Onshape review was not approved; the second pass was approved.
Material B is the frozen implementation; UI Lab compares the previous recipe (A), refined recipe (B) and opaque
adaptation (C) with identical geometry. B uses a 70% cool tint, 10px bounded blur,
internal radial/angled luminance, a 2px directed masked edge and a darker base.
A static local titanium luminance bed belongs to Forge. No parent pixels are read.
Small `.glass-action` controls share highlights without nested backdrop filters.
The send action has a restrained optical blue fill instead of a bright blue block.

The input starts at 44px and grows to 144px. A width observer schedules a single
resize fit when the form width changes; it has no idle loop and cleans up queued
work. Examples are quiet 36px text actions with directional hover affordance.
During send their space is retained to avoid moving the composer. Progress uses
one reserved line. Send/stop crossfades within a fixed control. One 420ms mark-plane
alignment runs when the header mounts; normal mode changes do not remount it.
Reduced motion removes the transition and pointer tracking.

The welcome is a small mark beside two lines, followed by examples and the input.
It disappears after the first exchange. The header holds the identity, one optical
Read-only state and a single menu; the context control explicitly names the CAD
inspector. Menu → Privacy and the composer's Data use info open the transfer/retention
disclosure. Introduction also describes explicit sharing. There is no visible
privacy/development footer. Menu → Developer opens a development-only diagnostic
dialog; signed-out development embeds have a Developer entry beside recovery actions.

A compatible overview shows Current model, feature order and typographic counts.
Only known topology is counted; unknown stays unknown. Selected face/edge titles
require matching exact selection evidence. Generic answers have no visible author
heading. Evidence is one full-width optical row with count and chevron; its original
rows and full answer mount on demand. Exact repeated uncertainty text can collapse
under an unchanged-limits disclosure; new limits remain visible. Optional guidance
follows core answer, uncertainty and evidence.

The header stays outside the single `.workspace-pane` scroll region. Mode navigation
sticks to its top. The composer stays in flow and sticks near the bottom during a
conversation, with a small local fade above it. Dialogs and a capped long text input
may scroll independently when necessary; answers never get a second scroll plane.

## Final product copy and freeze controls

Normal product copy never uses internal phase numbers, transport errors, schema/
adapter jargon or test/evaluation labels. DEV diagnostics may remain precise behind
their existing boundary; actual quoted CAD names remain data and are never rewritten.
Header capability is **Read-only**. Canonical write refusal is “Forge is currently
read-only and can't modify CAD yet.” Where useful it continues “I can inspect the
current model and explain or propose how a change could be made.” Selection states
say “One face is selected.” / “One edge is selected.” Ownership and measurements
remain unknown; no part/body/feature join is inferred.

Global limits preserve default configuration/end-of-feature-list scope, separate
reads, unverified currentness/snapshot consistency, independently unverified units
and unavailable exact mass/volume. Validation remains unverified. Product wording
changes neither evidence statuses nor the deterministic refusal boundary.

The final Settings pass only regularizes spacing, field groups, control heights,
labels, dividers and focus. The approved workspace strip and 420ms opening motion
are retained. No effects are intensified. The one production glass implementation
has prefix-first/unprefixed-last filter overrides so CSS minification retains the
opaque/forced-color fallbacks. Historical A/B/C recipes and alternative logo vectors
remain DEV-only review references, not competing production material/brand systems.

Forced-color mode maps semantic colors to system Canvas/CanvasText/LinkText and
ButtonFace/ButtonText, so text and control contrast follow the user’s system palette.
This adaptation does not change the approved normal appearance.
