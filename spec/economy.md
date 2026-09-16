# AMCP in the agent economy: purpose, landscape, implementation

## 1. Purpose

Every layer of the agent stack now has an owner except one: **the room where mixed groups of agents and humans do paid work together, and the portable proof that it happened honestly.** MCP owns tools. A2A owns messages. x402/MPP move money. AP2 proves spending authority. ERC-8004 records reputation raw material. Nobody owns multi-party sessions with humans, decision-integrity envelopes across those sessions, or receipts that stay verifiable when you leave the platform that minted them. That unowned layer is AMCP's entire reason to exist. Everything in this repo that doesn't serve it is scope creep.

## 2. The settled stack (as of September 2026)

The industry converged on composable layers, not a winner. AMCP composes with all of them and duplicates none:

| Layer | Standard | Status | AMCP relationship |
|---|---|---|---|
| Tools | MCP | Broadest adoption | Consumes; never redefines |
| Messages | A2A | Enterprise traction | Superset descriptors; x402 extension v0.2 embedding pattern adopted for contracts |
| Settlement | x402 (Linux Foundation, Jul 2026; 50M+ txns) | Production | `settlement_proof` carries x402 receipts; standalone flow supported |
| Settlement sessions | MPP, Stripe+Tempo (Mar 2026) | Rolling out via Stripe | `upto` budgets map to MPP pre-auth tabs (§4.1) |
| Checkout | ACP, OpenAI+Stripe | Fiat merchant flows | Out of scope; AMCP stops at machine-to-machine |
| Authorization | AP2, Google 100+ partners (v0.2 → FIDO governance) | Standardizing | Contracts embed mandate-style order authorization (§4.2) |
| Trust raw material | ERC-8004 (mainnet Jan 29 2026; 20k+ agents) | Live, aggregator competition 2026–27 | Directory ingests it operationally (§4.3) |
| Resolution | NANDA / DNS-AID / IETF draft (registry-assisted) | Federating | Directory consumes as resolution inputs, never competes (§4.4) |
| Wallets + guardrails | Coinbase Agentic Wallets, MetaMask Agent Wallet, Turnkey, agentwallet.ai | Shipping | Payer binding + cap hierarchy (§4.5) |

## 3. Expert facts that changed this design

**F1 — Decision integrity ≠ execution integrity.** A 2026 study: indirect prompt injection achieved 100% success manipulating product rankings shown to an agent; AP2-style signatures stayed cryptographically valid throughout. *Consequence:* signatures prove authorization, never judgment. AMCP's envelope classes (`instruction`/`content`/`evidence`), canary-tested redaction, and budgets-as-circuit-breakers are the decision-side controls — elevated from features to the protocol's primary security claim. *Status: built (reference + adapter firewall).*

**F2 — MPP defined the session-tab semantics.** Pre-authorized spending limit, streaming micropayments, single batch settlement ("OAuth for money"). *Consequence:* AMCP `upto` MUST be expressible as an MPP session, not a parallel invention. Budget lines gain `settlement_session` refs; batch-settle closes them. *Status: spec delta (§4.1), adapter gate 4.*

**F3 — AP2 mandate chains are the authorization vocabulary.** Intent → Cart → Payment mandates as VDCs, human-present and human-absent flows, and crucially the **Embedded Flow** pattern (order authorization envelops the payment payload, one approval prompt). *Consequence:* AMCP negotiation-accept produces an order-authorization object shaped to carry an AP2 PaymentMandate or x402 payload — never a competing mandate format. *Status: spec delta (§4.2).*

**F4 — ERC-8004 is live and its design validates ours.** Raw public signals, competing off-chain aggregators, revocations as public events, Sybil policy pushed to indexers, composite sub-scores (feedback/validation/sybil-resistance/reliability), v2 converging on x402 payment-proofs inside feedback. *Consequence:* (a) our "no canonical score" stance is now consensus — keep it; (b) the directory MUST resolve CAIP-10 identities, ingest `NewFeedback`/`FeedbackRevoked` events, honor the `x402Support` flag, and adopt tag conventions; (c) settlement-backed receipts are exactly the v2 signal direction. *Status: partially built (evidence model matches); operational ingest is a directory milestone.*

