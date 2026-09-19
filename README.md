# AMCP — Agent Model Context Protocol

<p align="left">
  <img src="docs/logo.svg" width="72" alt="AMCP logo: a verified room">
</p>

[![AMCP conformance](https://github.com/salahkodous/amcp/actions/workflows/ci.yml/badge.svg)](https://github.com/salahkodous/amcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **`amcp/0.1` — public draft.** The wire contract is fixture-pinned and stable enough to build against; reputation weights, directory ranking, and MPP-tab mappings are explicitly versioned experiments. Nothing here is final until a non-affiliated implementation settles real tasks against it.

> **MCP gives agents tools. A2A gives agents communication. AMCP gives agentic work a shared context of authority, commitment, accountability, and economic settlement.**

AMCP is the interoperability layer for the **any-agent-to-any-agent economy**: any agent can find any agent, understand what it does, negotiate work, collaborate in shared sessions alongside humans, and settle payment — with portable proof.

- **Standalone and platform-neutral.** This repo is the home of the protocol. No vendor owns it.
- **Composes, never duplicates:** A2A (messages/tasks/artifacts) · MCP (model↔tool layer) · x402 v2 (exact/upto/escrow settlement) · ERC-8004 (onchain identity/reputation anchors).
- Full rationale and design: [`spec/overview.md`](spec/overview.md) (extracted from the original design doc).

## Why AMCP?

MCP gives a model tools. A2A gives two agents messages. Neither answers what happens when autonomous participants transact across organizational boundaries: who authorized whom, under what bounds, with whose money, with what proof — and what happens when it fails. AMCP standardizes exactly that: eight primitives (Identity · Capability · Intent · Authorization Chain · Commitment · Receipt · Evidence · Dispute) whose state and evidence survive across A2A, MCP, payment rails, and heterogeneous services. See [`VISION.md`](VISION.md) for the full picture.

## Install

```bash
npm install @amcp-protocol/sdk   # zero runtime dependencies
```

```ts
import { TaskClient, DisputeClient, IntentsClient } from "@amcp-protocol/sdk";

const tasks = new TaskClient({ baseUrl: "https://agent.example" });
const { receipt } = await tasks.run("score_lead", { lead: {...} },
  { idempotencyKey: crypto.randomUUID(), trial: true });
```

Python implementers start at `reference/` (stdlib-only oracle); every other language starts at `conformance/` (replay the fixtures).

## Repo layout

```text
schemas/      Normative JSON Schemas (draft 2020-12): descriptor, contract, session, receipt, part
spec/         Human-readable spec: overview, sessions, settlement, security, wire,
              directory, adapter, streaming (+ escalation + keys designs)
examples/     Valid sample documents (each validated against its schema in CI)
conformance/  Level checklist + portable JSON fixtures + replay.py (131/131 green)
reference/    MIT reference agent (stdlib-only Python) — the spec oracle, frozen at amcp/0.1
sdk-ts/       TypeScript SDK (@amcp-protocol/sdk, zero-dep): clients + fixture replayer, 34/34 tests green
runtime-rs/   (planned) Rust production runtime for non-Cloudflare hosting
```

## Conformance (fixture-first)

Any implementation, any language, proves compatibility by replaying the fixtures:

```bash
python conformance/replay.py          # portable assertions, 131/131 vs the reference
```

The Python suites underneath (186 checks total, all green) test implementation behavior;
the fixtures test the **wire contract**. Ports MUST ship an equivalent replayer before
claiming any level. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## 5-minute quickstart (become findable)

1. Copy `examples/descriptor.minimal.json`, fill in your agent.
2. Serve it at `https://YOUR-HOST/.well-known/amcp.json`.
3. (Optional, recommended) Register an ERC-8004 identity pointing at it → you are now globally discoverable.

That's L0 readiness. L1–L4 (reachable → collaborative → accountable) are defined in `spec/overview.md` §15.

## Docs

| Doc | What it answers |
|---|---|
| [`VISION.md`](VISION.md) | Why this exists; the eight locked primitives; consent as a control plane |
| [`spec/overview.md`](spec/overview.md) | Full rationale, levels, composition with A2A/MCP/x402/ERC-8004 |
| [`spec/disputes.md`](spec/disputes.md) | Claim → adjudicate → enforce failure lifecycle |
| [`spec/authorization.md`](spec/authorization.md) | Delegation chains, monotone rule, evaluation order |
| [`spec/verification.md`](spec/verification.md) | Executed acceptance, verdict objects |
| [`spec/intents.md`](spec/intents.md) | Demand-side discovery (request-for-quote) |
| [`spec/reputation.md`](spec/reputation.md) | Pinned v1 weights, weight-zero experiments |
| [`spec/economy.md`](spec/economy.md) | Cross-protocol economic research deltas |
| [`CHANGELOG.md`](CHANGELOG.md) | What shipped, per release |
| [`content/`](content/announcing-amcp.md) | Announcement, comparison vs MCP/A2A/x402, FAQ |
| [`llms.txt`](llms.txt) | AI-oriented repo index |

## Contributing & community

- Protocol changes need fixtures first; ports must ship a replayer — see [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **AI contributors** start at [`AGENTS.md`](AGENTS.md) (fixture-first doctrine, parity rules).
- Bugs in behavior → issues. Suspected vulnerabilities → private report per [`SECURITY.md`](SECURITY.md), never a public issue.
- Conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Status

`amcp/0.1` — draft. Nothing here is final until a non-affiliated reference implementation settles real tasks against it.

## License

MIT — see [LICENSE](LICENSE).
