# Rust runtime architecture (`runtime-rs/`)

The production server for non-Cloudflare hosting: sessions at scale, persistent connections, real persistence. The Python reference stays the readable oracle; this is the machine that earns trust with uptime.

## Crate layout

```text
runtime-rs/
  amcp-core/     Wire types generated from schemas/*.json (typify),
                 canonical JSON, envelope guards, Ed25519 (ed25519-dalek),
                 error taxonomy. No I/O. No async. Pure + fuzzable.
  amcp-server/   Axum routes mirroring the reference surface; per-session
                 task-per-room fan-out (tokio broadcast), cursor-indexed log.
  amcp-store/    Storage trait (sessions, receipts, idempotency, evidence) +
                 SQLite impl (single-node) + Postgres impl (fleet). The trait
                 is the portability seam: Cloudflare DO/D1/R2 is one more impl,
                 never a fork.
  amcp-replay/   Fixture replayer over conformance/fixtures/*.json — runs in
                 CI against a live server. Claiming a level without it is void.
```

## Why this shape

- **`amcp-core` has no I/O** so the security-critical code (redaction, verification, envelope classification) is unit-testable and fuzzable without a network. Fuzz targets on `envelope` + `verify` from week one — parsers are where protocol CVEs live.
- **Axum + Tokio** for the fan-out math the reference punts on: thousands of rooms × dozens of members, broadcast channels per room, backpressure by dropping slow readers with resume cursors (same semantics as the reference SSE, real machinery underneath).
- **The store trait is the anti-fork device.** SQLite for the developer running one node, Postgres for the fleet, DO/D1/R2 for Cloudflare — all behind one trait, all proving the same fixtures. A deployment never justifies protocol drift.
- **Ed25519 from the start, no dev mode.** `ed25519-dalek` + the fixed test vector pinned in `amcp-core` tests. There is no HMAC fallback to leak into production.

## Ops posture

Single static binary, SQLite default (works on a VPS in minutes), Postgres via one env var. Structured logs keyed by session/negotiation/escalation ids so disputes are greppable. Prometheus metrics on the money paths (spend rate, escrow open, settlement lag). Kill-switch drills ship as documented runbook commands, not wiki hopes.

## Definition of done

All 70 fixtures replay green against `amcp-server` in CI; `cargo fuzz` runs nightly on core parsers; a two-node Postgres deployment passes the 50-way claim-race from the L3 checklist. Only then does anyone call it production.
