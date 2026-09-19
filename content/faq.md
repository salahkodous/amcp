# AMCP FAQ

## Is AMCP production-ready?

It's a versioned draft (`amcp/0.1`), honest about it. The wire contract is
fixture-pinned (131/131 green across implementations) and runs in a live
production deployment. Reputation weights, ranking profiles, and frontier
pieces are explicitly versioned experiments. Adopt the pinned parts;
watch the experimental ones.

## Who owns AMCP?

Nobody. The repo is MIT-licensed, platform-neutral, and designed so any
party can implement, rank, adjudicate, or directory-build independently.
Portability isn't a feature — it's the antitrust mechanism.

## How is trust established for a brand-new agent?

Through trials, not claims: cheap verifiable work beats prose. Absent history
scores as absent (excluded from composites), never as failure. The directory
ranks newcomers on what they prove, starting at L0 lookup-only.

## What stops Sybil attacks on reputation?

Economics, not cleverness: settlement-backed receipts cost real money per
fake identity; reviewer graphs and burst detection run as published,
weight-zero instrumentation until adversarial data promotes them. Anyone
claiming Sybil-proofing without adversarial data is selling something.

## Why not build this on A2A/MCP directly?

Different layers. A2A moves messages; MCP moves tool context; neither knows
about budgets, escrow, receipts, or disputes. AMCP references both instead
of re-implementing either. See `content/amcp-vs-mcp-a2a-x402.md`.

## Does AMCP move money?

No. It composes with x402 facilitators for movement and records
authorization linkage, contracts, receipts, and escrow-ledger state. A
payment can be valid on the rails and unauthorized by the principal — AMCP
exists precisely to tell those cases apart.

## What happens when something goes wrong?

The dispute lifecycle: file a claim → bind evidence by hash → respondent
answers → arbiter adjudicates (tiers escalate, clocks bound silence) →
pre-committed hooks enforce (e.g. escrow refund). Every step signed,
replayable, and portable across implementations.

## How do humans stay in control at scale?

Through bounded authority, not per-transaction approval. Humans define
consent policy and delegation limits once; agents operate inside them;
exceptions escalate with signed decision receipts. See VISION.md §8.

## How do I implement AMCP?

1. Read `spec/overview.md`, then the primitive spec you need.
2. Replay `conformance/fixtures/*.json` against your implementation.
3. Check `conformance/vectors/*.json` for arithmetic parity.
4. Ship your own replayer before claiming compatibility.
5. Python: copy patterns from `reference/`. TypeScript: `npm install @amcp-protocol/sdk`.

## How do I contribute?

Fixtures first (see CONTRIBUTING.md), AI contributors start at AGENTS.md,
vulnerabilities go private per SECURITY.md. The fastest contribution is a
failing fixture that proves a real gap.
