# AMCP: the full picture

This is the thinking behind the protocol, kept next to the code it produced.
For the operational record (topology, incidents, runbook) see the private
adapter's `STATUS.md`. For the contract itself, start at `spec/overview.md`.

## 1. The problem

Models got tools (MCP). Agents got messages (A2A). Money got movement (x402).
Identity got anchors (ERC-8004). What nobody built is the room where
**strangers transact**: any agent finds any agent, understands what it does,
negotiates work, collaborates alongside humans, settles payment — with
portable proof that survives leaving any single platform.

Platforms will always offer this inside their walls. AMCP exists so it works
**between** walls. The test of every design decision below: does it still
hold when the counterparty runs different code, on different infrastructure,
with different incentives?

## 2. Positioning: compose, never duplicate

- **MCP** is the model↔tool layer. AMCP never defines tools.
- **A2A** is messages/tasks/artifacts between agents. AMCP consumes that
  shape where it fits and adds what A2A lacks: sessions, budgets, humans,
  settlement, receipts.
- **x402 v2** moves the money (exact/upto/escrow). AMCP never moves money —
  it records the decision, binds the receipt to the settlement proof, and
  projects evidence. The economy composes with the existing facilitator
  rather than forking it.
- **ERC-8004** anchors identity and raw reputation onchain. AMCP reads it as
  evidence; it does not re-implement it, compete with resolvers (NANDA,
  DNS-AID), or treat raw chain values as scores.
- **MPP session tabs** (the `upto` future): adopt the stable protocol when it
  lands; never pre-implement someone else's draft.

If a capability already has a home, AMCP references it. New protocol surface
is a cost paid only when nothing existing carries the semantics.

## 3. The core thesis

Strangers transact on **proof, not promises**. Three proofs, each portable:

1. **Settlement receipts** — work happened, money moved, both sides signed.
   Costs real money to fake, which is the entire Sybil budget.
2. **Decision integrity** — every constrained action (spend, approve, deny,
   appeal) is attributable, threshold-gated, and receipted. Default-deny;
   pending is a first-class state (202), never a silent drop.
3. **Versioned reputation** — a weighted composite over public evidence with
   pinned weights and a version string. Weight changes ship as v2, never
   silently. Anything experimental is computed, published, and given
   **weight zero** until it meets real adversarial data.

## 4. Decisions and why

**Wire-first, fixtures-first.** Schemas + spec + fixtures + vectors are
normative; code is commentary. Any implementation in any language proves
itself by replaying the fixtures. This is what makes a future Rust runtime a
porting exercise instead of a redesign, and what lets independent directories
compare rankings instead of vibes.

**Frozen readable oracle.** The Python reference is stdlib-only and optimized
for readability, not speed. Performance belongs in other runtimes; ergonomics
in the SDK. If a change makes the reference harder to read, it goes elsewhere.

**Integer money with scale parity.** Floats are a bug class, not a format.
Micro-USDC integers plus preserved scale, proven byte-identical across
implementations by shared vectors. The vectors caught real divergences
(NaN handling, over-permissive formats) before any third implementation existed.

**Evidence keyed by immutable source identity.** Retries, overlapping RPC
ranges, redeploys, and cron overlaps must be physically unable to mint a
second reputation event. Idempotency is a schema property (`source` +
`source_key`), not a prayer.

**Revocation removes the contribution, keeps the audit.** A revoked feedback
stops counting but stays visible, and reliability penalizes churn. Retraction
is not a clean slate — that single rule defuses most reputation gaming.

**L0 is lookup-only.** Unverified descriptors are servable by direct address
and invisible to discovery. No query flag, no rank path, no exception can
promote an unverified agent. Liveness is proven by an isolated prober, never
by the serving worker (submitted URLs are an SSRF surface by definition).

**Audit everything, rank only the understood.** Raw chain feedback is
preserved (`scoreable=false`) but never scored. An untyped event must not
become an implicit failed review just because no ranking profile understands
its tag yet. This is the line between a transparent ledger and a gossip engine.

**Reviewer graphs logged from day one, judged never (yet).** Every receipt
emits reviewer→agent fuel. Unique reviewers, overlap density, burst windows
are computed and published — and excluded from rank. Clustering stays
experimental until it has met abuse. Anyone selling Sybil-proofing without
adversarial data is selling something.

**Humans are members, not overseers.** Escalation routes to roles, approvals
pend through the same queue as spends, and the room state machine treats a
human message like any member message. The approval bridge (not a side
channel) is what makes mixed teams auditable.

**Settlement availability outranks directory freshness.** Receipt→evidence
projection is asynchronous and replay-safe. The directory may lag; settlement
may not. Similarly, ranking caches are disposable — anyone recomputes them
from public evidence, which is the actual antitrust mechanism: portability
enables aggregator competition, and competition is what keeps any single
ranker honest.

**Control tower is the enterprise sale.** Metrics live on money paths
(spend, escrow, settlement), not vanity surfaces. The thing operators pay for
is Kill-switch drills, budget freezes, and dispute pipelines — rehearsed
before external counterparties arrive.

## 5. Execution strategy: risk-ordered gates

Build order followed the risk, not the demo value: deterministic keys →
constrained+attributed decisions → formalized+instrumented Sybil posture →
directory and discovery. Each gate shipped with its test matrix green before
the next began, so the system was always in a releasable state. Production
rollout repeated the pattern: database first, secrets second, code third,
probes last — with unsafe infrastructure (crawling, liveness) deliberately
split into an isolated service whose compromise yields at most stale flags.

## 6. Production lessons (distilled)

- Migration journals are state: out-of-band DDL without journaling poisons
  every later apply. Verify remote schema + journal before forcing anything.
- Runtimes differ where it hurts: Node allows method-called `fetch`, the edge
  throws. Test with adversarial stubs that enforce the stricter semantics.
- Providers differ where it hurts: public RPCs cap `eth_getLogs` ranges;
  chunk small, since chunking is only slower, never wrong.
- Secrets are write-only: design diagnostics that never need to read them
  (shape validation offline, always-on summary logging, state-as-instrument).
- Sampled logs mislead: at 10% head sampling, absence of a log line proves
  nothing. The durable state (cursors, tables) is the instrument.
- Split topologies beat heroic repairs: when platform state is poisoned, a
  fresh worker with a `script_name` binding routes around it — and the blast
  isolation is worth keeping afterward.

## 7. What “done” looks like from here

- A second, independent ranker consuming the same evidence (aggregator
  competition begins; portability proves itself).
- Semantic retrieval shadowing BM25 with recall checks before any switch —
  the index must never silently change eligibility.
- `runtime-rs/` graduating from design to implementation once a toolchain
  appears, replay-green from day one.
- Reputation v2 only when adversarial data promotes a signal — with the v1
  vectors frozen as the regression floor.
- The reference unfreezing only for clarity, never for cleverness.

## 8. Open questions

- Who runs the first directory nobody owns, and what makes operators trust
  a ranker they didn't write? (Candidate answer: because they can recompute it.)
- Which abuse pattern first justifies promoting a clustering signal — and who
  decides the bar?
- What is the minimum viable MPP-tabs mapping that doesn't fork the wire?
- How small can the trusted core stay while the ecosystem grows around it?

The project is done when strangers settle real tasks on proof neither side
can forge, through implementations neither side controls. Everything else is
scaffolding.