**F5 — Resolution is not search (IETF/NANDA).** Registries bind identity→endpoint and explicitly refuse to be capability-search engines. *Consequence:* the AMCP directory is search + reputation ranking OVER resolved descriptors. It consumes NANDA index, DNS-AID, AI-Catalog, and ERC-8004 registrations as resolution inputs. Competing with them would be both rude and pointless. *Status: spec delta (§4.4).*

**F6 — Wallets converged on the same control vocabulary.** Session caps (Coinbase), per-txn/daily/monthly velocity caps with approval routing (agentwallet.ai), Worker/Observer/Approver personas with default-deny (Turnkey), scoped delegation vs dedicated wallets (MetaMask). *Consequence:* AMCP roles map 1:1 to Turnkey personas (adopt the names where they don't clash); budgets gain a three-tier hierarchy (per-task cap → session ceiling → owner daily cap, enforced at the adapter); payer identity binds `agentWallet` per ERC-8004. *Status: spec delta (§4.5); owner caps = adapter gate 4.*

**F7 — The control tower is the enterprise sale.** Splunk's thesis: the battle is won on governing what wallet-holding agents do — per-agent budgets, circuit breakers, cost↔value correlation on one dashboard. *Consequence:* every AMCP money path emits observable events (spend, escrow-open, settle-lag as Prometheus metrics — already in runtime-rs design); kill-switch drills are documented runbooks, not aspirations. *Status: designed; adapter gate 4.*

## 4. Alignment deltas (normative when implemented)

- **4.1 Budgets ↔ MPP sessions.** `budget` lines accept `settlement_session` (MPP tab id); `upto` ceiling ≡ pre-auth limit; batch settlement closes the line and mints the receipt. x402 standalone flow stays for permissionless strangers.
- **4.2 Contracts embed, never invent.** `contract.acceptance` carries an order-authorization object; AP2 mandates and x402 payloads ride inside it per the Embedded Flow pattern. One approval prompt, two signatures max.
- **4.3 Directory ingests ERC-8004.** Resolution: CAIP-10 → registration file → descriptor. Evidence: `NewFeedback` (+tags), `FeedbackRevoked` (reliability penalty, never silent drop), validation responses, `x402Support` as a search filter. Tag conventions adopted, not forked.
- **4.4 Directory resolves via NANDA/DNS-AID/AI-Catalog.** Resolution inputs are pluggable; AMCP MAY publish descriptors where those systems look (well-known paths) but MUST NOT require its own resolution step when a DNS-anchored path exists.
- **4.5 Wallets + caps.** Payer binds ERC-8004 `agentWallet` where present. Cap hierarchy: per-task (contract) → session ceiling (budget) → owner daily (adapter policy, approval-routed). Roles documented against Turnkey personas.

## 5. What AMCP owns (and will defend)

1. **Mixed sessions** — the only protocol object for multi-agent + human rooms with roles, scoped state, and ordering.
2. **Portable receipts** — verifiable offline, aggregator-neutral, carrying settlement proofs from any rail.
3. **Decision envelopes** — instruction/content/evidence classification with served-time redaction.
4. **Circuit breakers** — budgets, pauses, kill switches that work when authority is compromised, not just when it is absent.

## 6. Implementation order (economy-driven)

1. Directory ERC-8004 ingest (4.3) — reputation becomes real; unlocks strangers transacting.
2. Contract order-authorization embedding (4.2) — AP2/x402 counterparties can close AMCP negotiations.
3. Budget↔MPP mapping (4.1) + owner caps (4.5) — enterprise control tower story; adapter gate 4.
4. Resolution inputs (4.4) — federation; cheap once 1–3 exist.
5. Everything else waits for a counterparty that needs it.

## 7. Risks

- **Sybil discounting is unproven at scale.** Our reviewer-clustering is theory; ERC-8004 indexers are learning in public. Track their formulas, steal what works.
- **Decision integrity has no complete answer.** Envelopes + redaction + caps bound the blast radius; nothing prevents a determined principal from authorizing nonsense. Say so openly.
- **Key management is ours to lose.** Scoped delegation, rotation without downtime, instant revocation — the wallet industry's checklist is our checklist wherever AMCP touches signing.
- **Regulatory perimeter.** AP2/FIDO alignment keeps us inside the compliance tent; receipt audit trails must be court-legible, not just cryptographically valid.
