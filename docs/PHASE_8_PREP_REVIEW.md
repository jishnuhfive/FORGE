# Phase 8A preparation review

Branch `phase8/bracket-check-step`, based on `main` at `24aaf67`.

**Phase 7 check:** absent. No `docs/PHASE_7_REVIEW.md`, no lesson domain or state
architecture, and `apps/web/src/features/Learn.tsx` is still the original static
four-step placeholder. Phase 8B is therefore not started.

## Delivered

- `docs/PHASE_8_LESSON_SPEC.md` — evidence capability map, lesson, requirement
  contract, status semantics, test vectors, alternatives, UI specification, blockers.
- `apps/api/src/forge_api/step_checks/` — isolated pure functions over the existing
  `CadInspector`. No imports from lesson or Learn code, no routes, no Onshape or AI
  calls, no persistence.
- `apps/api/tests/test_step_checks.py` — 21 tests with synthetic evidence.

## Boundaries preserved

No CAD writes, no new scopes, no AI involvement in status, no UI change, no dependency
or lockfile change, no migration.

## Checks run (Windows)

`ruff format`, `ruff check`, `mypy` (strict) and `pytest` for the new module; full
backend suite recorded in the commit message of the preparation commit.

Waiting for Phase 7 to merge.
