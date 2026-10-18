# Hackathon Modify B1: Natural-Language Planner

B1 turns one natural-language Modify request into an authoritative A1 plan **preview**.
It stops there. B1 never approves, executes or writes CAD. Approval stays a separate,
human-only action (A1 `plan_service.approve`), which B2 will surface.

## Pipeline

`POST /api/modify/plan` with `{context, request}` and nothing else:

1. Auth, same-origin, CSRF, closed JSON schema, 8 KiB body cap, request 1-512 chars,
   no control characters. Write capability and AI must be configured. Per-user hourly
   cap (30) plus the shared one-in-flight/5 s cooldown gate.
2. A deterministic pre-screen refuses obvious non-plans (delete, create, holes,
   assemblies, lofts, FeatureScript, API/payload talk, strength or optimization) with
   `unsupported_request`. No CAD read and no model call happen.
3. A fresh A1 `discover()` produces the server-owned `target_catalog` and the opaque
   target handles.
4. The planner model sees only a minimal catalog: opaque handle, display label, feature
   type, position and supported operations. It returns a flat strict JSON wire plan.
5. The server validates it (below) and builds the A1 `SemanticPlan` itself, using the
   server-owned `target_catalog`.
6. A1 `prepare()` re-reads the model and returns the authoritative `PlanPreview`
   (digest, expiry, per-operation before/after). The response is a clarification or
   `{"outcome": "plan", "preview": ...}`.

## Trust model

- **The model is not an authority.** It has no tools. It can choose catalog handles and
  semantic values only; it cannot name a catalog, a feature id, a microversion, a URL, a
  method, a payload or FeatureScript. Extra fields fail the strict schema.
- **A1 `prepare()` is the authority.** B1 imports exactly `discover` and `prepare`. A
  test asserts no planner module references `approve`, `SafeEditClient`, evidence, the
  edit registry, resolved operations, stored plans, write records or fences, and that
  `approve` and the client write methods raise if called (they are never called).
- **The browser sends only context and text.** It cannot send a catalog, handles,
  operations, a provider or an approval flag. Clarification choices contain only label,
  feature type and position, never handles.
- Feature names are untrusted data, delivered in a labelled catalog block. The request
  is delivered as a separate untrusted message.

## Server validation of model output

Unknown handle, operation unsupported by that target, missing or extra fields for the
operation, an invalid quantity (`N mm`/`N in` only) or an invalid rename (A1's own
validators) are model errors: `502 plan_unavailable`, nothing forwarded to A1. Min 1,
max 5 operations. Same field of the same target requested twice with different values is
a `contradictory_request` clarification; an exact repeat is dropped. Duplicate labels,
several same-type candidates without a name or locator, and ordinals ("final fillet",
"first extrude") that contradict the chosen target become `ambiguous_target`
clarifications with display-only choices. Clarification reasons are server-owned codes,
not model prose.

## Providers

Reuses the operator-selected provider only (Groq `openai/gpt-oss-120b` by default, or
OpenAI Responses), the shared transport, budgets and error mapping. One strict
structured request, no tools, no retry, no fallback, no new vendor. The wire schema is
flat with `$ref` inlined so strict mode is identical on both. The prompt, catalog, CAD
names and model output are never logged. Because the CAD cooldown gate runs after
`discover`, the server waits out the remaining cooldown (at most 6 s) before `prepare`.

## Errors

`400 invalid_request`, `401`, `403 csrf_failed`/`write_disabled`, `413`,
`429 rate_limited`/`request_in_progress`, `503 not_configured`/provider unavailable,
`504 timeout`, `502 plan_unavailable` (unusable model output), and A1's own codes
(`model_changed`, `context_changed`, `unsupported_target`, ...) propagated unchanged.

## Verification

75 deterministic tests (`apps/api/tests/test_modify_planner.py`): the 31 core scenarios,
route, auth/CSRF, closed-schema and size tests, both providers, injection (request and
feature name), authority spies and privacy checks. A one-off synthetic Groq probe
(invented catalog, no CAD, no Onshape, no approve) confirmed the strict schema is
accepted and returns plans and clarifications. Real Onshape writes: zero.

## Known limitations

Only the five A1 operations. No creation or deletion of features, sketches, holes,
assemblies, mates, lofts or sweeps; no general parameter editing, FeatureScript,
geometry generation or optimization. Suppression is limited to the terminal fillet.
Ambiguity detection is conservative and heuristic; A1 still revalidates everything.
A model refusing a valid request is possible and shows as a clarification. No B2 UI
exists yet, so nothing in the interface calls this route.
