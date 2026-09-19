# Changelog

Follows the shipped state, not aspirations. Dates are commit dates (UTC).

## Unreleased (on master past v0.1.0)

- Authorization chains (authz-v1 spec + 15 shared vectors + reference/adapter evaluators).
- Verification (verify-v1 spec + subset vectors + re-run verdicts + SDK client).
- Intents demand-side discovery (spec + fixtures + reference + SDK client + adapter module).
- Transaction anchor schema (`amcp-transaction.schema.json`).
- Open-source bar: code of conduct, agent instructions, SECURITY.md, CI, social card, logo mark, content arsenal, llms.txt.
- Registry SDK consumption in the adapter; dependency tree clean-resolving.

## v0.1.0 — 2026-09-18

First public cut (draft status — see README).

- **Intents (demand-side discovery):** publish/quote/accept/withdraw lifecycle,
  lazy expiry, supersede-not-edit quotes, boolean matching. Spec, fixtures,
  reference, SDK client, adapter module + migration.
- **Verification (verify-v1):** subset-schema validator + deterministic
  re-run verdicts, signed; vectors enforced on both implementations.
- **Authorization chains (authz-v1):** monotone-delegation evaluator with
  fixed evaluation order and machine-readable reasons; 15 shared vectors.
- **Disputes + transaction anchor:** claim/respond/adjudicate/appeal/withdraw
  state machine, escrow enforcement hooks (refund_full CAS), `dispute.schema.json`,
  `amcp-transaction.schema.json`.
- **Reputation v1:** pinned weights, reviewer graphs at weight zero,
  cross-implementation vectors.
- **TypeScript SDK published:** `@amcp-protocol/sdk@0.1.0`, zero runtime deps.
- **Repo bar:** CI (replay + 11 suites + examples validation + SDK),
  SECURITY.md, code of conduct, agent instructions.

## Pre-history (private development, summarized)

- Gates 1–5: descriptors/firewall, guest joins, DO-hosted rooms, key
  lifecycle + scoped grants, owner caps + escrow + receipts, general
  directory with ERC-8004 ingest.
- Production hardening that fed back into the protocol: integer micro-USDC
  with scale parity, retained-but-unscoreable evidence, Illegal-invocation
  edge discipline, 100-block chain ranges, lazy clocks everywhere.
