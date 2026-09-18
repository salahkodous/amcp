# Security policy

AMCP is pre-1.0 draft software that touches money-adjacent flows (settlement
proofs, escrow ledgers, spending authority). Treat it accordingly: **do not
run pre-release AMCP code against mainnet funds you cannot afford to lose**,
and never commit secrets (see `CONTRIBUTING.md`).

## Reporting vulnerabilities

- **Do not open public issues** for suspected vulnerabilities.
- Email the maintainers privately (see commit history / repo owners for
  contact). Include: affected component, reproduction steps or proof of
  concept, and your assessment of impact.
- We aim to acknowledge within 72 hours and to ship a fix with a
  regression fixture before disclosing. Security fixes land with the same
  fixture-first discipline as features: the exploit becomes a permanent
  conformance case so all implementations inherit the fix.

## Scope notes

- The threat model lives in `spec/` (keys, adapter, directory designs).
- Decisions that move money or authority are the highest-severity surface:
  decision receipts, escrow transitions, delegation evaluation, directory
  ranking inputs.
- Test vectors and fixtures are part of the security boundary: a PR that
  weakens a vector without a versioned rationale will not merge.
