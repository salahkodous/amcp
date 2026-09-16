# Conformance checklist

An implementation claiming `AMCP L<n>-compatible` MUST pass every item at that level and all levels below. Levels: L0 Discoverable · L1 Registered · L2 Reachable · L3 Collaborative · L4 Accountable.

## L0 — Discoverable
- [ ] `GET /amcp` and `GET /.well-known/amcp.json` return a document valid against `schemas/descriptor.schema.json`.
- [ ] Embedded or linked A2A AgentCard parses for A2A-only clients.
- [ ] `amcp_version` present and `0.1`.

## L1 — Registered
- [ ] Descriptor `registrations[]` binds at least one external identity; binding verifies (signature / onchain read).
- [ ] Key rotation publishes `key_history`; superseded keys validate old receipts, never live auth.

## L2 — Reachable
- [ ] Task create honors `Idempotency-Key` (replay returns identical response, no fork).
- [ ] Errors match `spec/wire.md` codes; unknown members/methods never fail silently.
- [ ] Rate limits declared and enforced with `RateLimit-*` headers.
- [ ] Paid capability without contract is refused (`capability_denied`).

## L3 — Collaborative
- [ ] Join delivers role-scoped snapshot only (canary-key redaction test passes).
- [ ] Claims are atomic under concurrency (no double-claim in a 50-way race test).
- [ ] Conflict policy enforced as declared; pause freezes spend + delegation.
- [ ] Human member can approve/reject inline with timeout resolving to declared default.
- [ ] 2-member default session behaves as a plain conversation.

## L4 — Accountable
- [ ] Acceptance mints a receipt valid against `schemas/receipt.schema.json`, bound to a settlement proof.
- [ ] Unsigned/self-asserted counterparties are ineligible for paid roles (T2 test).
- [ ] Content-class parts never execute as instructions (T3 injection battery passes).
- [ ] Kill switch revokes a member session-wide within the bounded window; revocation is a signed timeline event.
- [ ] Receipts verify offline (descriptor key + settlement proof, no host callback required).
