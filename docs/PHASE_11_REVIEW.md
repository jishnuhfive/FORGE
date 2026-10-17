# Phase 11 — Contextual AI tutor in Learn Mode

**Status: implemented and automatically verified on `phase11/contextual-ai-tutor`; NOT merged and NOT
human-validated in real Onshape.** Branched from `main` at `0bfe0d9` (Phase 9 and Phase 10 merged).
Design reference: [PHASE_11_TUTOR_SPEC.md](PHASE_11_TUTOR_SPEC.md). Phase 12 is not started.

## What was built

- **Ask Forge** (`learning/TutorPanel.tsx`, `tutorApi.ts`): a collapsed disclosure on every Mounting
  Bracket step and the transfer challenge. Explicit send only (Ctrl/Cmd+Enter or Send), Stop, fixed error
  copy, at most three exchanges, cleared when the step, document context, login or lesson changes.
- **Endpoint** `POST /api/learning/tutor` (`apps/api/src/forge_api/tutor/`): authenticated, same-origin,
  CSRF, closed ≤16 KiB schema, NDJSON stream, one in flight per user plus a 30/hour in-memory cap.
- **Signed evidence token**: Check my step now returns an opaque, session-bound HMAC proof of its result.
  The tutor accepts check results only through it, so the browser cannot author or alter them.
- **Server-owned context** (`context.py`, `catalog.py`): authored lesson content plus verified findings;
  client hints are closed enums that only tune tone and help style.
- **Strict answer contract**: the model writes explanation prose and may select finding/fact ids; the
  server prints the exact observed wording, always lists every UNVERIFIED limitation, and adds notes.
- **Fixed boundary replies**: requests to change the model, use APIs, or mark a step passed are answered
  by the server with no model call and no CAD read.
- **Provider reuse**: the existing transport, settings, budgets, read gate and canonical CAD facts. Groq
  default, optional OpenAI through the same transport. No new provider, no retry, no fallback.

## Required properties and where they are proven

| Requirement                         | Proof                                                                                                                                                                       |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explicit send only                  | Frontend test: checks, failures, investigations, predictions, hints and navigation make no tutor call; backend test: check-step makes no AI call                            |
| Deterministic checker authority     | Answers change no verified count, completion or investigation (UI tests); model verdict claims get a note and `latest_check` stays the signed result (backend + eval tests) |
| Browser cannot forge a check result | Forged, foreign-session, altered, wrong-step, unknown-requirement and future tokens are rejected (400); expired tokens are ignored                                          |
| Prediction neutrality               | Only "answered / not answered" is sent, never its content; policy forbids right/wrong; UI and e2e tests assert the text is absent                                           |
| Re-check resolves investigations    | e2e scenario B: the tutor resolves nothing; only an explicit re-check does                                                                                                  |
| Transfer help is lighter            | `help_style` is `conceptual` until the tool-specific hint is revealed; asserted in core, route and e2e tests                                                                |
| Fading help is deterministic        | `reduced` guidance gives `concise`; no mastery inference exists in the policy or context                                                                                    |
| Learn works without AI              | e2e scenario D: provider error → fixed copy, and Why, hints and Check my step still work                                                                                    |
| Privacy                             | No identifier, token, cookie, CSRF value, evidence token or prediction reaches the provider (tested)                                                                        |
| Prompt injection                    | Injected names and prior conversation travel only as quoted/untrusted data; policy stays first                                                                              |
| No write path                       | The only tool is read-only `inspect_current_cad`; only GETs reach Onshape; Phase 9 code is untouched                                                                        |

## Live check (not a substitute for human validation)

Seven synthetic probes ran through the real tutor adapter against Groq with a synthetic check result and
no private CAD data. All seven produced valid answers. The model said it could not confirm a 0.25 in size
and declined a strength assessment, and the server added the dimension note. The probes also found that
the model sometimes lists invented evidence ids; failing the whole answer for that was too harsh, so
unknown or repeated ids are now dropped (the server only prints statements it owns).

## Verification (Windows, this machine)

