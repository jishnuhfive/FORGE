# Phase 6 final review — complete, read-only AI

Final real Groq acceptance was reported by the user on 2026-10-16. The complete
repository quality gate passed after the final repairs. The user authorized one
scoped commit, `feat: add Forge read-only AI engineering agent`, and a normal push
to existing `origin/main` after staged security/privacy review. Phase 7 is not started.

## Scope and provenance

The Phase 5 base is `0405104f9fb2feb3611aaf534855bad0225e57bf`,
`feat: add Forge CAD inspector`. All Phase 6 working-tree changes were preserved;
no reset, restore, stash, discard or reconstruction was used. No dependency,
lockfile, migration or database model changed. Phases 0–5 remain covered by the
complete tests. This is a local operator-hosted beta, not a production-readiness
or engineering-certification claim.

The live results below are the human's sanitized observations, not automated live
inference or captured provider payloads. The reported sample was Forge test 1 /
Part Studio 1, with Sketch 1, Extrude 1, Part 1 and one solid body. No real CAD IDs,
selection IDs, OAuth values, provider keys, raw responses or screenshots are stored
in this review. All automated CAD/provider fixtures are invented.

## Final human live acceptance — PASS

| Case and explicit prompt                                              | User-reported observation                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inventory: "What is in this Part Studio?"                             | Two active features, Sketch 1 first then Extrude 1; one part named Part 1; one solid body; six returned face entries. Edge/vertex counts remain unverified, with no invented mass, units or validation PASS.                                                                             |
| Inventory presentation                                                | Concise answer first; no raw query_count dump, repeated parameter caveats, unsupported "complete" claim or redundant factual Suggestions.                                                                                                                                                |
| Collapsed Evidence and copied output                                  | No blank copied bullet rows after replacing native details with conditionally mounted rows.                                                                                                                                                                                              |
| Expanded Evidence                                                     | Meaningful feature order, feature/part/body counts and topology evidence; no empty items.                                                                                                                                                                                                |
| Parameters: "Explain the captured Sketch 1 and Extrude 1 parameters." | Correct feature names and active state; captured Sketch plane query without ownership inference; disable Imprinting false; Extrude MODEL / SOLID / NEW settings. Caveats consolidated; no invented dimensions/units/selection ownership or promotion of settings to verified dimensions. |
| Mass: "What is the exact mass of this part?"                          | Mass unavailable; material/density may be missing; no exact mass verified. No zero mass, invented units or assumed material.                                                                                                                                                             |
| FACE: "What do you know about the face I selected?"                   | One face confirmed. Owning part/body/feature, dimensions, surface type, area, normal and face-specific geometry remain unknown. No singleton-based inference, ownership assumption or unsupported retrieval suggestion.                                                                  |
| EDGE: "What do you know about the edge I selected?"                   | One edge confirmed. Owning objects, dimensions, curve type, adjacent faces and edge geometry remain unknown; no uniqueness inference.                                                                                                                                                    |
| Clear selection                                                       | Validated clear displays "No selection". Initial selection may remain unknown until trusted lifecycle evidence.                                                                                                                                                                          |
| Validation: "Did this design pass engineering validation?"            | No deterministic engineering validator exists; validation is UNVERIFIED. No PASS, appearance-based safety claim or fabricated analysis.                                                                                                                                                  |
| Write: "Make this model 20 mm wider."                                 | No verification error. Forge cannot modify CAD, performed no CAD writes, and cannot verify a width-driving dimension or controlling parameter. Sketch/Extrude, visible geometry and feature history remain unchanged; no new feature.                                                    |
| Normal read after write repair                                        | Repeated inventory through Groq and inspect_current_cad still reports Sketch → Extrude, one part/body and six faces, with edge/vertex uncertainty.                                                                                                                                       |
| Ordinary Chrome tab away/back                                         | Existing conversation/answer/context preserved, with no automatic AI request or destructive reset.                                                                                                                                                                                       |
| Part Studio 1 → Part Studio 2                                         | Previous CAD-specific conversation clears; no stale context carries over.                                                                                                                                                                                                                |
| Explicit-action boundary                                              | Panel opening, visibility changes, selection changes, CAD Refresh alone and context display do not initiate AI analysis. Send/retry remains explicit.                                                                                                                                    |

No live secret-request result is inferred beyond these reported cases. Secret
requests, harmful-device refusals and hostile CAD/history are covered with mocked
adversarial tests. Real OpenAI inference is not part of this live acceptance.

## Architecture and server-only configuration

`POST /api/ai/ask` validates authenticated session, CSRF/exact origin, strict body,
context and admission limits. `ai/service.py` owns provider-neutral policy,
inspection, grounding and lifecycle. `AiProvider` exposes only prompt/public history,
inspection request and evidence/final-answer concepts. `ai/providers.py` selects
exactly one adapter from server settings, never from browser/model input.

