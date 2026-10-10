# Phase 3 review — complete

Review date: 2026-10-10. **PASS — implementation and real Onshape embedding verified.**
The human reports real Onshape Part Studio right-panel embedding, an authenticated
iframe display name and `valid-context` with no launch-diagnostic reasons. The human
subsequently supplied the corrected authoritative FACE capture, confirming that the
previous EDGE-valued face sample was mislabeled. Its single ENTITY/FACE structure,
string selectionId, undefined occurrencePath and ignored extra field match the existing
parser and synthetic fixture. This resolves the final external-evidence blocker.
No parser, architecture, Action URL or security change was needed for this update.
Phase 3 is complete. Phase 4 has not begun and requires separate authorization.

## Implementation

- One existing React/Vite SPA serves standalone `/` and embedded `/extension`.
  Context parsing validates bounded IDs, revision kind and the fixed Onshape origin;
  ancillary clientId/sessionCompanyId/theme values are bounded and discarded.
- The exact browser origin and parent window are checked before data inspection.
  A workspace sends documented applicationInit once, including StrictMode replay.
  Explicit versions remain versions and do not send workspace initialization.
- `selection.ts` accepts a top-level SELECTION/selections envelope with zero or one
  ENTITY item, FACE/EDGE category, bounded opaque string reference, and absent or
  undefined occurrencePath. Unknown fields are discarded without interpretation.
  No raw payload, private capture values or new outgoing selection command exists.
- Valid messages atomically replace selection; an explicit empty array clears it.
  Malformed trusted selection removes old references and displays unavailable.
  Wrong origins/windows and unsupported message names cannot alter state.
- show and browser lifecycle invalidation clear selection. Invalidation suspends
  further selection acceptance until show or a fresh frame; changed document,
  workspace and element launches create new stores with no previous references.
- CAD Context displays validated counts and abbreviated launch IDs, never selection
  references or invented names. Standalone, waiting, unavailable and error states
  remain distinct. The Design composer uses normalized context.
- DEV-only launch/selection diagnostics retain only bounded redacted output, behind
  the same trust boundary. Production excludes both and the synthetic simulator.
  Fixtures contain invented strings only, matching the verified FACE/EDGE/clear
  structures. Multi-selection remains presentation-only in the simulator.
- Auth/session/CSRF/token encryption and server production code are unchanged.
  Embedded session-unavailable fallback preserves top-level and separate-tab login.
  No new scopes, dependencies, database schema, CAD REST/AI calls or CAD writes.

## Source and evidence boundary

The current official [client messaging](https://onshape-public.github.io/docs/app-dev/messages/)
and [right-panel lifecycle](https://onshape-public.github.io/docs/app-dev/messages/element-right-panel/)
were rechecked. They document message names, initialization and panel destruction,
but not an inbound selection payload schema. The outgoing highlight example was
not repurposed as an inbound contract. The sanitized live FACE, EDGE and clear
structures provide the adapter envelope. No raw IDs were requested or supplied;
opaque reference length/control-character checks still run on the actual input.

Full source links, existing registration, exact Action URL, limits and manual steps
are in [ONSHAPE_EXTENSION.md](ONSHAPE_EXTENSION.md). That URL remains unchanged.

## Verification

| Check                                | Final result                                                   |
| ------------------------------------ | -------------------------------------------------------------- |
| Targeted parser/bridge/context tests | 86 passed                                                      |
| Complete frontend tests              | 277 passed                                                     |
| Backend default suite                | 97 passed; 3 opt-in PostgreSQL tests skipped here              |
| Explicit PostgreSQL regressions      | 3 passed in isolated temporary schemas                         |
| Playwright                           | 219 passed: 73 each in Chromium, Firefox and WebKit            |
| Format/lint                          | Prettier, ESLint and Ruff passed                               |
| Type checking                        | TypeScript and mypy passed (28 Python source files)            |
| Production build                     | Passed; diagnostics, simulator and synthetic references absent |
| Migration check                      | No new upgrade operations detected                             |
| Compose                              | Configuration validation passed                                |
| Dependency audits                    | npm and pip-audit: no known vulnerabilities                    |
| make check                           | Passed                                                         |
| Local services                       | HTTPS `/extension` and API `/health` returned 200              |

The first complete browser run passed 210 tests and exposed a double `?` in the nine
new synthetic launch tests. The fixture was corrected without relaxing validation;
all nine targeted tests and the final full suite pass. Lint rejected a control-character
regex; equivalent explicit character checks now satisfy the existing lint policy.
No failed check remains. Existing Phase 0/1/2 coverage was preserved and passed.
Dependencies and lockfiles are unchanged; Python checks use the frozen environment.

Visual review inspected 320/380/480 px live selection views in light/dark themes,
standalone/wide and error states. Browser checks cover 320/380/480/1280 px, overflow
and accessibility. No clipping or horizontal overflow was observed. All screenshots
contain synthetic data and remain ignored. Playwright stopped its 4173/4174 servers;
the user's existing HTTPS/API services were preserved.

Git safety inspection covered 47 changed/untracked source files: zero OAuth secret,
token or private-key contents, and no environment, certificate
or database files in the change set. `.env`, `.certs` and diagnostic/test artifacts
are ignored. The pre-staging index was empty; final staged content is checked again before commit. Selection/launch fixture values are invented;
no raw live IDs or diagnostic captures were added. Backend production code, migrations
and dependency lockfiles have no changes. The configured GitHub origin's main was
read-only verified at the Phase 2 hash below. The expanded final scan also compared
local database configuration: the only matches were unchanged, already-committed
public Compose-default examples in the setup docs, not newly exposed credentials.

## Final FACE verification and Git completion

The corrected FACE evidence matches every structural field used by `parseSelection`.
The final targeted parser/bridge/context run passed all **86 tests**; the three-engine
selection/browser run passed all **9 tests**. Final formatting and lint also passed. The full gate above already passed against
the unchanged implementation; this update only corrects documentation and fixture
provenance comments. No unrelated expensive gate is repeated.

Phase 0/1/2 history remains preserved through Phase 2 commit
`676414f09aeb0f7256cc7956f6065f1b7a7b8c25`. The user authorized the single Phase 3 commit
`feat: integrate Forge with Onshape client context` and a normal push of main to the
existing origin after final tests and staged-file safety checks. The resulting hash
and push result are reported in the completion handoff; no force push is permitted.

Remaining limits: browser-wide cookie compatibility, versions, assembly paths and
multiple selection are not established by this single Part Studio session. The live
captures establish message structure; automated fixtures verify UI, replacement and
lifecycle behavior. They are not an independent end-to-end Onshape test by the agent.
Production hosting and enterprise stack support remain future work. Phase 4 has not
begun; no CAD reads/writes or OpenAI calls were added.
