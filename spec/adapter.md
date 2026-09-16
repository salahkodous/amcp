# Anakin adapter architecture (Track B)

Makes Anakin agents full AMCP citizens using only Track A primitives. Adapter code MUST live in one bounded module, import spec types, and pass the same conformance battery as the reference. Any Anakin-only need goes through the RFC process — no private fields, enforced by bidirectional unknown-field rejection tests.

## Mapping to Cloudflare primitives

| AMCP need | Implementation | Notes |
|---|---|---|
| Descriptor serving (`/amcp`, well-known) | Worker route over existing discovery data; edge-cached, revalidated on version bump | Superset of agent-card/catalog; never breaks them |
| Session state (ordering + blackboard + fan-out) | **Durable Object per session**: single-writer ordering, in-memory blackboard, WebSocket fan-out | The DO sweet spot; hibernation API + snapshot-to-R2 or idle rooms burn budget |
| Contracts / receipts / claims ledger | D1 tables (append-only receipts; claims with unique constraint = atomicity) | Hot budget rows: batch via `waitUntil`, shard hot keys |
| Artifact blobs | R2 with role-scoped grants, retention executed at session close | Hash-verified on read |
| Budgets (`upto` against owner caps) | Atomic decrement with floor-at-zero per spend event; spend events into existing metering | Overspend past ceiling is a financial bug — single decrement-and-check, always |
| Approvals / typed human input | Existing approval queue as the human-member surface; typed inputs ride the session envelope | Approval records signed, attached to task + timeline |
| Reputation ingest / display | Receipts table feeds the general directory; no Anakin-private score silo | Portable receipts or it didn't happen |
| Semantic capability search | Directory service (Track A), not the request path | Worker CPU walls forbid embed/rerank inline |

## Rollout (flag-gated, in order)

1. Descriptors served (read-only, zero risk).
2. Join external sessions (scoped reads, outbound claims).
3. Host mixed sessions (ordering + redaction live).
4. Budgets + escrow against owner caps (money moves — audit on).
5. Receipts + reputation ingest (economy closes).

Each gate has a metric: redaction-canary rate, claim-race pass, dispute rate, settlement-reconciliation 100% (every receipt ↔ facilitator proof, daily job).

## Module firewall (how Track B stays honest)

- Adapter code lives in **one bounded module** (`src/amcp/`) importing `sdk-ts` — never vendored copies, never framework-coupled protocol logic.
- **Bidirectional unknown-field rejection tests:** the adapter rejects protocol documents with unknown fields AND the SDK rejects adapter-emitted documents with Anakin-private fields. Either direction failing means the firewall is breached.
- **Fixture replay in Anakin CI:** every rollout gate replays `conformance/fixtures/*.json` against the adapter's routes. A gate that passes without fixtures is theater.

## Production hazards (stack-specific)

- **DO cost at scale:** 10k sessions × 15 members needs hibernation + snapshot discipline; load-test fan-out first.
- **D1 contention:** hot claims/budget rows shard or batch; never read-then-write money.
- **Secret hygiene:** session grants in envelope-vault pattern; never plaintext in DO storage.
- **Kill switch drills:** member revoke, directory delist, budget freeze rehearsed before external counterparties arrive; dispute pipeline staffed before external settlement.
