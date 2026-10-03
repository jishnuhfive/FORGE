# Future integration boundaries

No Onshape or OpenAI integration is implemented. Later adapters belong behind
server-owned interfaces with strict schemas, fixed allowed endpoints, timeouts,
sanitized failures, and resource authorization. The browser/model must never receive
provider credentials or unrestricted HTTP/shell tools. See `docs/ONSHAPE.md` and
`docs/AI_AGENT.md` before introducing adapters. There are no stub success responses.
