# Hackathon Modify B2 — live natural-language Modify

The live Modify tab now consumes the integrated B1/A1/A2 pipeline. Backend CAD
capabilities, OAuth settings and write flags are unchanged. The development UI lab
remains an explicitly labelled local mock.

- A natural-language request sends only `{context, request}` to
  `POST /api/modify/plan`. Strict closed parsers accept a clarification or an
  authoritative 1–5 operation preview. Clarifications show fixed explanatory copy
  and display-only choices; the human rewrites the request.
- The preview shows every ordered target, field and exact current → proposed text.
  Only an explicit human click sends `{digest}` to
  `POST /api/modify/plans/{handle}/approve`. Synchronous one-use protection prevents
  rapid clicks, renders, effects and status requests from approving again.
- A2 NDJSON parsing validates closed event/stage/state enums, operation indexes,
  operation counts, ordering and journal consistency. Bounds are 21 events,
  512 UTF-8 bytes per line including newline and 8,192 bytes total. Truncation,
  malformed data, invalid UTF-8, network failure and timeout remain unresolved;
  HTTP 200 or stream end alone never establishes success.
- Per-operation progress shows Checking, Applying, Verifying and the actual result.
  Partial failure preserves earlier verified changes and identifies failed/skipped
  operations. No rollback or undo is implied.
- Uncertainty offers **Check status**, using only
  `GET /api/modify/plans/{handle}`. Approval is never retried, even after an HTTP
  error, disconnect, timeout or parsing failure. In-flight status remains queryable.
- **Cancel plan** sends `{}` to the generalized cancel endpoint. Cancellation is
  confirmed only by the closed cancelled/skipped result.
- Proposal handle/digest stay in component memory. Account/session/workspace/element
  or revision changes clear local authority, abort the consumer and ignore late
  responses. Face/edge selection and ordinary rerenders do not approve anything.
  Names and values render as React text. No authority enters browser storage,
  navigation URLs, analytics or provider request construction.

Verification uses synthetic CAD/model traffic only. Focused tests cover strict
schemas, request/approval boundaries, 1/3/5 operations, clarification, progress,
partial completion, malformed/incomplete streams, timeout, status, cancellation,
context reset and inert labels. Browser fixtures exercise the new workflow in a
320px panel with keyboard navigation, accessibility, forced colors and reduced motion.

**Real Onshape writes during implementation/testing: ZERO. OAuth changes: ZERO.**
Controlled disposable-document live validation remains pending. Existing A1 adapter
limits and Phase 9 conformance limitations still apply; this UI does not establish
geometry suitability or engineering certification.

Final checks: 101 focused B2 tests, all 820 frontend tests, TypeScript, build,
ESLint/Prettier and 314 focused backend regressions pass. The broader backend run
passed all 2,149 tests with isolated PostgreSQL. Browser checks pass 66 cases across
Chromium, Firefox and WebKit (39 B2 + 27 navigation/accessibility). An initial broader
run passed 576 and found 12 missing standalone-copy assertions; restoring the original
explanation resolved them in the final affected-suite run. Both dependency audits
and secret/privacy review pass. The build has a nonblocking 500 kB chunk warning.
