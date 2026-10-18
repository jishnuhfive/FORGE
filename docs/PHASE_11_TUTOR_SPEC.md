# Phase 11 specification — Contextual AI tutor in Learn Mode

Design reference for **Ask Forge**, a learner-requested AI explanation channel inside the Mounting
Bracket guided lesson and its transfer challenge. Deterministic checkers remain the only authority
for correctness. The tutor explains; it never verifies, grades, approves or edits.

## 1. Principle

Forge optimizes for the learner becoming able to do the work. Ask Forge adds a conversational way to
get _reasoning_ help, next to the authored hint ladder (which it does not replace) and the
deterministic Check my step (which it cannot influence). No AI request is ever made automatically.

## 2. Authority model

| Owned by                       | What                                                                                      |
| ------------------------------ | ----------------------------------------------------------------------------------------- |
| Deterministic checker (server) | PASS / FAIL (Not yet) / WARNING / UNVERIFIED, step verification, investigation resolution |
| Authored lesson content        | Objectives, why, hints, completion criteria                                               |
| Session reducer (browser)      | Learner completion, hints, predictions, investigation stage                               |
| The tutor model                | Educational explanation prose and optional Socratic question only                         |

The tutor output is a strict schema. The model may select which check findings (`check_refs`) and
which canonical CAD facts (`fact_ids`) to display; the **server prints their exact wording**. Nothing
the model writes can set a status, resolve an investigation, mark a step done or change a count. A
presentation guard adds a visible note if the prose claims a verdict, confirms a size, or certifies
strength, and a fixed "Based on your last check…" note accompanies any check-based answer.

## 3. Trust boundary: how check results reach the model

The browser must not author evidence (`{"checkResult":"PASS"}` is never believed). Design:

1. `POST /api/learning/check-step` already evaluates the deterministic result. It now also returns an
   opaque **evidence token**: `base64url(payload).base64url(HMAC-SHA256)`.
2. The HMAC key is derived from the caller's own **session credential**, the same idea as the CSRF
   MAC. A token therefore cannot be replayed from another session, forged, or edited; any change to
   the signed bytes fails verification. The payload holds the lesson, step, outcome, capture time,
   issue time and the compact per-requirement findings, nothing else.
3. Ask Forge sends the token back. The server verifies it, requires the lesson/step to match the
   question's step, requires every finding id to be a requirement the server's own checker defines for
   that step, rejects future-dated tokens, and treats tokens older than one hour as absent.
4. A forged, altered, foreign or mismatched token is a **rejected request (400)**, never silently
   downgraded. An authentic but expired token is simply ignored.

**Tradeoff.** Fully server-owning Phase 10 session state would need persistence (a student record),
which is out of scope and against the privacy rules. A stateless, session-bound signed token gives the
same trust property for the one thing that must be trusted (the check findings) with no storage. The
token is opaque to the browser, is never sent to the AI provider, and dies with the session.

**Untrusted learner hints.** The request also carries a closed set of enums (experience, goal, hints
revealed, guidance level, investigation stage and whether a prediction was answered). They can only
tune tone and help style. They cannot establish verification. The learner's prediction _text_ is never
sent.

## 4. Context the tutor receives

Built server-side by a pure function (`tutor/context.py`):

- **Trusted:** authored step content from a server catalog (`tutor/catalog.py`, mirrored to
  `bracket.ts` by step id, with a drift test), and the verified check findings with requirement labels
  taken from the checker.
- **Untrusted, labeled:** the learner's question, prior conversation (at most 3 exchanges, each bounded),
  and every CAD name or string.
- **Derived `help_style`:** `conceptual` (ideas and questions only), `guided` (name the feature type and
  next action, no click path, no dimensions), `concise` (at most three short sentences). The transfer
  challenge stays `conceptual` until the learner has deliberately revealed the tool-specific hint
  (hint level ≥ 2). A learner whose investigation guidance is `reduced` gets `concise`. No mastery
  inference exists.
- **Never included:** document/workspace/element/feature/body IDs, tokens, cookies, CSRF, database ids,
  microversion ids, the evidence token, or the learner's prediction.

## 5. CAD evidence

Only when a validated workspace Part Studio context was supplied does the model get the existing fixed
`inspect_current_cad` tool (no arguments, no IDs, no URLs). The model decides whether the question needs
current state beyond the last check. The read goes through the existing authorized, gated, read-only
pipeline and the existing canonical-fact projection. Old conversation text is never evidence. With no
context, the tool is not offered and the answer says so.

## 6. Fixed boundary responses (no model call)

A deterministic server reply, with no model call and no CAD read, handles requests to exceed the tutor's
authority: change the model ("Suppress this feature for me", "Delete the fillet"), use APIs or
FeatureScript, or mark/verify a step ("Mark this step as passed"). The unsafe-prompt screen runs first.
Legitimate questions (including "why isn't my step complete?") are not caught.

## 7. Request, response and limits

`POST /api/learning/tutor` (authenticated session, exact Origin, CSRF, ≤16 KiB closed JSON, errors never
echo the question). NDJSON events: `progress` (`understanding`, `inspecting`, `reviewing`, `preparing`),
then `result` or `error`. Limits: one request in flight per user with the shared cooldown, plus a
per-user cap of 30 tutor questions per hour held in memory. Two model rounds at most; **no automatic
retry and no provider fallback**. Groq is the default; the optional OpenAI provider is supported through
the same transport. Cancellation stops the request and a cancelled answer is never shown.

Response (`TutorAnswer`): `explanation`, `reasoning_question`, `next_action`, `observed[]` (server
wording; `source` = `check` or `cad`), `unknowns[]` (every UNVERIFIED finding is always listed; a CAD
read always adds the units and freshness caveats), `notes[]`, `latest_check`, `used_cad`,
`captured_at`, `capability_state: read_only`.

## 8. User interface

An **Ask Forge** disclosure (collapsed by default) after the check result and investigation, on every
Mounting Bracket step and the transfer challenge (not the Phase 7 sample). It states what it uses,
accepts one question (≤600 characters; Ctrl/Cmd+Enter sends), shows `Reading your question…` stages,
offers Stop, and renders the answer explanation-first, then "What Forge observed", "Still unknown", "Next
thing to try" and notes. Errors use fixed copy, always say the lesson still works, and offer Try again.
Conversation is React memory only (max 3 exchanges) and is cleared when the step, document context,
login or lesson changes. Quiet Engineering Precision: no avatars, sparkles or chatbot chrome.

## 9. Non-goals and boundaries

No CAD write, OAuth/scope change, new provider, persistence, grade, mastery or analytics; no Modify
changes; Phase 9 write code is unreachable from the tutor (its only tool is the read-only inspect call).
No automatic AI call on opening Learn, advancing, checking, failing, opening an investigation, choosing a
prediction, changing selection or refreshing CAD.
