# runtime-rs: detailed implementation design

Companion to spec/runtime-rs.md (architecture). This doc is the build order: what to write first, what proves each step, what not to build. No code lands without its fixture proof.

## 0. Ground rules

- **Fixtures are the spec.** Every behavior below names the fixture file or vector file that proves it. A green `cargo test` without replay parity is theater.
- **Port semantics, never transliterate.** The TS `Room` and Python reference are oracles for edge cases, not templates. Money = integer micro-USDC (`i64`) + scale tracking, proven by `conformance/vectors/money.json` (already enforced on both existing implementations).
- **No runtime dependency that isn't justified in one sentence here.**

## 1. Build order (each step replay-green before the next)

1. **amcp-core (pure, no I/O):** canonical JSON (byte-parity with `canonicalJson`, pinned by TEST_VECTOR signature bytes), envelope guards, `AmcpError` taxonomy, Ed25519 verify (`ed25519-dalek` — the one justified dep: memory-safe crypto no one should hand-roll), amount parse/scale/print vs `money.json`.
2. **amcp-replay:** fixture replayer over `conformance/fixtures/*.json` (capture/substitution/`identical_to`/`absent`/indices — the full matcher set, ported from `replay.py`). It runs against a base URL, so it tests the server from step 3 onward AND cross-checks other implementations.
3. **amcp-server skeleton:** axum routes mirroring the reference surface; in-memory state; replay `l0-l2.json` green.
4. **Sessions:** port Room semantics (roles, scoped snapshots, routing, claims, budgets with scale parity, lifecycle, negotiation, escalation/decide/appeal, decision policy + approvals, SSE replay endpoint). Replay `sessions/negotiation/escalation` fixtures green. Claim race: 50 tokio tasks, exactly-once (the L3 checklist race the Python suite can't run).
5. **Keys + streaming:** `/amcp/keys`, envelope signing, SSE live-tail with broadcast channels + resume cursors. Fuzz targets on envelope parsing + amount parsing from week one (parsers are where protocol CVEs live).
6. **amcp-store:** trait (`sessions/get-put`, `receipts/append`, `idempotency`, `evidence`) + SQLite impl (`sqlx` or `rusqlite` — pick at build time, one sentence justification) + Postgres impl. All prior replays re-run against SQLite; parity is the migration proof.
7. **Hardening:** `cargo fuzz` nightly, `clippy -D warnings`, Docker image (distroless), Prometheus metrics on money paths, kill-switch runbook commands.

## 2. Money (the sharpest edge)

`i64` micro-USDC + `u8` scale, mirroring the TS room exactly: input scale preserved, sums take max scale, print with exactly scale decimals. `money.json` cases/sequences/invalid are unit tests in `amcp-core` — any divergence from Python/TS fails the build. `i64` range (≈$9.2T) exceeds any sane ceiling; overflow is `budget_exceeded`, never wrap.

## 3. What not to build

Admin UI, multi-region replication, the directory (separate service, separate scaling envelope), MPP tabs (adopt the protocol when stable, per spec/economy.md), platform disbursement, an ORM (SQL is the portability seam — the store trait speaks SQL-shaped operations, never objects).
