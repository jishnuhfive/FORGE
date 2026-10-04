# Roadmap

Advance only with explicit phase authorization. Security, tests, deterministic
verification, documentation, and maintainability are requirements of every phase.
Later hardening does not defer security for earlier live integrations.

| Phase | Scope and completion gate                                                                                      |
| ----- | -------------------------------------------------------------------------------------------------------------- |
| 0     | Repository foundation: reproducible scaffold, docs, tools, tests, database health, local Git                   |
| 1     | UI foundation: narrow-panel accessible layout and presentation system; no fake integrations                    |
| 2     | Onshape OAuth: secure state, server sessions, encrypted tokens, refresh/logout/disconnect tests                |
| 3     | Onshape extension shell: real embedding, messaging and selection security, browser/session compatibility       |
| 4     | Onshape REST client: official APIs, response contracts, permissions, retries and rate limits                   |
| 5     | CAD inspector: real read-only document/Part Studio/assembly evidence                                           |
| 6     | Read-only AI agent: backend Responses API, strict read tools, bounded budgets, streaming                       |
| 7     | First real CAD write: user-approved constrained operation, target/version gate, verified editable geometry     |
| 8     | CAD tool library: high-level allowlisted operations, bounds/units/authorization, failure reconciliation        |
| 9     | Reality Lock inventory: component availability, dimensions and manufacturing capabilities                      |
| 10    | Assemblies and mates: supported instances/mates verified through official APIs                                 |
| 11    | Validation engine: deterministic PASS/WARNING/FAIL/UNVERIFIED checks and evidence                              |
| 12    | Full agent execution loop: understand/inspect/plan/approve/execute/reinspect/validate/revise/report            |
| 13    | Modify mode: selection-aware approved changes and context freshness                                            |
| 14    | Learn mode: clear CAD/engineering teaching grounded in supported operations                                    |
| 15    | Camera slider flagship demo: approved design using supplied inventory and at least 400 mm travel               |
| 16    | Product/account/history polish: useful user-facing plans/actions/results, data deletion and account controls   |
| 17    | Security hardening: adversarial assessment, production policy, privilege and data boundary review              |
| 18    | Reliability/evaluation suite: provider failure, limits, regressions, manufacturing and write-safety evaluation |
| 19    | Production deployment: HTTPS, managed secrets/database, images, migrations, backups, observability             |
| 20    | Onshape App Store preparation: current official launch checklist and review requirements                       |

Phase 0 is preserved in commit `2b68754`. Phase 1 implements the accessible UI
foundation, local preferences and development-only synthetic previews. Live
functionality described by later phases remains planned. Phase 2 now implements Onshape OAuth, identity persistence, encrypted refresh tokens,
revocable sessions, CSRF and account UI. Automated verification is recorded in
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md); real OAuth requires human credential setup.
Phase 1 remains preserved in `31f545a`. Phase 3 has not begun. The flagship camera-slider example is a future evaluation scenario,
not a generated design or promise that all engineering constraints can be certified.
Forge v1 targets education, makers, low-risk prototypes, and student engineering.
