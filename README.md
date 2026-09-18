# AMCP — Agent Model Context Protocol

> **`amcp/0.1` — public draft.** The wire contract is fixture-pinned and stable enough to build against; reputation weights, directory ranking, and MPP-tab mappings are explicitly versioned experiments. Nothing here is final until a non-affiliated implementation settles real tasks against it.

> **MCP gives a model tools. A2A gives two agents messages and tasks. AMCP gives the whole team — agents and humans — one room to work in, with identity, roles, budgets, and settlement.**

AMCP is the interoperability layer for the **any-agent-to-any-agent economy**: any agent can find any agent, understand what it does, negotiate work, collaborate in shared sessions alongside humans, and settle payment — with portable proof.

- **Standalone and platform-neutral.** This repo is the home of the protocol. No vendor owns it.
- **Composes, never duplicates:** A2A (messages/tasks/artifacts) · MCP (model↔tool layer) · x402 v2 (exact/upto/escrow settlement) · ERC-8004 (onchain identity/reputation anchors).
- Full rationale and design: [`spec/overview.md`](spec/overview.md) (extracted from the original design doc).

## Repo layout

```text
schemas/      Normative JSON Schemas (draft 2020-12): descriptor, contract, session, receipt, part
spec/         Human-readable spec: overview, sessions, settlement, security, wire,
              directory, adapter, streaming (+ escalation + keys designs)
examples/     Valid sample documents (each validated against its schema in CI)
conformance/  Level checklist + portable JSON fixtures + replay.py (111/111 green)
reference/    MIT reference agent (stdlib-only Python) — the spec oracle, frozen at amcp/0.1
sdk-ts/       TypeScript SDK (@amcp/sdk, zero-dep): clients + fixture replayer, 30/30 tests green
runtime-rs/   (planned) Rust production runtime for non-Cloudflare hosting
```

## Conformance (fixture-first)

Any implementation, any language, proves compatibility by replaying the fixtures:

```bash
python conformance/replay.py          # portable assertions, 77/77 vs the reference
```

The Python suites underneath (151 checks total, all green) test implementation behavior;
the fixtures test the **wire contract**. Ports MUST ship an equivalent replayer before
claiming any level. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## 5-minute quickstart (become findable)

1. Copy `examples/descriptor.minimal.json`, fill in your agent.
2. Serve it at `https://YOUR-HOST/.well-known/amcp.json`.
3. (Optional, recommended) Register an ERC-8004 identity pointing at it → you are now globally discoverable.

That's L0 readiness. L1–L4 (reachable → collaborative → accountable) are defined in `spec/overview.md` §15.

## Status

`amcp/0.1` — draft. Nothing here is final until a non-affiliated reference implementation settles real tasks against it.

## License

MIT — see [LICENSE](LICENSE).
