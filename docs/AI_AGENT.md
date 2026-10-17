# Phase 6 read-only AI agent

Implementation began on 2026-10-14. Final real Groq verification was reported by
the user on 2026-10-16, including repaired Evidence, FACE/EDGE grounding and the
deterministic write-capability path. The complete final repository gate passes;
[PHASE_6_REVIEW.md](PHASE_6_REVIEW.md) records results and limits.
The separately authorized Phase 7 authored learning foundation makes no AI calls;
all CAD mutations remain deferred. This is design assistance, not
engineering certification. Codex develops Forge; Forge's runtime AI is separate.

## Groq contract reviewed — 2026-10-15; retention/quotas rechecked 2026-10-16

The official [model page](https://console.groq.com/docs/model/openai/gpt-oss-120b)
confirms `openai/gpt-oss-120b`, local function calling, JSON-schema output and
low/medium/high effort, with a 131,072-token context and 65,536-token maximum
completion. Forge applies much smaller budgets below. [Structured Outputs](https://console.groq.com/docs/structured-outputs)
supports strict mode for this model but explicitly excludes streaming and tool use
in the same request. Forge therefore requests the single local tool in round one,
then supplies its result without tools and requests strict JSON schema in round two.

Groq's [Responses API](https://console.groq.com/docs/responses-api) exists in beta;
its specific history section says stateful conversations are not yet supported.
Forge uses the documented [Chat Completions API](https://console.groq.com/docs/api-reference)
for this provider because [GPT-OSS reasoning controls](https://console.groq.com/docs/reasoning)
explicitly support `include_reasoning:false` there. OpenAI compatibility does not
mean identical flags: Groq Chat's `store` option is unsupported, so Forge omits it.
There is no downgrade to loose JSON when strict output fails, and no automatic
retry or provider fallback. API-specific differences stay inside adapters.

The [free plan limits](https://console.groq.com/docs/rate-limits) currently list
30 RPM, 1,000 RPD, 8,000 TPM and 200,000 TPD for this model. These are shared at
organization level, can vary, and are not an unlimited or guaranteed free service.
Two requests per model-assisted read turn imply at most 500 such turns/day from the request limit
alone; token limits reduce practical capacity. The operator must check the account's
actual Limits page and remain on Free if paid Groq usage is not desired. Forge does
not upgrade accounts, circumvent quotas or fall back to a paid OpenAI key.
The [services agreement](https://console.groq.com/docs/legal/services-agreement)
permits API integration into customer applications for end users subject to its
terms, model terms and use restrictions. This supports an operator-hosted bounded
beta, not a guarantee of capacity, suitability or legal clearance for every use.

[Groq data controls](https://console.groq.com/docs/your-data) say inference inputs/
outputs are not retained by default, with system-reliability/abuse exceptions of
up to 30 days unless law requires longer. Usage metadata is retained. Organization
admins can enable ZDR in Data Controls; Forge cannot verify or activate that account
setting. No zero-retention claim is made for an unverified account. Retained
customer data is described as residing in US GCP storage. Do not use batch/files,
fine-tuning or other persistence features for Phase 6.

## Optional OpenAI contract reviewed

Official OpenAI documentation reviewed on 2026-10-14:

- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol): exact API ID `gpt-6.1-sol`; Responses tool calling, Structured Outputs and high effort supported.
- [Responses migration](https://developers.openai.com/api/docs/guides/migrate-to-responses): Responses request shapes and stateless continuation.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling): strict no-extra-properties function schemas; validate calls independently.
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): strict `text.format` schema and explicit refusal/incomplete handling.
- [Reasoning](https://developers.openai.com/api/docs/guides/reasoning): encrypted reasoning replay for stateless tool continuation.
- [Data controls](https://developers.openai.com/api/docs/guides/your-data): `store:false` is not a zero-retention guarantee. Separate abuse monitoring and prompt-cache policies apply.
- [Agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) and [safety practices](https://developers.openai.com/api/docs/guides/safety-best-practices): keep untrusted data below privileged instructions, constrain data flow and test adversarial cases.

These sources verify the interface, not account eligibility or real task quality.
Real eligibility, quota and grounding must be tested with the operator's API project.

## Flow and ownership

Normal read questions follow this provider-assisted path. Explicit CAD modification
requests branch directly to the existing bound inspection and a server-owned
capability answer; they make no provider request (details below).

```text
Explicit Design send (disclosed hosted-service transfer)
  -> POST /api/ai/ask (session, CSRF, strict bounded body)
  -> Forge agent -> AiProvider protocol, safe AgentTask only
  -> selected adapter requests inspect_current_cad({})
  -> adapter validates exactly one no-argument call
  -> existing session-owned Phase 4 capture -> Phase 5 CadInspector
  -> minimized untrusted evidence and canonical facts
  -> selected adapter generates strict ModelAnswer without further tools
  -> Forge resolves fact IDs -> normalized final answer/progress
```

`ai/provider.py` defines `AiProvider` and a prompt/history-only `AgentTask`. Its
`request_inspection` and `answer_with_evidence` methods expose no HTTP details,
provider IDs, CAD references, keys or raw responses to the agent. Each adapter
instance belongs to one request and consumes its continuation exactly once.
`ai/providers.py` selects exactly one adapter from validated operator settings.
`ai/groq.py` translates Groq Chat; the preserved `ai/adapter.py` translates OpenAI
Responses. `ai/transport.py` supplies fixed-endpoint, bounded HTTP/error handling
using the existing httpx2 client. No SDK, competing stack or lockfile change is needed.

`ai/service.py` retains the same two-round loop, policy, evidence/grounding and
session checks for model-assisted read questions. Explicit CAD modification requests
take a server-owned capability branch before provider generation: one existing
authorized inspection, zero model requests, and a strict read-only public answer.
`ai/routes.py` retains admission, CSRF, timeout and normalized NDJSON.
`ai/evidence.py` and `acquire_bound` retain the Phase 4/5 authorization/data boundary.
Onshape independently authorizes every object using the session owner's grant.
The model cannot redirect a read, choose another user/host or execute arbitrary code.

## Server configuration

The existing repository-root `.env` is server-only and ignored. `apps/api/.env`
is not the configured settings source. `.env.example` retains empty placeholders.

| Setting                       | Default / allowed values                             |
| ----------------------------- | ---------------------------------------------------- |
| FORGE_AI_PROVIDER             | `groq`; only `groq` or `openai`                      |
| GROQ_API_KEY                  | Required only for selected Groq; backend SecretStr   |
| FORGE_GROQ_MODEL              | `openai/gpt-oss-120b`, reviewed allowlist only       |
| FORGE_GROQ_REASONING_EFFORT   | `low`; `low`, `medium`, `high`                       |
| OPENAI_API_KEY                | Required only for selected OpenAI; backend SecretStr |
| FORGE_OPENAI_MODEL            | `gpt-6.1-sol`, reviewed allowlist only               |
| FORGE_OPENAI_REASONING_EFFORT | `high`; `low`, `medium`, `high`                      |

Legacy `FORGE_AI_MODEL` and `FORGE_AI_REASONING_EFFORT` remain aliases for OpenAI
only; explicit OpenAI names take precedence. They never select/configure Groq.
Empty example placeholders use defaults. Neither provider requires the other's key.
Missing selected-provider configuration fails closed, even when the other key exists.
The browser cannot choose provider/model/effort/key/endpoint. No custom origin,
ambient proxy, redirects or production fake transport exists. Tests need no real key.

## Privacy and lifecycle

Optional OpenAI Responses requests explicitly use `store:false`, `background:false`
and no Conversation object or `previous_response_id`. Its single tool continuation
replays bounded call data and opaque encrypted reasoning in request-local backend
memory. Readable reasoning summaries are discarded. Groq uses stateless Chat history,
requests `include_reasoning:false` in both rounds and discards unexpected reasoning
fields. Its unsupported `store` parameter is omitted. No provider reasoning or
response ID reaches the browser or persistent storage.

Private prompts, evidence, generated text and history never enter PostgreSQL,
application logs, analytics or localStorage. The shared transport logs only random
Forge correlation, sanitized provider request ID and status class. Access/HTTP logs
remain suppressed; ingress/APM must omit AI bodies. Groq reliability/abuse retention
and optional OpenAI abuse-monitoring/caching retention remain provider/account
policies, not controls implied by Forge's ephemeral local state. See the official
sources above; neither provider is represented as zero retention by default.
The [OpenAI data policy](https://developers.openai.com/api/docs/guides/your-data)
was rechecked on 2026-10-16: `store:false` disables normal stored-response state,
while separate abuse-monitoring logs may retain content up to 30 days (or longer
under the documented exceptions), and prompt-cache state may remain up to 24 hours.
No approved account-level ZDR/MAM configuration is assumed or verified.

The UI keeps at most three exchanges (six messages), resending at most six prior
public messages of 4,000 characters each as explicitly untrusted history. It reads
fresh CAD on every explicit send; old assistant text is not current CAD evidence.
Actual document/workspace/element/origin/microversion/session changes remount and
clear the old conversation, draft and pending request. Logout/disconnect/revoke,
invalid context, actual navigation/pagehide, panel destruction or leaving the
mounted Design workspace also clears it. Ordinary same-frame browser hide/show,
focus and valid selection changes preserve prior exchanges without AI/CAD calls.
Captured time and send-time selection are explicit. A changed selection category
while an answer is pending discards that answer; resending requires a click.
Clear conversation removes local exchanges. No background polling or auto retry.

## Read tool and evidence minimization

The only function is `inspect_current_cad`, strict object schema with no properties,
`additionalProperties:false`, `{}` only. Fixed dispatch validates name, arguments
and call count before reading. Unknown tools, duplicate/multiple calls, extra IDs,
URL/method arguments, malformed JSON and a second-round call fail closed.

Tool output reuses `forge-cad-inspector-v1`, excluding the random source request ID.
It includes conservative source statuses/counts, capture time, default/end-of-list
context, consistency, freshness, completeness/omission metadata, physical
availability and normalized `none`/`FACE`/`EDGE`/`unknown` panel selection. No raw
selection reference, provider record, feature/part/body identifier, geometry,
provider URL, credential, cookie, session/user/database ID or microversion goes to
the selected AI provider. Metadata text is intentionally allowed private CAD content and must be
reviewed under the project's external-service policy.

AI minimization further limits the inspector to the first 20 features, 20 parts,
20 bodies and four parameters per feature. Omitted counts/completeness are updated;
whole JSON/value semantics remain intact. The serialized evidence plus canonical
fact catalog must fit 65,536 UTF-8 bytes; excess fails safely, never silently drops
caveats. Stale/mismatched evidence is rejected. Partial successful reads stay
explicitly partial; permission failures stop analysis. No repeated Onshape capture
occurs within a turn. The existing per-user CAD gate is shared with Refresh CAD.

Null topology is unknown, never zero. Unavailable mass is not numeric zero.
Expression strings are not evaluated and do not establish verified units. Selection
is a panel observation, not proof of surface geometry or feature/part ownership.
Separate provider reads cannot prove atomicity/currentness. The first 20 entries
cannot answer questions about omitted entries; the assistant must say what is missing.

## Agent policy and grounding

The concise policy is in `ai/policy.py`. Forge uses current evidence for CAD claims,
distinguishes verified/unverified/unknown/assumption, preserves missing information
and never claims a CAD change, engineering PASS or certification. It can explain,
identify missing evidence or propose general approaches. No validator exists yet.

Model output selects up to 12 canonical fact IDs and up to three reviewed optional
next-step IDs. The provider-neutral strict schema has `suggestion_ids`,
`assumption_ids` and `question_ids` instead of free-form discussion, assumptions
or questions. Both adapters use this same schema. The public text arrays and
`discussion` are resolved from reviewed server-owned catalogs. An empty next-step list omits it.
Broad inventory asks suppress suggestions rather than restate the answer.

The provider cannot author current-model conclusions such as "active and complete"
through suggestion prose. ACTIVE means only not suppressed. Inspector completeness
means captured-field coverage, never sketch correctness, constraints, completion,
manufacturability or a validation PASS. The underlying CAD inspector schema and
acquisition semantics remain unchanged.

Model output selects canonical fact IDs. The server validates each ID and
renders the exact corresponding statement/status. A model cannot add arbitrary
verified evidence statements. The final Forge contract contains `answer`, `evidence`,
`uncertainties`, optional `discussion`, `assumptions`, `follow_up_questions`,
`capability_state:read_only` and capture time. Suggestions are visibly
unverified optional checks; the model chooses their relevance, not their wording.
Assumptions are reviewed, explicitly hypothetical engineering cases, never assertions
about the CAD or selection ownership. Follow-up questions request user requirements,
never offer unsupported tools. Relevance remains model-dependent; mocked evals do
not establish live quality or universal robustness. No model output is executed or used as permission.

CAD names, descriptions, string values and expressions are untrusted quoted data,
never interpolated into privileged instructions. The tool output marks its trust
level, and feature names/values in canonical facts remain quoted literals. History
also remains untrusted user-role data. Prompt wording is defense in depth; the
fixed tool surface, no secrets in context, strict schemas, fact resolution and
bounded loop enforce independent architectural restrictions.

Forge targets education, makers and low-risk engineering. Policy refuses weapon
construction/optimization, harmful-device instructions and secret/system-prompt
requests. A deliberately narrow local rule blocks clear weapon-building and secret
requests before model spend; a structured model safety refusal maps to fixed safe
copy. The local rule is not a comprehensive classifier and is not certification.
Normal mechanical design and education remain allowed. No write tool exists.

## Response presentation and evidence disclosure

Unambiguous inventory questions such as "What is in this Part Studio?" use a
server-built overview from the same bounded inspector: observed counts, ordered
names/activity, independent part/body observations and returned topology. Missing
counts remain unknown. Relevant evidence stays behind the Evidence button; detailed
parameters are not dumped into the primary inventory answer. Specific questions
continue to use the selected canonical facts. Numeric parameter values are still
captured settings, not evaluated dimensions; one consolidated uncertainty replaces
repeated per-parameter caveats. User/CAD strings remain quoted, escaped data.

Evidence statements reject empty/whitespace values in the backend and browser
contracts. The frontend also filters blank rows defensively and omits an empty
Evidence section. Evidence rows mount only when expanded. Chrome rich HTML copying
of the previous collapsed native details element was reproduced with empty list
items even though screen rendering and the actual statements were correct. Not
mounting collapsed rows removes this clipboard serialization failure; expanded
rows contain their meaningful text and status. No private capture is needed.

An initial launch remains selection-unknown until a trusted SELECTION arrives.
Only an explicit validated empty selection array means no selection. Initialization
and show are not empty-selection evidence; no new selection request/highlight
capability or message shape was introduced.

## Hard selection-grounding boundary

`ai/selection.py` accepts only the normalized selection category. It cannot inspect
inventory counts, names or recent features, and has no ownership join. Even one
body/part/Extrude never establishes which object an opaque selected FACE/EDGE
belongs to. Canonical facts explicitly mark owning part, body, feature, dimensions,
surface/curve type and selection-specific geometry unknown. FACE area/normal and
EDGE adjacent geometry remain unknown; the current tool cannot retrieve them.

Direct selection questions use a server-owned answer and these facts even if the
model selects singleton body/part/feature facts. Suggestions, assumptions and
follow-up questions are all empty for that response. Unknown remains unknown in
all output channels. Outside these questions, assumptions/questions select only
reviewed hypothetical load/environment cases and requests for user requirements.
No ownership hypothesis is allowed in this Phase 6 output contract, including a
conditional one. Legacy free-text fields and arbitrary IDs fail closed in both
provider adapters. The public response schema remains unchanged.

The service passes the same send-time category to projection and resolution; user
wording or earlier conversation cannot change FACE to EDGE/none or map an entity.
No raw selection IDs, extra CAD calls, measurements or model capabilities are added.
The single bound tool, two provider rounds and all existing security/lifecycle
controls remain unchanged. The new tests use only invented CAD and mock transports.

## Budgets and failures

| Resource               | Phase 6 bound                                                                                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Prompt                 | 4,000 characters, nonblank                                                                                                                                               |
| Prior public history   | Six messages, each at most 4,000 characters                                                                                                                              |
| Entire browser request | 65,536 bytes, five-second body receive limit                                                                                                                             |
| CAD tool / capture     | One / four existing bounded GETs                                                                                                                                         |
| Model round trips      | Two, no automatic retries                                                                                                                                                |
| Output tokens          | Groq 1,024 tool / 2,048 final (3,072 total); OpenAI 8,192 per round (16,384 total)                                                                                       |
| Provider response      | 262,144 bytes; bounded JSON depth/nodes/strings                                                                                                                          |
| Model final            | 12 fact IDs, three reviewed next-step IDs; public discussion capped at 1,600 characters; three reviewed assumption/question IDs; public strings capped at 600 characters |
| Total agent duration   | 150 seconds; browser abort after 155 seconds                                                                                                                             |
| Provider transport     | Connect/write 5s, read inactivity 45s, pool 2s; eight connections shared by selected providers                                                                           |
| Admission              | One active turn per user, five-second minimum cooldown; existing bounded per-process gate                                                                                |
| Browser stream         | 262,144 bytes, at most eight normalized events                                                                                                                           |

Server-owned progress streams `understanding`, `inspecting`, `reviewing`, `preparing`
only at the corresponding actual stage, followed by one structured result or safe
error. This is progress streaming, not final-text token streaming; raw provider SSE,
reasoning, tool arguments/results and provider internals are never proxied. Hosting
must disable buffering for this endpoint (`X-Accel-Buffering:no` is supplied).

Abort cancels the foreground provider transport and prevents further model calls.
An existing synchronous Onshape capture already in progress may complete its at
most four bounded GETs in a background thread; its result is discarded. Remote
compute/billing cancellation is best effort, not guaranteed. No CAD writes occur.
Timeouts stop the agent. Retrying is always an explicit user action.

Groq also caps its entire serialized request at 32 KiB. This is a byte bound, not a
tokenizer or a guarantee to fit the free TPM/TPD quota. Oversized payloads and Groq
413/429/498 responses map to fixed `capacity_unavailable`, with bounded retry-after
and explicit retry only. No key/provider switch or automatic paid fallback exists.

Fixed public mappings cover missing config, auth failure, connection failure,
rate limit, quota, timeout, refusal, incomplete/malformed response, missing context,
read permission, unavailable evidence, expired session and admission rejection.
Retry-after seconds are parsed as a bounded integer, never arbitrary error text.
Raw response/error bodies and exceptions do not cross the browser boundary.

## Write-request contract and safe validation diagnostics

The user's safe live diagnostic confirmed HTTP 400 at `inspection_request` with
`tool_use_failed` / `invalid_request_error`, before CAD or final schema. Forge
forced a specific inspection call even for unsupported action requests; Groq did
not generate the required valid tool call for "Make this model 20 mm wider.".
Read prompts had generated the expected call. The request builder used the same
model, roles, no-argument tool, forced choice, parallel setting, reasoning and
token budget; only prompt/history content differed. No write-only HTTP field,
inspection response schema or OpenAI-only compatibility flag was present. The
diagnostic does not disclose whether the invalid generation was prose or another
call; no private generation is inspected or retained to speculate further.

`ai/writes.py` recognizes explicit modification requests with a bounded anchored
rule, distinct from read questions discussing an Extrude feature or a possible
change. After the existing policy check, the service directly invokes the same
session/context-authorized inspection. It checks freshness/permissions, rechecks
the session, and returns `resolve_write`'s strict public read-only answer. No
provider request, generated tool call, final model schema, fake provider output
or retry is needed. The statement that writes are unavailable is server-owned;
the first two captured features may supply context. Width/controlling parameters
remain unknown. Suggestions, assumptions and follow-ups are empty. Progress goes
from understanding to inspecting to preparing; no model-review stage is fabricated.

Every request remains read-only, including phrasing outside this narrow routing
rule. Unrecognized requests retain the normal bounded model/tool flow and generic
safe errors. Its strict output, unknown/duplicate-ID, tool/protocol, incomplete and
safety-refusal handling is unchanged. Empty model answers still fail grounding;
there is no relaxed empty-array or malformed-output success fallback. CAD evidence
permission/freshness/bounds, admission, cancellation and session checks apply to
both branches. A healthy configured backend is still required by the AI route.

The actual round-two schema is unchanged: five required properties, closed object,
four bounded arrays and the safety enum. All IDs remain bounded strings/enums;
there are no optional/nullable fields. Arrays have no minimum count, so `[]` is
schema-valid. Groq documents arrays/enums and required closed objects; optional
values would require a required property with a null union. Its documentation
does not enumerate every supported length constraint, so live compatibility is
still an acceptance check. Strict output remains separate from tools/streaming.
Budgets stay 1,024/2,048 completion tokens with low default effort and suppressed
reasoning; `length` is an incomplete error, never partial success. Official sources:
[Structured Outputs](https://console.groq.com/docs/structured-outputs),
[reasoning](https://console.groq.com/docs/reasoning),
[API reference](https://console.groq.com/docs/api-reference), rechecked 2026-10-15.

Only `ENVIRONMENT=development` emits `ai_validation` warning records: fixed reason,
allowlisted provider/stage, numeric HTTP status when available, allowlisted root
validation field (optional `[]`) and Forge's random request correlation ID. Groq
rejections may additionally report exact allowlisted error code/type/parameter
literals; arbitrary values, error messages and `failed_generation` are excluded. Unknown
field names and all values/messages/exception representations are omitted. No
prompt, CAD, provider content, secret or raw payload is logged. Production emits no
such diagnostic; both environments keep the same generic browser error contract.
Codes distinguish transport rejection, tool shape/arguments, incomplete/refusal,
JSON parsing, required/enum/schema fields, empty/unknown/duplicate canonical IDs,
grounding rewrite and final public validation. Official
[local tool calling](https://console.groq.com/docs/tool-use/local-tool-calling)
documents HTTP 400 when a forced tool is not generated. The same request builder
served inventory/write prompts with only prompt/history differences; no write-only
parameter or round-one schema existed. The live `tool_use_failed` code confirmed
generation failure. For normal reads this failure still maps to generic invalid
response with no automatic retry or paid fallback; explicit writes do not call it.

## Verification

`tests/test_ai.py` preserves the OpenAI suite and `tests/test_groq.py` adds the
provider-interface, selection, no-fallback, two-stage Groq, quota, cancellation and
privacy regressions. Both use MockTransport and invented CAD only, including the complete
route/tool continuation, privacy/log exclusions, transport errors, refusal,
incomplete/unexpected output, malformed arguments, tool budgets, body/history
limits, revocation, timeout, hostile CAD and product safety. Its 14 deterministic
eval cases are summary, empty Part Studio, unknown feature, missing mass, unverified
units, absent validation, incomplete parameters, face, edge, stale evidence,
unsupported write, injected name, direct
secret request and invented fact ID. The expected behavior is grounded known
facts, preserved uncertainty, safe refusal/failure and no unauthorized tool.

Frontend unit/Playwright tests cover explicit typing/send/keyboard, progress,
cancel/duplicate prevention, errors/retry, evidence labels, selection minimization,
context/account clearing, same-context tab preservation, narrow layouts,
accessibility and no automatic AI calls on selection/focus/Refresh CAD. Fixtures
are excluded from production. The user reported all final live acceptance cases
passed. This verifies the recorded Part Studio scenarios, not every prompt,
model version, account, browser platform or future provider behavior.

## Later phases — planned only

Approval-bound CAD writes, execution, post-write reconciliation, deterministic
validation, Reality Lock, assemblies/mates and full autonomous workflows remain
in their authorized roadmap phases. Future writes require authentication,
object-level authorization, strict schemas/units/bounds, a specific approved
plan/document version, sanitized action logging and result verification. Preserve
PASS/WARNING/FAIL/UNVERIFIED independently of LLM judgment. Nothing in Phase 6
creates a write tool or grants approval for Phase 7.

## Phase 7 authored teaching boundary

The Sketch to solid lesson, instructions, Why text, vocabulary and three hint levels
are deterministic authored frontend content. Learning never calls this agent or any
provider, reads CAD automatically or uses model output to assess a learner. Its
completion summary reports only local observed lesson interactions and learner-marked
steps. Future optional AI teaching would require explicit design/authorization;
Phase 8 deterministic checking is not implemented. Existing Design sends retain all
Phase 6 disclosure, grounding, privacy and read-only boundaries.

## Phase 9A authority design — not a runtime tool

[The future first-write design](PHASE_9_SAFE_WRITE_SPEC.md) permits intent
interpretation/clarification and explanation of a server-created proposal for one
terminal Fillet suppression. Deterministic code alone would own target identity,
approval, freshness, execution and result status. The private executor must never
be an AI-callable function. No generic HTTP, model-provided IDs/tokens/FeatureScript,
model approval, success override or expired-approval reuse is permitted.

Phase 9A adds no model tools, provider changes or executable proposal code.
Current deterministic read-only write refusal and the no-argument inspection tool
remain unchanged. Phase 8B contracts are external/unmerged; 9B must await their
final integration and explicit authorization.
