# Integration boundaries

Phase 2 OAuth and identity live in `forge_api.auth`; only fixed token and sessioninfo
endpoints are called. CAD, OpenAI and model tool adapters remain unimplemented.
Future adapters must retain fixed high-level tools, strict schemas, timeouts,
sanitized errors and independent object authorization. Never offer a general HTTP
or shell executor. See docs/ONSHAPE.md and docs/AI_AGENT.md before adding capabilities.
