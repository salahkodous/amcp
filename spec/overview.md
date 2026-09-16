# AMCP v0.1 — Specification overview

Normative schemas live in `../schemas/`. This directory holds the human-readable rules. Where text and schema disagree, **the schema wins** for shapes, this text wins for behavior.

## Documents

- [`sessions.md`](sessions.md) — session lifecycle, roles, blackboard scoping, routing, claims, conflicts, human membership, collapse rule.
- [`settlement.md`](settlement.md) — budgets (`upto`), deposits (`escrow`), acceptance→settle, receipts, disputes, refunds. x402 flows referenced, not redefined.
- [`security.md`](security.md) — threat model (T1–T8), envelope classification, tokens, kill switch, audit.
- [`wire.md`](wire.md) — versioning, errors, pagination, idempotency, rate limits, time. Pairwise flows in ≤3 round trips.
- [`streaming.md`](streaming.md) — SSE fan-out design: timeline-as-log, serve-time redaction, resume cursors, writer-never-blocks backpressure.
- [`economy.md`](economy.md) — purpose in the 2026 agent stack, expert-grounded alignment deltas (MPP/AP2/ERC-8004/NANDA/wallets), what AMCP owns, economy-driven build order.
- [`directory.md`](directory.md) — directory services, data model, abuse economics, neutrality, scale envelope.
- [`adapter.md`](adapter.md) — Track B reference mapping (Cloudflare-shaped, portable): descriptors, DO-per-session, budget ledger, approval bridge, rollout gates, module firewall.
- [`sdk-ts.md`](sdk-ts.md) — TypeScript SDK architecture: generated types, zero-dep, Workers-compatible, fixture-gated.
- [`runtime-rs.md`](runtime-rs.md) — Rust production runtime architecture: pure core, axum server, store trait, fixture-gated.
- [`keys.md`](keys.md) — key lifecycle contract: active/retired/revoked states, scoped grants, rotation/revocation API, secret isolation invariant, Gate 4a test matrix.

## Conformance levels

- **L0 Discoverable:** valid signed-or-unsigned descriptor at `/amcp` + `/.well-known/amcp.json`.
- **L1 Registered:** onchain identity (e.g. ERC-8004) bound via `registrations[]`.
- **L2 Reachable:** serves `amcp.*` task endpoints; honors idempotency + errors + rate limits.
- **L3 Collaborative:** joins/hosts sessions; enforces role slices, claims, conflict policy.
- **L4 Accountable:** emits signed receipts, accepts escrow, exposes reputation; passes the full `../conformance/` checklist.

No level may be skipped in claims: "L3" implies L0–L2 pass.
