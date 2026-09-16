# TypeScript SDK architecture (`sdk-ts/`)

The SDK is the ecosystem on-ramp: what agent developers install. It MUST be thin — protocol logic lives in the spec and is proven by fixtures, never re-implemented by feel in the SDK.

## Package shape

```text
sdk-ts/
  src/
    types.ts      Generated from schemas/*.json (json-schema-to-ts, checked in;
                  CI fails if generated output drifts from schemas/)
    envelope.ts   Part/article builders, instruction-class guards, canonical JSON
    descriptor.ts Descriptor builder + serve helper (any framework) + keys mgmt
    receipts.ts   Offline receipt verification (WebCrypto Ed25519, no callbacks)
    session.ts    Session client: join/views with role scoping, claims, budgets,
                  negotiate, escalate, SSE stream with resume cursors
    directory.ts  Directory client: submit, search with typed filters
    errors.ts     Wire error taxonomy (one class per code in spec/wire.md)
    replay.ts     Fixture replayer (conformance/fixtures/*.json) — the gate
  test/
    fixtures.test.ts  Replays every fixture file against the Python reference
                      in CI (cross-language proof from day one)
```

## Non-negotiable constraints

- **Zero runtime dependencies.** A dependency is a supply-chain vote every downstream user must trust. Dev-deps only (build, test).
- **Runtimes: Node 20+ AND Cloudflare Workers.** No `node:*` imports in `src/` (enforced by lint); WebCrypto for Ed25519 so verification works at the edge. Anything platform-specific lives in documented adapter shims, never in core.
- **Generated types, not hand types.** `types.ts` is generated from the normative schemas. Hand-editing it is a review failure — drift between SDK types and schemas is how two protocols happen.
- **Errors are values.** Every wire code maps to a typed error carrying `retryable`, `doc`, and the raw envelope. Retries key off `retryable`, not message sniffing.
- **SSE client resumes by construction.** The stream helper persists last `seq` (caller-provided store, memory default) and reconnects with backoff+jitter. Users never manage cursors manually.

## What the SDK does NOT do

No orchestration frameworks, no agent loops, no retry-everything magic, no hosting. It speaks AMCP fluently and gets out of the way — frameworks (LangChain-style, Anakin internals) build on top.

## Definition of done

`npm test` replays all 70 fixtures green against the reference; `npm run check` proves zero runtime deps, Workers-compat, and type drift == 0. Only then does the adapter get to import it.
