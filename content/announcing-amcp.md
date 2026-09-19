# Introducing AMCP: proof, not promises, for the agent economy

*Cross-post to dev.to / Hashnode / Medium. Tags: agents, ai-agents, protocols,
open-source, typescript, python, web3, x402.*

Models got tools. Agents got messages. Money got movement. But when an agent
hires another agent across organizational boundaries, nobody standardizes what
happens: who authorized whom, under what bounds, with whose money, with what
proof — and what happens when it fails.

Today we're open-sourcing **AMCP, the Agent Model Context Protocol**: the
interoperability layer for the any-agent-to-any-agent economy.

## The hole

An economic transaction between autonomous participants is larger than any
existing primitive:

```text
find → understand → identify → assess trust → negotiate → authorize →
commit → pay → execute → verify → receive evidence → settle →
handle failure → update reputation
```

MCP covers agent↔tool. A2A covers agent↔agent messaging. x402 covers payment
movement. ERC-8004 anchors identity. None covers the *transaction* — the
machine-readable commercial relationship with authorization, proof, and
recourse. That's the hole AMCP occupies. It composes with all four; it
duplicates none.

## What ships today (amcp/0.1, MIT)

- **The wire contract**: JSON Schemas + human spec + **131 portable
  conformance fixtures** + shared vectors (money, reputation, delegation,
  verification). Any implementation in any language proves itself by replay.
- **Reference oracle**: stdlib-only Python, frozen for readability.
- **TypeScript SDK**: `npm install @amcp-protocol/sdk` — zero runtime deps,
  works on Node 20+ and Cloudflare Workers.
- **A live production deployment** settling the design against reality:
  directory with chain-ingested reputation, session rooms, escrow ledger,
  signed decision receipts.
- **Eight locked primitives**: Identity · Capability · Intent ·
  Authorization Chain · Commitment · Receipt · Evidence · Dispute.

## The ideas we're proudest of

- **Source-keyed evidence**: retries and overlapping crawls physically cannot
  mint a second reputation event. Idempotency is a schema property.
- **Absent ≠ zero**: newcomers rank on trials, never punished for having no
  past. Revocations penalize churn without rewriting history.
- **Consent as a control plane**: humans define authority boundaries once;
  agents operate inside them; exceptions escalate with signed decision
  receipts. Millions of transactions, zero human bottlenecks.
- **Experimental signals at weight zero**: reviewer graphs and clustering are
  computed, published, and unranked — until adversarial data promotes them.
- **Disputes as a first-class lifecycle**: claim → adjudicate → enforce, with
  escrow hooks and portable evidence. A protocol without a failure vocabulary
  outsources every conflict to support tickets.

## Proof, not promises

Every claim above replays green: 131/131 fixtures, 186 reference checks,
34 SDK tests, CI on every push. The repo tells you exactly what's draft and
what's pinned.

## Get started

```bash
npm install @amcp-protocol/sdk
```

- 5-minute quickstart (become findable): README in the repo.
- Implementers: start at `conformance/`, ship a replayer, claim your level.
- Critics: the fastest way to hurt us is a failing fixture — open the issue.

AMCP is standalone and platform-neutral. No vendor owns it, including us.
If you settle real tasks against it — especially outside our stack — we want
to hear from you. That's the only graduation criterion that matters.

*Repo: https://github.com/salahkodous/amcp · Docs: README + VISION.md + spec/*
