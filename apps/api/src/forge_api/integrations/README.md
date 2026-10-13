# Integration boundaries

Phase 2 OAuth and identity live in `forge_api.auth`. Phase 4 `onshape/` adds four
allowlisted versioned CAD GET operations, strict origin/reference policy, bounded
HTTP/JSON, provider-to-Forge normalization and request-local read snapshots. The
single authenticated API projects only counts/statuses. It reuses TokenManager;
provider credentials and raw CAD remain backend-only.

No CAD mutation, OpenAI or model tool adapter is implemented. Never offer a general
HTTP or shell executor. See docs/PHASE_4_REVIEW.md for the verified official contract,
trust boundaries, schema/units limits and required live test. Phase 5 is deferred.