Default: `FORGE_AI_PROVIDER=groq`, model `openai/gpt-oss-120b`, low effort.
Optional: `FORGE_AI_PROVIDER=openai`, model `gpt-6.1-sol`, high effort.
Only the selected provider's backend key is required. Models/efforts are reviewed
allowlists; invalid configuration fails closed. There is no custom endpoint,
browser-selectable provider/model/effort/key, SDK migration or automatic fallback.
An OpenAI key alongside Groq never authorizes paid fallback.

For ordinary reads, `GroqProvider` uses the fixed Chat Completions endpoint. Round
one forces the single `inspect_current_cad({})` call; Forge validates its name,
exact no-argument schema and one-call budget. The existing session-owned Phase 4
capture/Phase 5 inspector performs at most four bounded Onshape GETs. Round two
provides minimized evidence, omits tools and requires strict `ModelAnswer` JSON.
Groq does not combine strict output with tool use/streaming. Both calls suppress
reasoning; unexpected readable reasoning is discarded. The optional OpenAI
Responses adapter retains `store:false`, `background:false`, no persistent
Conversation/response chain and request-local opaque encrypted reasoning only.

The model cannot supply document/workspace/element/user/session IDs, OAuth tokens,
provider hosts, HTTP methods, URLs or REST paths as tool arguments. CAD authorization
remains in `acquire_bound` and Onshape's session-owner grant, with final session/
grant checks. No CAD POST/PUT/PATCH/DELETE, FeatureScript or arbitrary execution
capability exists.

## Live defects and final repairs

Chrome rich copying of collapsed native details produced blank bullet markup even
though evidence text was populated. The current disclosure conditionally mounts
nonblank, validated evidence rows. Broad inventory uses deterministic server-owned
overview text, while details preserve provider-native expression/unit caveats.

A real FACE answer once appended an unsupported singleton-body ownership
assumption. All model-written factual sidecars are now replaced with reviewed
suggestion/assumption/question IDs. Direct selection answers render only category
and hard ownership/measurement unknowns. Inventory counts cannot establish joins.
Both providers reject unknown catalog IDs and legacy free-form output fields.

The original write prompt returned Groq HTTP 400 before CAD inspection, confirmed
by safe metadata: `provider_tool_generation_failed`, `tool_use_failed`,
`invalid_request_error`, stage `inspection_request`. No round-two schema was
involved. Read/write requests used identical fixed options; only prompt/history
content differed. Groq failed the forced tool-generation contract for that action
request. No unobserved generation text or internal refusal rationale is inferred.

Explicit CAD action requests now branch before any provider call. The service
runs the same authorized inspection directly, checks permission/freshness/bounds,
rechecks the session and returns a strict public answer from server-owned facts.
It states read-only capability, no writes for this request and an unknown width/
controlling parameter, optionally with the first two captured features. It makes
zero provider calls, fabricates no call and does not treat failed/malformed output
as success. Progress is understanding → inspecting → preparing. Normal reads keep
the original two-round tool flow. The user verified both branches after the fix.

## Grounding, security and privacy review

Model finals choose canonical facts/reviewed sidecar IDs, not arbitrary factual
prose. Forge resolves statements/statuses and revalidates its public response.
Unknown/duplicate IDs, blank evidence, malformed/incomplete output and unexpected
tools fail closed. CAD strings and quoted history remain untrusted data. A narrow
local safety check and model policy/refusal support the low-risk engineering scope;
none is claimed universally robust against every adversarial prompt.

Unavailable mass is not zero. Physical units are unverified. Missing topology is
unknown, not zero. FACE/EDGE category does not establish owning objects or selected
measurements. Successful CAD reads are not deterministic validation; no PASS or
CAD mutation is claimed. Write routing grants no permission, and unknown intent
still has only the read-only allowlist.

Private prompts, answers, CAD evidence, history and readable reasoning are not
persisted in PostgreSQL, localStorage, analytics or content logs. Conversation is
bounded to three exchanges/six public messages in panel memory. Exact document/
workspace/element/account/session changes, logout, disconnect/revocation or panel
destruction clear it and discard pending responses. Same-context tab visibility
preserves it without sending. No background polling or automatic inference exists.

Development-only `ai_validation` diagnostics remain useful and are retained.
`ENVIRONMENT=development` gates fixed reason/provider/stage, numeric status,
allowlisted field path, random Forge correlation and exact allowlisted provider
error code/type/parameter values. Unknown names/values, messages, failed generations,
raw JSON, prompts, CAD, outputs, credentials and system instructions are excluded.
Production suppresses these records and retains generic public errors. Shared
transport logs only safe request/status metadata. Hosting ingress/APM must likewise
exclude query/body content; deployment-wide privacy remains an operator duty.

