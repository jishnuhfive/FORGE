# Phase 6.5 — approved product freeze and final quality gate

The human approved the second-pass design inside real Onshape after two visual
review passes. Approved states include first-open Design, overview, expanded
Evidence, FACE/EDGE, the selection-aware composer, Settings/Appearance and dark
Forge beside real CAD. The approved direction is frozen. Phase 7 has not started.

## Final scope

- Timeless canonical read-only, selection, mass, units, freshness and validation copy.
- No normal product phase numbers or provider/schema/test internals; DEV diagnostics
  and internal documentation remain precise. Quoted CAD names remain untouched data.
- Small Settings-only rhythm/grouping/height/focus/label adjustments; no redesign.
- Approved Current workspace/CAD inspector strip, Oblique Plane geometry, palette,
  navigation/composer/response architecture, type/spacing and 420ms intro retained.
- One canonical production glass material. Filter fallback declaration order fixed
  so minification preserves opaque/forced-color behavior; normal effects unchanged.
- Discoverable Data use/Privacy, provider-retention caveat, DEV-only diagnostics,
  conditional evidence mounting and no idle decoration retained.

The intentional backend changes are canonical **wording only**, plus copy tests.
Provider behavior, strict schemas, orchestration, tool boundaries, authorization,
CSRF, origin/parent checks, fact IDs/statuses, FACE/EDGE ownership unknowns, stale
context handling, conversation lifecycle and deterministic no-write refusal remain
unchanged. No package additions, lockfile changes, migrations, CAD writes, new scopes,
FeatureScript, Modify execution, deterministic validator or Reality Lock work.

## Canonical copy

- Header: **Read-only**.
- Refusal: “Forge is currently read-only and can't modify CAD yet.” When useful:
  “I can inspect the current model and explain or propose how a change could be made.”
- Selection: “One face is selected.” / “One edge is selected.” Owning part/body/
  feature, dimensions and selection-specific geometry remain unknown; FACE includes
  surface type/area/normal, EDGE includes curve type/adjacent faces.
- Limits: default configuration/end of feature list; separate reads, currentness
  and snapshot consistency remain unverified. Physical units haven't been
  independently verified; exact mass/volume aren't supplied. Material/density may
  explain unavailable mass, never an invented mass. Validation remains unverified.

## Approved design system

[FORGE_DESIGN_SYSTEM.md](FORGE_DESIGN_SYSTEM.md) is canonical for future phases:
Quiet Engineering Precision, Obsidian, Arc Blue, Oblique Plane, functional Liquid
Glass, quiet solid content, 4px-derived spacing, 6/8/12px radii, system typography,
answer-first hierarchy, progressive disclosure, restrained motion, no idle
animation, accessible fallbacks and visually dominant CAD. Anti-Vibecode rules
remain in force. Future UI requires authorization and must conform to this system.

## Verification ledger

Final gate passed from the frozen code state; no real Groq/OpenAI requests.

| Check                | Final result                                                                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Formatting           | Prettier and Ruff passed                                                                                                                      |
| `make check`         | Passed: frontend/backend lint, strict TypeScript/mypy, complete tests, production build, Compose validation                                   |
| Frontend             | **534 passed**, 24 files                                                                                                                      |
| Backend              | **773 passed**, including **3 real PostgreSQL tests**; zero skips                                                                             |
| PostgreSQL isolation | UUID test schemas cleaned up; application revision and data preserved                                                                         |
| Migration drift      | No new upgrade operations detected                                                                                                            |
| Playwright           | **432 passed**, 144 per Chromium/Firefox/WebKit, **4.2 minutes**, no retries                                                                  |
| Accessibility        | Tested axe checks passed; keyboard, focus, disclosures, errors/progress, opaque/reduced-motion adaptations and Chromium forced colors checked |
| npm / Python audits  | 0 vulnerabilities / no known vulnerabilities                                                                                                  |
| Private-data scan    | 66 intended files; zero known-private-value/credential-pattern matches; no forbidden artifact paths or literal 24-hex CAD IDs                 |
| Source freeze        | Source/test/asset fingerprints unchanged during the final gate                                                                                |
| Whitespace           | `git diff --check` passed                                                                                                                     |
| Bundle               | JS 418.45 kB / 130.58 kB gzip; CSS 52.35 kB / 10.84 kB gzip                                                                                   |

The full Phase 0–6 regression gate preserves security, read-only behavior, both
provider adapters, stale-context and conversation lifecycles, selection unknowns,
privacy and deterministic refusal. Initial checks caught retired copy expectations
and a theme audit sampling intermediate transition colors; expectations now match
final copy and audits wait for actual finite transitions. No assertions were disabled.
The production fallback repair also retains filter overrides through minification
and maps forced-color tokens to system colors. Normal approved effects are unchanged.

Visual review opened the final first-open, overview, expanded Evidence, FACE/EDGE,
Settings at narrow/wide widths, reduced effects and frozen identity screenshots.
Historical comparison renders existing concepts only; no new logo candidates.
Synthetic QA output and logs remain ignored. QA servers close after browser tests;
existing application services and database volumes are retained. Staged privacy/
scope review is required before the one authorized commit and normal push.

## Visual and accessibility review

Final synthetic screenshots cover first-open, overview, expanded Evidence, FACE,
EDGE, 320/480px, reduced transparency/motion and Settings at
320/360/380/400/480/640px. The approved identity is checked at
16/20/24/32/64/128px in monochrome/accent contexts. No new candidates are created.
Production forced-color fallback, keyboard/focus, names/headings, disclosures,
progress/error announcements, contrast, hit targets and single scroll/sticky
behavior are checked. Screenshots/logs are ignored in `.cache/phase6.5-final/`;
performance samples remain ignored in `.cache/phase6.5/`. Automated results do not
replace the human's real Onshape approval or constitute engineering certification.

## Database and private-data handling

Use only the existing local PostgreSQL URL in process memory. The opt-in tests
create/drop their own random schemas; preserve application data and volumes.
Migration drift check is read-only. Do not print secrets/URLs or commit private
configuration, real CAD/provider captures, manual screenshots, HARs, IDs, certificates,
keys, cookies or QA output. Review the intended staged diff and scan before commit.

## Publication and stopping point

The user authorized exactly one commit after the complete passing gate:

`feat: polish Forge product UI and design system`

Push `main` normally to existing `origin`, never force. Verify local HEAD,
`origin/main` and remote main match and tracked work is clean; `.env` stays ignored.
The resulting hashes and publication outcome are reported in the closing delivery
rather than embedding a commit's own hash inside itself. Stop after verification.
Phase 7 requires a new explicit prompt.

## Known remaining UI limits

- Read-only CAD; no write execution or engineering certification.
- Selected geometry ownership/measurements remain unknown.
- Units, exact mass/volume and snapshot consistency retain their existing limits.
- SVG backdrop refraction is progressive; unsupported engines use the base material.
- Automated accessibility/performance samples do not certify every device, browser,
  assistive technology or real-CAD workload.

Forced-color mode maps semantic colors to system Canvas/CanvasText/LinkText and
ButtonFace/ButtonText, so text and control contrast follow the user’s system palette.
This adaptation does not change the approved normal appearance.

Stable-theme accessibility audits wait for finite theme/intro transitions to finish
before sampling colors. No contrast rule is suppressed, no fixed sleep is used,
and the approved motion is preserved.
