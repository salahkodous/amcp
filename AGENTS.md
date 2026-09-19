# AGENTS.md — instructions for AI contributors

You are contributing to a **wire-first protocol repository**. The norms below
are load-bearing; violating them breaks cross-implementation compatibility.

## The doctrine (non-negotiable)

1. **Fixtures first.** `schemas/` + `spec/` + `conformance/fixtures/` +
   `conformance/vectors/` are normative; code is commentary. Protocol changes
   need fixtures (or vectors) BEFORE implementation. A behavior without a
   fixture is a rumor.
2. **Ports prove, never trust.** Every implementation (Python reference, TS
   SDK, future runtimes) must replay the fixtures/vectors. If your change
   alters an expected value, you must justify a new protocol version, not
   edit the expectation quietly.
3. **Reference stays boring.** `reference/` is stdlib-only Python, optimized
   for readability. Performance belongs in `runtime-rs/`; ergonomics in
   `sdk-ts/`. If your change makes the reference harder to read, it goes
   elsewhere. (See CONTRIBUTING.md §4.)
4. **Money is integers.** Micro-USDC + scale parity, proven by
   `conformance/vectors/money.json`. Never introduce float arithmetic on
   money paths. Never invent a new money format.
5. **Experimental stays weight-zero.** Reviewer-graph and clustering signals
   are computed and reported, never ranked — until real adversarial data
   promotes one, with a versioned rationale.
6. **No vendor fields on the wire.** The `x-anakin-*` rule generalizes: no
   implementation-specific extensions in shared schemas without a spec
   section and fixtures.
7. **Absence ≠ zero.** Missing evidence/history scores as absent (excluded),
   never as failure. Newcomers rank on trials, not on punishments for having
   no past.
8. **Determinism is testable.** Same inputs → same outputs on every runtime.
   Timestamps, randomness, and wall-clocks in tests must be pinned or
   injected. Tests depending on the current date are bugs.

## Workflow

- Small slices: one primitive or one fixture file per change. Reference →
  SDK → adapter order for behavior; spec + fixtures lead, code follows.
- Run the proofs before claiming done: `python conformance/replay.py`, the
  `reference/test_*.py` suites, `npm test` + `npm run check` in `sdk-ts/`.
- Keep README counts honest: fixture totals, suite totals, SDK test counts
  are load-bearing documentation. Update them in the same commit.
- Never commit secrets. Never invent URLs. Verify by execution, not by
  assertion.

## What good looks like

The dispute package (`spec/disputes.md` + `conformance/fixtures/dispute*.json`
+ `reference/disputes.py` + SDK client) is the reference example: design doc
first, fixtures second, three implementations third, counts updated fourth.