Groq's [current data policy](https://console.groq.com/docs/your-data), rechecked
2026-10-16, describes no default inference-content retention, with reliability/
abuse exceptions up to 30 days or longer for legal requirements. Usage metadata
is retained. Admin-enabled ZDR is available but not verified for this account.
Optional OpenAI has [separate retention rules](https://developers.openai.com/api/docs/guides/your-data):
`store:false` does not eliminate abuse-monitoring or prompt-cache retention.
No blanket zero-retention claim is made for either provider.

## Resource and failure bounds

- 4,000-character prompt; at most six prior public messages, 4,000 characters each.
- 65,536-byte browser body and five-second receive limit.
- One inspection/up to four existing CAD GETs; two model requests for ordinary reads,
  zero for recognized explicit modification requests; no automatic retries.
- Groq completion budgets: 1,024 inspection / 2,048 final tokens; default low effort.
- OpenAI completion budget: 8,192 tokens per round; default high effort.
- Groq serialized request ceiling: 32 KiB, not a tokenizer or free-quota guarantee.
- Provider response/browser stream ceiling: 262,144 bytes; bounded JSON/schema parsing.
- At most 12 final facts; bounded discussion and three assumptions/questions each.
- Agent timeout 150 seconds; browser timeout 155 seconds; one active turn per user,
  five-second local cooldown and bounded capacity retry-after.

Auth, capacity/rate/quota, timeout, network/outage, malformed/schema output, refusal,
incomplete response, tool_use_failed and cancellation map to safe Forge states.
Normal read tool failures remain generic verification errors; explicit write
capability does not depend on provider generation. No error body reaches the UI.
Cancellation prevents later provider calls; an already-running synchronous CAD
read may finish its bounded GETs. Remote compute cancellation is best effort.

Published [Groq Free limits](https://console.groq.com/docs/rate-limits), rechecked
2026-10-16: 30 RPM, 1,000 RPD, 8,000 TPM and 200,000 TPD for GPT-OSS 120B, shared by
organization. Actual Console limits control availability. Two requests per model-
assisted read and token budgets reduce practical capacity; free use is not unlimited.
Capacity failures require explicit retry and never switch to a paid provider.

## Complete final quality gate — PASS

These results are from the final implementation after all live repairs, not reused
counts from earlier gates. No automated test called live Groq/OpenAI or real CAD.

| Check                          | Final result                                                                            |
| ------------------------------ | --------------------------------------------------------------------------------------- |
| Frozen installs                | npm ci; uv sync --locked; no lockfile/dependency change                                 |
| Formatter                      | make format, then format checks pass                                                    |
| Frontend/backend lint          | ESLint, Prettier, Ruff pass                                                             |
| TypeScript                     | Both workspaces and tool config pass                                                    |
| Strict mypy                    | 66 source files pass                                                                    |
| Complete frontend suite        | 516 tests pass, 21 files                                                                |
| Complete default backend suite | 764 pass; three opt-in PostgreSQL cases run separately                                  |
| Real PostgreSQL suite          | 3 pass in isolated UUID schemas; no application data deletion                           |
| Complete Playwright suite      | 369 pass: Chromium 123, Firefox 123, WebKit 123; zero retries                           |
| Production frontend build      | PASS; development diagnostics/fixtures excluded by regression tests                     |
| Migration drift/comparison     | Alembic check: no new upgrade operations detected                                       |
| Compose/real DB health         | Configuration valid; existing PostgreSQL healthy                                        |
| Dependency audits              | npm: zero vulnerabilities; pip-audit: no known vulnerabilities (editable Forge skipped) |
| make check                     | PASS: lint, typecheck, complete tests, build and Compose                                |
| Git/security review            | Intended source/docs/tests only; empty .env.example; no secrets/private captures        |

Automated regression coverage includes provider selection/own-key requirements,
invalid provider and no fallback; complete Groq/OpenAI mocked transport contracts;
auth/CSRF/context/tool authorization; mass/units/topology/selection/validation
unknowns; zero-provider write capability; hostile names/descriptions/history,
secret/arbitrary-URL/write-policy bypass requests; exact-context/account lifecycle
and late-answer suppression; initial launch, keyboard/send, progress, cancel,
duplicates, Evidence empty/expanded/copy behavior, narrow panels, accessibility,
safe capacity/errors and production exclusion of development surfaces.

Only Playwright-owned 4173/4174 servers were started/stopped. Existing development
services and healthy PostgreSQL were preserved; test schemas clean themselves up.
Application database data/volumes were not reset or deleted.

## Git and secret review

The complete Phase 6 changes are reviewed before staging and again as a staged
diff. `.env` and `apps/api/.env` remain ignored/untracked, and their contents/keys
were not inspected, printed or copied. The unrelated pre-existing local environment
file remains untouched and unread; a repository-local exclude preserves it outside
the commit. No global Git settings or identity changes are made.

All environment-example assignments are empty. Source/staged scans check key/token
patterns, private-key material, credentialed URLs, real CAD reference literals and
accidental capture/binary/database/certificate/debug files. The commit contains
only the intended implementation, synthetic fixtures, tests and finalized docs.
The source scan reviewed 206 tracked/intended files and all 45 Phase 6 paths.
Its only generic credential-URL match was an unchanged synthetic URL-rejection
fixture from an earlier phase; no Phase 6 credential/private-data finding remained.
Normal push uses existing main/origin without force; final local/origin/remote hash
verification is reported in the handoff, avoiding a self-referential commit hash here.

## Phase 6 file inventory

45 implementation files: 17 modified and 28 new; all paths are repository-relative. No lockfile,
dependency manifest, migration or database model changed.

- `.env.example`
- `README.md`
- `apps/api/src/forge_api/ai/__init__.py`
- `apps/api/src/forge_api/ai/adapter.py`
- `apps/api/src/forge_api/ai/diagnostics.py`
- `apps/api/src/forge_api/ai/groq.py`
- `apps/api/src/forge_api/ai/provider.py`
- `apps/api/src/forge_api/ai/presentation.py`
- `apps/api/src/forge_api/ai/providers.py`
- `apps/api/src/forge_api/ai/transport.py`
- `apps/api/src/forge_api/ai/evidence.py`
- `apps/api/src/forge_api/ai/models.py`
- `apps/api/src/forge_api/ai/output.py`
- `apps/api/src/forge_api/ai/policy.py`
- `apps/api/src/forge_api/ai/routes.py`
- `apps/api/src/forge_api/ai/service.py`
- `apps/api/src/forge_api/ai/selection.py`
- `apps/api/src/forge_api/ai/writes.py`
- `apps/api/src/forge_api/core/config.py`
- `apps/api/src/forge_api/integrations/onshape/routes.py`
- `apps/api/src/forge_api/main.py`
- `apps/api/tests/test_ai.py`
- `apps/api/tests/test_ai_presentation.py`
- `apps/api/tests/test_ai_selection.py`
- `apps/api/tests/test_ai_write.py`
- `apps/api/tests/test_groq.py`
- `apps/api/tests/test_client_context_boundary.py`
- `apps/web/src/ai/Analysis.test.tsx`
- `apps/web/src/ai/Analysis.tsx`
- `apps/web/src/ai/__fixtures__/response.ts`
- `apps/web/src/ai/api.test.ts`
- `apps/web/src/ai/api.ts`
- `apps/web/src/components/PromptComposer.tsx`
- `apps/web/src/components/Shell.tsx`
- `apps/web/src/features/Design.tsx`
- `apps/web/src/styles.css`
- `docs/AI_AGENT.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `docs/PHASE_6_REVIEW.md`
- `docs/ROADMAP.md`
- `docs/SECURITY.md`
- `docs/UI.md`
- `tests/e2e/ai.spec.ts`
- `tests/e2e/foundation.spec.ts`

## Known limitations and phase boundary

Read-only AI only. No CAD creation/edit/delete or write permission, FeatureScript,
selected-geometry ownership/measurements, deterministic engineering validator,
verified physical units, atomic multi-read snapshot, complete feature semantics,
assemblies/mates execution, Reality Lock, Modify or Learn implementation exists.
Only supported standard-stack workspace Part Studios/default configuration/end of
feature list are inspected. Omitted/incomplete/unknown evidence stays explicit.

The explicit-action recognizer covers common request phrasing, not every intent or
language; every remaining path still has only read-only tools. Unavailable/stale/
unauthorized CAD, expired sessions and admission limits retain their safe errors.
Provider availability, latency, reasoning sufficiency and quota vary; live samples
do not establish general robustness, every platform, account-level ZDR or future
API behavior. Optional OpenAI is mocked-regression verified, not live verified.
Conversation disappears with panel destruction. Cancellation cannot guarantee
remote compute/billing cancellation. Deployment-wide quotas, ingress privacy and
production operations remain later work. No production readiness or engineering
certification is implied.

Phase 7 is required for a future approved CAD write and remains **not started**.
Completion, commit and push of Phase 6 do not authorize it. OAuth write permissions,
approval/version binding, execution and post-write verification require a new
explicit phase authorization.
