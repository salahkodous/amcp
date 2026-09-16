# Wire hygiene

Small rules, mandatory for "AMCP-compatible" claims.

- **Versioning:** `amcp_version` in every envelope. Additive = minor. Breaking = major + 90-day dual-serve. Capability schemas pinned by hash at contract time; drift pauses the task pending re-accept.
- **Errors:** `{error: {code, message, retryable, doc}}`. Registered codes: `unknown_agent`, `unknown_capability`, `capability_denied`, `terms_rejected`, `negotiation_failed`, `budget_exceeded`, `approval_timeout`, `artifact_rejected`, `settlement_failed`, `rate_limited`, `idempotency_replayed`. Never silent degradation.
- **Pagination:** `{data, pagination: {next_cursor, has_more}}`. Limits 1–100, default 20.
- **Idempotency:** mutating calls accept `Idempotency-Key`; 24h same-response replay. Retries safe by default — paid operations especially.
- **Rate limits:** declared per capability; `RateLimit-*` + `Retry-After` on responses; `429` is retryable by definition.
- **Time:** ISO-8601 UTC on the wire; timezones at the human-display layer only.
- **Transport:** HTTPS+JSON primary (A2A-compatible subset), SSE/WebSocket for streams. `amcp.*` JSON-RPC methods: `session.create/join/message/claim/pause`, `contract.propose/counter/accept`, `approval.decide`, `settlement.receipt`, `directory.search`.
- **Simplicity guard:** pairwise flows complete in ≤3 round trips. Ceremony scales with membership only.