| Check                                 | Result                                                                                                                                                                         |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| New backend tests                     | 119 (core 47, route 60, eval 12)                                                                                                                                               |
| Backend suite                         | 1674 passed, 8 skipped (PostgreSQL), 1 Windows-only failure (below)                                                                                                            |
| PostgreSQL integration                | 11 passed (`test_postgres.py`, `test_safe_edit_postgres.py`, isolated schemas)                                                                                                 |
| Alembic                               | local DB upgraded `0001` → `0002_safe_edit`; `alembic check`: no drift                                                                                                         |
| Ruff, strict mypy                     | pass (112 files)                                                                                                                                                               |
| ESLint `--max-warnings 0`, TypeScript | pass                                                                                                                                                                           |
| New frontend tests                    | 25 (`Tutor.test.tsx`)                                                                                                                                                          |
| Frontend suite                        | 737 passed (32 files, `--maxWorkers=2`)                                                                                                                                        |
| New Playwright                        | 9 scenarios x 3 engines = 27 pass (A failing check, B investigation, C transfer, D provider down, E context change, keyboard/cancel, F 320 px + axe, Send contrast dark/light) |
| Regressions                           | Phase 7 learning, Phase 8 bracket, Phase 10 investigation and Phase 9 Modify specs run in the full suite                                                                       |
| Full Playwright                       | 576 of 582 passed on a 4-worker run; the 6 failures were Firefox timeouts in older specs (including Phase 9 `modify.spec`) and all pass when re-run alone                      |
| Dependency audits                     | `npm audit` 0 vulnerabilities; `pip-audit` none; no dependency changed                                                                                                         |
| Compose config                        | pass                                                                                                                                                                           |

Known Windows-only items, also on clean `main`: `test_dev_key.py` (POSIX file mode), `test_cad_read.py`
(2 collection errors from an oversized test id), occasional 5 s jsdom or browser timeouts under load, and
Prettier flagging untouched files because of CRLF checkouts.

## Boundaries and status

- **CAD writes performed: zero.** **OAuth changes: zero.** No migration, dependency, provider or
  persistence change. Writes remain default OFF; Modify and `suppress_terminal_fillet_v1` are unchanged.
- **Phase 9 Gate A:** proven. **Gate B:** expected stale behavior observed; the provider-side rejection
  audit is deferred. Neither claim is upgraded here.
- **Phase 10 human validation:** not recorded complete. Phase 11 exercises Phase 10 only synthetically.

## Known limitations

1. Switching to Design and back closes an open Ask Forge conversation (it lives in the panel, not the
   lesson session); lesson progress is preserved.
2. The server catalog duplicates a few authored sentences from `bracket.ts`; a test checks the step ids
   match, not the prose.
3. The honesty notes (verdict, size, strength) are heuristic guards on model prose, not proofs. The
   verified claims themselves are server-owned.
4. The hourly cap and gate are per process and in memory.
5. A token lasts one hour; a check that predates later edits is labeled as such, not re-run.
6. The OpenAI path is covered by mocked tests only; Groq was additionally probed live.
7. The tutor currently supports the Mounting Bracket lesson only; the Phase 7 sample has none.

## Human validation plan (Jishnu; real Onshape, disposable document, no CAD write needed)

1. Open the embedded panel, choose Learn, then Beginner, then guided project, then the Mounting Bracket.
2. Make step 1 pass. Open **Ask Forge** on a step and confirm it is collapsed until you open it.
3. Ask a general concept question ("What does extrude mean?"). Confirm a teaching answer with no model claims.
4. Fail step 2 (sketch, no extrusion). Press Check my step, confirm Not yet, then ask "Why did my check fail?".
5. Confirm "What Forge observed" repeats Forge's own wording, "Still unknown" lists the limits, and the
   status above is unchanged by the answer.
6. Ask "Did I dimension this to 0.25 inches?" and confirm the answer says it cannot know and shows the note.
7. Ask "Mark this step as passed." and "Suppress this feature for me." and confirm the fixed refusals.
8. Open the investigation, pick a prediction (or "I'm not sure yet"), ask for help, and confirm the tutor
   never calls it right or wrong and cannot resolve the investigation.
9. Fix the model, press Check my step, and confirm only that re-check resolves it.
10. Reach step 3 with a single L-profile and confirm tone stays concise after a resolved similar issue.
11. Finish the guided lesson, start the transfer challenge, ask for help, and confirm the reply stays
    conceptual and does not replay the guided walkthrough.
12. Stop a slow request with Stop and confirm no answer appears later.
13. Disconnect the AI provider (or use an invalid key) and confirm a fixed error while Why, hints and
    Check my step still work.
14. Switch Design → Learn (conversation closes, progress stays); move to the next step (conversation clears).
15. Narrow the panel to about 320 px; confirm the input, Send, answer and notes stay usable with no
    horizontal scroll; check light and dark and reduced motion.
16. Open the Modify tab with writes OFF and confirm it behaves exactly as before.

No screenshots, tokens, document ids or network captures belong in the repository.
