# SDK tiers: how languages join (and graduate)

A standard is measured by independent implementations. AMCP grows languages
the way MCP grew SDKs: explicit tiers with explicit gates — never a pile of
half-maintained clients.

## Tier 0 — the oracle (not an SDK)

`reference/` (stdlib-only Python). Frozen readability; defines correct
behavior. Everything else proves against it. Tier 0 never "releases" — it
*is* the definition of done for everyone else.

## Tier 1 — maintained

Criteria: full fixture replay green in CI, vectors enforced, drift tripwire
against `schemas/`, versioned releases, maintained by this repo.

| SDK | Status |
|---|---|
| TypeScript `@amcp-protocol/sdk` (npm) | Tier 1 since v0.1.0 |

## Tier 2 — community ports

Any language may claim Tier 2 by satisfying, in CI, all of:

1. **Replay every fixture** in `conformance/fixtures/*.json` green against
   a live reference (spawn it like `replay.py` does, or target a URL).
2. **Enforce every vector** in `conformance/vectors/*.json` (money,
   reputation, delegation, verification — exact equality, stated tolerances).
3. **Schema drift tripwire**: every `required` field of every normative
   schema exists in the port's types (mirror `test/schema-drift.test.ts`).
4. **Zero silent fallback**: crypto and money paths fail closed and loud
   (the dev-key and Illegal-invocation incidents are the template for what
   must never recur silently).

Candidates (tracked, not promised): Go client, Rust runtime (`runtime-rs/`
design is the prerequisite, done), Python client library (reference is an
agent, not an importable lib — a client wrapper is a real gap), shell
replayer (`conformance/replay.sh`, curl+jq, for dependency-free verification).

## Tier promotion

Tier 2 → Tier 1 requires: sustained maintenance (responds to fixture
changes within one release), adoption evidence (real tasks settled, not
demos), and a maintainer sponsor. Promotion is declared in this file, not
in marketing copy.

## What tiers are NOT

- Not quality grades for users to comparison-shop. They describe
  *maintenance and proof*, nothing else.
- Not permission to fragment the wire. Tier 2 ports MUST NOT extend
  schemas; proposals come back here as fixtures first.
